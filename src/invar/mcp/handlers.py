"""
MCP tool handlers for Invar.

DX-76: Extracted from server.py to manage file size.
Contains all _run_* handler functions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.lowlevel.server import CombinationContent
from mcp.types import TextContent
from returns.result import Failure, Result, Success

from invar.mcp.guard_runs import (
    GUARD_RUNS,
    build_wrapper_instability_envelope,
)

HandlerPayload = list[TextContent] | CombinationContent
HandlerResult = Result[HandlerPayload, str]


def _content(text: str) -> Result[HandlerPayload, str]:
    return Success([TextContent(type="text", text=text)])


def _json_text(payload: Any) -> Result[str, str]:
    try:
        return Success(json.dumps(payload, indent=2))
    except (TypeError, ValueError) as exc:
        return Failure(f"Unable to serialize JSON payload: {exc}")


def _success_json(payload: Any) -> Result[HandlerPayload, str]:
    text = _json_text(payload)
    if isinstance(text, Failure):
        return Failure(text.failure())
    content = _content(text.unwrap())
    if isinstance(content, Failure):
        return Failure(content.failure())
    return Success(content.unwrap())


# @shell_complexity: Security validation requires multiple checks
def _validate_path(path: str) -> Result[None, str]:
    """Validate path argument for safety.

    Rejects paths that could be interpreted as shell commands or flags.

    Note: This validation is for MCP (Model Context Protocol) handlers, which
    are designed to provide AI agents with access to the project filesystem.
    We validate format and reject shell injection patterns, but do not restrict
    to working directory (unlike CLI tools) since MCP is a trusted local protocol.
    """
    if not path:
        return Success(None)  # Empty path defaults to "." in handlers

    if path.startswith("-"):
        return Failure(f"Invalid path: cannot start with '-': {path}")

    dangerous_chars = [";", "&", "|", "$", "`", "\n", "\r"]
    for char in dangerous_chars:
        if char in path:
            return Failure(f"Invalid path: contains forbidden character: {char!r}")

    try:
        Path(path).resolve()
    except (OSError, ValueError) as exc:
        return Failure(f"Invalid path: {exc}")

    return Success(None)


# @shell_orchestration: MCP handler - subprocess is called inside
# @shell_complexity: Guard command with multiple optional flags
async def _run_guard(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar guard command."""
    path = args.get("path", ".")
    validated_path = _validate_path(path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "guard"]
    cmd.append(path)

    changed_mode = args.get("changed", True)
    cmd.append("--changed" if changed_mode else "--all")
    if args.get("strict", False):
        cmd.append("--strict")
    if args.get("coverage", False):
        cmd.append("--coverage")
    if args.get("contracts_only", False):
        cmd.append("--contracts-only")

    if not changed_mode:
        sync_budget_ms = _read_sync_budget_ms(args)
        if isinstance(sync_budget_ms, Failure):
            return Failure(sync_budget_ms.failure())
        should_defer = _should_defer_full_scan(path, args, sync_budget_ms.unwrap())
        if isinstance(should_defer, Failure):
            return Failure(should_defer.failure())
        if should_defer.unwrap():
            run = await GUARD_RUNS.start(
                cmd=cmd,
                path=path,
                changed=False,
                timeout_reason="estimated_duration_exceeds_sync_budget",
            )
            deferred = {
                "status": "deferred",
                "run_id": run.run_id,
                "mode": "full_scan",
                "path": path,
                "changed": False,
                "accepted_at": run.accepted_at,
                "poll_after_ms": 1000,
                "timeout_reason": run.timeout_reason,
            }
            return _success_json(deferred)

    return await _execute_command(
        cmd,
        full_scan_contract=not changed_mode,
        target_path=path,
        changed=changed_mode,
    )


# @shell_orchestration: MCP handler - reads deferred run status
async def _run_guard_status(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Return status snapshot for a deferred guard run."""
    run_id = args.get("run_id", "")
    if not run_id or not isinstance(run_id, str):
        return Failure("run_id is required")

    status = await GUARD_RUNS.status(run_id)
    return _success_json(status)


# @shell_orchestration: MCP handler - bounded long-poll for deferred runs
# @shell_complexity: wait_ms normalization and bounded long-poll handling
async def _run_guard_wait(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Wait for deferred guard run completion with bounded timeout."""
    run_id = args.get("run_id", "")
    if not run_id or not isinstance(run_id, str):
        return Failure("run_id is required")

    wait_ms_raw = args.get("wait_ms", 8000)
    wait_ms = 8000
    if isinstance(wait_ms_raw, int):
        wait_ms = wait_ms_raw
    elif isinstance(wait_ms_raw, float):
        wait_ms = int(wait_ms_raw)

    if wait_ms < 0:
        wait_ms = 0
    if wait_ms > 10000:
        wait_ms = 10000

    status = await GUARD_RUNS.wait(run_id, wait_ms)
    return _success_json(status)


# @shell_orchestration: MCP handler - subprocess is called inside
async def _run_sig(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar sig command."""
    target = args.get("target", "")
    if not target:
        return Failure("target is required")

    validated_target_path = target.split("::")[0] if "::" in target else target
    validated_path = _validate_path(validated_target_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "sig", target, "--json"]
    return await _execute_command(cmd)


# @shell_orchestration: MCP handler - subprocess is called inside
async def _run_map(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar map command."""
    path = args.get("path", ".")
    validated_path = _validate_path(path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "map"]
    cmd.append(path)

    top = args.get("top", 10)
    cmd.extend(["--top", str(top)])

    cmd.append("--json")
    return await _execute_command(cmd)


# @shell_orchestration: MCP handler - orchestrates refs command execution
async def _run_refs(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar refs command.

    Find all references to a symbol.
    Target format: "path/to/file.py::symbol" or "path/to/file.pyi::symbol"
    """
    target = args.get("target", "")
    if not target:
        return Failure("'target' parameter is required")

    if "::" not in target:
        return Failure("Invalid target format. Use 'file::symbol'")

    file_part, _symbol = target.rsplit("::", 1)
    validated_path = _validate_path(file_part)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "refs"]
    cmd.append(target)
    cmd.append("--json")

    return await _execute_command(cmd)


# DX-76: Document query handlers
# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_toc(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_toc - extract document structure."""
    from dataclasses import asdict

    from invar.shell.doc_tools import read_toc

    file_path = args.get("file", "")
    if not file_path:
        return Failure("file is required")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = read_toc(path)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    toc = result.unwrap()
    sections = []
    for section in toc.sections:
        serialized = _section_to_dict(section)
        if isinstance(serialized, Failure):
            return Failure(serialized.failure())
        sections.append(serialized.unwrap())

    output = {
        "sections": sections,
        "frontmatter": asdict(toc.frontmatter) if toc.frontmatter else None,
    }
    return _success_json(output)


# @shell_orchestration: Helper for MCP response formatting
def _section_to_dict(section: Any) -> Result[dict[str, Any], str]:
    """Convert Section to JSON-serializable dict (recursive)."""
    children: list[dict[str, Any]] = []
    for child in section.children:
        serialized = _section_to_dict(child)
        if isinstance(serialized, Failure):
            return Failure(serialized.failure())
        children.append(serialized.unwrap())

    return Success(
        {
            "title": section.title,
            "slug": section.slug,
            "level": section.level,
            "line_start": section.line_start,
            "line_end": section.line_end,
            "char_count": section.char_count,
            "path": section.path,
            "children": children,
        }
    )


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_read(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_read - read a specific section."""
    from invar.shell.doc_tools import read_section

    file_path = args.get("file", "")
    section_path = args.get("section", "")

    if not file_path:
        return Failure("file is required")
    if not section_path:
        return Failure("section is required")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = read_section(path, section_path)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    content = result.unwrap()
    output = {"path": section_path, "content": content}
    return _success_json(output)


# @shell_complexity: Multiple arg validation branches + error handling
async def _run_doc_read_many(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_read_many - read multiple sections."""
    from invar.shell.doc_tools import read_sections_batch

    file_path = args.get("file", "")
    sections = args.get("sections", [])
    include_children = args.get("include_children", True)

    if not file_path:
        return Failure("file is required")
    if not sections:
        return Failure("sections list is required")
    if not isinstance(sections, list):
        return Failure("sections must be a list")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = read_sections_batch(path, sections, include_children)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    return _success_json(result.unwrap())


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_find(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_find - find sections matching pattern."""
    from invar.shell.doc_tools import find_sections

    file_path = args.get("file", "")
    pattern = args.get("pattern", "")
    content_pattern = args.get("content")

    if not file_path:
        return Failure("file is required")
    if not pattern:
        return Failure("pattern is required")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = find_sections(path, pattern, content_pattern)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

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
    return _success_json(output)


# DX-76 Phase A-2: Extended editing handlers
# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_replace(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_replace - replace section content."""
    from invar.shell.doc_tools import replace_section_content

    file_path = args.get("file", "")
    section_path = args.get("section", "")
    content = args.get("content", "")
    keep_heading = args.get("keep_heading", True)

    if not file_path:
        return Failure("file is required")
    if not section_path:
        return Failure("section is required")
    if not content:
        return Failure("content is required")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = replace_section_content(path, section_path, content, keep_heading)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    info = result.unwrap()
    output = {"success": True, **info}
    return _success_json(output)


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_insert(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_insert - insert content relative to section."""
    from invar.shell.doc_tools import insert_section_content

    file_path = args.get("file", "")
    anchor_path = args.get("anchor", "")
    content = args.get("content", "")
    position = args.get("position", "after")

    if not file_path:
        return Failure("file is required")
    if not anchor_path:
        return Failure("anchor is required")
    if not content:
        return Failure("content is required")

    valid_positions = ("before", "after", "first_child", "last_child")
    if position not in valid_positions:
        return Failure(f"position must be one of {valid_positions}")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    pos: Literal["before", "after", "first_child", "last_child"] = position
    result = insert_section_content(path, anchor_path, content, pos)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    info = result.unwrap()
    output = {"success": True, **info}
    return _success_json(output)


# @shell_orchestration: MCP handler - calls shell layer directly
# @shell_complexity: MCP input validation + result handling
async def _run_doc_delete(args: dict[str, Any]) -> Result[HandlerPayload, str]:
    """Run invar_doc_delete - delete a section."""
    from invar.shell.doc_tools import delete_section_content

    file_path = args.get("file", "")
    section_path = args.get("section", "")

    if not file_path:
        return Failure("file is required")
    if not section_path:
        return Failure("section is required")

    validated_path = _validate_path(file_path)
    if isinstance(validated_path, Failure):
        return Failure(validated_path.failure())

    path = Path(file_path)
    result = delete_section_content(path, section_path)

    if isinstance(result, Failure):
        return Failure(str(result.failure()))

    info = result.unwrap()
    output = {"success": True, **info}
    return _success_json(output)


# @shell_complexity: Command execution with error handling branches
async def _execute_command(
    cmd: list[str],
    timeout: int = 600,
    *,
    full_scan_contract: bool = False,
    target_path: str = ".",
    changed: bool = True,
) -> Result[HandlerPayload, str]:
    """Execute a command and return result."""
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = process.stdout.strip()

        if process.returncode != 0 and full_scan_contract:
            payload = build_wrapper_instability_envelope(
                run_id="sync",
                path=target_path,
                changed=changed,
                subprocess_exit_code=process.returncode,
                stderr=process.stderr.strip(),
            )
            if isinstance(payload, Failure):
                return Failure(payload.failure())
            return _success_json(payload.unwrap())

        try:
            parsed = json.loads(stdout)
            return _success_json(parsed)
        except json.JSONDecodeError:
            fixed = _fix_json_newlines(stdout)
            if isinstance(fixed, Failure):
                return Failure(fixed.failure())
            try:
                parsed = json.loads(fixed.unwrap())
                return _success_json(parsed)
            except json.JSONDecodeError:
                output = stdout
                if process.stderr:
                    output += f"\n\nStderr:\n{process.stderr}"
                content = _content(output)
                if isinstance(content, Failure):
                    return Failure(content.failure())
                return Success(content.unwrap())

    except subprocess.TimeoutExpired:
        return Failure(f"Command timed out ({timeout}s)")
    except Exception as exc:
        return Failure(str(exc))


# @shell_complexity: Character-level scan and escaping requires multiple branches
# @shell_orchestration: MCP output normalization (shell-owned, not reusable core API)
def _fix_json_newlines(text: str) -> Result[str, str]:
    """Fix unescaped newlines in JSON strings.

    When subprocess outputs multiline JSON, newlines inside string values
    are not escaped, causing json.loads() to fail. This function escapes them.

    DX-33: Escape hatch for complex pure logic helper.
    """
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            result.append('"')
            i += 1
            while i < len(text):
                c = text[i]
                if c == "\\" and i + 1 < len(text):
                    result.append("\\")
                    result.append(text[i + 1])
                    i += 2
                elif c == '"':
                    result.append('"')
                    i += 1
                    break
                elif c == "\n" or c == "\r":
                    result.append("\\n")
                    i += 1
                else:
                    result.append(c)
                    i += 1
        else:
            result.append(text[i])
            i += 1
    return Success("".join(result))


def _read_sync_budget_ms(args: dict[str, Any]) -> Result[int, str]:
    """Read optional sync budget in milliseconds with safe fallback."""
    budget_raw = args.get("sync_budget_ms")
    if isinstance(budget_raw, int):
        return Success(max(1000, min(60000, budget_raw)))
    if isinstance(budget_raw, float):
        return Success(max(1000, min(60000, int(budget_raw))))
    return Success(8000)


def _should_defer_full_scan(
    path: str, args: dict[str, Any], sync_budget_ms: int
) -> Result[bool, str]:
    """Estimate whether a full scan should defer under DX-94 sync budget."""
    estimated_ms = _estimate_full_scan_duration_ms(path, args)
    if isinstance(estimated_ms, Failure):
        return Failure(estimated_ms.failure())
    return Success(estimated_ms.unwrap() > sync_budget_ms)


# @shell_complexity: Runtime planning combines feature flags and file estimates
def _estimate_full_scan_duration_ms(path: str, args: dict[str, Any]) -> Result[int, str]:
    """Cheap estimator for full guard runtime in MCP context.

    Source: DX-94 timeout-avoidance strategy requires a planning pass and
    `sync_budget_ms` comparison for changed=false calls.
    """
    root = Path(path)
    file_count = _estimate_candidate_file_count(root)
    if isinstance(file_count, Failure):
        return Failure(file_count.failure())

    if args.get("contracts_only", False):
        base = 500
        per_file = 20
    else:
        base = 1200
        per_file = 120

    if args.get("coverage", False):
        per_file += 50
    if args.get("strict", False):
        base += 100

    return Success(base + (file_count.unwrap() * per_file))


# @shell_complexity: Directory walk with bounded scan and exclusions
def _estimate_candidate_file_count(root: Path) -> Result[int, str]:
    """Count Python candidates with bounded scan effort for planning."""
    try:
        if root.is_file():
            return Success(1 if root.suffix == ".py" else 0)

        if not root.exists():
            return Success(1)

        count = 0
        for _dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d
                not in {".git", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache"}
            ]
            for filename in filenames:
                if filename.endswith(".py"):
                    count += 1
                    if count >= 5000:
                        return Success(5000)
        return Success(count)
    except OSError as exc:
        return Failure(f"Unable to estimate file count: {exc}")
