"""
Pi Coding Agent hooks for Invar.

LX-04: Full feature parity with Claude Code hooks.
- pytest/crosshair blocking via tool_call
- Protocol injection via pi.send() for long conversations
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader
from returns.result import Failure, Result, Success

from invar.core.language import detect_language_from_markers
from invar.core.template_helpers import escape_for_js_template
from invar.shell.claude_hooks import detect_syntax, get_invar_md_content

if TYPE_CHECKING:
    from rich.console import Console

# Pi hooks directory
PI_HOOKS_DIR = ".pi/hooks"
PROTOCOL_VERSION = "5.0"


def get_pi_templates_path() -> Path:
    """Get the path to Pi hook templates."""
    return Path(__file__).parent.parent / "templates" / "hooks" / "pi"


# @shell_complexity: Template rendering with protocol escaping
def generate_pi_hook_content(project_path: Path) -> Result[str, str]:
    """Generate Pi hook content from template."""
    templates_path = get_pi_templates_path()
    template_file = "invar.ts.jinja"

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

        # Get and escape protocol content for JS template literal
        protocol_content = get_invar_md_content(project_path)
        protocol_escaped = escape_for_js_template(protocol_content)

        # Build context for template
        context = {
            "protocol_version": PROTOCOL_VERSION,
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
            "guard_cmd": guard_cmd,
            "language": language,
            "invar_protocol_escaped": protocol_escaped,
        }

        content = template.render(**context)
        return Success(content)
    except Exception as e:
        return Failure(f"Failed to generate Pi hook: {e}")


def install_pi_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Install Pi hooks for Invar.

    Creates .pi/hooks/invar.ts with:
    - pytest/crosshair blocking
    - Protocol injection for long conversations
    """
    hooks_dir = project_path / PI_HOOKS_DIR
    hooks_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold]Installing Pi hooks (LX-04)...[/bold]")
    console.print("  Hooks will:")
    console.print("    ✓ Block pytest/crosshair → redirect to invar guard")
    console.print("    ✓ Refresh protocol in long conversations")
    console.print("")

    result = generate_pi_hook_content(project_path)
    if isinstance(result, Failure):
        console.print(f"  [red]Failed:[/red] {result.failure()}")
        return Failure(result.failure())

    content = result.unwrap()
    hook_file = hooks_dir / "invar.ts"
    hook_file.write_text(content)

    console.print(f"  [green]Created[/green] {PI_HOOKS_DIR}/invar.ts")
    console.print("\n  [bold green]✓ Pi hooks installed[/bold green]")
    console.print("  [dim]Requires: Pi coding agent with hooks support[/dim]")
    console.print("  [yellow]⚠ Restart Pi session for hooks to take effect[/yellow]")

    return Success(["invar.ts"])


# @shell_complexity: Version detection and conditional update logic
def sync_pi_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Update Pi hooks with current INVAR.md content.

    Called during `invar init` to ensure hooks stay in sync with protocol.
    Only updates if Pi hooks are already installed.
    """
    hooks_dir = project_path / PI_HOOKS_DIR
    hook_file = hooks_dir / "invar.ts"

    if not hook_file.exists():
        return Success([])  # No hooks installed, nothing to sync

    # Check version in existing hook
    try:
        existing_content = hook_file.read_text()
        version_match = re.search(r"Protocol: v([\d.]+)", existing_content)
        old_version = version_match.group(1) if version_match else "unknown"

        if old_version != PROTOCOL_VERSION:
            console.print(f"[cyan]Updating Pi hooks: v{old_version} → v{PROTOCOL_VERSION}[/cyan]")
        else:
            console.print("[dim]Refreshing Pi hooks...[/dim]")
    except OSError:
        pass

    result = generate_pi_hook_content(project_path)
    if isinstance(result, Failure):
        console.print(f"  [yellow]Warning:[/yellow] Failed to generate Pi hook: {result.failure()}")
        return Failure(result.failure())

    content = result.unwrap()
    hook_file.write_text(content)
    console.print("[green]✓[/green] Pi hooks synced")

    return Success(["invar.ts"])


def remove_pi_hooks(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """Remove Pi hooks."""
    hooks_dir = project_path / PI_HOOKS_DIR
    hook_file = hooks_dir / "invar.ts"

    if hook_file.exists():
        hook_file.unlink()
        console.print(f"  [red]Removed[/red] {PI_HOOKS_DIR}/invar.ts")

        # Remove directory if empty
        try:
            hooks_dir.rmdir()
            console.print(f"  [red]Removed[/red] {PI_HOOKS_DIR}/")
        except OSError:
            pass  # Directory not empty, keep it

        console.print("[bold green]✓ Pi hooks removed[/bold green]")
    else:
        console.print("[dim]No Pi hooks installed[/dim]")

    return Success(None)


def pi_hooks_status(
    project_path: Path,
    console: Console,
) -> Result[dict[str, str], str]:
    """Check status of Pi hooks."""
    hooks_dir = project_path / PI_HOOKS_DIR
    hook_file = hooks_dir / "invar.ts"

    status: dict[str, str] = {}

    if not hook_file.exists():
        console.print("[dim]No Pi hooks installed[/dim]")
        return Success({"status": "not_installed"})

    status["status"] = "installed"

    # Try to get version
    try:
        content = hook_file.read_text()
        match = re.search(r"Protocol: v([\d.]+)", content)
        if match:
            version = match.group(1)
            status["version"] = version
            console.print(f"[green]✓ Pi hooks installed (v{version})[/green]")
        else:
            console.print("[green]✓ Pi hooks installed[/green]")
    except OSError:
        console.print("[green]✓ Pi hooks installed[/green]")

    return Success(status)
