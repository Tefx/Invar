"""
Invar MCP Server implementation.

Exposes invar guard, sig, and map as first-class MCP tools.
Part of DX-16: Agent Tool Enforcement.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

# Strong instructions for agent behavior (DX-16 + DX-17)
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
| Symbolic verification | `Bash("crosshair ...")` | `invar_guard` with prove=true |
| Understand file structure | `Read` entire .py file | `invar_sig` |
| Find entry points | `Grep` for "def " | `invar_map` |

### Common Mistakes to AVOID

❌ `Bash("python -m pytest file.py")` - Use invar_guard instead
❌ `Bash("pytest --doctest-modules ...")` - invar_guard includes doctests
❌ `Bash("crosshair check ...")` - Use invar_guard with prove=true
❌ `Read("src/foo.py")` just to see signatures - Use invar_sig instead
❌ `Grep` for function definitions - Use invar_map instead
❌ `Bash("invar guard ...")` - Use invar_guard MCP tool instead

### Task Completion

A task is complete ONLY when:
- Session Start executed (invar_guard + invar_map)
- Final `invar_guard` passed
- User requirement satisfied

### Why This Matters

1. **invar_guard** = Smart Guard (static analysis + doctests + optional symbolic)
2. **invar_sig** shows @pre/@post contracts that Read misses
3. **invar_map** includes reference counts for importance ranking

### Correct Usage Examples

```
# Session Start (REQUIRED before any code)
invar_guard(changed=true)
invar_map(top=10)

# Verify code after changes
invar_guard(changed=true)

# Add symbolic verification
invar_guard(changed=true, prove=true)

# Understand a file's structure
invar_sig(target="src/invar/core/parser.py")
```

IMPORTANT: Using Bash commands for Invar operations bypasses
the MCP tools and may not follow the correct workflow.
"""


def _get_guard_tool() -> Tool:
    """Define the invar_guard tool."""
    return Tool(
        name="invar_guard",
        description=(
            "Smart Guard: Verify code quality with static analysis + doctests. "
            "Use this INSTEAD of Bash('pytest ...') or Bash('crosshair ...'). "
            "Default runs static + doctests. Add prove=true for symbolic verification."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project path (default: .)", "default": "."},
                "changed": {"type": "boolean", "description": "Only verify git-changed files", "default": True},
                "prove": {"type": "boolean", "description": "Add symbolic verification", "default": False},
                "strict": {"type": "boolean", "description": "Treat warnings as errors", "default": False},
            },
        },
    )


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


async def _run_guard(args: dict[str, Any]) -> list[TextContent]:
    """Run invar guard command."""
    cmd = [sys.executable, "-m", "invar.shell.cli", "guard"]

    path = args.get("path", ".")
    cmd.append(path)

    if args.get("changed", True):
        cmd.append("--changed")
    if args.get("prove", False):
        cmd.append("--prove")
    if args.get("strict", False):
        cmd.append("--strict")

    # Always use JSON output for agent consumption
    cmd.append("--json")

    return await _execute_command(cmd)


async def _run_sig(args: dict[str, Any]) -> list[TextContent]:
    """Run invar sig command."""
    target = args.get("target", "")
    if not target:
        return [TextContent(type="text", text="Error: target is required")]

    cmd = [sys.executable, "-m", "invar.shell.cli", "sig", target, "--json"]
    return await _execute_command(cmd)


async def _run_map(args: dict[str, Any]) -> list[TextContent]:
    """Run invar map command."""
    cmd = [sys.executable, "-m", "invar.shell.cli", "map"]

    path = args.get("path", ".")
    cmd.append(path)

    top = args.get("top", 10)
    cmd.extend(["--top", str(top)])

    cmd.append("--json")
    return await _execute_command(cmd)


async def _execute_command(cmd: list[str]) -> list[TextContent]:
    """Execute a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
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
        return [TextContent(type="text", text="Error: Command timed out (120s)")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


def run_server() -> None:
    """Run the Invar MCP server."""
    import asyncio

    from mcp.server.stdio import stdio_server

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
