"""Backward-compatible alias for `invar dev sync`.

DX-91 retains `invar dev sync` as internal command; `sync-self` stays hidden.
"""

from __future__ import annotations

from pathlib import Path

import typer

from invar.shell.commands.dev_sync import dev_sync


def sync_self(
    path: Path = typer.Argument(Path(), help="Invar project root"),
    check: bool = typer.Option(False, "--check", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", "-f", help="Write even if unchanged"),
    file: str = typer.Option("CLAUDE.md", "--file", help="Managed instruction file target"),
    template_root: str | None = typer.Option(
        None,
        "--template-root",
        help="Template root (absolute or relative to project root)",
    ),
) -> None:
    """Deprecated alias routed to `dev_sync`."""
    dev_sync(path=path, check=check, force=force, file=file, template_root=template_root)
