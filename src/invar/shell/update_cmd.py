"""
Update command for Invar.

Shell module: handles updating Invar-managed files to latest version.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from returns.result import Failure, Result, Success
from rich.console import Console

from invar.shell.templates import copy_examples_directory, copy_template, get_template_path

console = Console()

# Version pattern: matches "v3.23" or "v3.23.1"
VERSION_PATTERN = re.compile(r"v(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """
    Parse version string from text.

    >>> parse_version("Protocol v3.23")
    (3, 23, 0)
    >>> parse_version("v3.23.1")
    (3, 23, 1)
    >>> parse_version("no version here")
    """
    match = VERSION_PATTERN.search(text)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)
    return None


def get_current_version(path: Path) -> Result[tuple[int, int, int], str]:
    """Get version from current INVAR.md file."""
    invar_md = path / "INVAR.md"
    if not invar_md.exists():
        return Failure("INVAR.md not found. Run 'invar init' first.")

    try:
        content = invar_md.read_text()
        version = parse_version(content)
        if version is None:
            return Failure("Could not parse version from INVAR.md")
        return Success(version)
    except OSError as e:
        return Failure(f"Failed to read INVAR.md: {e}")


def get_template_version() -> Result[tuple[int, int, int], str]:
    """Get version from template INVAR.md."""
    template_result = get_template_path("INVAR.md")
    if isinstance(template_result, Failure):
        return template_result

    template_path = template_result.unwrap()
    try:
        content = template_path.read_text()
        version = parse_version(content)
        if version is None:
            return Failure("Could not parse version from template")
        return Success(version)
    except OSError as e:
        return Failure(f"Failed to read template: {e}")


def format_version(version: tuple[int, int, int]) -> str:
    """Format version tuple as string."""
    if version[2] == 0:
        return f"v{version[0]}.{version[1]}"
    return f"v{version[0]}.{version[1]}.{version[2]}"


def update_invar_md(path: Path, console: Console) -> Result[bool, str]:
    """Update INVAR.md by overwriting with template."""
    template_result = get_template_path("INVAR.md")
    if isinstance(template_result, Failure):
        return template_result

    template_path = template_result.unwrap()
    dest_file = path / "INVAR.md"

    try:
        dest_file.write_text(template_path.read_text())
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to update INVAR.md: {e}")


def update_examples(path: Path, console: Console) -> Result[bool, str]:
    """Update .invar/examples/ directory."""
    import shutil

    examples_dest = path / ".invar" / "examples"

    # Remove existing examples
    if examples_dest.exists():
        try:
            shutil.rmtree(examples_dest)
        except OSError as e:
            return Failure(f"Failed to remove old examples: {e}")

    # Copy new examples
    return copy_examples_directory(path, console)


def update(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Update even if already at latest version"
    ),
    check: bool = typer.Option(
        False, "--check", help="Check for updates without applying"
    ),
) -> None:
    """
    Update Invar-managed files to latest version.

    Updates INVAR.md and .invar/examples/ from the installed python-invar package.
    User-managed files (CLAUDE.md, .invar/context.md) are never modified.

    Use --check to see if updates are available without applying them.
    Use --force to update even if already at latest version.
    """
    # Get current version
    current_result = get_current_version(path)
    if isinstance(current_result, Failure):
        console.print(f"[red]Error:[/red] {current_result.failure()}")
        raise typer.Exit(1)
    current_version = current_result.unwrap()

    # Get template version
    template_result = get_template_version()
    if isinstance(template_result, Failure):
        console.print(f"[red]Error:[/red] {template_result.failure()}")
        raise typer.Exit(1)
    template_version = template_result.unwrap()

    current_str = format_version(current_version)
    template_str = format_version(template_version)

    # Compare versions
    needs_update = template_version > current_version

    if check:
        # Check mode: just report status
        if needs_update:
            console.print(f"[yellow]Update available:[/yellow] {current_str} → {template_str}")
        else:
            console.print(f"[green]Up to date:[/green] {current_str}")
        return

    if not needs_update and not force:
        console.print(f"[green]Already at latest version:[/green] {current_str}")
        console.print("[dim]Use --force to update anyway[/dim]")
        return

    # Perform update
    console.print(f"\n[bold]Updating Invar files...[/bold]")
    console.print(f"  Version: {current_str} → {template_str}")
    console.print()

    # Update INVAR.md
    result = update_invar_md(path, console)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)
    console.print(f"[green]Updated[/green] INVAR.md ({template_str})")

    # Update examples
    result = update_examples(path, console)
    if isinstance(result, Failure):
        console.print(f"[yellow]Warning:[/yellow] {result.failure()}")
    else:
        console.print("[green]Updated[/green] .invar/examples/")

    # Remind about user-managed files
    console.print()
    console.print("[dim]User-managed files unchanged:[/dim]")
    console.print("[dim]  ○ CLAUDE.md[/dim]")
    console.print("[dim]  ○ .invar/context.md[/dim]")
    console.print("[dim]  ○ pyproject.toml [tool.invar][/dim]")
