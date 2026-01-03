"""
Claude Code hooks management for Invar.

DX-57: Implements hook installation, update, and management.
Shell module: handles file I/O for hooks.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader
from returns.result import Failure, Result, Success

from invar.core.language import detect_language_from_markers

if TYPE_CHECKING:
    from rich.console import Console

# Protocol version for hook version tracking
PROTOCOL_VERSION = "5.0"

# Hook types supported
HOOK_TYPES = ["PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"]

# Path constants
HOOKS_SUBDIR = ".claude/hooks"
DISABLED_MARKER = ".invar_disabled"


# Marker for identifying Invar hooks in settings
INVAR_HOOK_MARKER = ".claude/hooks/"

# Regex pattern for extracting protocol version from hook files
PROTOCOL_VERSION_PATTERN = r"Protocol: v([\d.]+)"


# @shell_orchestration: Tightly coupled to Claude Code settings.local.json format
def is_invar_hook(hook_entry: dict) -> bool:
    """Check if a hook entry is an Invar hook.

    Works with both new format ({"hooks": [...]}) and legacy format.
    """
    # All hook types now use {"hooks": [...]} format
    if "hooks" in hook_entry:
        return any(
            INVAR_HOOK_MARKER in h.get("command", "")
            for h in hook_entry.get("hooks", [])
        )
    # Legacy format fallback: {"type": "command", "command": "..."}
    return INVAR_HOOK_MARKER in hook_entry.get("command", "")


def get_templates_path() -> Path:
    """Get the path to hook templates."""
    return Path(__file__).parent.parent / "templates" / "hooks"


def get_invar_md_content(project_path: Path) -> str:
    """Read INVAR.md content for embedding in UserPromptSubmit hook."""
    invar_md = project_path / "INVAR.md"
    if invar_md.exists():
        return invar_md.read_text()
    # Fallback to template if INVAR.md not yet created
    template_path = Path(__file__).parent.parent / "templates" / "protocol" / "INVAR.md"
    if template_path.exists():
        return template_path.read_text()
    return "# INVAR.md not found"


def detect_syntax(project_path: Path) -> str:
    """Detect syntax mode from .mcp.json presence."""
    mcp_json = project_path / ".mcp.json"
    if mcp_json.exists():
        try:
            content = mcp_json.read_text()
            if '"invar"' in content:
                return "mcp"
        except OSError:
            pass
    return "cli"


# @shell_complexity: Template rendering with syntax detection
def generate_hook_content(
    hook_type: str,
    project_path: Path,
) -> Result[str, str]:
    """Generate hook content from template."""
    templates_path = get_templates_path()
    template_file = f"{hook_type}.sh.jinja"

    if not (templates_path / template_file).exists():
        return Failure(f"Template not found: {template_file}")

    try:
        env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            keep_trailing_newline=True,
        )
        template = env.get_template(template_file)

        # Determine guard command based on syntax
        syntax = detect_syntax(project_path)
        guard_cmd = "invar_guard" if syntax == "mcp" else "invar guard"

        # Detect project language from marker files
        markers = frozenset(f.name for f in project_path.iterdir() if f.is_file())
        language = detect_language_from_markers(markers)

        # Build context for template
        context = {
            "protocol_version": PROTOCOL_VERSION,
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
            "guard_cmd": guard_cmd,
            "language": language,
        }

        # For UserPromptSubmit, add the full INVAR.md content
        if hook_type == "UserPromptSubmit":
            context["invar_protocol"] = get_invar_md_content(project_path)

        content = template.render(**context)
        return Success(content)
    except Exception as e:
        return Failure(f"Failed to generate {hook_type} hook: {e}")


# @shell_complexity: Hook installation with user hook merging

def _register_hooks_in_settings(project_path: Path) -> Result[bool, str]:
    """
    Register hooks in .claude/settings.local.json.

    Claude Code requires explicit hook registration - hooks are NOT auto-discovered
    from the .claude/hooks/ directory.

    Uses merge strategy:
    - Preserves user's existing hooks
    - Only adds/updates Invar hooks (identified by .claude/hooks/ path)
    """
    import json

    settings_path = project_path / ".claude" / "settings.local.json"

    def build_invar_hook(hook_type: str) -> dict:
        """Build Invar hook entry for a hook type."""
        # Use $CLAUDE_PROJECT_DIR for portable paths that work regardless of cwd
        # Claude Code provides this env var to all hooks (see code.claude.com/docs/hooks)
        hook_cmd = {
            "type": "command",
            "command": f'"$CLAUDE_PROJECT_DIR"/.claude/hooks/{hook_type}.sh',
        }
        if hook_type in ("PreToolUse", "PostToolUse"):
            # These need a matcher - use "*" to match all tools
            return {
                "matcher": "*",
                "hooks": [hook_cmd],
            }
        # UserPromptSubmit, Stop don't use matchers but still need hooks wrapper
        return {
            "hooks": [hook_cmd],
        }

    try:
        existing = json.loads(settings_path.read_text()) if settings_path.exists() else {}

        # Get existing hooks or create empty dict
        existing_hooks = existing.get("hooks", {})

        # Merge each hook type
        for hook_type in HOOK_TYPES:
            existing_list = existing_hooks.get(hook_type, [])

            # Filter out old Invar hooks, keep user hooks
            user_hooks = [h for h in existing_list if not is_invar_hook(h)]

            # Append new Invar hook
            user_hooks.append(build_invar_hook(hook_type))

            existing_hooks[hook_type] = user_hooks

        existing["hooks"] = existing_hooks

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(existing, indent=2))
        return Success(True)

    except (OSError, json.JSONDecodeError) as e:
        return Failure(f"Failed to update settings: {e}")


# @shell_complexity: Feedback config management in settings.local.json
def add_feedback_config(
    project_path: Path,
    enabled: bool = True,
    console: Console | None = None,
) -> Result[bool, str]:
    """
    Add feedback configuration to .claude/settings.local.json.

    DX-79 Phase C: Init Integration for /invar-reflect skill.

    Args:
        project_path: Path to project root
        enabled: Whether to enable feedback collection (default: True)
        console: Optional Rich console for output

    Returns:
        Success(True) if config added/updated, Failure with error message otherwise
    """
    import json

    settings_path = project_path / ".claude" / "settings.local.json"

    try:
        existing = json.loads(settings_path.read_text()) if settings_path.exists() else {}

        # Add feedback configuration
        existing["feedback"] = {
            "enabled": enabled,
            "auto_trigger": enabled,  # Same as enabled
            "retention_days": 90,
        }

        # Ensure .claude directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with indentation for readability
        settings_path.write_text(json.dumps(existing, indent=2) + "\n")

        if console:
            status = "enabled" if enabled else "disabled"
            console.print(f"  [green]✓[/green] Feedback collection {status}")

        return Success(True)

    except (OSError, json.JSONDecodeError) as e:
        return Failure(f"Failed to update settings: {e}")


# @shell_complexity: Multi-file installation with backup/merge logic for user hooks
def install_claude_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Install Claude Code hooks for Invar.

    Creates:
    - .claude/hooks/invar.{HookType}.sh - Invar hook scripts
    - .claude/hooks/{HookType}.sh - Wrapper that sources Invar hook

    Preserves existing user hooks by creating wrapper that runs both.
    """
    hooks_dir = project_path / HOOKS_SUBDIR
    hooks_dir.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    failed: list[str] = []

    console.print("\n[bold]Installing Claude Code hooks (DX-57)...[/bold]")
    console.print("  Hooks will:")
    console.print("    ✓ Block pytest/crosshair → redirect to invar_guard")
    console.print("    ✓ Remind to verify after code changes")
    console.print("    ✓ Refresh protocol in long conversations (~1,800 tokens)")
    console.print("")

    for hook_type in HOOK_TYPES:
        result = generate_hook_content(hook_type, project_path)
        if isinstance(result, Failure):
            console.print(f"  [red]Failed:[/red] {result.failure()}")
            failed.append(hook_type)
            continue

        content = result.unwrap()
        invar_hook = hooks_dir / f"invar.{hook_type}.sh"
        wrapper_hook = hooks_dir / f"{hook_type}.sh"

        # Write Invar hook
        invar_hook.write_text(content)
        invar_hook.chmod(0o755)

        # Handle wrapper hook
        if wrapper_hook.exists():
            existing_content = wrapper_hook.read_text()
            if f"invar.{hook_type}.sh" in existing_content:
                # Already has Invar reference, just update invar hook
                console.print(f"  [cyan]Updated[/cyan] invar.{hook_type}.sh")
            else:
                # User hook exists, create backup and merge
                backup = hooks_dir / f"{hook_type}.sh.user_backup"
                if not backup.exists():
                    backup.write_text(existing_content)
                    console.print(f"  [dim]Backed up user {hook_type}.sh[/dim]")

                # Create merged wrapper
                merged = f'''#!/bin/bash
# Merged hook: User + Invar (DX-57)
# Ensure correct working directory regardless of where Claude Code invokes from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if ! cd "$PROJECT_ROOT" 2>/dev/null; then
  echo "[invar] Warning: Could not cd to $PROJECT_ROOT" >&2
  exit 0  # Don't block Claude Code
fi

# Run user hook first (higher priority)
if [[ -f "$SCRIPT_DIR/{hook_type}.sh.user_backup" ]]; then
  source "$SCRIPT_DIR/{hook_type}.sh.user_backup" "$@"
  USER_EXIT=$?
  [[ $USER_EXIT -ne 0 ]] && exit $USER_EXIT
fi

# Run Invar hook
if [[ -f "$SCRIPT_DIR/invar.{hook_type}.sh" ]]; then
  source "$SCRIPT_DIR/invar.{hook_type}.sh" "$@"
fi
'''
                wrapper_hook.write_text(merged)
                wrapper_hook.chmod(0o755)
                console.print(f"  [green]Merged[/green] {hook_type}.sh (user hook preserved)")
        else:
            # No user hook, create simple wrapper
            wrapper = f'''#!/bin/bash
# Invar hook wrapper (DX-57)
# Ensure correct working directory regardless of where Claude Code invokes from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if ! cd "$PROJECT_ROOT" 2>/dev/null; then
  echo "[invar] Warning: Could not cd to $PROJECT_ROOT" >&2
  exit 0  # Don't block Claude Code
fi
source "$SCRIPT_DIR/invar.{hook_type}.sh" "$@"
'''
            wrapper_hook.write_text(wrapper)
            wrapper_hook.chmod(0o755)
            console.print(f"  [green]Created[/green] {hook_type}.sh")

        installed.append(hook_type)

    if installed:
        # Register hooks in settings.local.json (Claude Code requires explicit registration)
        reg_result = _register_hooks_in_settings(project_path)
        if isinstance(reg_result, Failure):
            console.print(f"  [yellow]Warning:[/yellow] {reg_result.failure()}")
        else:
            console.print("  [green]Registered[/green] hooks in .claude/settings.local.json")

        console.print("\n  [bold green]✓ Claude Code hooks installed[/bold green]")
        console.print("  [dim]Auto-escape: pytest --pdb, pytest --cov, vendor/[/dim]")
        console.print("  [dim]Manual escape: INVAR_ALLOW_PYTEST=1[/dim]")
        console.print("  [yellow]⚠ Restart Claude Code session for hooks to take effect[/yellow]")

    if failed:
        return Failure(f"Failed to install hooks: {', '.join(failed)}")

    return Success(installed)


# @shell_complexity: Hook sync with version detection
def sync_claude_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Update Claude Code hooks with current INVAR.md content.

    Called during `invar init` to ensure hooks stay in sync with protocol.
    Only updates if Invar hooks are already installed.
    """
    hooks_dir = project_path / HOOKS_SUBDIR

    # Check if Invar hooks are installed
    check_hook = hooks_dir / "invar.UserPromptSubmit.sh"
    if not check_hook.exists():
        return Success([])  # No hooks installed, nothing to sync

    # Check version in existing hook
    try:
        existing_content = check_hook.read_text()
        # Extract version from header comment
        version_match = re.search(PROTOCOL_VERSION_PATTERN, existing_content)
        old_version = version_match.group(1) if version_match else "unknown"

        if old_version != PROTOCOL_VERSION:
            console.print(f"[cyan]Updating Claude hooks: v{old_version} → v{PROTOCOL_VERSION}[/cyan]")
        else:
            # Still update to refresh INVAR.md content
            console.print("[dim]Refreshing Claude hooks...[/dim]")
    except OSError:
        pass

    updated: list[str] = []
    failed: list[str] = []

    for hook_type in HOOK_TYPES:
        result = generate_hook_content(hook_type, project_path)
        if isinstance(result, Failure):
            console.print(f"  [yellow]Warning:[/yellow] Failed to generate {hook_type}: {result.failure()}")
            failed.append(hook_type)
            continue

        content = result.unwrap()
        invar_hook = hooks_dir / f"invar.{hook_type}.sh"

        if invar_hook.exists():
            invar_hook.write_text(content)
            invar_hook.chmod(0o755)
            updated.append(hook_type)

    if updated:
        console.print(f"[green]✓[/green] Claude hooks synced ({len(updated)} files)")
    if failed:
        console.print(f"[yellow]⚠[/yellow] {len(failed)} hook(s) failed to sync")

    return Success(updated)


# @shell_complexity: Hook removal with backup restoration
def remove_claude_hooks(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """
    Remove Invar Claude Code hooks.

    Restores user hooks from backup if available.
    """
    hooks_dir = project_path / HOOKS_SUBDIR

    if not hooks_dir.exists():
        console.print("[yellow]No hooks directory found[/yellow]")
        return Success(None)

    console.print("[bold]Removing Invar Claude Code hooks...[/bold]")

    for hook_type in HOOK_TYPES:
        invar_hook = hooks_dir / f"invar.{hook_type}.sh"
        wrapper_hook = hooks_dir / f"{hook_type}.sh"
        backup_hook = hooks_dir / f"{hook_type}.sh.user_backup"

        # Remove Invar hook
        if invar_hook.exists():
            invar_hook.unlink()
            console.print(f"  [red]Removed[/red] invar.{hook_type}.sh")

        # Restore user backup if exists
        if backup_hook.exists():
            if wrapper_hook.exists():
                wrapper_hook.unlink()
            backup_hook.rename(wrapper_hook)
            console.print(f"  [green]Restored[/green] {hook_type}.sh (from backup)")
        elif wrapper_hook.exists():
            # Check if it's just an Invar wrapper
            content = wrapper_hook.read_text()
            if f"invar.{hook_type}.sh" in content and "user_backup" not in content:
                wrapper_hook.unlink()
                console.print(f"  [red]Removed[/red] {hook_type}.sh (Invar wrapper)")

    console.print("[bold green]✓ Invar hooks removed[/bold green]")
    return Success(None)


def disable_claude_hooks(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """Temporarily disable Invar hooks."""
    hooks_dir = project_path / HOOKS_SUBDIR

    if not hooks_dir.exists():
        return Failure("No hooks directory found")

    disabled_marker = hooks_dir / DISABLED_MARKER
    disabled_marker.touch()

    console.print("[yellow]✓ Invar hooks disabled[/yellow]")
    console.print(f"[dim]Remove {HOOKS_SUBDIR}/{DISABLED_MARKER} to re-enable[/dim]")
    return Success(None)


def enable_claude_hooks(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """Re-enable Invar hooks."""
    hooks_dir = project_path / HOOKS_SUBDIR
    disabled_marker = hooks_dir / DISABLED_MARKER

    if disabled_marker.exists():
        disabled_marker.unlink()
        console.print("[green]✓ Invar hooks enabled[/green]")
    else:
        console.print("[dim]Invar hooks were not disabled[/dim]")

    return Success(None)


# @shell_complexity: Status display with version extraction
def hooks_status(
    project_path: Path,
    console: Console,
) -> Result[dict[str, str], str]:
    """Check status of Claude Code hooks."""
    hooks_dir = project_path / HOOKS_SUBDIR

    status: dict[str, str] = {}

    if not hooks_dir.exists():
        console.print("[yellow]No hooks directory[/yellow]")
        return Success({"status": "not_installed"})

    disabled = (hooks_dir / DISABLED_MARKER).exists()
    if disabled:
        console.print("[yellow]⏸ Invar hooks disabled[/yellow]")
        status["status"] = "disabled"
    else:
        status["status"] = "enabled"

    for hook_type in HOOK_TYPES:
        invar_hook = hooks_dir / f"invar.{hook_type}.sh"
        if invar_hook.exists():
            status[hook_type] = "installed"
            # Try to get version
            try:
                content = invar_hook.read_text()
                match = re.search(PROTOCOL_VERSION_PATTERN, content)
                if match:
                    status[f"{hook_type}_version"] = match.group(1)
            except OSError:
                pass
        else:
            status[hook_type] = "not_installed"

    # Display status
    installed_count = sum(1 for h in HOOK_TYPES if status.get(h) == "installed")
    if installed_count == len(HOOK_TYPES):
        version = status.get("UserPromptSubmit_version", "?")
        console.print(f"[green]✓ All hooks installed (v{version})[/green]")
    elif installed_count > 0:
        console.print(f"[yellow]⚠ Partial installation ({installed_count}/{len(HOOK_TYPES)})[/yellow]")
    else:
        console.print("[dim]No Invar hooks installed[/dim]")

    return Success(status)
