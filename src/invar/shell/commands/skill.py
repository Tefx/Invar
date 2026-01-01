"""
Skill management command for Invar.

LX-07: Extension Skills - CLI interface for skill management.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure, Result
from rich.console import Console
from rich.table import Table

from invar.shell.skill_manager import (
    add_skill,
    list_skills,
    remove_skill,
    update_skill,
)

PROJECT_SKILLS_DIR = ".claude/skills"

console = Console()

app = typer.Typer(help="Manage extension skills")


def _handle_result(result: Result[object, str]) -> None:
    """Print error message if result is Failure."""
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Typer callback with docstring examples
@app.callback(invoke_without_command=True)
def skill_callback(ctx: typer.Context) -> None:
    """
    Manage Invar extension skills.

    Extension skills add specialized capabilities like acceptance testing
    and security auditing to your project.

    \b
    Examples:
        invar skill              # List all skills
        invar skill add security # Install security skill
        invar skill remove security
        invar skill update security
    """
    # If no subcommand, show list
    if ctx.invoked_subcommand is None:
        list_cmd(Path())


# @invar:allow entry_point_too_thick: Rich table formatting for CLI output
@app.command("list")
def list_cmd(
    path: Path = typer.Argument(Path(), help="Project root directory"),
) -> None:
    """List available extension skills."""
    path = path.resolve()

    result = list_skills(path, console)
    if isinstance(result, Failure):
        _handle_result(result)
        return

    skills = result.unwrap()

    # Create rich table
    table = Table(title="Extension Skills", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Tier", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Description")

    # Status styling
    status_styles = {
        "installed": "[green]installed[/green]",
        "available": "[blue]available[/blue]",
        "pending_discussion": "[yellow]pending[/yellow]",
    }

    for skill in skills:
        status_display = status_styles.get(skill.status, skill.status)
        isolation = " [dim](isolated)[/dim]" if skill.isolation else ""

        table.add_row(
            f"/{skill.name}",
            skill.tier,
            status_display,
            f"{skill.description}{isolation}",
        )

    console.print(table)
    console.print()
    console.print("[dim]Use 'invar skill add <name>' to install a skill[/dim]")


# @invar:allow entry_point_too_thick: CLI output with usage hints
@app.command("add")
def add_cmd(
    name: str = typer.Argument(..., help="Skill name to add"),
    path: Path = typer.Option(Path(), "--path", "-p", help="Project root"),
) -> None:
    """Add or update an extension skill (idempotent)."""
    path = path.resolve()

    # DX-71: add_skill now prints its own status (Adding/Updating)
    result = add_skill(name, path, console)

    if isinstance(result, Failure):
        _handle_result(result)
        return

    console.print(f"[green]{result.unwrap()}[/green]")
    console.print()
    console.print(f"[dim]Use '/{name}' in Claude Code to invoke the skill[/dim]")


# @invar:allow entry_point_too_thick: CLI with confirmation dialog
@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(..., help="Skill name to remove"),
    path: Path = typer.Option(Path(), "--path", "-p", help="Project root"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal"),
) -> None:
    """Remove an extension skill from the project."""
    from invar.shell.skill_manager import has_user_extensions

    path = path.resolve()
    skill_dir = path / PROJECT_SKILLS_DIR / name

    # DX-71 review: Check existence before any user interaction
    if not skill_dir.exists():
        console.print(f"[red]Error:[/red] Skill not installed: {name}")
        raise typer.Exit(1)

    # DX-71: Check extensions FIRST to avoid confusing confirmation→failure flow
    if not force:
        # If skill has user extensions, require --force (no confirmation dialog)
        if has_user_extensions(skill_dir):
            console.print(
                f"[yellow]Warning:[/yellow] Skill '{name}' has custom extensions "
                "content that will be lost."
            )
            console.print(
                "[dim]Use --force to confirm removal, or backup extensions first.[/dim]"
            )
            raise typer.Exit(1)

        # No extensions - show simple confirmation dialog
        confirm = typer.confirm(f"Remove skill '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    console.print(f"[bold]Removing skill:[/bold] {name}")
    # force=True here because we've already done CLI-level checks
    result = remove_skill(name, path, console, force=True)

    if isinstance(result, Failure):
        _handle_result(result)
        return

    console.print(f"[green]{result.unwrap()}[/green]")


@app.command("update")
def update_cmd(
    name: str = typer.Argument(..., help="Skill name to update"),
    path: Path = typer.Option(Path(), "--path", "-p", help="Project root"),
) -> None:
    """Update an extension skill (deprecated, use 'add' instead)."""
    path = path.resolve()

    # DX-71: update_skill now shows deprecation notice and delegates to add_skill
    result = update_skill(name, path, console)

    if isinstance(result, Failure):
        _handle_result(result)
        return

    console.print(f"[green]{result.unwrap()}[/green]")
