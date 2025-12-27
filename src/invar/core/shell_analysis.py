"""
Shell source analysis helpers for DX-22.

Helper functions for analyzing Shell layer code:
- I/O operation detection
- Marker pattern detection
- Branch counting
- Symbol source extraction

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from deal import post, pre

if TYPE_CHECKING:
    from invar.core.models import Symbol

# I/O indicators that mark a function as legitimately in Shell
IO_INDICATORS: frozenset[str] = frozenset([
    # File operations
    ".read(",
    ".write(",
    ".read_text(",
    ".write_text(",
    ".read_bytes(",
    ".write_bytes(",
    "open(",
    "Path(",
    ".exists()",
    ".is_file()",
    ".is_dir()",
    ".rglob(",
    ".glob(",
    ".iterdir(",
    ".mkdir(",
    ".unlink(",
    "shutil.",
    "tempfile.",
    # Process operations
    "subprocess.",
    "os.system(",
    "os.popen(",
    "os.getenv(",
    "os.environ",
    # Terminal/System
    "sys.stdout",
    "sys.stderr",
    "sys.stdin",
    ".isatty()",
    # Module loading
    "importlib.",
    "exec_module(",
    # Network operations
    "requests.",
    "aiohttp.",
    "httpx.",
    "urllib.",
    # Console output
    "print(",
    "console.",
    "Console(",
    "typer.",
    "click.",
    "rich.",
    # Result wrapping (Shell's primary job)
    "Success(",
    "Failure(",
    "Result[",
    # Database
    "cursor.",
    "connection.",
    "session.",
    # Logging
    "logger.",
    "logging.",
    # Serialization (often to files)
    "json.dump(",
    "json.load(",
    "toml.load(",
    "yaml.load(",
])

# Marker pattern to exempt functions from complexity check
COMPLEXITY_MARKER_PATTERN = re.compile(r"#\s*@shell_complexity\s*:")

# Marker pattern to exempt functions from pure logic check (for orchestration functions)
ORCHESTRATION_MARKER_PATTERN = re.compile(r"#\s*@shell_orchestration\s*:")


# @invar:allow missing_contract: Boolean predicate, empty string is valid input
def has_io_operations(source: str) -> bool:
    """
    Check if source code contains I/O operations.

    Examples:
        >>> has_io_operations("x = Success(value)")
        True
        >>> has_io_operations("return x + y")
        False
        >>> has_io_operations("path.read_text()")
        True
        >>> has_io_operations("print('hello')")
        True
    """
    return any(indicator in source for indicator in IO_INDICATORS)


@pre(lambda symbol, source: symbol is not None)  # Symbol must exist
def has_orchestration_marker(symbol: Symbol, source: str) -> bool:
    """
    Check if symbol has @shell_orchestration marker comment.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="run_phase", kind=SymbolKind.FUNCTION, line=3, end_line=10)
        >>> source = '''
        ... # @shell_orchestration: Coordinates shell modules
        ... def run_phase():
        ...     pass
        ... '''
        >>> has_orchestration_marker(sym, source)
        True

        >>> sym2 = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> has_orchestration_marker(sym2, "def calc(): pass")
        False
    """
    lines = source.splitlines()
    if not lines:
        return False

    start_line = max(0, symbol.line - 4)
    end_line = symbol.line

    context_lines = lines[start_line:end_line]
    context = "\n".join(context_lines)

    return bool(ORCHESTRATION_MARKER_PATTERN.search(context))


@pre(lambda symbol, source: symbol is not None)  # Symbol must exist
def has_complexity_marker(symbol: Symbol, source: str) -> bool:
    """
    Check if symbol has @shell_complexity marker comment.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="load", kind=SymbolKind.FUNCTION, line=3, end_line=10)
        >>> source = '''
        ... # @shell_complexity: Config cascade with fallbacks
        ... def load():
        ...     pass
        ... '''
        >>> has_complexity_marker(sym, source)
        True

        >>> sym2 = Symbol(name="simple", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> has_complexity_marker(sym2, "def simple(): pass")
        False
    """
    lines = source.splitlines()
    if not lines:
        return False

    # Look at lines before the function definition
    start_line = max(0, symbol.line - 4)
    end_line = symbol.line

    context_lines = lines[start_line:end_line]
    context = "\n".join(context_lines)

    return bool(COMPLEXITY_MARKER_PATTERN.search(context))


@post(lambda result: result >= 0)  # Branch count is non-negative
def count_branches(source: str) -> int:
    """
    Count the number of branches in source code.

    Counts: if, elif, except, for, while, match case, ternary

    Examples:
        >>> count_branches("if x: pass")
        1
        >>> count_branches("if x: pass\\nelif y: pass")
        2
        >>> count_branches("for x in y: pass")
        1
        >>> count_branches("x = a if b else c")
        1
        >>> count_branches("pass")
        0
        >>> count_branches("")
        0
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # ast.walk visits all If nodes including elifs
            count += 1
        elif isinstance(node, ast.For | ast.While | ast.ExceptHandler):
            count += 1
        elif isinstance(node, ast.Match):
            # Count match cases
            count += len(node.cases)
        elif isinstance(node, ast.IfExp):
            # Ternary expression
            count += 1

    return count


@pre(lambda symbol, file_source: symbol is not None)  # Symbol must exist
def get_symbol_source(symbol: Symbol, file_source: str) -> str:
    """
    Extract the source code for a specific symbol.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=2, end_line=4)
        >>> source = '''# comment
        ... def foo():
        ...     return 1
        ... '''
        >>> 'def foo' in get_symbol_source(sym, source)
        True
    """
    lines = file_source.splitlines()
    if not lines:
        return ""

    # Line numbers are 1-indexed
    start = max(0, symbol.line - 1)
    end = min(len(lines), symbol.end_line)

    return "\n".join(lines[start:end])
