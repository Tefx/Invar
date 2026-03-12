"""DX-91 developer sync command.

Regenerates only DX-91 managed artifacts for the Invar repository:
- managed instruction block (default target: CLAUDE.md)
- INVAR.md
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure
from rich.console import Console

from invar.core.sync_helpers import SyncConfig
from invar.shell.commands.template_sync import sync_templates
from invar.shell.template_engine import is_invar_project

console = Console()


# @shell_complexity: CLI entrypoint handles validation, config wiring, and report output.
def dev_sync(
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
    """Synchronize DX-91 managed template output."""
    if not is_invar_project(path):
        console.print("[red]Error:[/red] This command is only for the Invar project itself.")
        console.print("[dim]Use 'invar init' for other projects.[/dim]")
        raise typer.Exit(1)

    config = SyncConfig(
        syntax="mcp",
        language="python",
        inject_project_additions=True,
        force=force,
        check=check,
        template_root=template_root,
        target_file=file,
    )

    result = sync_templates(path, config)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    report = result.unwrap()
    label_created = "Would create" if check else "Created"
    label_updated = "Would update" if check else "Updated"

    for entry in report.created:
        console.print(f"[green]{label_created}[/green] {entry}")
    for entry in report.updated:
        console.print(f"[cyan]{label_updated}[/cyan] {entry}")
    for entry in report.skipped:
        console.print(f"[dim]Skipped[/dim] {entry} (unchanged)")
    for entry in report.errors:
        console.print(f"[yellow]Warning:[/yellow] {entry}")

    if check:
        console.print("[bold]Preview mode complete.[/bold]")
    else:
        console.print("[bold green]DX-91 dev sync complete.[/bold green]")
