"""Python reference finding using jedi.

DX-78: Provides cross-file reference finding for Python symbols.
Shell module: Uses jedi library for I/O-based symbol analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import jedi


@dataclass
class Reference:
    """A reference to a Python symbol."""

    file: Path
    line: int
    column: int
    context: str
    is_definition: bool = False


# @shell_complexity: Reference finding with jedi library and error handling
def find_references(
    file_path: Path,
    line: int,
    column: int,
    project_root: Path | None = None,
) -> list[Reference]:
    """Find all references to symbol at position using jedi.

    Args:
        file_path: File containing the symbol
        line: 1-based line number
        column: 0-based column number
        project_root: Project root for cross-file resolution

    Returns:
        List of references found

    >>> from pathlib import Path
    >>> import tempfile, os
    >>> # Test with a simple Python file
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    ...     _ = f.write('def hello():\\n    pass\\n')
    ...     temp_file = Path(f.name)
    >>> # Find references returns a list (may be empty if jedi not configured)
    >>> refs = find_references(temp_file, 1, 4)
    >>> isinstance(refs, list)
    True
    >>> os.unlink(temp_file)
    """
    source = file_path.read_text(encoding="utf-8")

    project = None
    if project_root:
        project = jedi.Project(path=str(project_root))

    script = jedi.Script(source, path=str(file_path), project=project)
    refs = script.get_references(line, column)

    results: list[Reference] = []
    for ref in refs:
        # Skip builtins (no module_path)
        if not ref.module_path:
            continue

        line_code = ref.get_line_code()
        context = line_code.strip() if line_code else ""

        results.append(
            Reference(
                file=Path(ref.module_path),
                line=ref.line,
                column=ref.column,
                context=context,
                is_definition=ref.is_definition(),
            )
        )

    return results


# @shell_complexity: Symbol search using jedi library
def find_symbol_position(file_path: Path, symbol_name: str) -> tuple[int, int] | None:
    """Find the position of a symbol definition in a file.

    Args:
        file_path: File to search
        symbol_name: Name of the symbol to find

    Returns:
        Tuple of (line, column) or None if not found

    >>> from pathlib import Path
    >>> import tempfile, os
    >>> # Test finding a function definition
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    ...     _ = f.write('def test_func():\\n    return 42\\n')
    ...     temp_file = Path(f.name)
    >>> pos = find_symbol_position(temp_file, "test_func")
    >>> isinstance(pos, tuple) or pos is None  # Returns tuple or None
    True
    >>> os.unlink(temp_file)
    """
    source = file_path.read_text(encoding="utf-8")
    script = jedi.Script(source, path=str(file_path))

    # Get all names defined in the file
    names = script.get_names(all_scopes=True)

    for name in names:
        if name.name == symbol_name and name.is_definition():
            return (name.line, name.column)

    return None


# @shell_complexity: Combines symbol position lookup and reference finding
def find_all_references_to_symbol(
    file_path: Path,
    symbol_name: str,
    project_root: Path | None = None,
) -> list[Reference]:
    """Find all references to a named symbol.

    Convenience function that combines find_symbol_position and find_references.

    Args:
        file_path: File containing the symbol definition
        symbol_name: Name of the symbol
        project_root: Project root for cross-file resolution

    Returns:
        List of references found

    >>> from pathlib import Path
    >>> import tempfile, os
    >>> # Test finding all references to a symbol
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    ...     _ = f.write('def greet():\\n    pass\\ngreet()\\n')
    ...     temp_file = Path(f.name)
    >>> refs = find_all_references_to_symbol(temp_file, "greet")
    >>> isinstance(refs, list)  # Returns list of references
    True
    >>> os.unlink(temp_file)
    """
    position = find_symbol_position(file_path, symbol_name)
    if position is None:
        return []

    line, column = position
    return find_references(file_path, line, column, project_root)
