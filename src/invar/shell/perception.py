"""
Perception CLI implementation (Phase 4).

Shell module: handles file I/O for map and sig commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success
from rich.console import Console

from invar.core.formatter import (
    format_map_json,
    format_map_text,
    format_signatures_json,
    format_signatures_text,
)
from invar.core.models import FileInfo
from invar.core.parser import parse_source
from invar.core.references import build_perception_map
from invar.shell.fs import discover_python_files

if TYPE_CHECKING:
    from invar.core.models import Symbol

console = Console()


def run_map(path: Path, top_n: int, json_output: bool) -> Result[None, str]:
    """
    Run the map command.

    Scans project and generates perception map with reference counts.
    """
    if not path.exists():
        return Failure(f"Path does not exist: {path}")

    # Collect all files and their sources
    file_infos: list[FileInfo] = []
    sources: dict[str, str] = {}

    for py_file in discover_python_files(path):
        try:
            content = py_file.read_text(encoding="utf-8")
            rel_path = str(py_file.relative_to(path))
            # Skip empty files (e.g., __init__.py)
            if not content.strip():
                continue
            file_info = parse_source(content, rel_path)
            if file_info:
                file_infos.append(file_info)
                sources[rel_path] = content
        except (OSError, UnicodeDecodeError) as e:
            console.print(f"[yellow]Warning:[/yellow] {py_file}: {e}")
            continue

    if not file_infos:
        return Failure("No Python files found")

    # Build perception map
    perception_map = build_perception_map(file_infos, sources, str(path.absolute()))

    # Output
    if json_output:
        output = format_map_json(perception_map, top_n)
        console.print(json.dumps(output, indent=2))
    else:
        output = format_map_text(perception_map, top_n)
        console.print(output)

    return Success(None)


def run_sig(target: str, json_output: bool) -> Result[None, str]:
    """
    Run the sig command.

    Extracts signatures from a file or specific symbol.
    Target format: "path/to/file.py" or "path/to/file.py::symbol_name"
    """
    # Parse target
    if "::" in target:
        file_path_str, symbol_name = target.split("::", 1)
    else:
        file_path_str = target
        symbol_name = None

    file_path = Path(file_path_str)
    if not file_path.exists():
        return Failure(f"File not found: {file_path}")

    # Read and parse
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return Failure(f"Failed to read {file_path}: {e}")

    # Handle empty files
    if not content.strip():
        file_info = FileInfo(path=str(file_path), lines=0, symbols=[], imports=[], source="")
    else:
        file_info = parse_source(content, str(file_path))
        if file_info is None:
            return Failure(f"Syntax error in {file_path}")

    # Filter symbols
    symbols: list[Symbol] = file_info.symbols
    if symbol_name:
        symbols = [s for s in symbols if s.name == symbol_name]
        if not symbols:
            return Failure(f"Symbol '{symbol_name}' not found in {file_path}")

    # Output
    if json_output:
        output = format_signatures_json(symbols, str(file_path))
        console.print(json.dumps(output, indent=2))
    else:
        output = format_signatures_text(symbols, str(file_path))
        console.print(output)

    return Success(None)
