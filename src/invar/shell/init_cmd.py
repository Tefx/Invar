"""
Init command for Invar.

Shell module: handles project initialization.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure, Success
from rich.console import Console

from invar.shell.templates import add_config, copy_template, create_directories, install_hooks

console = Console()


def init(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    dirs: bool = typer.Option(
        None, "--dirs/--no-dirs", help="Create src/core and src/shell directories"
    ),
    hooks: bool = typer.Option(
        True, "--hooks/--no-hooks", help="Install pre-commit hooks (default: ON)"
    ),
) -> None:
    """
    Initialize Invar configuration in a project.

    Works with or without pyproject.toml:
    - If pyproject.toml exists: adds [tool.invar.guard] section
    - Otherwise: creates invar.toml

    Use --dirs to always create directories, --no-dirs to skip.
    Use --no-hooks to skip pre-commit hooks installation.
    """
    config_result = add_config(path, console)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)
    config_added = config_result.unwrap()

    result = copy_template("INVAR.md", path)
    if isinstance(result, Success) and result.unwrap():
        console.print("[green]Created[/green] INVAR.md (Invar Protocol)")

    result = copy_template("CLAUDE.md.template", path, "CLAUDE.md")
    if isinstance(result, Success) and result.unwrap():
        console.print("[green]Created[/green] CLAUDE.md (customize for your project)")

    # Handle directory creation based on --dirs flag
    if dirs is not False:
        create_directories(path, console)

    invar_dir = path / ".invar"
    if not invar_dir.exists():
        invar_dir.mkdir()
        result = copy_template("context.md.template", invar_dir, "context.md")
        if isinstance(result, Success) and result.unwrap():
            console.print("[green]Created[/green] .invar/context.md (context management)")

    # Create proposals directory for protocol governance
    proposals_dir = invar_dir / "proposals"
    if not proposals_dir.exists():
        proposals_dir.mkdir()
        result = copy_template("proposal.md.template", proposals_dir, "TEMPLATE.md")
        if isinstance(result, Success) and result.unwrap():
            console.print("[green]Created[/green] .invar/proposals/TEMPLATE.md")

    # Install pre-commit hooks if requested
    if hooks:
        install_hooks(path, console)

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")
