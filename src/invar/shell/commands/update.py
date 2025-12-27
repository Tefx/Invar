"""
Update command for Invar.

DX-55: Now an alias for 'invar init' (unified idempotent command).
Maintained for backwards compatibility.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from invar.shell.commands.init import init as init_command

console = Console()


def update(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    check: bool = typer.Option(False, "--check", help="Preview changes"),
    force: bool = typer.Option(False, "--force", "-f", help="Update even if current"),
) -> None:
    """
    Alias for 'invar init' (DX-55).

    Maintained for backwards compatibility.
    Both commands are now idempotent and do the same thing.

    Use 'invar init --check' to preview changes.
    Use 'invar init --force' to refresh even if current.
    """
    console.print("[dim]Note: 'update' is now an alias for 'init'[/dim]")
    return init_command(path=path, check=check, force=force)
