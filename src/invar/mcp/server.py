"""
Invar MCP Server implementation.

Exposes invar guard, sig, and map as first-class MCP tools.
Part of DX-16: Agent Tool Enforcement.
DX-52: Added Phase 2 smart re-spawn for project Python compatibility.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from invar.shell.subprocess_env import should_respawn


# @invar:allow shell_result: Pure validation helper, no I/O, returns tuple not Result
# @shell_complexity: Security validation requires multiple checks
def _validate_path(path: str) -> tuple[bool, str]:
    """Validate path argument for safety.

    Returns (is_valid, error_message).
    Rejects paths that could be interpreted as shell commands or flags.
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

    # Try to resolve path - this catches malformed paths
    try:
        Path(path).resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"

    return True, ""


# Strong instructions for agent behavior (DX-16 + DX-17 + DX-26)
INVAR_INSTRUCTIONS = """
## Invar Tool Usage (MANDATORY)

This project uses Invar for all code verification and analysis.
The following rules are MANDATORY, not suggestions.

### Session Start (REQUIRED)

Before writing ANY code, you MUST execute:

1. `invar_guard(changed=true)` — Check existing violations
2. `invar_map(top=10)` — Understand code structure

Then read `.invar/examples/` and `.invar/context.md` for project context.

**Skipping Session Start → Non-compliant code → Task failure.**

### Tool Substitution Rules (ENFORCED)

| Task | ❌ NEVER Use | ✅ ALWAYS Use |
|------|-------------|---------------|
| Verify code quality | `Bash("pytest ...")` | `invar_guard` |
| Symbolic verification | `Bash("crosshair ...")` | `invar_guard` (included by default) |
| Understand file structure | `Read` entire .py file | `invar_sig` |
| Find entry points | `Grep` for "def " | `invar_map` |

### Common Mistakes to AVOID

❌ `Bash("python -m pytest file.py")` - Use invar_guard instead
❌ `Bash("pytest --doctest-modules ...")` - invar_guard includes doctests
❌ `Bash("crosshair check ...")` - invar_guard includes CrossHair by default
❌ `Read("src/foo.py")` just to see signatures - Use invar_sig instead
❌ `Grep` for function definitions - Use invar_map instead
❌ `Bash("invar guard ...")` - Use invar_guard MCP tool instead

### Task Completion

A task is complete ONLY when:
- Session Start executed (invar_guard + invar_map)
- Final `invar_guard` passed
- User requirement satisfied

### Why This Matters

1. **invar_guard** = Smart Guard (static + doctests + CrossHair + Hypothesis)
2. **invar_sig** shows @pre/@post contracts that Read misses
3. **invar_map** includes reference counts for importance ranking

### Correct Usage Examples

```
# Session Start (REQUIRED before any code)
invar_guard(changed=true)
invar_map(top=10)

# Verify code after changes (full verification by default)
invar_guard(changed=true)

# Understand a file's structure
invar_sig(target="src/invar/core/parser.py")
```

IMPORTANT: Using Bash commands for Invar operations bypasses
the MCP tools and may not follow the correct workflow.
"""


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for guard command
def _get_guard_tool() -> Tool:
    """Define the invar_guard tool."""
    return Tool(
        name="invar_guard",
        description=(
            "Smart Guard: Verify code quality with static analysis + doctests. "
            "Use this INSTEAD of Bash('pytest ...') or Bash('crosshair ...'). "
            "Default runs static + doctests + CrossHair + Hypothesis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project path (default: .)", "default": "."},
                "changed": {"type": "boolean", "description": "Only verify git-changed files", "default": True},
                "strict": {"type": "boolean", "description": "Treat warnings as errors", "default": False},
                "coverage": {"type": "boolean", "description": "DX-37: Collect branch coverage from doctest + hypothesis", "default": False},
            },
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for sig command
def _get_sig_tool() -> Tool:
    """Define the invar_sig tool."""
    return Tool(
        name="invar_sig",
        description=(
            "Show function signatures and contracts (@pre/@post). "
            "Use this INSTEAD of Read('file.py') when you want to understand structure."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "File or file::symbol path"},
            },
            "required": ["target"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for map command
def _get_map_tool() -> Tool:
    """Define the invar_map tool."""
    return Tool(
        name="invar_map",
        description=(
            "Symbol map with reference counts. "
            "Use this INSTEAD of Grep for 'def ' to find functions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project path", "default": "."},
                "top": {"type": "integer", "description": "Show top N symbols", "default": 10},
            },
        },
    )


# @shell_orchestration: MCP server setup - registers handlers with framework
# @invar:allow shell_result: MCP framework API returns Server
def create_server() -> Server:
    """Create and configure the Invar MCP server."""
    server = Server(name="invar", version="0.1.0", instructions=INVAR_INSTRUCTIONS)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [_get_guard_tool(), _get_sig_tool(), _get_map_tool()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        handlers = {"invar_guard": _run_guard, "invar_sig": _run_sig, "invar_map": _run_map}
        handler = handlers.get(name)
        if handler:
            return await handler(arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


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


# @shell_orchestration: MCP server entry point - runs async server
def run_server() -> None:
    """Run the Invar MCP server.

    DX-52 Phase 2: If project has invar installed, re-spawn with project Python
    to ensure C extensions are compatible with project's Python version.
    """
    import asyncio

    from mcp.server.stdio import stdio_server

    # DX-52 Phase 2: Smart re-spawn with project Python
    cwd = Path.cwd()
    do_respawn, project_python = should_respawn(cwd)

    if do_respawn and project_python is not None:
        # Re-spawn with project Python (has both invar AND project deps)
        import subprocess
        import sys

        if os.name == "nt":
            # Windows: execv doesn't replace process, use subprocess + exit
            result = subprocess.call([str(project_python), "-m", "invar.mcp"])
            sys.exit(result)
        else:
            # Unix: execv replaces current process, does not return
            os.execv(
                str(project_python),
                [str(project_python), "-m", "invar.mcp"],
            )

    # Phase 1 fallback: Continue with uvx + PYTHONPATH injection
    async def main():
        server = create_server()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(main())


if __name__ == "__main__":
    run_server()
