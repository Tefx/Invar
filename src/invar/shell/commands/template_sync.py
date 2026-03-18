"""DX-91 template sync and managed-section merge pipeline.

Contract source:
- docs/proposals/DX-91-migration-semantics.md section 5.1
- docs/proposals/DX-91-generated-file-contracts.md section 4.1
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from returns.result import Failure, Result, Success

from invar.core.sync_helpers import SyncConfig, SyncReport
from invar.shell.template_engine import get_templates_dir, render_template_file

__all__ = ["SyncConfig", "SyncReport", "sync_templates"]

MANAGED_BEGIN = "<!--invar:begin-->"
MANAGED_END = "<!--invar:end-->"
PROJECT_ADDITIONS_BEGIN = "<!--invar:project-additions:begin-->"
PROJECT_ADDITIONS_END = "<!--invar:project-additions:end-->"
V2_MANAGED_PATTERN = re.compile(r"<!--invar:begin-->.*?<!--invar:end-->", re.DOTALL)
PROJECT_ADDITIONS_BLOCK_PATTERN = re.compile(
    r"<!--invar:project-additions:begin-->.*?<!--invar:project-additions:end-->",
    re.DOTALL,
)
LEGACY_PRIMARY_BLOCK_PATTERN = re.compile(
    r"<!--invar:(critical|managed)(?:\s+version=[\"'][^\"']+[\"'])?-->"
    r".*?<!--/invar:\1-->",
    re.DOTALL,
)
LEGACY_PROJECT_PATTERN = re.compile(
    r"<!--invar:project(?:\s+version=[\"'][^\"']+[\"'])?-->"
    r"(.*?)<!--/invar:project-->",
    re.DOTALL,
)
LEGACY_USER_PATTERN = re.compile(
    r"<!--invar:user-->\s*(.*?)\s*<!--/invar:user-->",
    re.DOTALL,
)
LEGACY_SIGNAL_PATTERN = re.compile(r"<!--invar:(critical|managed|project|user)")


@dataclass(frozen=True)
class _RenderedAssets:
    """Rendered DX-91 sync assets.

    CLAUDE managed content is expected to be a single begin/end managed block.
    """

    claude_managed_block: str
    invar_content: str


# @shell_complexity: sync pipeline handles write ordering, optional context file, and failure rollback reporting.
def sync_templates(path: Path, config: SyncConfig) -> Result[SyncReport, str]:
    """Synchronize DX-91 managed template output into a target repository.

    Behavior (DX-91):
    - Last-writer-wins is limited to managed template output.
    - User content outside managed markers is preserved exactly.
    - Legacy marker layouts are migrated to one v2 managed block.
    - Sync scope is reduced to CLAUDE managed target + INVAR.md.
    """

    repo_root = path.resolve()
    report = SyncReport()
    written: list[str] = []

    templates_dir = _resolve_template_root(repo_root, config)
    assets_result = _render_assets(templates_dir, config)
    if isinstance(assets_result, Failure):
        return assets_result
    assets = assets_result.unwrap()

    project_additions_result = _read_project_additions(repo_root, config)
    if isinstance(project_additions_result, Failure):
        return project_additions_result
    project_additions = project_additions_result.unwrap()

    target_file = _resolve_target_file(repo_root, config.target_file)
    target_rel = _display_path(repo_root, target_file)

    try:
        _sync_managed_target(
            target_file,
            target_rel,
            assets.claude_managed_block,
            project_additions,
            config,
            report,
        )
        written.append(target_rel)

        invar_file = repo_root / "INVAR.md"
        _sync_fully_managed(invar_file, "INVAR.md", assets.invar_content, config, report)
        written.append("INVAR.md")

    except OSError as exc:
        detail = ", ".join(written) if written else "none"
        return Failure(f"DX-91 sync interrupted after writing: {detail}. Error: {exc}")

    return Success(report)


def _resolve_template_root(repo_root: Path, config: SyncConfig) -> Path:
    if not config.template_root:
        return get_templates_dir()

    template_root = Path(config.template_root)
    return (
        template_root.resolve()
        if template_root.is_absolute()
        else (repo_root / template_root).resolve()
    )


def _resolve_target_file(repo_root: Path, target_file: str) -> Path:
    target_path = Path(target_file)
    return target_path if target_path.is_absolute() else repo_root / target_path


def _display_path(repo_root: Path, candidate: Path) -> str:
    try:
        return str(candidate.relative_to(repo_root))
    except ValueError:
        return str(candidate)


def _read_utf8_or_empty(path: Path) -> str:
    """Read UTF-8 text; treat undecodable files as empty content."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


# @shell_complexity: rendering requires fallback sequencing across managed, protocol, and optional context templates.
def _render_assets(templates_dir: Path, config: SyncConfig) -> Result[_RenderedAssets, str]:
    variables = {"syntax": config.syntax, "language": config.language, "version": "5.0"}

    claude_result = _render_with_fallback(
        templates_dir,
        [
            "config/CLAUDE.md.v2.jinja",
            "config/CLAUDE.md.jinja",
        ],
        variables,
    )
    if isinstance(claude_result, Failure):
        return claude_result

    invar_result = _render_with_fallback(
        templates_dir,
        [
            "protocol/INVAR.md.v2.jinja",
            "protocol/INVAR.md.jinja",
        ],
        variables,
    )
    if isinstance(invar_result, Failure):
        return invar_result

    managed_result = _extract_managed_block(claude_result.unwrap())
    if isinstance(managed_result, Failure):
        return managed_result

    return Success(
        _RenderedAssets(
            claude_managed_block=managed_result.unwrap(),
            invar_content=invar_result.unwrap(),
        )
    )


# @shell_complexity: fallback chain handles missing templates and render errors.
def _render_with_fallback(
    templates_dir: Path,
    relative_candidates: list[str],
    variables: dict[str, str],
) -> Result[str, str]:
    seen: list[str] = []
    for relative in relative_candidates:
        template_path = templates_dir / relative
        if not template_path.exists():
            seen.append(f"missing:{relative}")
            continue
        rendered = render_template_file(template_path, variables)
        if isinstance(rendered, Failure):
            seen.append(f"error:{relative}:{rendered.failure()}")
            continue
        return rendered

    detail = "; ".join(seen) if seen else "no candidates"
    return Failure(f"No usable DX-91 template source. Tried: {detail}")


def _extract_managed_block(rendered_claude: str) -> Result[str, str]:
    v2_match = V2_MANAGED_PATTERN.search(rendered_claude)
    if v2_match:
        return Success(v2_match.group(0).strip("\n"))

    legacy_match = re.search(
        r"<!--invar:managed(?:\s+version=[\"'][^\"']+[\"'])?-->(.*?)<!--/invar:managed-->",
        rendered_claude,
        flags=re.DOTALL,
    )
    if legacy_match:
        managed_body = legacy_match.group(1).strip("\n")
        return Success(f"{MANAGED_BEGIN}\n{managed_body}\n{MANAGED_END}")

    return Failure("Rendered CLAUDE template missing managed markers (v2 or legacy)")


def _read_project_additions(repo_root: Path, config: SyncConfig) -> Result[str | None, str]:
    """Read optional project additions configured for CLAUDE sync."""
    if not config.inject_project_additions:
        return Success(None)

    additions_path = repo_root / ".invar" / "project-additions.md"
    if not additions_path.exists():
        return Success(None)

    try:
        content = additions_path.read_text(encoding="utf-8").strip("\n")
    except OSError as exc:
        return Failure(f"Failed to read {additions_path}: {exc}")

    return Success(content or None)


# @shell_complexity: merge must handle legacy migration, v2 replacement, and append mode.
def _merge_managed(existing_content: str, managed_block: str) -> str:
    if LEGACY_SIGNAL_PATTERN.search(existing_content):
        # DX-91 4.1: any legacy signal forces migration behavior.
        normalized = _strip_legacy_blocks(existing_content)
        normalized = V2_MANAGED_PATTERN.sub("", normalized)
        preserved = normalized.strip("\n")
        if preserved:
            return f"{preserved}\n\n{managed_block.strip()}\n"
        return f"{managed_block.strip()}\n"

    if V2_MANAGED_PATTERN.search(existing_content):
        first = V2_MANAGED_PATTERN.search(existing_content)
        if first is None:
            return existing_content
        head = existing_content[: first.start()]
        tail = existing_content[first.end() :]
        tail_without_duplicates = V2_MANAGED_PATTERN.sub("", tail)
        return head + managed_block.strip() + tail_without_duplicates

    preserved = existing_content.strip("\n")
    if preserved:
        return f"{preserved}\n\n{managed_block.strip()}\n"
    return f"{managed_block.strip()}\n"


def _strip_legacy_blocks(content: str) -> str:
    without_primary = LEGACY_PRIMARY_BLOCK_PATTERN.sub("", content)
    without_project_markers = LEGACY_PROJECT_PATTERN.sub(
        lambda m: m.group(1).strip("\n"), without_primary
    )
    return LEGACY_USER_PATTERN.sub(lambda m: m.group(1), without_project_markers)


def _normalize_project_additions(project_additions: str | None) -> str | None:
    if project_additions is None:
        return None
    normalized = project_additions.strip("\n")
    return normalized or None


def _build_project_additions_block(additions_body: str) -> str:
    return f"{PROJECT_ADDITIONS_BEGIN}\n{additions_body}\n{PROJECT_ADDITIONS_END}"


def _replace_project_additions_block(existing_content: str, additions_block: str) -> str | None:
    first = PROJECT_ADDITIONS_BLOCK_PATTERN.search(existing_content)
    if first is None:
        return None

    head = existing_content[: first.start()]
    tail = existing_content[first.end() :]
    tail_without_duplicates = PROJECT_ADDITIONS_BLOCK_PATTERN.sub("", tail)
    return head + additions_block + tail_without_duplicates


def _append_project_additions_block(existing_content: str, additions_block: str) -> str:
    preserved = existing_content.strip("\n")
    if preserved:
        return f"{preserved}\n\n{additions_block}\n"
    return f"{additions_block}\n"


def _merge_project_additions(existing_content: str, project_additions: str | None) -> str:
    """Inject or replace project additions outside managed markers."""
    additions_body = _normalize_project_additions(project_additions)
    if additions_body is None:
        return existing_content

    additions_block = _build_project_additions_block(additions_body)
    replaced = _replace_project_additions_block(existing_content, additions_block)
    if replaced is not None:
        return replaced

    return _append_project_additions_block(existing_content, additions_block)


# @shell_complexity: target sync branches on existence, force/check, and change detection.
def _sync_managed_target(
    target_file: Path,
    target_rel: str,
    managed_block: str,
    project_additions: str | None,
    config: SyncConfig,
    report: SyncReport,
) -> None:
    existed = target_file.exists()
    existing_content = _read_utf8_or_empty(target_file) if existed else ""
    merged = _merge_managed(existing_content, managed_block)
    merged = _merge_project_additions(merged, project_additions)

    if existed and merged == existing_content and not config.force:
        report.skipped.append(target_rel)
        return

    if not config.check:
        _atomic_write(target_file, merged)

    if existed:
        report.updated.append(target_rel)
    else:
        report.created.append(target_rel)


# @shell_complexity: fully managed sync branches on existence, force/check, and change detection.
def _sync_fully_managed(
    target_file: Path,
    target_rel: str,
    new_content: str,
    config: SyncConfig,
    report: SyncReport,
) -> None:
    existed = target_file.exists()
    existing_content = _read_utf8_or_empty(target_file) if existed else ""

    if existed and existing_content == new_content and not config.force:
        report.skipped.append(target_rel)
        return

    if not config.check:
        _atomic_write(target_file, new_content)

    if existed:
        report.updated.append(target_rel)
    else:
        report.created.append(target_rel)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=str(path.parent)
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
