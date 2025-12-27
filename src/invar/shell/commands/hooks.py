"""
Hooks management command for Invar.

DX-57: Claude Code hooks installation, removal, and management.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure, Result
from rich.console import Console

from invar.shell.claude_hooks import (
    disable_claude_hooks,
    enable_claude_hooks,
    hooks_status,
    install_claude_hooks,
    remove_claude_hooks,
    sync_claude_hooks,
)

console = Console()


def _handle_result(result: Result[object, str]) -> None:
    """Print error message if result is Failure."""
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")

app = typer.Typer(help="Manage Claude Code hooks")


# @invar:allow entry_point_too_thick: Typer command with options and docstring
@app.callback(invoke_without_command=True)
def hooks(
    ctx: typer.Context,
    path: Path = typer.Argument(Path(), help="Project root directory"),
    remove: bool = typer.Option(False, "--remove", help="Remove Invar hooks"),
    disable: bool = typer.Option(False, "--disable", help="Temporarily disable hooks"),
    enable: bool = typer.Option(False, "--enable", help="Re-enable disabled hooks"),
    install: bool = typer.Option(False, "--install", help="Install hooks"),
    sync: bool = typer.Option(False, "--sync", help="Sync hooks with current INVAR.md"),
) -> None:
    """
    Manage Claude Code hooks for Invar.

    Without flags, shows current hooks status.

    \b
    Examples:
        invar hooks                  # Show status
        invar hooks --install        # Install hooks
        invar hooks --remove         # Permanently remove hooks
        invar hooks --disable        # Temporarily disable
        invar hooks --enable         # Re-enable
        invar hooks --sync           # Update with current INVAR.md
    """
    path = path.resolve()

    if remove:
        _handle_result(remove_claude_hooks(path, console))
    elif disable:
        _handle_result(disable_claude_hooks(path, console))
    elif enable:
        _handle_result(enable_claude_hooks(path, console))
    elif install:
        _handle_result(install_claude_hooks(path, console))
    elif sync:
        _handle_result(sync_claude_hooks(path, console))
    else:
        # Default: show status
        _handle_result(hooks_status(path, console))
