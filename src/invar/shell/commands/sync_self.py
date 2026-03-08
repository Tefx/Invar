"""
DX-56: Developer sync command for Invar (unified sync engine).

Shell module: Special command for updating Invar's own project files.
Uses MCP syntax and injects project-additions.md content.

CLI: `invar dev sync` (formerly `invar sync-self`)

This is a thin wrapper around the unified template_sync engine.
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


# @shell_complexity: CLI command with result display and multiple output branches
def sync_self(
    path: Path = typer.Argument(Path(), help="Invar project root"),
    check: bool = typer.Option(
        False, "--check", help="Preview changes without applying"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Update even if already current"
    ),
) -> None:
    """
    Synchronize Invar's own project files from templates.

    DX-56: Now uses unified sync engine with manifest-driven file lists.

    This command is for the Invar project only. It:
    - Uses MCP syntax (invar_guard, invar_map, etc.)
    - Injects .invar/project-additions.md into project region
    - Updates managed regions while preserving user content
    - Handles DX-55 state recovery (intact/partial/missing/absent)

    Use --check to preview changes without applying them.
    Use --force to update even if already current.
    """
    # Verify this is the Invar project
    if not is_invar_project(path):
        console.print("[red]Error:[/red] This command is only for the Invar project itself.")
        console.print("[dim]Use 'invar init' for other projects.[/dim]")
        raise typer.Exit(1)

    console.print("[bold]Syncing Invar project files...[/bold]")
    console.print("[dim]Using MCP syntax for templates[/dim]")
    console.print()

    # Configure for Invar project
    config = SyncConfig(
        syntax="mcp",
        inject_project_additions=True,
        force=force,
        check=check,
    )

    # Run unified sync engine
    result = sync_templates(path, config)

    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    report = result.unwrap()

    # Display results
    if check:
        console.print("[bold]Preview mode - no changes applied[/bold]")
        console.print()

    for file in report.created:
        action = "Would create" if check else "Created"
        console.print(f"[green]{action}[/green] {file}")

    for file in report.updated:
        action = "Would update" if check else "Updated"
        console.print(f"[cyan]{action}[/cyan] {file}")

    for file in report.skipped:
        console.print(f"[dim]Skipped[/dim] {file} (unchanged)")

    for error in report.errors:
        console.print(f"[yellow]Warning:[/yellow] {error}")

    # Summary
    console.print()
    if check:
        console.print("[bold]Dry run complete.[/bold]")
        console.print(f"  Would create: {len(report.created)} files")
        console.print(f"  Would update: {len(report.updated)} files")
        console.print(f"  Would skip: {len(report.skipped)} files (unchanged)")
    else:
        console.print("[bold green]Sync complete![/bold green]")
        console.print(f"  Created: {len(report.created)} files")
        console.print(f"  Updated: {len(report.updated)} files")
        console.print(f"  Skipped: {len(report.skipped)} files (unchanged)")

    console.print()
    console.print("[dim]MCP syntax applied:[/dim]")
    console.print("[dim]  invar_guard(changed=true) instead of invar guard --changed[/dim]")
    console.print("[dim]  invar_map(top=10) instead of invar map --top 10[/dim]")
