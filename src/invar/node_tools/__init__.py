"""Embedded Node.js tools for TypeScript verification.

This module provides access to @invar/* Node tools that are embedded
in the Python package for zero-configuration TypeScript support.

The tools are built from typescript/packages/* and copied here during
the Python package build process. Users who install invar-tools via pip
get these tools automatically without needing npm.

Workflow:
1. Developer: typescript/packages/*/src/ -> pnpm build -> dist/
2. Release: scripts/embed_node_tools.py copies dist/ -> src/invar/node_tools/
3. User: pip install invar-tools (includes node_tools/)
"""

from pathlib import Path


# @invar:allow shell_result: Simple path lookup, None is clear return value
def get_tool_path(tool_name: str) -> Path | None:
    """Get path to an embedded Node tool.

    Args:
        tool_name: Tool name without @invar/ prefix (e.g., "ts-analyzer")

    Returns:
        Path to cli.js if embedded, None otherwise.

    Examples:
        >>> # When tools are embedded (after running embed script)
        >>> path = get_tool_path("ts-analyzer")
        >>> # Returns: Path(".../node_tools/ts-analyzer/cli.js") or None
    """
    tool_dir = Path(__file__).parent / tool_name
    cli_js = tool_dir / "cli.js"
    return cli_js if cli_js.exists() else None


# @invar:allow shell_result: Directory listing for embedded tools discovery
def list_available_tools() -> list[str]:
    """List all embedded tools.

    Returns:
        List of tool names that have cli.js available.
    """
    tools_dir = Path(__file__).parent
    available = []
    for subdir in tools_dir.iterdir():
        if subdir.is_dir() and (subdir / "cli.js").exists():
            available.append(subdir.name)
    return sorted(available)
