"""
Sync-self command for Invar.

Shell module: Special command for updating Invar's own project files.
DX-49: Uses MCP syntax and injects project-additions.md content.

Region naming:
- CLAUDE.md: managed/user/project regions
- Skills: skill/extensions regions (semantic naming)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from returns.result import Failure
from rich.console import Console

if TYPE_CHECKING:
    from invar.core.template_parser import ParsedFile

from invar.shell.template_engine import (
    get_templates_dir,
    is_invar_project,
    load_manifest,
    parse_invar_regions,
    reconstruct_file,
    render_template_file,
)

console = Console()

# Region name mappings: (primary_region, user_region)
# Primary region is overwritten, user region is preserved
REGION_SCHEMES = {
    "managed": ("managed", "user"),     # CLAUDE.md pattern
    "skill": ("skill", "extensions"),   # Skill template pattern
}


# @shell_orchestration: Region scheme lookup for sync-self command
def _find_primary_region(parsed: ParsedFile) -> tuple[str, str] | None:
    """Find primary region name and its corresponding user region.

    Returns (primary_name, user_name) or None if no known scheme found.

    Examples:
        >>> from invar.core.template_parser import ParsedFile, Region
        >>> p = ParsedFile(regions={"managed": Region("managed", 0, 10, "")})
        >>> _find_primary_region(p)
        ('managed', 'user')
        >>> p2 = ParsedFile(regions={"skill": Region("skill", 0, 10, "")})
        >>> _find_primary_region(p2)
        ('skill', 'extensions')
        >>> p3 = ParsedFile(regions={})
        >>> _find_primary_region(p3) is None
        True
    """
    for _, (primary_name, user_name) in REGION_SCHEMES.items():
        if primary_name in parsed.regions:
            return (primary_name, user_name)
    return None


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
    # Copy to avoid mutating cached manifest
    variables = {**manifest.get("variables", {}), "syntax": "mcp"}  # Always MCP for Invar project

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

        # Parse new content for primary region (managed or skill)
        new_parsed = parse_invar_regions(new_content)
        region_scheme = _find_primary_region(new_parsed)
        if region_scheme is None:
            console.print(f"[yellow]Warning:[/yellow] No managed/skill region in template: {template_rel}")
            continue
        primary_region, user_region = region_scheme

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
            # No regions - wrap existing content in user region, add primary from template
            template_region = new_parsed.regions[primary_region]
            template_content = template_region.content
            # Preserve version attribute from template
            if template_region.version:
                start_tag = f'<!--invar:{primary_region} version="{template_region.version}"-->'
            else:
                start_tag = f"<!--invar:{primary_region}-->"
            wrapped_content = (
                f"{start_tag}\n{template_content}\n<!--/invar:{primary_region}-->\n\n"
                f"<!--invar:{user_region}-->\n{existing_content}\n<!--/invar:{user_region}-->\n"
            )
            if dry_run:
                console.print(f"[cyan]Would add regions to[/cyan] {dest_rel}")
            else:
                dest_file.write_text(wrapped_content)
                console.print(f"[green]Added regions to[/green] {dest_rel}")
            updated_files.append(dest_rel)
            continue

        # Build updates - use the primary region from template
        updates: dict[str, str] = {}
        # Map template region to existing file region (may have different names during migration)
        existing_primary = _find_primary_region(parsed)
        existing_primary_name = existing_primary[0] if existing_primary else primary_region
        updates[existing_primary_name] = new_parsed.regions[primary_region].content

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
