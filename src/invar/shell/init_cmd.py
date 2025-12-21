"""
Init command for Invar.

Shell module: handles project initialization.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure, Success
from rich.console import Console

from invar.shell.templates import (
    add_config,
    add_invar_reference,
    copy_examples_directory,
    copy_template,
    create_directories,
    detect_agent_configs,
    install_hooks,
)

console = Console()


def init(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    dirs: bool = typer.Option(
        None, "--dirs/--no-dirs", help="Create src/core and src/shell directories"
    ),
    hooks: bool = typer.Option(
        True, "--hooks/--no-hooks", help="Install pre-commit hooks (default: ON)"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Accept defaults without prompting"
    ),
) -> None:
    """
    Initialize Invar configuration in a project.

    Works with or without pyproject.toml:
    - If pyproject.toml exists: adds [tool.invar.guard] section
    - Otherwise: creates invar.toml

    Use --dirs to always create directories, --no-dirs to skip.
    Use --no-hooks to skip pre-commit hooks installation.
    Use --yes to accept defaults without prompting.
    """
    config_result = add_config(path, console)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)
    config_added = config_result.unwrap()

    # Create INVAR.md (protocol)
    result = copy_template("INVAR.md", path)
    if isinstance(result, Success) and result.unwrap():
        console.print("[green]Created[/green] INVAR.md (Invar Protocol)")

    # Copy examples directory
    copy_examples_directory(path, console)

    # Create .invar directory structure
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

    # Agent detection and configuration (DX-11)
    console.print("\n[bold]Checking for agent configurations...[/bold]")
    agent_status = detect_agent_configs(path)

    # Handle existing configs
    for agent, status in agent_status.items():
        if status == "configured":
            console.print(f"  [green]✓[/green] {agent}: already configured")
        elif status == "found":
            # Ask before modifying
            if yes or typer.confirm(f"  Add Invar reference to {agent} config?", default=True):
                add_invar_reference(path, agent, console)
            else:
                console.print(f"  [yellow]○[/yellow] {agent}: skipped")

    # Handle missing CLAUDE.md specifically
    claude_status = agent_status.get("claude", "not_found")
    if claude_status == "not_found":
        # Create CLAUDE.md from template
        result = copy_template("CLAUDE.md.template", path, "CLAUDE.md")
        if isinstance(result, Success) and result.unwrap():
            console.print("[green]Created[/green] CLAUDE.md (project guide)")
        elif isinstance(result, Failure):
            console.print(f"[yellow]Warning:[/yellow] {result.failure()}")

    # Show guidance for other agents
    other_missing = [
        agent for agent, status in agent_status.items()
        if status == "not_found" and agent != "claude"
    ]
    if other_missing:
        console.print("\n[dim]For other agents, add to their config:[/dim]")
        console.print('[dim]  "Follow the Invar Protocol in INVAR.md"[/dim]')

    # Handle directory creation based on --dirs flag
    if dirs is not False:
        create_directories(path, console)

    # Install pre-commit hooks if requested
    if hooks:
        install_hooks(path, console)

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")
