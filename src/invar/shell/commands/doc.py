"""
CLI commands for document tools.

DX-76: Structured document query and editing commands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from returns.result import Success

from invar.shell.doc_tools import (
    delete_section_content,
    find_sections,
    insert_section_content,
    read_section,
    read_toc,
    replace_section_content,
)

# Max content size for stdin reading (10MB) - matches parse_toc limit
MAX_STDIN_SIZE = 10_000_000

# Create doc subcommand app
doc_app = typer.Typer(
    name="doc",
    help="Structured document query and editing tools.",
    no_args_is_help=True,
)


def _read_stdin_limited() -> str:
    """Read from stdin with size limit to prevent OOM."""
    content = sys.stdin.read(MAX_STDIN_SIZE + 1)
    if len(content) > MAX_STDIN_SIZE:
        raise typer.BadParameter(f"Input exceeds maximum size of {MAX_STDIN_SIZE} bytes")
    return content


def _read_file_limited(path: Path) -> str:
    """Read file with size limit to prevent OOM.

    Uses single read to avoid TOCTOU race between stat and read.
    """
    content = path.read_text(encoding="utf-8")
    if len(content) > MAX_STDIN_SIZE:
        raise typer.BadParameter(f"File {path} exceeds maximum size of {MAX_STDIN_SIZE} bytes")
    return content


# @shell_orchestration: CLI helper for glob pattern resolution
def _resolve_glob(pattern: str) -> list[Path]:
    """Resolve glob pattern to list of files."""
    path = Path(pattern)
    if path.exists() and path.is_file():
        return [path]
    # Try as glob pattern
    if "*" in pattern or "?" in pattern:
        # Handle ** for recursive
        if "**" in pattern:
            base = Path()
            matches = list(base.glob(pattern))
        else:
            matches = list(Path().glob(pattern))
        return [p for p in matches if p.is_file()]
    # Single file that doesn't exist
    return [path]


# @shell_orchestration: CLI output formatter for text mode
# @shell_complexity: Recursive formatting with depth filtering
def _format_toc_text(toc_data: dict, depth: int | None = None) -> str:
    """Format TOC as human-readable text."""
    lines: list[str] = []

    if toc_data.get("frontmatter"):
        fm = toc_data["frontmatter"]
        lines.append(f"[frontmatter] ({fm['line_start']}-{fm['line_end']})")

    def format_section(section: dict, current_depth: int = 1) -> None:
        if depth is not None and section["level"] > depth:
            return
        indent = "  " * (section["level"] - 1)
        prefix = "#" * section["level"]
        char_display = _format_size(section["char_count"])
        lines.append(
            f"{indent}{prefix} {section['title']} "
            f"({section['line_start']}-{section['line_end']}, {char_display})"
        )
        for child in section.get("children", []):
            format_section(child, current_depth + 1)

    for section in toc_data.get("sections", []):
        format_section(section)

    return "\n".join(lines)


def _format_size(chars: int) -> str:
    """Format character count as human-readable size."""
    if chars >= 1000:
        return f"{chars / 1000:.1f}K"
    return f"{chars}B"


# @shell_orchestration: CLI helper for JSON serialization
def _section_to_dict(section) -> dict:
    """Convert Section to dict (recursive)."""
    return {
        "title": section.title,
        "slug": section.slug,
        "level": section.level,
        "line_start": section.line_start,
        "line_end": section.line_end,
        "char_count": section.char_count,
        "path": section.path,
        "children": [_section_to_dict(c) for c in section.children],
    }


# @shell_orchestration: CLI helper for depth filtering
def _filter_by_depth(sections: list[dict], max_depth: int) -> list[dict]:
    """Filter sections by maximum depth."""
    result = []
    for s in sections:
        if s["level"] <= max_depth:
            filtered = s.copy()
            filtered["children"] = _filter_by_depth(s.get("children", []), max_depth)
            result.append(filtered)
    return result


# @invar:allow entry_point_too_thick: Multi-file glob + dual output format orchestration
@doc_app.command("toc")
def toc_command(
    files: Annotated[
        list[str],
        typer.Argument(help="File(s) or glob pattern (e.g., 'docs/*.md')"),
    ],
    depth: Annotated[
        int | None,
        typer.Option("--depth", "-d", help="Maximum heading depth (1-6)"),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json or text"),
    ] = "json",
) -> None:
    """Extract document structure (Table of Contents).

    Shows headings hierarchy with line numbers and character counts.
    """
    all_results: list[dict] = []
    has_error = False

    for pattern in files:
        resolved = _resolve_glob(pattern)
        if not resolved or (len(resolved) == 1 and not resolved[0].exists()):
            typer.echo(f"Error: No files found matching '{pattern}'", err=True)
            has_error = True
            continue

        for path in resolved:
            result = read_toc(path)
            if isinstance(result, Success):
                toc = result.unwrap()
                from dataclasses import asdict

                toc_dict = {
                    "file": str(path),
                    "sections": [_section_to_dict(s) for s in toc.sections],
                    "frontmatter": asdict(toc.frontmatter) if toc.frontmatter else None,
                }

                # Apply depth filter if specified
                if depth is not None:
                    toc_dict["sections"] = _filter_by_depth(toc_dict["sections"], depth)

                all_results.append(toc_dict)
            else:
                typer.echo(f"Error: {result.failure()}", err=True)
                has_error = True

    if not all_results:
        raise typer.Exit(1)

    # Output
    if output_format == "text":
        for toc_data in all_results:
            if len(all_results) > 1:
                typer.echo(f"\n=== {toc_data['file']} ===")
            typer.echo(_format_toc_text(toc_data, depth))
    else:
        # JSON output
        if len(all_results) == 1:
            typer.echo(json.dumps(all_results[0], indent=2))
        else:
            typer.echo(json.dumps({"files": all_results}, indent=2))

    if has_error:
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Section addressing + output format orchestration
@doc_app.command("read")
def read_command(
    file: Annotated[Path, typer.Argument(help="Path to markdown file")],
    section: Annotated[str, typer.Argument(help="Section path (slug, fuzzy, index, or @line)")],
    include_children: Annotated[
        bool,
        typer.Option("--children/--no-children", help="Include child sections"),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Read a specific section from a document.

    Section addressing:
    - Slug path: "requirements/auth"
    - Fuzzy: "auth" (matches first containing)
    - Index: "#0/#1" (positional)
    - Line anchor: "@48" (section at line 48)
    """
    result = read_section(file, section, include_children=include_children)

    if isinstance(result, Success):
        content = result.unwrap()
        if json_output:
            typer.echo(json.dumps({"path": section, "content": content}, indent=2))
        else:
            typer.echo(content)
    else:
        typer.echo(f"Error: {result.failure()}", err=True)
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Multi-file glob + pattern/level filtering orchestration
@doc_app.command("find")
def find_command(
    pattern: Annotated[str, typer.Argument(help="Title pattern (glob-style, e.g., '*auth*')")],
    files: Annotated[
        list[str],
        typer.Argument(help="File(s) or glob pattern"),
    ],
    content: Annotated[
        str | None,
        typer.Option("--content", "-c", help="Content search pattern"),
    ] = None,
    level: Annotated[
        int | None,
        typer.Option("--level", "-l", help="Filter by heading level (1-6)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = True,
) -> None:
    """Find sections matching a pattern.

    Supports glob patterns for titles and optional content search.
    """
    all_matches: list[dict] = []
    has_error = False

    for file_pattern in files:
        resolved = _resolve_glob(file_pattern)
        if not resolved or (len(resolved) == 1 and not resolved[0].exists()):
            typer.echo(f"Error: No files found matching '{file_pattern}'", err=True)
            has_error = True
            continue

        for path in resolved:
            result = find_sections(path, pattern, content, level=level)
            if isinstance(result, Success):
                sections = result.unwrap()
                for s in sections:
                    all_matches.append({
                        "file": str(path),
                        "path": s.path,
                        "title": s.title,
                        "level": s.level,
                        "line_start": s.line_start,
                        "line_end": s.line_end,
                        "char_count": s.char_count,
                    })
            else:
                typer.echo(f"Error: {result.failure()}", err=True)
                has_error = True

    if json_output:
        typer.echo(json.dumps({"matches": all_matches}, indent=2))
    else:
        for m in all_matches:
            typer.echo(f"{m['file']}:{m['line_start']} {m['path']} ({m['char_count']}B)")

    if has_error:
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Content input + section replacement orchestration
@doc_app.command("replace")
def replace_command(
    file: Annotated[Path, typer.Argument(help="Path to markdown file")],
    section: Annotated[str, typer.Argument(help="Section path to replace")],
    content_file: Annotated[
        Path | None,
        typer.Option("--content", "-c", help="File containing new content (use - for stdin)"),
    ] = None,
    keep_heading: Annotated[
        bool,
        typer.Option("--keep-heading/--no-keep-heading", help="Preserve original heading"),
    ] = True,
) -> None:
    """Replace a section's content.

    Content can be provided via --content file or stdin.
    """
    # Read content from file or stdin
    if content_file is None:
        typer.echo("Reading content from stdin (Ctrl+D to end)...", err=True)
        new_content = _read_stdin_limited()
    elif str(content_file) == "-":
        new_content = _read_stdin_limited()
    else:
        new_content = _read_file_limited(content_file)

    result = replace_section_content(file, section, new_content, keep_heading)

    if isinstance(result, Success):
        info = result.unwrap()
        typer.echo(json.dumps({"success": True, **info}, indent=2))
    else:
        typer.echo(f"Error: {result.failure()}", err=True)
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Content input + position-based insertion orchestration
@doc_app.command("insert")
def insert_command(
    file: Annotated[Path, typer.Argument(help="Path to markdown file")],
    anchor: Annotated[str, typer.Argument(help="Section path for anchor")],
    content_file: Annotated[
        Path | None,
        typer.Option("--content", "-c", help="File containing content to insert"),
    ] = None,
    position: Annotated[
        str,
        typer.Option("--position", "-p", help="Where to insert: before, after, first_child, last_child"),
    ] = "after",
) -> None:
    """Insert new content relative to a section.

    Content should include heading if adding a new section.
    """
    valid_positions = ("before", "after", "first_child", "last_child")
    if position not in valid_positions:
        typer.echo(f"Error: position must be one of {valid_positions}", err=True)
        raise typer.Exit(1)

    # Read content from file or stdin
    if content_file is None:
        typer.echo("Reading content from stdin (Ctrl+D to end)...", err=True)
        content = _read_stdin_limited()
    elif str(content_file) == "-":
        content = _read_stdin_limited()
    else:
        content = _read_file_limited(content_file)

    from typing import Literal
    pos: Literal["before", "after", "first_child", "last_child"] = position  # type: ignore[assignment]
    result = insert_section_content(file, anchor, content, pos)

    if isinstance(result, Success):
        info = result.unwrap()
        typer.echo(json.dumps({"success": True, **info}, indent=2))
    else:
        typer.echo(f"Error: {result.failure()}", err=True)
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Section deletion with children handling
@doc_app.command("delete")
def delete_command(
    file: Annotated[Path, typer.Argument(help="Path to markdown file")],
    section: Annotated[str, typer.Argument(help="Section path to delete")],
    include_children: Annotated[
        bool,
        typer.Option("--children/--no-children", help="Include child sections in deletion"),
    ] = True,
) -> None:
    """Delete a section from a document.

    Removes the heading and all content until the next same-level heading.
    """
    result = delete_section_content(file, section, include_children=include_children)

    if isinstance(result, Success):
        info = result.unwrap()
        typer.echo(json.dumps({"success": True, **info}, indent=2))
    else:
        typer.echo(f"Error: {result.failure()}", err=True)
        raise typer.Exit(1)
