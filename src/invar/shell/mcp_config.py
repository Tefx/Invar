"""
MCP configuration detection and generation.

Shell module: handles MCP server configuration for AI agents.
DX-21B: Smart detection of available MCP execution methods.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


class McpMethod(Enum):
    """Available MCP execution methods."""

    UVX = "uvx"
    COMMAND = "command"
    PYTHON = "python"


@dataclass
class McpExecConfig:
    """Configuration for MCP server execution.

    Examples:
        >>> config = McpExecConfig(
        ...     method=McpMethod.UVX,
        ...     command="uvx",
        ...     args=["invar-tools", "mcp"],
        ...     description="uvx (recommended - isolated environment)",
        ... )
        >>> config.to_mcp_json()
        {'command': 'uvx', 'args': ['invar-tools', 'mcp']}
    """

    method: McpMethod
    command: str
    args: list[str]
    description: str

    def to_mcp_json(self) -> dict[str, Any]:
        """Convert to MCP JSON format for .mcp.json."""
        return {
            "command": self.command,
            "args": self.args,
        }


def detect_available_methods() -> list[McpExecConfig]:
    """
    Detect available MCP execution methods, ordered by preference.

    Returns a list of available methods, with the most preferred first.

    Examples:
        >>> methods = detect_available_methods()
        >>> len(methods) >= 1  # At least Python fallback
        True
        >>> methods[-1].method == McpMethod.PYTHON  # Python is always last
        True
    """
    methods: list[McpExecConfig] = []

    # 1. uvx (recommended - isolated, auto-updates)
    if shutil.which("uvx"):
        methods.append(
            McpExecConfig(
                method=McpMethod.UVX,
                command="uvx",
                args=["invar-tools", "mcp"],
                description="uvx (recommended - isolated environment)",
            )
        )

    # 2. invar command in PATH
    if shutil.which("invar"):
        methods.append(
            McpExecConfig(
                method=McpMethod.COMMAND,
                command="invar",
                args=["mcp"],
                description="invar command (from PATH)",
            )
        )

    # 3. Current Python (always available as fallback)
    methods.append(
        McpExecConfig(
            method=McpMethod.PYTHON,
            command=sys.executable,
            args=["-m", "invar.mcp"],
            description=f"Python ({sys.executable})",
        )
    )

    return methods


# @shell_orchestration: MCP method selection helper
def get_recommended_method() -> McpExecConfig:
    """
    Get the recommended MCP execution method.

    Returns the first (most preferred) available method.

    Examples:
        >>> config = get_recommended_method()
        >>> config.method in [McpMethod.UVX, McpMethod.COMMAND, McpMethod.PYTHON]
        True
    """
    methods = detect_available_methods()
    return methods[0]


# @shell_orchestration: MCP method lookup helper
def get_method_by_name(name: str) -> McpExecConfig | None:
    """
    Get a specific MCP method by name.

    Args:
        name: Method name ('uvx', 'command', or 'python')

    Returns:
        McpExecConfig if the method is available, None otherwise.

    Examples:
        >>> config = get_method_by_name("python")
        >>> config is not None
        True
        >>> config.method == McpMethod.PYTHON
        True
    """
    methods = detect_available_methods()
    for method in methods:
        if method.method.value == name:
            return method
    return None


# @shell_orchestration: MCP configuration generator
def generate_mcp_json(config: McpExecConfig | None = None) -> dict[str, Any]:
    """
    Generate .mcp.json content for the given configuration.

    Args:
        config: MCP execution config, or None to use recommended.

    Returns:
        Dictionary suitable for writing to .mcp.json.

    Examples:
        >>> from invar.shell.mcp_config import generate_mcp_json, McpExecConfig, McpMethod
        >>> config = McpExecConfig(
        ...     method=McpMethod.UVX,
        ...     command="uvx",
        ...     args=["invar-tools", "mcp"],
        ...     description="test",
        ... )
        >>> result = generate_mcp_json(config)
        >>> result["mcpServers"]["invar"]["command"]
        'uvx'
    """
    if config is None:
        config = get_recommended_method()

    return {
        "mcpServers": {
            "invar": config.to_mcp_json(),
        }
    }
