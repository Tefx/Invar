"""
Skill management for Invar extension skills.

LX-07: Extension Skills Architecture
- List available extension skills from registry
- Add/remove skills to/from project
- Update installed skills from templates

DX-71: Simplified to idempotent `add` command with region merge.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from returns.result import Failure, Result, Success

from invar.core.template_parser import parse_invar_regions, reconstruct_file

if TYPE_CHECKING:
    from rich.console import Console


SKILLS_REGISTRY = "extensions/_registry.yaml"
SKILLS_DIR = "extensions"
PROJECT_SKILLS_DIR = ".claude/skills"

# Core skills managed by Invar (shared with uninstall.py)
CORE_SKILLS = {"develop", "review", "investigate", "propose", "guard", "audit"}


# @shell_orchestration: Validation helper used only by shell add_skill/remove_skill
def _is_valid_skill_name(name: str) -> bool:
    """Validate skill name to prevent path traversal and filesystem attacks."""
    # Block path traversal characters and null bytes
    if ".." in name or "/" in name or "\\" in name or "\x00" in name:
        return False
    # Block special names that could cause issues
    if name in (".", ""):
        return False
    # Must not start with dot or underscore
    return not name.startswith(".") and not name.startswith("_")


def _merge_md_file(src: Path, dst: Path) -> tuple[bool, str]:
    """
    Merge .md file preserving user's extensions region.

    DX-71: Only updates <!--invar:skill--> region, preserves <!--invar:extensions-->.

    Returns:
        (merged, message) - True if merged, False if copied fresh
    """
    if not dst.exists():
        shutil.copy2(src, dst)
        return False, "Copied"

    try:
        new_content = src.read_text()
        old_content = dst.read_text()

        parsed_new = parse_invar_regions(new_content)
        parsed_old = parse_invar_regions(old_content)

        # If old file has regions and new file has skill region, merge
        if parsed_old.has_regions and "skill" in parsed_new.regions:
            updates = {"skill": parsed_new.regions["skill"].content}
            merged = reconstruct_file(parsed_old, updates)
            dst.write_text(merged)
            return True, "Merged (extensions preserved)"

        # No regions to merge - overwrite file
        shutil.copy2(src, dst)
        return False, "Updated"

    except (OSError, UnicodeDecodeError, ValueError, KeyError) as e:
        # On I/O or parse error, preserve existing file - don't silently lose user data
        # Include error details for debugging
        return False, f"Skipped (merge failed: {type(e).__name__}: {e})"


@dataclass
class SkillInfo:
    """Information about an extension skill."""

    name: str
    description: str
    tier: str
    isolation: bool
    status: str  # "available", "pending_discussion", "installed"
    files: list[str]


def get_templates_path() -> Path:
    """Get the path to Invar templates directory."""
    # Navigate from this file to templates/skills/
    return Path(__file__).parent.parent / "templates" / "skills"


def load_registry() -> Result[dict, str]:
    """Load the extension skills registry."""
    registry_path = get_templates_path() / SKILLS_REGISTRY

    if not registry_path.exists():
        return Failure(f"Registry not found: {registry_path}")

    try:
        content = registry_path.read_text()
        data = yaml.safe_load(content)
        return Success(data)
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        return Failure(f"Failed to parse registry: {e}")


# @shell_complexity: Iterates registry entries and checks installed status
def list_skills(
    project_path: Path, console: Console
) -> Result[list[SkillInfo], str]:
    """
    List all available extension skills.

    Returns both available and installed skills with their status.
    """
    registry_result = load_registry()
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.unwrap()
    extensions = registry.get("extensions", {})

    # Check which skills are installed
    installed_dir = project_path / PROJECT_SKILLS_DIR
    installed_skills = set()
    if installed_dir.exists():
        for skill_dir in installed_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                # Check if it's an extension (not a core skill)
                if (skill_dir / "SKILL.md").exists():
                    installed_skills.add(skill_dir.name)

    skills = []
    for name, info in extensions.items():
        status = info.get("status", "available")
        if name in installed_skills:
            status = "installed"

        skills.append(
            SkillInfo(
                name=name,
                description=info.get("description", ""),
                tier=info.get("tier", "T0"),
                isolation=info.get("isolation", False),
                status=status,
                files=info.get("files", ["SKILL.md"]),
            )
        )

    return Success(skills)


# @shell_complexity: Validates skill, copies files/directories with error recovery
def add_skill(
    skill_name: str, project_path: Path, console: Console
) -> Result[str, str]:
    """
    Add or update an extension skill to the project.

    DX-71: Idempotent - installs if missing, updates if exists.
    For .md files, preserves <!--invar:extensions--> region.

    Copies skill files from templates to .claude/skills/<name>/
    """
    # Validate skill name (defense in depth against path traversal)
    if not _is_valid_skill_name(skill_name):
        return Failure(
            f"Invalid skill name: {skill_name}. "
            "Names cannot contain '.', '/', '\\' or start with '_'"
        )

    # Load registry to validate skill exists
    registry_result = load_registry()
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.unwrap()
    extensions = registry.get("extensions", {})

    if skill_name not in extensions:
        available = ", ".join(extensions.keys())
        return Failure(f"Unknown skill: {skill_name}. Available: {available}")

    skill_info = extensions[skill_name]

    # Check status
    if skill_info.get("status") == "pending_discussion":
        return Failure(
            f"Skill '{skill_name}' is pending discussion (T1). "
            "It will be available in a future release."
        )

    # Source and destination paths
    source_dir = get_templates_path() / SKILLS_DIR / skill_name
    dest_dir = project_path / PROJECT_SKILLS_DIR / skill_name

    if not source_dir.exists():
        return Failure(f"Skill template not found: {source_dir}")

    # DX-71: Determine if this is install or update
    is_update = dest_dir.exists()
    action = "Updating" if is_update else "Adding"
    console.print(f"{action} skill: {skill_name}")

    # Copy/merge skill files
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file_path in skill_info.get("files", ["SKILL.md"]):
            src = source_dir / file_path
            dst = dest_dir / file_path

            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)

                # DX-71: Use merge for .md files when updating
                if is_update and file_path.endswith(".md"):
                    _merged, msg = _merge_md_file(src, dst)
                    # DX-71 review: Show warning for merge failures
                    if msg.startswith("Skipped"):
                        console.print(f"  [yellow]Warning: {msg}: {file_path}[/yellow]")
                    else:
                        console.print(f"  [dim]{msg}: {file_path}[/dim]")
                else:
                    shutil.copy2(src, dst)
                    action_msg = "Updated" if is_update else "Copied"
                    console.print(f"  [dim]{action_msg}: {file_path}[/dim]")

            elif src.is_dir():
                # Handle directory (e.g., patterns/)
                # DX-71 review: Use dirs_exist_ok=True for atomic update (no rmtree race)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                action_msg = "Updated" if is_update else "Copied"
                console.print(f"  [dim]{action_msg}: {file_path}/[/dim]")

        result_msg = "updated" if is_update else "installed"
        return Success(f"Skill '{skill_name}' {result_msg} successfully")

    except (OSError, shutil.Error) as e:
        # Clean up on failure (only for fresh install)
        # M3 note: Updates that fail mid-way may leave directory in partial state.
        # This is acceptable because: (1) user extensions are preserved via merge,
        # (2) re-running add will complete the update. Full atomicity would require
        # temp directory + rename, adding complexity for rare failure cases.
        if not is_update and dest_dir.exists():
            shutil.rmtree(dest_dir)
        return Failure(f"Failed to {'update' if is_update else 'install'} skill: {e}")


def has_user_extensions(skill_dir: Path) -> bool:
    """Check if SKILL.md has user content in extensions region."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False

    # M1 fix: Narrow exception scope for better error handling
    try:
        content = skill_md.read_text()
    except (OSError, UnicodeDecodeError):
        # Cannot read file - assume extensions exist (safe default)
        return True

    try:
        parsed = parse_invar_regions(content)

        if "extensions" in parsed.regions:
            ext_content = parsed.regions["extensions"].content

            # Remove HTML comment blocks (the template content is inside comments)
            # This preserves user content like markdown lists (- item)
            cleaned = re.sub(r"<!--.*?-->", "", ext_content, flags=re.DOTALL)

            # Check if any non-whitespace content remains
            return bool(cleaned.strip())
    except (ValueError, KeyError):
        # Parse error - assume extensions exist (safe default)
        return True

    return False


# @shell_complexity: Validates core skill protection + user extensions check
def remove_skill(
    skill_name: str, project_path: Path, console: Console, force: bool = False
) -> Result[str, str]:
    """
    Remove an extension skill from the project.

    DX-71: Warns if user has custom extensions content.
    """
    # Validate skill name (defense in depth against path traversal)
    if not _is_valid_skill_name(skill_name):
        return Failure(
            f"Invalid skill name: {skill_name}. "
            "Names cannot contain '.', '/', '\\' or start with '_'"
        )

    dest_dir = project_path / PROJECT_SKILLS_DIR / skill_name

    if not dest_dir.exists():
        return Failure(f"Skill not installed: {skill_name}")

    # Protect core skills
    if skill_name in CORE_SKILLS:
        return Failure(
            f"Cannot remove core skill: {skill_name}. "
            "Only extension skills can be removed."
        )

    # DX-71: Check for user extensions
    # Note: CLI also checks this for UX ordering (warn before confirm dialog).
    # This check remains for programmatic API callers.
    if not force and has_user_extensions(dest_dir):
        console.print(
            "[yellow]Warning:[/yellow] This skill has custom extensions content "
            "that will be lost."
        )
        # M2 fix: API-appropriate message (not CLI --force)
        return Failure(
            "Skill has user extensions. Pass force=True to confirm removal."
        )

    try:
        shutil.rmtree(dest_dir)
        return Success(f"Skill '{skill_name}' removed successfully")
    except (OSError, shutil.Error) as e:
        return Failure(f"Failed to remove skill: {e}")


def update_skill(
    skill_name: str, project_path: Path, console: Console
) -> Result[str, str]:
    """
    Update an installed extension skill from templates.

    DX-71: Deprecated - use `add_skill` instead (idempotent).
    This function now delegates to add_skill with a deprecation notice.
    """
    console.print(
        "[dim]Note: 'skill update' is deprecated, use 'skill add' instead[/dim]"
    )
    return add_skill(skill_name, project_path, console)
