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
    configure_mcp_server,
    copy_examples_directory,
    copy_template,
    create_agent_config,
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
    agent_result = detect_agent_configs(path)
    if isinstance(agent_result, Failure):
        console.print(f"[yellow]Warning:[/yellow] {agent_result.failure()}")
        agent_status: dict[str, str] = {}
    else:
        agent_status = agent_result.unwrap()

    # Handle agent configs (DX-11, DX-17)
    for agent, status in agent_status.items():
        if status == "configured":
            console.print(f"  [green]✓[/green] {agent}: already configured")
        elif status == "found":
            # Existing file without Invar reference - ask before modifying
            if yes or typer.confirm(f"  Add Invar reference to {agent} config?", default=True):
                add_invar_reference(path, agent, console)
            else:
                console.print(f"  [yellow]○[/yellow] {agent}: skipped")
        elif status == "not_found":
            # Create full template with workflow enforcement (DX-17)
            create_agent_config(path, agent, console)

    # Configure MCP server (DX-16)
    console.print("\n[bold]Configuring MCP server...[/bold]")
    mcp_result = configure_mcp_server(path, console)
    if isinstance(mcp_result, Success):
        configured_agents = mcp_result.unwrap()
        if configured_agents:
            console.print(f"[green]MCP ready for:[/green] {', '.join(configured_agents)}")
        else:
            console.print("[dim]See .invar/mcp-setup.md for manual MCP configuration[/dim]")
    else:
        console.print(f"[yellow]Warning:[/yellow] {mcp_result.failure()}")

    # Handle directory creation based on --dirs flag
    if dirs is not False:
        create_directories(path, console)

    # Install pre-commit hooks if requested
    if hooks:
        install_hooks(path, console)

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")
