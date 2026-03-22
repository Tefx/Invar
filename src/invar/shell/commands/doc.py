"""
CLI commands for document tools.

DX-76: Structured document query and editing commands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Literal

import typer
from returns.result import Failure, Result, Success

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

    sections: list[dict] = toc_data.get("sections", [])
    if depth is not None:
        sections = _filter_by_depth(sections, depth)

    def format_section(section: dict, current_depth: int = 1) -> None:
        indent = "  " * (section["level"] - 1)
        prefix = "#" * section["level"]
        char_display = _format_size(section["char_count"])
        lines.append(
            f"{indent}{prefix} {section['title']} "
            f"({section['line_start']}-{section['line_end']}, {char_display})"
        )
        for child in section.get("children", []):
            format_section(child, current_depth + 1)

    for section in sections:
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


def _resolve_file_patterns(file_patterns: list[str]) -> tuple[list[Path], list[str]]:
    """Resolve file patterns into concrete file paths and collection errors."""
    resolved_files: list[Path] = []
    errors: list[str] = []
    for file_pattern in file_patterns:
        resolved = _resolve_glob(file_pattern)
        if not resolved or (len(resolved) == 1 and not resolved[0].exists()):
            errors.append(f"No files found matching '{file_pattern}'")
            continue
        resolved_files.extend(resolved)
    return resolved_files, errors


def _build_toc_dict(path: Path, depth: int | None = None) -> Result[dict[str, object], str]:
    """Build TOC payload for one document path."""
    result = read_toc(path)
    if isinstance(result, Failure):
        return Failure(result.failure())

    from dataclasses import asdict

    toc = result.unwrap()
    sections = [_section_to_dict(s) for s in toc.sections]
    if depth is not None:
        sections = _filter_by_depth(sections, depth)

    toc_dict: dict[str, object] = {
        "file": str(path),
        "sections": sections,
        "frontmatter": asdict(toc.frontmatter) if toc.frontmatter else None,
    }
    return Success(toc_dict)


def _run_toc(
    file_patterns: list[str], depth: int | None = None
) -> Result[tuple[list[dict[str, object]], list[str]], str]:
    """Collect TOC payloads for all matching files."""
    resolved_files, errors = _resolve_file_patterns(file_patterns)
    all_results: list[dict[str, object]] = []

    for path in resolved_files:
        toc_result = _build_toc_dict(path, depth=depth)
        if isinstance(toc_result, Success):
            all_results.append(toc_result.unwrap())
        else:
            errors.append(toc_result.failure())

    return Success((all_results, errors))


def _run_read(file: Path, section: str, include_children: bool) -> Result[str, str]:
    """Read one section from a document path."""
    return read_section(file, section, include_children=include_children)


def _run_find(
    pattern: str,
    file_patterns: list[str],
    content: str | None,
    level: int | None,
) -> Result[tuple[list[dict[str, object]], list[str]], str]:
    """Find section matches across file patterns."""
    resolved_files, errors = _resolve_file_patterns(file_patterns)
    all_matches: list[dict[str, object]] = []

    for path in resolved_files:
        result = find_sections(path, pattern, content, level=level)
        if isinstance(result, Failure):
            errors.append(result.failure())
            continue

        sections = result.unwrap()
        for section in sections:
            all_matches.append(
                {
                    "file": str(path),
                    "path": section.path,
                    "title": section.title,
                    "level": section.level,
                    "line_start": section.line_start,
                    "line_end": section.line_end,
                    "char_count": section.char_count,
                }
            )

    return Success((all_matches, errors))


def _read_content_input(content_file: Path | None) -> Result[str, str]:
    """Load content from explicit file or stdin."""
    try:
        if content_file is None:
            typer.echo("Reading content from stdin (Ctrl+D to end)...", err=True)
            return Success(_read_stdin_limited())
        if str(content_file) == "-":
            return Success(_read_stdin_limited())
        return Success(_read_file_limited(content_file))
    except typer.BadParameter as error:
        return Failure(str(error))


def _run_replace(
    file: Path,
    section: str,
    content_file: Path | None,
    keep_heading: bool,
) -> Result[dict[str, str | int], str]:
    """Replace section content after resolving content input."""
    content_result = _read_content_input(content_file)
    if isinstance(content_result, Failure):
        return Failure(content_result.failure())
    return replace_section_content(file, section, content_result.unwrap(), keep_heading)


def _parse_insert_position(
    position: str,
) -> Result[Literal["before", "after", "first_child", "last_child"], str]:
    """Validate and normalize insert position option."""
    valid_positions: dict[str, Literal["before", "after", "first_child", "last_child"]] = {
        "before": "before",
        "after": "after",
        "first_child": "first_child",
        "last_child": "last_child",
    }
    normalized = valid_positions.get(position)
    if normalized is not None:
        return Success(normalized)

    allowed_positions = ("before", "after", "first_child", "last_child")
    return Failure(f"position must be one of {allowed_positions}")


def _run_insert(
    file: Path,
    anchor: str,
    content_file: Path | None,
    position: str,
) -> Result[dict[str, str | int], str]:
    """Insert content relative to an anchor section."""
    position_result = _parse_insert_position(position)
    if isinstance(position_result, Failure):
        return Failure(position_result.failure())

    content_result = _read_content_input(content_file)
    if isinstance(content_result, Failure):
        return Failure(content_result.failure())

    return insert_section_content(file, anchor, content_result.unwrap(), position_result.unwrap())


def _run_delete(
    file: Path,
    section: str,
    include_children: bool,
) -> Result[dict[str, str | int], str]:
    """Delete one section from a document."""
    return delete_section_content(file, section, include_children=include_children)


def _exit_command(result: Result[int, str]) -> None:
    """Exit with standardized Result handling."""
    if isinstance(result, Failure):
        typer.echo(f"Error: {result.failure()}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(result.unwrap())


# @shell_complexity: Multi-mode output with partial-failure handling for toc aggregation
def _run_toc_cli(files: list[str], depth: int | None, output_format: str) -> Result[int, str]:
    """Execute toc command and render output."""
    result = _run_toc(files, depth=depth)
    if isinstance(result, Failure):
        return Failure(result.failure())
    all_results, errors = result.unwrap()
    for error in errors:
        typer.echo(f"Error: {error}", err=True)
    if not all_results:
        return Success(1)
    if output_format == "text":
        for toc_data in all_results:
            if len(all_results) > 1:
                typer.echo(f"\n=== {toc_data['file']} ===")
            typer.echo(_format_toc_text(toc_data, depth))
    elif len(all_results) == 1:
        typer.echo(json.dumps(all_results[0], indent=2))
    else:
        typer.echo(json.dumps({"files": all_results}, indent=2))
    return Success(1 if errors else 0)


def _run_read_cli(
    file: Path, section: str, include_children: bool, json_output: bool
) -> Result[int, str]:
    """Execute read command and render output."""
    result = _run_read(file, section, include_children)
    if isinstance(result, Failure):
        return Failure(result.failure())
    content = result.unwrap()
    typer.echo(
        json.dumps({"path": section, "content": content}, indent=2) if json_output else content
    )
    return Success(0)


# @shell_complexity: Multi-file find supports partial failures and dual output formatting
def _run_find_cli(
    pattern: str,
    files: list[str],
    content: str | None,
    level: int | None,
    json_output: bool,
) -> Result[int, str]:
    """Execute find command and render output."""
    result = _run_find(pattern, files, content, level)
    if isinstance(result, Failure):
        return Failure(result.failure())
    all_matches, errors = result.unwrap()
    for error in errors:
        typer.echo(f"Error: {error}", err=True)
    if json_output:
        typer.echo(json.dumps({"matches": all_matches}, indent=2))
    else:
        for match in all_matches:
            typer.echo(
                f"{match['file']}:{match['line_start']} {match['path']} ({match['char_count']}B)"
            )
    return Success(1 if errors else 0)


def _run_replace_cli(
    file: Path,
    section: str,
    content_file: Path | None,
    keep_heading: bool,
) -> Result[int, str]:
    """Execute replace command and render output."""
    result = _run_replace(file, section, content_file, keep_heading)
    if isinstance(result, Failure):
        return Failure(result.failure())
    typer.echo(json.dumps({"success": True, **result.unwrap()}, indent=2))
    return Success(0)


def _run_insert_cli(
    file: Path,
    anchor: str,
    content_file: Path | None,
    position: str,
) -> Result[int, str]:
    """Execute insert command and render output."""
    result = _run_insert(file, anchor, content_file, position)
    if isinstance(result, Failure):
        return Failure(result.failure())
    typer.echo(json.dumps({"success": True, **result.unwrap()}, indent=2))
    return Success(0)


def _run_delete_cli(file: Path, section: str, include_children: bool) -> Result[int, str]:
    """Execute delete command and render output."""
    result = _run_delete(file, section, include_children)
    if isinstance(result, Failure):
        return Failure(result.failure())
    typer.echo(json.dumps({"success": True, **result.unwrap()}, indent=2))
    return Success(0)


def toc_command(
    files: Annotated[list[str], typer.Argument(help="Files or glob")],
    depth: Annotated[int | None, typer.Option("--depth", "-d", help="Max heading depth")] = None,
    output_format: Annotated[str, typer.Option("--format", "-f", help="json or text")] = "json",
) -> None:
    _exit_command(_run_toc_cli(files, depth, output_format))


def read_command(
    file: Annotated[Path, typer.Argument(help="Markdown file")],
    section: Annotated[str, typer.Argument(help="Section path")],
    include_children: Annotated[
        bool, typer.Option("--children/--no-children", help="Include children")
    ] = True,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = False,
) -> None:
    _exit_command(_run_read_cli(file, section, include_children, json_output))


def find_command(
    pattern: Annotated[str, typer.Argument(help="Title pattern")],
    files: Annotated[list[str], typer.Argument(help="Files or glob")],
    content: Annotated[str | None, typer.Option("--content", "-c", help="Content pattern")] = None,
    level: Annotated[int | None, typer.Option("--level", "-l", help="Heading level")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output JSON")] = True,
) -> None:
    _exit_command(_run_find_cli(pattern, files, content, level, json_output))


def replace_command(
    file: Annotated[Path, typer.Argument(help="Markdown file")],
    section: Annotated[str, typer.Argument(help="Section path")],
    content_file: Annotated[
        Path | None, typer.Option("--content", "-c", help="Content file or -")
    ] = None,
    keep_heading: Annotated[
        bool, typer.Option("--keep-heading/--no-keep-heading", help="Keep heading")
    ] = True,
) -> None:
    _exit_command(_run_replace_cli(file, section, content_file, keep_heading))


def insert_command(
    file: Annotated[Path, typer.Argument(help="Markdown file")],
    anchor: Annotated[str, typer.Argument(help="Section path")],
    content_file: Annotated[
        Path | None, typer.Option("--content", "-c", help="Content file or -")
    ] = None,
    position: Annotated[
        str, typer.Option("--position", "-p", help="before|after|first_child|last_child")
    ] = "after",
) -> None:
    _exit_command(_run_insert_cli(file, anchor, content_file, position))


def delete_command(
    file: Annotated[Path, typer.Argument(help="Markdown file")],
    section: Annotated[str, typer.Argument(help="Section path")],
    include_children: Annotated[
        bool, typer.Option("--children/--no-children", help="Include children")
    ] = True,
) -> None:
    _exit_command(_run_delete_cli(file, section, include_children))


doc_app.command("toc")(toc_command)
doc_app.command("read")(read_command)
doc_app.command("find")(find_command)
doc_app.command("replace")(replace_command)
doc_app.command("insert")(insert_command)
doc_app.command("delete")(delete_command)
