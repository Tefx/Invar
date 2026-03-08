"""
DX-56: Unified template sync engine.

Shell module: Core sync logic shared by init and dev sync commands.
Handles state detection, manifest-driven file lists, region-based updates,
syntax switching, and project additions injection.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path  # noqa: TC003 - used at runtime

from returns.result import Failure, Result, Success

from invar.core.sync_helpers import (
    SyncConfig,
    SyncReport,
    detect_region_scheme,
    get_sync_file_lists,
    should_skip_file,
)
from invar.core.template_parser import (
    format_preserved_content,
    parse_invar_regions,
    reconstruct_file,
    strip_invar_markers,
)
from invar.shell.template_engine import (
    get_templates_dir,
    load_manifest,
    render_template_file,
)

# Re-export for convenience
__all__ = ["SyncConfig", "SyncReport", "sync_templates"]


# =============================================================================
# Core Sync Logic
# =============================================================================


# @shell_complexity: Multi-path sync with state detection and region handling
def sync_templates(path: Path, config: SyncConfig) -> Result[SyncReport, str]:
    """Unified template sync engine.

    DX-56: Core sync logic shared by init and dev sync commands.

    Handles:
    1. State detection (DX-55: intact/partial/missing/absent)
    2. Manifest-driven file list
    3. Region-based updates (managed/user/project/skill/extensions)
    4. Syntax switching (CLI vs MCP)
    5. Project additions injection

    Args:
        path: Project root directory
        config: Sync configuration

    Returns:
        Success with SyncReport, or Failure with error message
    """
    templates_dir = get_templates_dir()
    manifest_result = load_manifest(templates_dir)
    if isinstance(manifest_result, Failure):
        return manifest_result

    manifest = manifest_result.unwrap()
    report = SyncReport()

    # Build variables for template rendering (LX-05: include language)
    variables = {
        **manifest.get("variables", {}),
        "syntax": config.syntax,
        "language": config.language,
    }

    # Load project additions if enabled
    project_additions = _load_project_additions(path) if config.inject_project_additions else ""

    # Get file lists from manifest
    fully_managed, region_managed, create_only = get_sync_file_lists(manifest)

    # Process fully managed files (direct overwrite)
    for dest_rel, src_rel in fully_managed:
        if should_skip_file(dest_rel, config.skip_patterns):
            continue
        # Get template type from manifest (LX-05: support jinja for fully_managed)
        template_config = manifest.get("templates", {}).get(dest_rel, {})
        template_type = template_config.get("type", "copy")
        result = _sync_fully_managed(
            path, templates_dir, dest_rel, src_rel, template_type, variables, config, report
        )
        if isinstance(result, Failure):
            report.errors.append(result.failure())

    # Process region-managed files
    for dest_rel, src_rel in region_managed:
        if should_skip_file(dest_rel, config.skip_patterns):
            continue
        result = _sync_region_managed(
            path, templates_dir, dest_rel, src_rel,
            config, variables, project_additions, report
        )
        if isinstance(result, Failure):
            report.errors.append(result.failure())

    # Process create-only files (only if not exists)
    for dest_rel in create_only:
        if should_skip_file(dest_rel, config.skip_patterns):
            continue
        if dest_rel in manifest.get("templates", {}):
            template_config = manifest["templates"][dest_rel]
            result = _sync_create_only(
                path, templates_dir, dest_rel, template_config, variables, report
            )
            if isinstance(result, Failure):
                report.errors.append(result.failure())

    return Success(report)


def _load_project_additions(path: Path) -> str:
    """Load project-additions.md content if it exists."""
    pa_path = path / ".invar" / "project-additions.md"
    if pa_path.exists():
        try:
            return pa_path.read_text()
        except OSError:
            pass
    return ""


# @shell_complexity: File I/O with multiple existence/content checks and Jinja rendering
def _sync_fully_managed(
    path: Path,
    templates_dir: Path,
    dest_rel: str,
    src_rel: str,
    template_type: str,
    variables: dict,
    config: SyncConfig,
    report: SyncReport,
) -> Result[str, str]:
    """Sync a fully managed file (direct overwrite).

    LX-05: Now supports Jinja templates for composition.
    """
    dest_file = path / dest_rel
    src_file = templates_dir / src_rel

    if not src_file.exists():
        return Failure(f"Template not found: {src_rel}")

    # LX-05: Render Jinja templates, copy plain files
    if template_type == "jinja":
        render_result = render_template_file(src_file, variables)
        if isinstance(render_result, Failure):
            return render_result
        new_content = render_result.unwrap()
    else:
        try:
            new_content = src_file.read_text()
        except OSError as e:
            return Failure(f"Failed to read template {src_rel}: {e}")

    # Track if file exists BEFORE write (for correct created/updated reporting)
    file_existed = dest_file.exists()

    # Check if update needed
    if file_existed and not config.force:
        try:
            if dest_file.read_text() == new_content:
                report.skipped.append(dest_rel)
                return Success("skipped")
        except OSError:
            pass

    # Write file (unless check mode)
    if not config.check:
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(new_content)
        except OSError as e:
            return Failure(f"Failed to write {dest_rel}: {e}")

    # Report based on pre-write existence
    if file_existed:
        report.updated.append(dest_rel)
    else:
        report.created.append(dest_rel)
    return Success("synced")


# @shell_complexity: Region-based sync with DX-55 state detection and content merging
def _sync_region_managed(
    path: Path,
    templates_dir: Path,
    dest_rel: str,
    src_rel: str,
    config: SyncConfig,
    variables: dict,
    project_additions: str,
    report: SyncReport,
) -> Result[str, str]:
    """Sync a region-managed file (update managed regions, preserve user)."""
    dest_file = path / dest_rel
    src_file = templates_dir / src_rel

    if not src_file.exists():
        return Failure(f"Template not found: {src_rel}")

    # Render template
    render_result = render_template_file(src_file, variables)
    if isinstance(render_result, Failure):
        return render_result

    new_content = render_result.unwrap()
    new_parsed = parse_invar_regions(new_content)

    # Detect region scheme
    region_scheme = detect_region_scheme(new_parsed)
    if region_scheme is None:
        return Failure(f"No region markers in template: {src_rel}")

    primary_region, user_region = region_scheme

    # Handle new file
    if not dest_file.exists():
        return _create_new_region_file(
            dest_file, dest_rel, new_content, new_parsed, project_additions, config, report
        )

    # Read existing file
    try:
        existing_content = dest_file.read_text()
    except UnicodeDecodeError:
        # Binary content - replace entirely
        if not config.check:
            dest_file.unlink()
            dest_file.write_text(new_content)
        report.updated.append(dest_rel)
        return Success("replaced_binary")
    except OSError as e:
        return Failure(f"Failed to read {dest_rel}: {e}")

    # Process based on DX-55 state
    final_content = _merge_region_content(
        existing_content, new_content, new_parsed,
        primary_region, user_region, dest_rel, project_additions, config
    )

    # Check if changed
    if final_content == existing_content and not config.force:
        report.skipped.append(dest_rel)
        return Success("skipped")

    # Write updated file
    if not config.check:
        try:
            dest_file.write_text(final_content)
        except OSError as e:
            return Failure(f"Failed to write {dest_rel}: {e}")

    report.updated.append(dest_rel)
    return Success("updated")


def _create_new_region_file(
    dest_file: Path,
    dest_rel: str,
    new_content: str,
    new_parsed,
    project_additions: str,
    config: SyncConfig,
    report: SyncReport,
) -> Result[str, str]:
    """Create a new region-managed file."""
    final_content = new_content

    # Inject project additions for CLAUDE.md
    if dest_rel == "CLAUDE.md" and project_additions and "project" in new_parsed.regions:
        updates = {"project": project_additions}
        final_content = reconstruct_file(new_parsed, updates)

    if not config.check:
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(final_content)
        except OSError as e:
            return Failure(f"Failed to write {dest_rel}: {e}")

    report.created.append(dest_rel)
    return Success("created")


# @shell_orchestration: DX-55 state-based merge logic with multiple recovery paths
# @shell_complexity: Multiple state branches (intact/partial/missing)
def _merge_region_content(
    existing_content: str,
    new_content: str,
    new_parsed,
    primary_region: str,
    user_region: str,
    dest_rel: str,
    project_additions: str,
    config: SyncConfig,
) -> str:
    """Merge existing content with new template based on DX-55 state."""
    updates: dict[str, str] = {}

    # Reset mode: discard all user content, use fresh template
    if config.reset:
        # Only inject project additions for CLAUDE.md if available
        if dest_rel == "CLAUDE.md" and project_additions:
            parsed = parse_invar_regions(new_content)
            if "project" in parsed.regions:
                return reconstruct_file(parsed, {"project": project_additions})
        return new_content

    # Generic region detection: check if primary region markers exist
    # This works for any region scheme (managed/user, skill/extensions, etc.)
    primary_open = f"<!--invar:{primary_region}"
    primary_close = f"<!--/invar:{primary_region}-->"
    user_open = f"<!--invar:{user_region}-->"
    user_close = f"<!--/invar:{user_region}-->"

    has_primary_open = primary_open in existing_content
    has_primary_close = primary_close in existing_content
    has_user_open = user_open in existing_content
    has_user_close = user_close in existing_content

    primary_complete = has_primary_open and has_primary_close
    user_complete = has_user_open and has_user_close

    # Determine state based on generic region presence
    if primary_complete and user_complete:
        # Intact: update primary region, preserve user region
        existing_parsed = parse_invar_regions(existing_content)
        updates[primary_region] = new_parsed.regions[primary_region].content

        # DX-58: Also update critical region if present (always overwrite from template)
        if "critical" in new_parsed.regions and "critical" in existing_parsed.regions:
            updates["critical"] = new_parsed.regions["critical"].content

        if dest_rel == "CLAUDE.md" and project_additions and "project" in existing_parsed.regions:
            updates["project"] = project_additions
        return reconstruct_file(existing_parsed, updates)

    elif has_primary_open or has_user_open:
        # Partial: some markers present but incomplete - salvage user content
        existing_parsed = parse_invar_regions(existing_content)
        user_content = ""
        if user_region in existing_parsed.regions:
            user_content = existing_parsed.regions[user_region].content
        if not user_content:
            user_content = strip_invar_markers(existing_content)
        if user_content:
            user_content = format_preserved_content(user_content, date.today().isoformat())
        parsed = parse_invar_regions(new_content)
        if user_region in parsed.regions and user_content:
            updates = {user_region: "\n" + user_content + "\n"}
            if dest_rel == "CLAUDE.md" and project_additions and "project" in parsed.regions:
                updates["project"] = project_additions
            return reconstruct_file(parsed, updates)
        return new_content

    else:
        # Missing: no Invar markers - preserve entire content as user content
        # Handle empty content - just return fresh template
        if not existing_content.strip():
            if dest_rel == "CLAUDE.md" and project_additions:
                parsed = parse_invar_regions(new_content)
                if "project" in parsed.regions:
                    return reconstruct_file(parsed, {"project": project_additions})
            return new_content

        preserved = format_preserved_content(existing_content, date.today().isoformat())
        parsed = parse_invar_regions(new_content)
        if user_region in parsed.regions:
            updates = {user_region: "\n" + preserved + "\n"}
            if dest_rel == "CLAUDE.md" and project_additions and "project" in parsed.regions:
                updates["project"] = project_additions
            return reconstruct_file(parsed, updates)
        return new_content


# @shell_complexity: File creation with multiple template types
def _sync_create_only(
    path: Path,
    templates_dir: Path,
    dest_rel: str,
    template_config: dict,
    variables: dict,
    report: SyncReport,
) -> Result[str, str]:
    """Sync a create-only file (only create if not exists)."""
    dest_file = path / dest_rel
    src_rel = template_config.get("src", "")
    template_type = template_config.get("type", "copy")
    src_file = templates_dir / src_rel

    # Skip if already exists
    if dest_file.exists():
        report.skipped.append(dest_rel)
        return Success("skipped")

    # LX-05: Skip existence check for copy_dir_lang (has {language} placeholder)
    if template_type != "copy_dir_lang" and not src_file.exists():
        return Failure(f"Template not found: {src_rel}")

    try:
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if template_type == "copy":
            dest_file.write_text(src_file.read_text())
        elif template_type == "jinja":
            result = render_template_file(src_file, variables)
            if isinstance(result, Failure):
                return result
            dest_file.write_text(result.unwrap())
        elif template_type == "copy_dir":
            if src_file.is_dir():
                # Ignore Python bytecode and cache directories
                ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
                shutil.copytree(src_file, dest_file, ignore=ignore)
            else:
                return Failure(f"Expected directory: {src_rel}")
        elif template_type == "copy_dir_lang":
            # LX-05 hotfix: Language-aware directory copy
            lang = variables.get("language", "python")
            lang_src_rel = src_rel.replace("{language}", lang)
            lang_src_file = templates_dir / lang_src_rel
            if not lang_src_file.exists():
                return Failure(f"Language-specific template not found: {lang_src_rel}")
            if lang_src_file.is_dir():
                # Ignore Python bytecode and cache directories
                ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
                shutil.copytree(lang_src_file, dest_file, ignore=ignore)
            else:
                return Failure(f"Expected directory: {lang_src_rel}")

        report.created.append(dest_rel)
        return Success("created")

    except OSError as e:
        return Failure(f"Failed to create {dest_rel}: {e}")
