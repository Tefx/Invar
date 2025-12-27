"""
DX-55: Smart merge logic for CLAUDE.md recovery.

Shell module: handles merging and recovering CLAUDE.md content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Literal

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from pathlib import Path

from invar.core.template_parser import (
    ClaudeMdState,
    detect_claude_md_state,
    format_preserved_content,
    parse_invar_regions,
    reconstruct_file,
    strip_invar_markers,
)
from invar.shell.template_engine import generate_from_manifest

# =============================================================================
# DX-55: Project State Detection
# =============================================================================


@dataclass
class ProjectState:
    """Overall project initialization state.

    DX-55: Captures full state for idempotent init decision.
    """

    initialized: bool
    claude_md_state: ClaudeMdState
    version: str
    needs_update: bool

    @property
    def action(self) -> Literal["full_init", "update", "recover", "create", "none"]:
        """Determine what action to take."""
        if not self.initialized:
            return "full_init"

        match self.claude_md_state.state:
            case "intact":
                return "update" if self.needs_update else "none"
            case "partial" | "missing":
                return "recover"
            case "absent":
                return "create"
            case _:
                return "none"


# @shell_complexity: State detection requires multiple file existence checks
def detect_project_state(path: Path) -> ProjectState:
    """Detect Invar initialization state.

    DX-55: Core state detection for idempotent init.
    """
    from invar import __protocol_version__

    invar_md = path / "INVAR.md"
    invar_dir = path / ".invar"
    claude_md = path / "CLAUDE.md"

    initialized = invar_md.exists() and invar_dir.exists()

    # Detect CLAUDE.md state
    if claude_md.exists():
        try:
            content = claude_md.read_text()
            claude_state = detect_claude_md_state(content)
        except UnicodeDecodeError:
            # Binary or non-UTF-8 content - treat as corrupt, will be replaced
            claude_state = ClaudeMdState(state="partial")
    else:
        claude_state = ClaudeMdState(state="absent")

    # Extract protocol version from existing INVAR.md
    version = ""
    if invar_md.exists():
        content = invar_md.read_text()
        import re

        match = re.search(r"Invar (?:Protocol )?v([\d.]+)", content)
        if match:
            version = match.group(1)

    # Check if update needed (compare protocol versions, not package versions)
    needs_update = initialized and version != __protocol_version__

    return ProjectState(
        initialized=initialized,
        claude_md_state=claude_state,
        version=version,
        needs_update=needs_update,
    )


# =============================================================================
# DX-55: Smart Merge Functions
# =============================================================================


# @shell_complexity: Smart merge with multiple state handling paths
def merge_claude_md(path: Path, state: ClaudeMdState) -> Result[str, str]:
    """Smart merge CLAUDE.md based on detected state.

    DX-55: Preserves user content while restoring Invar regions.
    """
    from pathlib import Path as PathLib  # Runtime import for Path operations

    claude_md = PathLib(path) / "CLAUDE.md"

    # Read existing content (handle binary/corrupt files)
    existing_content = ""
    if claude_md.exists():
        try:
            existing_content = claude_md.read_text()
        except UnicodeDecodeError:
            # Binary content - delete and recreate
            claude_md.unlink()
            state = ClaudeMdState(state="absent")

    match state.state:
        case "intact":
            # Just update managed region, preserve user exactly
            return _update_managed_only(path, existing_content)

        case "partial":
            # Corruption: try to salvage user content
            return _recover_from_partial(path, existing_content, state)

        case "missing":
            # No Invar markers - treat entire file as user content
            return _merge_with_preserved(path, existing_content)

        case "absent":
            # Just create new file
            return Success("create_new")

    return Success("no_action")


# @shell_complexity: Template regeneration with region extraction
def _update_managed_only(path: Path, existing_content: str) -> Result[str, str]:
    """Update only the managed region, preserve user content."""
    # Parse existing
    parsed = parse_invar_regions(existing_content)

    if "user" not in parsed.regions:
        return Failure("No user region found")

    # Generate fresh template
    template_result = generate_from_manifest(
        path, syntax="cli", files_to_generate=["CLAUDE.md"]
    )
    if isinstance(template_result, Failure):
        return template_result

    # Re-read and extract managed
    new_content = (path / "CLAUDE.md").read_text()
    new_parsed = parse_invar_regions(new_content)

    if "managed" not in new_parsed.regions:
        return Failure("Template missing managed region")

    # Reconstruct with new managed but old user
    updates = {"managed": new_parsed.regions["managed"].content}
    final_content = reconstruct_file(parsed, updates)

    (path / "CLAUDE.md").write_text(final_content)
    return Success("updated_managed")


# @shell_complexity: Recovery with content salvage logic
def _recover_from_partial(
    path: Path, existing_content: str, state: ClaudeMdState
) -> Result[str, str]:
    """Recover from partial corruption."""
    from pathlib import Path as PathLib  # Runtime import for Path operations

    # Try to salvage user content
    if state.user_content:
        user_content = state.user_content
    else:
        # Strip markers and treat rest as user content
        user_content = strip_invar_markers(existing_content)
        if user_content:
            user_content = format_preserved_content(
                user_content, date.today().isoformat()
            )

    # Remove existing CLAUDE.md so generate_from_manifest creates fresh template
    claude_md = PathLib(path) / "CLAUDE.md"
    if claude_md.exists():
        claude_md.unlink()

    # Generate fresh template
    result = generate_from_manifest(
        path, syntax="cli", files_to_generate=["CLAUDE.md"]
    )
    if isinstance(result, Failure):
        return result

    # Inject recovered user content
    if user_content:
        new_content = claude_md.read_text()
        parsed = parse_invar_regions(new_content)
        if "user" in parsed.regions:
            updates = {"user": "\n" + user_content + "\n"}
            final_content = reconstruct_file(parsed, updates)
            claude_md.write_text(final_content)

    return Success("recovered")


def _merge_with_preserved(path: Path, existing_content: str) -> Result[str, str]:
    """Merge overwritten content as preserved user content."""
    from pathlib import Path as PathLib  # Runtime import for Path operations

    # Format existing content as preserved
    preserved = format_preserved_content(
        existing_content, date.today().isoformat()
    )

    # Remove existing CLAUDE.md so generate_from_manifest creates fresh template
    claude_md = PathLib(path) / "CLAUDE.md"
    if claude_md.exists():
        claude_md.unlink()

    # Generate fresh template
    result = generate_from_manifest(
        path, syntax="cli", files_to_generate=["CLAUDE.md"]
    )
    if isinstance(result, Failure):
        return result

    # Inject preserved content into user region
    new_content = claude_md.read_text()
    parsed = parse_invar_regions(new_content)

    if "user" in parsed.regions:
        updates = {"user": "\n" + preserved + "\n"}
        final_content = reconstruct_file(parsed, updates)
        claude_md.write_text(final_content)

    return Success("merged")
