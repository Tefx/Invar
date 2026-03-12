"""Perception CLI implementation.

Shell module: handles file I/O for map, sig, and refs commands.
"""

from __future__ import annotations

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
from invar.shell.json_output import write_json

if TYPE_CHECKING:
    from invar.core.models import Symbol

console = Console()


# @shell_complexity: Symbol map generation with sorting and output modes
def run_map(path: Path, top_n: int, json_output: bool) -> Result[None, str]:
    """Run map command for Python projects."""
    if not path.exists():
        return Failure(f"Path does not exist: {path}")
    return _run_map_python(path, top_n, json_output)


# @shell_complexity: Signature extraction with symbol filtering
def run_sig(target: str, json_output: bool) -> Result[None, str]:
    """
    Run the sig command.

    Extracts signatures from a file or specific symbol.
    Target format: "path/to/file.py" or "path/to/file.py::symbol_name".
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

    suffix = file_path.suffix.lower()
    if suffix not in (".py", ".pyi"):
        return Failure(f"Unsupported file type: {suffix}\n\nSupported: .py, .pyi")

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
        write_json(output, indent=2)
    else:
        output = format_signatures_text(symbols, str(file_path))
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
            "No source files found in this directory.\n\n"
            "💡 Available tools:\n"
            "- invar sig <file> — Extract signatures\n"
            "- invar refs <file>::Symbol — Find references\n"
            "- invar_doc_* — Document navigation\n"
            "- invar_guard — Static verification"
        )

    # Build perception map
    perception_map = build_perception_map(file_infos, sources, str(path.absolute()))

    # Output
    if json_output:
        output = format_map_json(perception_map, top_n)
        write_json(output, indent=2)
    else:
        output = format_map_text(perception_map, top_n)
        console.print(output)

    return Success(None)


# @shell_complexity: Reference finding with multi-language support and output formatting
def run_refs(target: str, json_output: bool) -> Result[None, str]:
    """Find all references to a symbol.

    Target format: "path/to/file.py::symbol_name".
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

    if suffix in (".py", ".pyi"):
        return _run_refs_python(file_path, symbol_name, json_output)
    return Failure(f"Unsupported file type: {suffix}\n\nSupported: .py, .pyi")


# @shell_complexity: Reference finding with output formatting and error handling
def _run_refs_python(file_path: Path, symbol_name: str, json_output: bool) -> Result[None, str]:
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
        write_json(output, indent=2)
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
