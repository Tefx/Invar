"""
Update command for Invar.

Shell module: handles updating Invar-managed files to latest version.
DX-49: Uses three-region architecture for partial updates.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import typer
from returns.result import Failure, Result, Success
from rich.console import Console

from invar.shell.template_engine import (
    generate_from_manifest,
    get_templates_dir,
    load_manifest,
    parse_invar_regions,
    reconstruct_file,
    render_template_file,
)

console = Console()

# Version pattern: matches "v3.23" or "v3.23.1" or "5.0"
VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)(?:\.(\d+))?")


# @shell_orchestration: Version parsing helper for update command
def parse_version(text: str) -> tuple[int, int, int] | None:
    """
    Parse version string from text.

    >>> parse_version("Protocol v3.23")
    (3, 23, 0)
    >>> parse_version("v3.23.1")
    (3, 23, 1)
    >>> parse_version("version 5.0")
    (5, 0, 0)
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
    """Get version from manifest.toml."""
    templates_dir = get_templates_dir()
    manifest_result = load_manifest(templates_dir)
    if isinstance(manifest_result, Failure):
        return manifest_result

    manifest = manifest_result.unwrap()
    version_str = manifest.get("meta", {}).get("version", "0.0")
    version = parse_version(version_str)
    if version is None:
        return Failure("Could not parse version from manifest")
    return Success(version)


def format_version(version: tuple[int, int, int]) -> str:
    """Format version tuple as string."""
    if version[2] == 0:
        return f"v{version[0]}.{version[1]}"
    return f"v{version[0]}.{version[1]}.{version[2]}"


# @shell_complexity: File removal before overwrite requires branching
def update_fully_managed(path: Path, console: Console) -> Result[list[str], str]:
    """Update fully managed files (overwrite completely)."""
    # Files to overwrite from manifest
    overwrite_files = [
        "INVAR.md",
        ".invar/examples/",
    ]

    # Remove existing examples directory first
    examples_dest = path / ".invar" / "examples"
    if examples_dest.exists():
        try:
            shutil.rmtree(examples_dest)
        except OSError as e:
            return Failure(f"Failed to remove old examples: {e}")

    # Remove existing INVAR.md to allow overwrite
    invar_md = path / "INVAR.md"
    if invar_md.exists():
        try:
            invar_md.unlink()
        except OSError as e:
            return Failure(f"Failed to remove old INVAR.md: {e}")

    return generate_from_manifest(path, syntax="cli", files_to_generate=overwrite_files)


# @shell_complexity: Partial update with region preservation
def update_partially_managed(
    path: Path, console: Console, syntax: str = "cli"
) -> Result[list[str], str]:
    """Update partially managed files, preserving user regions."""
    templates_dir = get_templates_dir()
    manifest_result = load_manifest(templates_dir)
    if isinstance(manifest_result, Failure):
        return manifest_result

    manifest = manifest_result.unwrap()
    # Copy to avoid mutating cached manifest
    variables = {**manifest.get("variables", {}), "syntax": syntax}

    updated: list[str] = []

    # Files to merge with region-based updates.
    # Each tuple: (destination, template, region_name)
    # CLAUDE.md uses "managed" region; SKILL.md files use "skill" region.
    merge_files = [
        ("CLAUDE.md", "config/CLAUDE.md.jinja", "managed"),
        (".claude/skills/develop/SKILL.md", "skills/develop/SKILL.md.jinja", "skill"),
        (".claude/skills/investigate/SKILL.md", "skills/investigate/SKILL.md.jinja", "skill"),
        (".claude/skills/propose/SKILL.md", "skills/propose/SKILL.md.jinja", "skill"),
        (".claude/skills/review/SKILL.md", "skills/review/SKILL.md.jinja", "skill"),
    ]

    for dest_rel, template_rel, region_name in merge_files:
        dest_file = path / dest_rel
        template_path = templates_dir / template_rel

        if not dest_file.exists():
            continue  # Skip if file doesn't exist (created by init)

        if not template_path.exists():
            continue

        # Render new template content
        render_result = render_template_file(template_path, variables)
        if isinstance(render_result, Failure):
            continue

        new_content = render_result.unwrap()

        # Parse existing file for regions
        try:
            existing_content = dest_file.read_text()
        except OSError:
            continue

        parsed = parse_invar_regions(existing_content)

        if not parsed.has_regions:
            # No regions in existing file - skip (don't overwrite user content)
            console.print(f"[dim]Skipped {dest_rel} (no region markers)[/dim]")
            continue

        # Parse new content for the appropriate region
        new_parsed = parse_invar_regions(new_content)
        if region_name not in new_parsed.regions:
            continue

        # Update the region, preserve user/extensions regions
        updates = {region_name: new_parsed.regions[region_name].content}
        result_content = reconstruct_file(parsed, updates)

        try:
            dest_file.write_text(result_content)
            updated.append(dest_rel)
        except OSError:
            continue

    return Success(updated)


# @shell_complexity: Update command with version comparison and region preservation
def update(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Update even if already at latest version"
    ),
    check: bool = typer.Option(
        False, "--check", help="Check for updates without applying"
    ),
    syntax: str = typer.Option(
        "cli", "--syntax", help="Command syntax: cli or mcp"
    ),
) -> None:
    """
    Update Invar-managed files to latest version.

    DX-49: Uses three-region architecture:
    - Fully managed (INVAR.md, examples): Overwritten completely
    - Partially managed (CLAUDE.md, skills): Only managed regions updated

    User regions (<!--invar:user-->) are always preserved.

    Use --check to see if updates are available without applying them.
    Use --force to update even if already at latest version.
    Use --syntax mcp for MCP command syntax in templates.
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
    console.print("\n[bold]Updating Invar files...[/bold]")
    console.print(f"  Version: {current_str} → {template_str}")
    console.print()

    # Update fully managed files (overwrite)
    result = update_fully_managed(path, console)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)
    for updated_file in result.unwrap():
        console.print(f"[green]Updated[/green] {updated_file}")

    # Update partially managed files (preserve user regions)
    result = update_partially_managed(path, console, syntax)
    if isinstance(result, Success):
        for updated_file in result.unwrap():
            console.print(f"[green]Merged[/green] {updated_file} (user regions preserved)")

    # Summary
    console.print()
    console.print("[dim]Region preservation:[/dim]")
    console.print("[dim]  ✓ <!--invar:managed--> sections updated[/dim]")
    console.print("[dim]  ○ <!--invar:user--> sections preserved[/dim]")
    console.print("[dim]  ○ .invar/context.md unchanged[/dim]")
