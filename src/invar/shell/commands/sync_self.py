"""
Sync-self command for Invar.

Shell module: Special command for updating Invar's own project files.
DX-49: Uses MCP syntax and injects project-additions.md content.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure
from rich.console import Console

from invar.shell.template_engine import (
    get_templates_dir,
    is_invar_project,
    load_manifest,
    parse_invar_regions,
    reconstruct_file,
    render_template_file,
)

console = Console()


# @shell_complexity: Sync-self with project injection and MCP syntax
def sync_self(
    path: Path = typer.Argument(Path(), help="Invar project root"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be updated without making changes"
    ),
) -> None:
    """
    Synchronize Invar's own project files from templates.

    This command is for the Invar project only. It:
    - Uses MCP syntax (invar_guard, invar_map, etc.)
    - Injects .invar/project-additions.md into project region
    - Updates managed regions while preserving user content

    Use --dry-run to preview changes without applying them.
    """
    # Verify this is the Invar project
    if not is_invar_project(path):
        console.print("[red]Error:[/red] This command is only for the Invar project itself.")
        console.print("[dim]Use 'invar update' for other projects.[/dim]")
        raise typer.Exit(1)

    console.print("[bold]Syncing Invar project files...[/bold]")
    console.print("[dim]Using MCP syntax for templates[/dim]")
    console.print()

    templates_dir = get_templates_dir()
    manifest_result = load_manifest(templates_dir)
    if isinstance(manifest_result, Failure):
        console.print(f"[red]Error:[/red] {manifest_result.failure()}")
        raise typer.Exit(1)

    manifest = manifest_result.unwrap()
    variables = manifest.get("variables", {})
    variables["syntax"] = "mcp"  # Always MCP for Invar project

    # Load project-additions.md if it exists
    project_additions_path = path / ".invar" / "project-additions.md"
    project_additions = ""
    if project_additions_path.exists():
        try:
            project_additions = project_additions_path.read_text()
            console.print(f"[dim]Loaded {project_additions_path}[/dim]")
        except OSError:
            pass

    # Files to sync
    sync_files = [
        ("CLAUDE.md", "config/CLAUDE.md.jinja"),
        (".claude/skills/develop/SKILL.md", "skills/develop/SKILL.md.jinja"),
        (".claude/skills/investigate/SKILL.md", "skills/investigate/SKILL.md.jinja"),
        (".claude/skills/propose/SKILL.md", "skills/propose/SKILL.md.jinja"),
        (".claude/skills/review/SKILL.md", "skills/review/SKILL.md.jinja"),
    ]

    updated_files: list[str] = []
    skipped_files: list[str] = []

    for dest_rel, template_rel in sync_files:
        dest_file = path / dest_rel
        template_path = templates_dir / template_rel

        if not template_path.exists():
            console.print(f"[yellow]Warning:[/yellow] Template not found: {template_rel}")
            continue

        # Render new template content
        render_result = render_template_file(template_path, variables)
        if isinstance(render_result, Failure):
            console.print(f"[yellow]Warning:[/yellow] Failed to render {template_rel}")
            continue

        new_content = render_result.unwrap()

        # Parse new content for managed region
        new_parsed = parse_invar_regions(new_content)
        if "managed" not in new_parsed.regions:
            console.print(f"[yellow]Warning:[/yellow] No managed region in template: {template_rel}")
            continue

        # Check if destination exists
        if not dest_file.exists():
            # New file - create with all regions
            if dry_run:
                console.print(f"[cyan]Would create[/cyan] {dest_rel}")
            else:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(new_content)
                console.print(f"[green]Created[/green] {dest_rel}")
            updated_files.append(dest_rel)
            continue

        # Parse existing file
        try:
            existing_content = dest_file.read_text()
        except OSError:
            skipped_files.append(dest_rel)
            continue

        parsed = parse_invar_regions(existing_content)

        if not parsed.has_regions:
            # No regions - add them (wrap existing in user region)
            if dry_run:
                console.print(f"[cyan]Would add regions to[/cyan] {dest_rel}")
            else:
                # Create new file with managed content + existing as user
                dest_file.write_text(new_content)
                console.print(f"[green]Added regions to[/green] {dest_rel}")
            updated_files.append(dest_rel)
            continue

        # Build updates
        updates: dict[str, str] = {}
        updates["managed"] = new_parsed.regions["managed"].content

        # Inject project additions if CLAUDE.md and project region exists
        if dest_rel == "CLAUDE.md" and "project" in parsed.regions and project_additions:
            updates["project"] = project_additions

        # Reconstruct with updates
        result_content = reconstruct_file(parsed, updates)

        # Check if content changed
        if result_content == existing_content:
            skipped_files.append(dest_rel)
            continue

        if dry_run:
            console.print(f"[cyan]Would update[/cyan] {dest_rel}")
        else:
            dest_file.write_text(result_content)
            console.print(f"[green]Updated[/green] {dest_rel}")
        updated_files.append(dest_rel)

    # Summary
    console.print()
    if dry_run:
        console.print("[bold]Dry run complete.[/bold]")
        console.print(f"  Would update: {len(updated_files)} files")
        console.print(f"  Would skip: {len(skipped_files)} files (unchanged)")
    else:
        console.print("[bold green]Sync complete![/bold green]")
        console.print(f"  Updated: {len(updated_files)} files")
        console.print(f"  Skipped: {len(skipped_files)} files (unchanged)")

    console.print()
    console.print("[dim]MCP syntax applied:[/dim]")
    console.print("[dim]  invar_guard(changed=true) instead of invar guard --changed[/dim]")
    console.print("[dim]  invar_map(top=10) instead of invar map --top 10[/dim]")
