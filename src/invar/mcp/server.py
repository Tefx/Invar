"""
Invar MCP Server implementation.

Exposes invar guard, sig, and map as first-class MCP tools.
Part of DX-16: Agent Tool Enforcement.
DX-52: Added Phase 2 smart re-spawn for project Python compatibility.
DX-76: Added doc_toc, doc_read, doc_find for structured document queries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from invar.mcp.handlers import (
    _run_doc_delete,
    _run_doc_find,
    _run_doc_insert,
    _run_doc_read,
    _run_doc_read_many,
    _run_doc_replace,
    _run_doc_toc,
    _run_guard,
    _run_map,
    _run_refs,
    _run_sig,
)
from invar.shell.subprocess_env import should_respawn

# Strong instructions for agent behavior (DX-16 + DX-17 + DX-26 + DX-76 + DX-78)
INVAR_INSTRUCTIONS = """
## Invar Tool Usage (MANDATORY)

This project uses Invar for all code verification and analysis.
The following rules are MANDATORY, not suggestions.

### Check-In (REQUIRED)

Your first message MUST display:
```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

**Actions:** Read `.invar/context.md`, then show status.
**Do NOT run guard at Check-In.**

Run guard only when:
- Entering VALIDATE phase of USBV workflow
- User explicitly requests verification
- After making code changes

### Tool x Language Support

| Tool | Python | TypeScript | Notes |
|------|--------|------------|-------|
| `invar_guard` | ✅ Full | ⚠️ Partial | TS: tsc + eslint + vitest |
| `invar_sig` | ✅ Full | ✅ Full | TS: TS Compiler API |
| `invar_map` | ✅ Full | ✅ Full | TS: With reference counts |
| `invar_refs` | ✅ Full | ✅ Full | Cross-file reference finding |
| `invar_doc_*` | ✅ Full | ✅ Full | Language-agnostic |

### Tool Substitution Rules (ENFORCED)

| Task | ❌ NEVER Use | ✅ ALWAYS Use |
|------|-------------|---------------|
| Verify code quality | `Bash("pytest ...")` | `invar_guard` |
| Symbolic verification | `Bash("crosshair ...")` | `invar_guard` (included by default) |
| Understand file structure | `Read` entire .py file | `invar_sig` |
| Find entry points | `Grep` for "def " | `invar_map` |
| Find symbol references | Manual grep | `invar_refs` |
| View document structure | `Read` entire .md file | `invar_doc_toc` |
| Read document section | `Read` with manual line counting | `invar_doc_read` |
| Read multiple sections | Multiple `invar_doc_read` calls | `invar_doc_read_many` |
| Find sections by pattern | `Grep` in markdown files | `invar_doc_find` |

### Document Tools (DX-76)

| I want to... | Use |
|--------------|-----|
| View document structure | `invar_doc_toc(file="path.md")` |
| Read specific section | `invar_doc_read(file="path.md", section="slug")` |
| Read multiple sections | `invar_doc_read_many(file="path.md", sections=["slug1", "slug2"])` |
| Search sections by title | `invar_doc_find(file="path.md", pattern="*auth*")` |
| Replace section content | `invar_doc_replace(file="path.md", section="slug", content="...")` |
| Insert new section | `invar_doc_insert(file="path.md", anchor="slug", content="...")` |
| Delete section | `invar_doc_delete(file="path.md", section="slug")` |

**Section addressing:** slug path (`requirements/auth`), fuzzy (`auth`), index (`#0/#1`), line (`@48`)

**Workflow:** ALWAYS call `invar_doc_toc` first to understand document structure before editing.

### Common Mistakes to AVOID

❌ `Bash("python -m pytest file.py")` - Use invar_guard instead
❌ `Bash("pytest --doctest-modules ...")` - invar_guard includes doctests
❌ `Bash("crosshair check ...")` - invar_guard includes CrossHair by default
❌ `Read("src/foo.py")` just to see signatures - Use invar_sig instead
❌ `Grep` for function definitions - Use invar_map instead
❌ `Bash("invar guard ...")` - Use invar_guard MCP tool instead
❌ `Read("docs/file.md")` to understand structure - Use invar_doc_toc instead
❌ `Grep` in markdown files - Use invar_doc_find instead

### Task Completion

A task is complete ONLY when:
- Check-In displayed at session start
- Final `invar_guard` passed (in VALIDATE phase)
- User requirement satisfied

### Why This Matters

1. **invar_guard** = Smart Guard (static + doctests + CrossHair + Hypothesis)
2. **invar_sig** shows @pre/@post contracts that Read misses
3. **invar_map** includes reference counts for importance ranking
4. **invar_doc_toc** shows document structure that Read doesn't parse

### Correct Usage Examples

```
# Check-In (REQUIRED at session start)
# Display: ✓ Check-In: Invar | main | clean
# Then read .invar/context.md

# Explore codebase (when needed)
invar_map(top=10)

# Understand a file's structure
invar_sig(target="src/invar/core/parser.py")

# Understand a document's structure
invar_doc_toc(file="docs/proposals/DX-76.md")

# Read specific section
invar_doc_read(file="docs/proposals/DX-76.md", section="phase-a")

# VALIDATE phase: Verify code after changes
invar_guard(changed=true)
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
        title="Smart Guard",
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
                "contracts_only": {"type": "boolean", "description": "DX-63: Contract coverage check only (skip tests)", "default": False},
            },
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for sig command
def _get_sig_tool() -> Tool:
    """Define the invar_sig tool."""
    return Tool(
        name="invar_sig",
        title="Show Signatures",
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
        title="Symbol Map",
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



# @shell_orchestration: MCP tool factory - creates tool definition for framework
# @invar:allow shell_result: MCP tool factory for refs command
def _get_refs_tool() -> Tool:
    """Define the invar_refs tool.

    DX-78: Cross-file reference finding.
    """
    return Tool(
        name="invar_refs",
        title="Find References",
        description=(
            "Find all references to a symbol. "
            "Supports Python (via jedi) and TypeScript (via TS Compiler API). "
            "Use this to understand symbol usage across the codebase."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target format: 'file.py::symbol' or 'file.ts::symbol'",
                },
            },
            "required": ["target"],
        },
    )


# DX-76: Document query tools
# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_toc command
def _get_doc_toc_tool() -> Tool:
    """Define the invar_doc_toc tool."""
    return Tool(
        name="invar_doc_toc",
        title="Markdown TOC",
        description=(
            "Extract document structure (Table of Contents) from markdown files. "
            "Shows headings hierarchy with line numbers and character counts. "
            "Use this INSTEAD of Read() to understand markdown structure."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "depth": {
                    "type": "integer",
                    "description": "Maximum heading depth to include (1-6)",
                    "default": 6,
                },
            },
            "required": ["file"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_read command
def _get_doc_read_tool() -> Tool:
    """Define the invar_doc_read tool."""
    return Tool(
        name="invar_doc_read",
        title="Read Markdown Section",
        description=(
            "Read a specific section from a markdown document. "
            "Supports multiple addressing formats: slug path, fuzzy match, "
            "index (#0/#1), or line anchor (@48). "
            "Use this INSTEAD of Read() with manual line counting."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "section": {
                    "type": "string",
                    "description": (
                        "Section path: slug ('requirements/auth'), "
                        "fuzzy ('auth'), index ('#0/#1'), or line ('@48')"
                    ),
                },
            },
            "required": ["file", "section"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_read_many command
def _get_doc_read_many_tool() -> Tool:
    """Define the invar_doc_read_many tool."""
    return Tool(
        name="invar_doc_read_many",
        title="Read Multiple Markdown Sections",
        description=(
            "Read multiple sections from a markdown document in one call. "
            "Reduces tool calls by batching section reads. "
            "Use this INSTEAD of multiple invar_doc_read() calls."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of section paths (slug, fuzzy, index, or line anchor)"
                    ),
                },
                "include_children": {
                    "type": "boolean",
                    "description": "Include child sections in output",
                    "default": True,
                },
            },
            "required": ["file", "sections"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_find command
def _get_doc_find_tool() -> Tool:
    """Define the invar_doc_find tool."""
    return Tool(
        name="invar_doc_find",
        title="Find Markdown Sections",
        description=(
            "Find sections in markdown documents matching a pattern. "
            "Supports glob patterns for titles and optional content search. "
            "Use this INSTEAD of Grep in markdown files."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "pattern": {
                    "type": "string",
                    "description": "Title pattern (glob-style, e.g., '*auth*')",
                },
                "content": {
                    "type": "string",
                    "description": "Optional content search pattern",
                },
            },
            "required": ["file", "pattern"],
        },
    )


# DX-76 Phase A-2: Extended editing tools
# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_replace command
def _get_doc_replace_tool() -> Tool:
    """Define the invar_doc_replace tool."""
    return Tool(
        name="invar_doc_replace",
        title="Replace Markdown Section",
        description=(
            "Replace a section's content in a markdown document. "
            "Use this INSTEAD of Edit()/Write() for section replacement."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "section": {
                    "type": "string",
                    "description": "Section path to replace (slug, fuzzy, index, or line anchor)",
                },
                "content": {"type": "string", "description": "New content to replace the section with"},
                "keep_heading": {
                    "type": "boolean",
                    "description": "If true, preserve the original heading line",
                    "default": True,
                },
            },
            "required": ["file", "section", "content"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_insert command
def _get_doc_insert_tool() -> Tool:
    """Define the invar_doc_insert tool."""
    return Tool(
        name="invar_doc_insert",
        title="Insert Markdown Section",
        description=(
            "Insert new content relative to a section in a markdown document. "
            "Use this INSTEAD of Edit()/Write() for section insertion."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "anchor": {
                    "type": "string",
                    "description": "Section path for the anchor (slug, fuzzy, index, or line anchor)",
                },
                "content": {"type": "string", "description": "Content to insert (include heading if new section)"},
                "position": {
                    "type": "string",
                    "description": "Where to insert: 'before', 'after', 'first_child', 'last_child'",
                    "default": "after",
                    "enum": ["before", "after", "first_child", "last_child"],
                },
            },
            "required": ["file", "anchor", "content"],
        },
    )


# @shell_orchestration: MCP tool factory - creates Tool objects
# @invar:allow shell_result: MCP tool factory for doc_delete command
def _get_doc_delete_tool() -> Tool:
    """Define the invar_doc_delete tool."""
    return Tool(
        name="invar_doc_delete",
        title="Delete Markdown Section",
        description=(
            "Delete a section from a markdown document. "
            "Use this INSTEAD of Edit()/Write() for section deletion."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to markdown file"},
                "section": {
                    "type": "string",
                    "description": "Section path to delete (slug, fuzzy, index, or line anchor)",
                },
            },
            "required": ["file", "section"],
        },
    )


# @shell_orchestration: MCP server setup - registers handlers with framework
# @invar:allow shell_result: MCP framework API returns Server
def create_server() -> Server:
    """Create and configure the Invar MCP server."""
    server = Server(name="invar", version="0.1.0", instructions=INVAR_INSTRUCTIONS)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            _get_guard_tool(),
            _get_sig_tool(),
            _get_map_tool(),
            _get_refs_tool(),  # DX-78: Reference finding
            # DX-76: Document query tools
            _get_doc_toc_tool(),
            _get_doc_read_tool(),
            _get_doc_read_many_tool(),  # DX-77: Batch section reading
            _get_doc_find_tool(),
            # DX-76 Phase A-2: Document editing tools
            _get_doc_replace_tool(),
            _get_doc_insert_tool(),
            _get_doc_delete_tool(),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        handlers = {
            "invar_guard": _run_guard,
            "invar_sig": _run_sig,
            "invar_map": _run_map,
            "invar_refs": _run_refs,  # DX-78: Reference finding
            # DX-76: Document query handlers
            "invar_doc_toc": _run_doc_toc,
            "invar_doc_read": _run_doc_read,
            "invar_doc_read_many": _run_doc_read_many,  # DX-77: Batch reading
            "invar_doc_find": _run_doc_find,
            # DX-76 Phase A-2: Document editing handlers
            "invar_doc_replace": _run_doc_replace,
            "invar_doc_insert": _run_doc_insert,
            "invar_doc_delete": _run_doc_delete,
        }
        handler = handlers.get(name)
        if handler:
            return await handler(arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


# @shell_orchestration: MCP server entry point - runs async server
def run_server() -> None:
    """Run the Invar MCP server.

    DX-52 Phase 2: If project has invar installed, re-spawn with project Python
    to ensure C extensions are compatible with project's Python version.
    """
    import asyncio
    import subprocess
    import sys

    from mcp.server.stdio import stdio_server

    # DX-52 Phase 2: Smart re-spawn with project Python
    cwd = Path.cwd()
    do_respawn, project_python = should_respawn(cwd)

    if do_respawn and project_python is not None:
        # Re-spawn with project Python (has both invar AND project deps)

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
    async def main() -> None:
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
