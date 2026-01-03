"""
Perception CLI implementation (Phase 4).

Shell module: handles file I/O for map and sig commands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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
        # DX-78 Phase B: Suggest alternative tools
        return Failure(
            f"File not found: {file_path}\n\n"
            "💡 Try using Grep to search for the symbol across the codebase."
        )

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
    """Run sig for TypeScript files.

    DX-78: Uses TS Compiler API when available, falls back to regex parser.
    """
    from invar.shell.ts_compiler import is_typescript_available, run_sig_typescript

    # Try TS Compiler API first (DX-78)
    if is_typescript_available():
        sig_result = run_sig_typescript(file_path)
        if isinstance(sig_result, Success):
            symbols = sig_result.unwrap()

            # Filter by symbol name if specified
            if symbol_name:
                symbols = [s for s in symbols if s.name == symbol_name]
                if not symbols:
                    return Failure(f"Symbol '{symbol_name}' not found in {file_path}")

            # Output using TS Compiler API format
            if json_output:
                output = {
                    "file": str(file_path),
                    "symbols": [
                        {
                            "name": s.name,
                            "kind": s.kind,
                            "signature": s.signature,
                            "line": s.line,
                            "contracts": s.contracts,
                            "members": s.members,
                        }
                        for s in symbols
                    ],
                }
                console.print(json.dumps(output, indent=2))
            else:
                console.print(f"[bold]{file_path}[/bold]")
                for s in symbols:
                    console.print(f"  [{s.kind}] {s.name}")
                    console.print(f"    {s.signature}")
                    if s.contracts:
                        for pre in s.contracts.get("pre", []):
                            console.print(f"    @pre {pre}")
                        for post in s.contracts.get("post", []):
                            console.print(f"    @post {post}")
                    if s.members:
                        for m in s.members:
                            console.print(f"    [{m['kind']}] {m['name']}: {m.get('signature', '')}")
                    console.print()

            return Success(None)

    # Fallback to regex parser (LX-06 legacy)
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

    # Convert generator to list to release directory handles immediately (DX-82)
    python_files = list(discover_python_files(path))

    for py_file in python_files:
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

    # Release file list to free memory (DX-82)
    del python_files

    if not file_infos:
        return Failure(
            "No Python symbols found.\n\n"
            "Available tools:\n"
            "- invar sig <file.py> — Extract signatures\n"
            "- invar refs <file.py>::Symbol — Find references\n"
            "- invar_doc_* — Document navigation\n"
            "- invar_guard — Static verification"
        )

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
    """Run map for TypeScript projects.

    DX-78: Uses TS Compiler API when available, falls back to regex parser.
    """
    from invar.shell.ts_compiler import is_typescript_available, run_map_typescript

    # Try TS Compiler API first (DX-78)
    if is_typescript_available():
        map_result = run_map_typescript(path, top_n)
        if isinstance(map_result, Success):
            data = map_result.unwrap()

            if not data.get("symbols"):
                return Failure(
                    "No TypeScript symbols found.\n\n"
                    "Available tools:\n"
                    "- invar sig <file.ts> — Extract signatures\n"
                    "- invar refs <file.ts>::Symbol — Find references\n"
                    "- invar_doc_* — Document navigation\n"
                    "- invar_guard — Static verification"
                )

            # Output using TS Compiler API format
            if json_output:
                output = {
                    "language": "typescript",
                    "total_symbols": data.get("total", len(data["symbols"])),
                    "symbols": data["symbols"],
                }
                console.print(json.dumps(output, indent=2))
            else:
                console.print("[bold]TypeScript Symbol Map[/bold]")
                console.print(f"Total symbols: {data.get('total', len(data['symbols']))}\n")
                for sym in data["symbols"]:
                    console.print(f"[{sym['kind']}] {sym['name']}")
                    console.print(f"  {sym['file']}:{sym['line']}")
                    console.print()

            return Success(None)

    # Fallback to regex parser (LX-06 legacy)
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
        return Failure(
            "No TypeScript symbols found.\n\n"
            "Available tools:\n"
            "- invar sig <file.ts> — Extract signatures\n"
            "- invar refs <file.ts>::Symbol — Find references\n"
            "- invar_doc_* — Document navigation\n"
            "- invar_guard — Static verification"
        )

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


# @shell_complexity: Reference finding with multi-language support and output formatting
def run_refs(target: str, json_output: bool) -> Result[None, str]:
    """Find all references to a symbol.

    Target format: "path/to/file.py::symbol_name" or "path/to/file.ts::symbol_name"
    DX-78: Supports both Python (via jedi) and TypeScript (via TS Compiler API).
    """
    # Parse target
    if "::" not in target:
        return Failure(
            "Invalid target format.\n\n"
            "Expected: path/to/file.py::symbol_name\n"
            "Example: src/auth.py::validate_token"
        )

    file_part, symbol_name = target.rsplit("::", 1)
    file_path = Path(file_part)

    if not file_path.exists():
        return Failure(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()

    # Route to language-specific implementation
    if suffix in (".ts", ".tsx"):
        return _run_refs_typescript(file_path, symbol_name, json_output)
    elif suffix in (".py", ".pyi"):
        return _run_refs_python(file_path, symbol_name, json_output)
    else:
        return Failure(
            f"Unsupported file type: {suffix}\n\n"
            "Supported: .py, .pyi, .ts, .tsx"
        )


# @shell_complexity: Reference finding with output formatting and error handling
def _run_refs_python(
    file_path: Path, symbol_name: str, json_output: bool
) -> Result[None, str]:
    """Find references in Python using jedi."""
    from invar.shell.py_refs import find_all_references_to_symbol

    # Find project root
    project_root = file_path.parent
    for parent in file_path.parents:
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            project_root = parent
            break

    refs = find_all_references_to_symbol(file_path, symbol_name, project_root)

    if not refs:
        return Failure(f"Symbol '{symbol_name}' not found in {file_path}")

    # Output
    if json_output:
        output = {
            "target": str(file_path) + "::" + symbol_name,
            "total": len(refs),
            "references": [
                {
                    "file": str(ref.file.relative_to(project_root))
                    if ref.file.is_relative_to(project_root)
                    else str(ref.file),
                    "line": ref.line,
                    "column": ref.column,
                    "context": ref.context,
                    "is_definition": ref.is_definition,
                }
                for ref in refs
            ],
        }
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"[bold]References to {symbol_name}[/bold]")
        console.print(f"Found {len(refs)} reference(s)\n")

        for ref in refs:
            rel_path = (
                ref.file.relative_to(project_root)
                if ref.file.is_relative_to(project_root)
                else ref.file
            )
            marker = " [definition]" if ref.is_definition else ""
            console.print(f"{rel_path}:{ref.line}{marker}")
            if ref.context:
                console.print(f"  {ref.context}")
            console.print()

    return Success(None)


@dataclass
class _SymbolPosition:
    """Temporary holder for symbol position during refs lookup."""
    line: int
    column: int
    name: str


# @shell_complexity: TypeScript refs with symbol lookup and output formatting
def _run_refs_typescript(
    file_path: Path, symbol_name: str, json_output: bool
) -> Result[None, str]:
    """Find references in TypeScript using TS Compiler API."""
    from invar.shell.ts_compiler import is_typescript_available, run_refs_typescript

    if not is_typescript_available():
        return Failure(
            "TypeScript tools not available.\n\n"
            "Requirements:\n"
            "- Node.js installed\n"
            "- tsconfig.json in project root"
        )

    # First, find the symbol's position using sig command
    from invar.shell.ts_compiler import run_sig_typescript

    sig_result = run_sig_typescript(file_path)
    if isinstance(sig_result, Failure):
        return sig_result

    symbols = sig_result.unwrap()
    symbol = next((s for s in symbols if s.name == symbol_name), None)

    if symbol is None:
        # Check class members
        for s in symbols:
            if s.members:
                for member in s.members:
                    if member.get("name") == symbol_name:
                        # Extract column if available, default to 0
                        column = member.get("column", 0)
                        symbol = _SymbolPosition(
                            line=member["line"],
                            column=column,
                            name=symbol_name
                        )
                        break
            if symbol:
                break

    if symbol is None:
        return Failure(f"Symbol '{symbol_name}' not found in {file_path}")

    # Find references using position
    # Use symbol.column if available (from member dict), defaults to 0
    column = getattr(symbol, "column", 0)
    refs_result = run_refs_typescript(file_path, symbol.line, column)
    if isinstance(refs_result, Failure):
        return refs_result

    refs = refs_result.unwrap()

    if not refs:
        return Failure(f"No references found for '{symbol_name}'")

    # Output (refs already have relative paths from ts-query.js)
    if json_output:
        output = {
            "target": str(file_path) + "::" + symbol_name,
            "total": len(refs),
            "references": [
                {
                    "file": ref.file,
                    "line": ref.line,
                    "column": ref.column,
                    "context": ref.context,
                    "is_definition": ref.is_definition,
                }
                for ref in refs
            ],
        }
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"[bold]References to {symbol_name}[/bold]")
        console.print(f"Found {len(refs)} reference(s)\n")

        for ref in refs:
            marker = " [definition]" if ref.is_definition else ""
            console.print(f"{ref.file}:{ref.line}{marker}")
            if ref.context:
                console.print(f"  {ref.context}")
            console.print()

    return Success(None)
