"""
MCP tool handlers for Invar.

DX-76: Extracted from server.py to manage file size.
Contains all _run_* handler functions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.types import TextContent
from returns.result import Success


# @invar:allow shell_result: Pure validation helper, no I/O, returns tuple not Result
# @shell_complexity: Security validation requires multiple checks
def _validate_path(path: str) -> tuple[bool, str]:
    """Validate path argument for safety.

    Returns (is_valid, error_message).
    Rejects paths that could be interpreted as shell commands or flags.

    Note: This validation is for MCP (Model Context Protocol) handlers, which
    are designed to provide AI agents with access to the project filesystem.
    We validate format and reject shell injection patterns, but do not restrict
    to working directory (unlike CLI tools) since MCP is a trusted local protocol.
    """
    if not path:
        return True, ""  # Empty path defaults to "." in handlers

    # Reject if looks like a flag (starts with -)
    if path.startswith("-"):
        return False, f"Invalid path: cannot start with '-': {path}"

    # Reject shell metacharacters that could cause issues
    dangerous_chars = [";", "&", "|", "$", "`", "\n", "\r"]
    for char in dangerous_chars:
        if char in path:
            return False, f"Invalid path: contains forbidden character: {char!r}"

    # Resolve path to canonical form, following symlinks
    # This ensures path is valid and catches directory traversal attempts
    try:
        Path(path).resolve()
        # Note: We don't restrict to cwd here because MCP handlers are designed
        # to access the full project. If path restriction is needed, implement
        # at the MCP server level, not per-handler.
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"

    return True, ""


# @shell_orchestration: MCP handler - subprocess is called inside
# @shell_complexity: Guard command with multiple optional flags
# @invar:allow shell_result: MCP handler for guard tool
async def _run_guard(args: dict[str, Any]) -> list[TextContent]:
    """Run invar guard command."""
    path = args.get("path", ".")
    is_valid, error = _validate_path(path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "guard"]
    cmd.append(path)

    if args.get("changed", True):
        cmd.append("--changed")
    if args.get("strict", False):
        cmd.append("--strict")
    # DX-37: Optional coverage collection
    if args.get("coverage", False):
        cmd.append("--coverage")
    # DX-63: Contract coverage check only
    if args.get("contracts_only", False):
        cmd.append("--contracts-only")

    # DX-26: TTY auto-detection - MCP runs in non-TTY, so agent JSON output is automatic
    # No explicit flag needed

    return await _execute_command(cmd)


# @shell_orchestration: MCP handler - subprocess is called inside
# @invar:allow shell_result: MCP handler for sig tool
async def _run_sig(args: dict[str, Any]) -> list[TextContent]:
    """Run invar sig command."""
    target = args.get("target", "")
    if not target:
        return [TextContent(type="text", text="Error: target is required")]

    # Validate target (can be file path or file::symbol)
    target_path = target.split("::")[0] if "::" in target else target
    is_valid, error = _validate_path(target_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "sig", target, "--json"]
    return await _execute_command(cmd)


# @shell_orchestration: MCP handler - subprocess is called inside
# @invar:allow shell_result: MCP handler for map tool
async def _run_map(args: dict[str, Any]) -> list[TextContent]:
    """Run invar map command."""
    path = args.get("path", ".")
    is_valid, error = _validate_path(path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "map"]
    cmd.append(path)

    top = args.get("top", 10)
    cmd.extend(["--top", str(top)])

    cmd.append("--json")
    return await _execute_command(cmd)


# @shell_orchestration: MCP handler - orchestrates refs command execution
# @invar:allow shell_result: MCP handler for refs tool
async def _run_refs(args: dict[str, Any]) -> list[TextContent]:
    """Run invar refs command.

    DX-78: Find all references to a symbol.
    Target format: "path/to/file.py::symbol" or "path/to/file.ts::symbol"
    """
    target = args.get("target", "")
    if not target:
        return [TextContent(type="text", text="Error: 'target' parameter is required")]

    # Parse target to validate file path
    if "::" not in target:
        return [TextContent(type="text", text="Error: Invalid target format. Use 'file::symbol'")]

    file_part, _symbol = target.rsplit("::", 1)
    is_valid, error = _validate_path(file_part)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "refs"]
    cmd.append(target)
    cmd.append("--json")

    return await _execute_command(cmd)


# DX-76: Document query handlers
# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_toc tool
async def _run_doc_toc(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_toc - extract document structure."""
    from dataclasses import asdict

    from invar.shell.doc_tools import read_toc

    file_path = args.get("file", "")
    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = read_toc(path)

    if isinstance(result, Success):
        toc = result.unwrap()
        # Convert to JSON-serializable format
        output = {
            "sections": [_section_to_dict(s) for s in toc.sections],
            "frontmatter": asdict(toc.frontmatter) if toc.frontmatter else None,
        }
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @invar:allow shell_result: Pure data transformation, no I/O
# @shell_orchestration: Helper for MCP response formatting
def _section_to_dict(section: Any) -> dict[str, Any]:
    """Convert Section to JSON-serializable dict (recursive)."""
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


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_read tool
async def _run_doc_read(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_read - read a specific section."""
    from invar.shell.doc_tools import read_section

    file_path = args.get("file", "")
    section_path = args.get("section", "")

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not section_path:
        return [TextContent(type="text", text="Error: section is required")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = read_section(path, section_path)

    if isinstance(result, Success):
        content = result.unwrap()
        output = {"path": section_path, "content": content}
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @shell_complexity: Multiple arg validation branches + error handling
# @invar:allow shell_result: MCP handler for doc_read_many tool
async def _run_doc_read_many(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_read_many - read multiple sections."""
    from invar.shell.doc_tools import read_sections_batch

    file_path = args.get("file", "")
    sections = args.get("sections", [])
    include_children = args.get("include_children", True)

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not sections:
        return [TextContent(type="text", text="Error: sections list is required")]
    if not isinstance(sections, list):
        return [TextContent(type="text", text="Error: sections must be a list")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = read_sections_batch(path, sections, include_children)

    if isinstance(result, Success):
        sections_data = result.unwrap()
        return [TextContent(type="text", text=json.dumps(sections_data, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_find tool
async def _run_doc_find(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_find - find sections matching pattern."""
    from invar.shell.doc_tools import find_sections

    file_path = args.get("file", "")
    pattern = args.get("pattern", "")
    content_pattern = args.get("content")

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not pattern:
        return [TextContent(type="text", text="Error: pattern is required")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = find_sections(path, pattern, content_pattern)

    if isinstance(result, Success):
        sections = result.unwrap()
        output = {
            "matches": [
                {
                    "path": s.path,
                    "title": s.title,
                    "level": s.level,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "char_count": s.char_count,
                }
                for s in sections
            ]
        }
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# DX-76 Phase A-2: Extended editing handlers
# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_replace tool
async def _run_doc_replace(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_replace - replace section content."""
    from invar.shell.doc_tools import replace_section_content

    file_path = args.get("file", "")
    section_path = args.get("section", "")
    content = args.get("content", "")
    keep_heading = args.get("keep_heading", True)

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not section_path:
        return [TextContent(type="text", text="Error: section is required")]
    if not content:
        return [TextContent(type="text", text="Error: content is required")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = replace_section_content(path, section_path, content, keep_heading)

    if isinstance(result, Success):
        info = result.unwrap()
        output = {"success": True, **info}
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_insert tool
async def _run_doc_insert(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_insert - insert content relative to section."""
    from invar.shell.doc_tools import insert_section_content

    file_path = args.get("file", "")
    anchor_path = args.get("anchor", "")
    content = args.get("content", "")
    position = args.get("position", "after")

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not anchor_path:
        return [TextContent(type="text", text="Error: anchor is required")]
    if not content:
        return [TextContent(type="text", text="Error: content is required")]

    valid_positions = ("before", "after", "first_child", "last_child")
    if position not in valid_positions:
        return [TextContent(type="text", text=f"Error: position must be one of {valid_positions}")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    # Cast position to Literal type for type safety
    pos: Literal["before", "after", "first_child", "last_child"] = position
    result = insert_section_content(path, anchor_path, content, pos)

    if isinstance(result, Success):
        info = result.unwrap()
        output = {"success": True, **info}
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
# @invar:allow shell_result: MCP handler for doc_delete tool
async def _run_doc_delete(args: dict[str, Any]) -> list[TextContent]:
    """Run invar_doc_delete - delete a section."""
    from invar.shell.doc_tools import delete_section_content

    file_path = args.get("file", "")
    section_path = args.get("section", "")

    if not file_path:
        return [TextContent(type="text", text="Error: file is required")]
    if not section_path:
        return [TextContent(type="text", text="Error: section is required")]

    is_valid, error = _validate_path(file_path)
    if not is_valid:
        return [TextContent(type="text", text=f"Error: {error}")]

    path = Path(file_path)
    result = delete_section_content(path, section_path)

    if isinstance(result, Success):
        info = result.unwrap()
        output = {"success": True, **info}
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    else:
        return [TextContent(type="text", text=f"Error: {result.failure()}")]


# @shell_complexity: Command execution with error handling branches
# @invar:allow shell_result: MCP subprocess wrapper utility
async def _execute_command(cmd: list[str], timeout: int = 600) -> list[TextContent]:
    """Execute a command and return the result.

    Args:
        cmd: Command to execute
        timeout: Maximum time in seconds (default: 600, accommodates full Guard cycle)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout
        if result.stderr:
            output += f"\n\nStderr:\n{result.stderr}"

        # Try to parse as JSON for better formatting
        try:
            parsed = json.loads(result.stdout)
            output = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            pass

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text=f"Error: Command timed out ({timeout}s)")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]
