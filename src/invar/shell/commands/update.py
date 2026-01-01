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
    preview: bool = typer.Option(False, "--preview", "--check", help="Preview changes (dry run)"),
) -> None:
    """
    Alias for 'invar init' (DX-55).

    Maintained for backwards compatibility.
    Both commands are now idempotent and do the same thing.

    Use 'invar init --preview' to preview changes.
    """
    console.print("[dim]Note: 'update' is now an alias for 'init'[/dim]")
    # Call init with matching parameters (DX-70 signature)
    return init_command(
        path=path,
        claude=False,
        pi=False,
        language=None,
        preview=preview,
    )
