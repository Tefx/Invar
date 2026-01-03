"""TypeScript Compiler API wrapper (single-shot subprocess).

DX-78: Provides Python interface to ts-query.js for TypeScript analysis.

Architecture:
- Single-shot subprocess: starts, runs query, exits
- No persistent process, no orphan risk
- Falls back to regex parser if Node.js unavailable
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from returns.result import Failure, Result, Success


@dataclass
class TSSymbolInfo:
    """TypeScript symbol information from Compiler API."""

    name: str
    kind: str
    signature: str
    line: int
    file: str = ""
    contracts: dict[str, list[str]] | None = None
    members: list[dict[str, Any]] | None = None


@dataclass
class TSReference:
    """A reference to a TypeScript symbol."""

    file: str
    line: int
    column: int
    context: str
    is_definition: bool = False


def _find_ts_query_js() -> Path:
    """Find the ts-query.js script bundled with invar-tools."""
    # Look relative to this file's location
    this_dir = Path(__file__).parent.parent
    ts_query_path = this_dir / "node_tools" / "ts-query.js"

    if ts_query_path.exists():
        return ts_query_path

    # Fallback: check if installed globally or in node_modules
    raise FileNotFoundError("ts-query.js not found")


# @shell_complexity: Project root discovery with parent traversal
def _find_tsconfig_root(file_path: Path) -> Path:
    """Find the project root containing tsconfig.json."""
    current = file_path.parent if file_path.is_file() else file_path

    while current != current.parent:
        if (current / "tsconfig.json").exists():
            return current
        current = current.parent

    # Fallback to file's directory
    return file_path.parent if file_path.is_file() else file_path


# @shell_complexity: Subprocess orchestration with error handling and JSON parsing
def query_typescript(
    project_root: Path,
    command: str,
    **params: Any,
) -> Result[dict[str, Any], str]:
    """Run ts-query.js and return parsed result.

    Single-shot subprocess: starts, runs query, exits.
    No persistent process, no orphan risk.

    Args:
        project_root: Project root containing tsconfig.json
        command: Query command (sig, map, refs)
        **params: Command-specific parameters

    Returns:
        Parsed JSON result or error message
    """
    try:
        ts_query_path = _find_ts_query_js()
    except FileNotFoundError:
        return Failure("ts-query.js not found. Install Node.js to use TypeScript tools.")

    query = {"command": command, **params}

    try:
        result = subprocess.run(
            ["node", str(ts_query_path), json.dumps(query)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,  # Safety timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return Failure(f"ts-query failed: {error_msg}")

        output = json.loads(result.stdout)

        # Check for error in output
        if "error" in output:
            return Failure(output["error"])

        return Success(output)

    except subprocess.TimeoutExpired:
        return Failure("TypeScript query timed out (30s)")
    except FileNotFoundError:
        return Failure(
            "Node.js not found.\n\n"
            "To use TypeScript tools, install Node.js:\n"
            "- macOS: brew install node\n"
            "- Ubuntu: apt install nodejs\n"
            "- Windows: https://nodejs.org/"
        )
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON from ts-query: {e}")
    except Exception as e:
        return Failure(f"TypeScript query error: {e}")


def run_sig_typescript(file_path: Path) -> Result[list[TSSymbolInfo], str]:
    """Get signatures for TypeScript file using Compiler API.

    Args:
        file_path: Path to TypeScript file

    Returns:
        List of symbol information or error message
    """
    project_root = _find_tsconfig_root(file_path)
    result = query_typescript(project_root, "sig", file=str(file_path))

    if isinstance(result, Failure):
        return result

    data = result.unwrap()
    symbols = []

    for sym in data.get("symbols", []):
        symbols.append(
            TSSymbolInfo(
                name=sym.get("name", ""),
                kind=sym.get("kind", ""),
                signature=sym.get("signature", ""),
                line=sym.get("line", 0),
                file=str(file_path),
                contracts=sym.get("contracts"),
                members=sym.get("members"),
            )
        )

    return Success(symbols)


def run_map_typescript(path: Path, top_n: int) -> Result[dict[str, Any], str]:
    """Get symbol map with reference counts for TypeScript project.

    Args:
        path: Project path to scan
        top_n: Maximum number of symbols to return

    Returns:
        Symbol map data or error message
    """
    return query_typescript(path, "map", path=str(path), top=top_n)


def run_refs_typescript(
    file_path: Path, line: int, column: int
) -> Result[list[TSReference], str]:
    """Find all references to symbol at position.

    Args:
        file_path: File containing the symbol
        line: 1-based line number
        column: 0-based column number

    Returns:
        List of references or error message
    """
    project_root = _find_tsconfig_root(file_path)
    result = query_typescript(
        project_root,
        "refs",
        file=str(file_path),
        line=line,
        column=column,
    )

    if isinstance(result, Failure):
        return result

    data = result.unwrap()
    references = []

    for ref in data.get("references", []):
        references.append(
            TSReference(
                file=ref.get("file", ""),
                line=ref.get("line", 0),
                column=ref.get("column", 0),
                context=ref.get("context", ""),
                is_definition=ref.get("isDefinition", False),
            )
        )

    return Success(references)


def is_typescript_available() -> bool:
    """Check if TypeScript Compiler API tools are available."""
    try:
        _find_ts_query_js()
        # Also check if Node.js is available
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
