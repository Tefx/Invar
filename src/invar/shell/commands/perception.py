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


# @shell_complexity: Symbol map generation with sorting and output modes
def run_map(path: Path, top_n: int, json_output: bool) -> Result[None, str]:
    """
    Run the map command.

    Scans project and generates perception map with reference counts.
    LX-06: Supports TypeScript projects (basic symbol listing).
    """
    if not path.exists():
        return Failure(f"Path does not exist: {path}")

    # LX-06: Detect language and dispatch
    from invar.shell.commands.init import detect_language

    project_language = detect_language(path)
    if project_language == "typescript":
        return _run_map_typescript(path, top_n, json_output)

    # Python path (original logic)
    return _run_map_python(path, top_n, json_output)


# @shell_complexity: Signature extraction with symbol filtering
def run_sig(target: str, json_output: bool) -> Result[None, str]:
    """
    Run the sig command.

    Extracts signatures from a file or specific symbol.
    Target format: "path/to/file.py" or "path/to/file.py::symbol_name"
    LX-06: Supports TypeScript files (.ts, .tsx).
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

    # Read file content
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return Failure(f"Failed to read {file_path}: {e}")

    # LX-06: Detect file type and dispatch to appropriate parser
    suffix = file_path.suffix.lower()
    if suffix in (".ts", ".tsx"):
        return _run_sig_typescript(content, file_path, symbol_name, json_output)

    # Python path (original logic)
    return _run_sig_python(content, file_path, symbol_name, json_output)


# @shell_complexity: Python sig orchestration with error handling and output modes
def _run_sig_python(
    content: str, file_path: Path, symbol_name: str | None, json_output: bool
) -> Result[None, str]:
    """Run sig for Python files."""
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


# @shell_complexity: TypeScript sig orchestration with error handling and output modes
def _run_sig_typescript(
    content: str, file_path: Path, symbol_name: str | None, json_output: bool
) -> Result[None, str]:
    """Run sig for TypeScript files (LX-06)."""
    from invar.core.ts_sig_parser import (
        extract_ts_signatures,
        format_ts_signatures_json,
        format_ts_signatures_text,
    )

    # Handle empty files consistently with Python path
    symbols = [] if not content.strip() else extract_ts_signatures(content)

    # Filter by symbol name if specified
    if symbol_name:
        symbols = [s for s in symbols if s.name == symbol_name]
        if not symbols:
            return Failure(f"Symbol '{symbol_name}' not found in {file_path}")

    # Output
    if json_output:
        output = format_ts_signatures_json(symbols, str(file_path))
        console.print(json.dumps(output, indent=2))
    else:
        output = format_ts_signatures_text(symbols, str(file_path))
        console.print(output)

    return Success(None)


# @shell_complexity: Python map with perception map building
def _run_map_python(path: Path, top_n: int, json_output: bool) -> Result[None, str]:
    """Run map for Python projects (original logic)."""
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


# @shell_complexity: TypeScript map with file discovery and symbol extraction
def _run_map_typescript(path: Path, top_n: int, json_output: bool) -> Result[None, str]:
    """Run map for TypeScript projects (LX-06).

    MVP: Lists symbols without reference counting (Phase 2 can add references).
    """
    from invar.core.ts_sig_parser import TSSymbol, extract_ts_signatures
    from invar.shell.fs import discover_typescript_files

    all_symbols: list[tuple[str, TSSymbol]] = []

    for ts_file in discover_typescript_files(path):
        try:
            content = ts_file.read_text(encoding="utf-8")
            rel_path = str(ts_file.relative_to(path))
            if not content.strip():
                continue
            symbols = extract_ts_signatures(content)
            for sym in symbols:
                all_symbols.append((rel_path, sym))
        except (OSError, UnicodeDecodeError) as e:
            console.print(f"[yellow]Warning:[/yellow] {ts_file}: {e}")
            continue

    if not all_symbols:
        return Failure("No TypeScript symbols found (files may be empty or contain no exportable symbols)")

    # Sort by kind priority (function/class first), then by name
    kind_order = {"function": 0, "class": 1, "interface": 2, "type": 3, "const": 4, "method": 5}
    all_symbols.sort(key=lambda x: (kind_order.get(x[1].kind, 99), x[1].name))

    # Limit to top_n
    display_symbols = all_symbols[:top_n] if top_n > 0 else all_symbols

    # Output
    if json_output:
        output = {
            "language": "typescript",
            "total_symbols": len(all_symbols),
            "symbols": [
                {
                    "name": sym.name,
                    "kind": sym.kind,
                    "file": file_path,
                    "line": sym.line,
                    "signature": sym.signature,
                }
                for file_path, sym in display_symbols
            ],
        }
        console.print(json.dumps(output, indent=2))
    else:
        console.print("[bold]TypeScript Symbol Map[/bold]")
        console.print(f"Total symbols: {len(all_symbols)}\n")
        for file_path, sym in display_symbols:
            console.print(f"[{sym.kind}] {sym.name}")
            console.print(f"  {file_path}:{sym.line}")
            console.print(f"  {sym.signature}")
            console.print()

    return Success(None)
