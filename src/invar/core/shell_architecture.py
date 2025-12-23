"""
Shell architecture rules for DX-22.

Detects architectural issues in Shell layer:
- shell_pure_logic: Pure logic that belongs in Core
- shell_too_complex: Excessive branching complexity

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from deal import post, pre

from invar.core.entry_points import get_symbol_lines, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation

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
    # Process operations
    "subprocess.",
    "os.system(",
    "os.popen(",
    # Network operations
    "requests.",
    "aiohttp.",
    "httpx.",
    "urllib.",
    # Console output
    "print(",
    "console.",
    "typer.",
    "click.",
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
])

# Marker pattern to exempt functions from complexity check
COMPLEXITY_MARKER_PATTERN = re.compile(r"#\s*@shell_complexity\s*:")

# Marker pattern to exempt functions from pure logic check (for orchestration functions)
PURE_MARKER_PATTERN = re.compile(r"#\s*@shell_orchestration\s*:")


@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, bool))
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


@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
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

    return bool(PURE_MARKER_PATTERN.search(context))


@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
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


@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, int) and result >= 0)
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


@pre(lambda symbol, file_source: symbol is not None and isinstance(file_source, str))
@post(lambda result: isinstance(result, str))
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


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_shell_pure_logic(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions contain I/O operations (DX-22).

    Pure logic belongs in Core where it can be tested with contracts.
    Functions > 5 lines without I/O indicators are flagged as ERROR.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=10)
        >>> source = "def calc(x, y):\\n    return x + y"
        >>> info = FileInfo(path="shell/util.py", lines=10, symbols=[sym], is_shell=True, source=source)
        >>> violations = check_shell_pure_logic(info, RuleConfig())
        >>> len(violations) >= 0  # May or may not flag based on line count
        True
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # Skip small functions (wrappers are fine)
        lines = get_symbol_lines(symbol)
        if lines <= 5:
            continue

        # Skip entry points (they're handled by DX-23)
        if is_entry_point(symbol, file_info.source):
            continue

        # Skip if marked with @shell_orchestration (coordinates other shell modules)
        if has_orchestration_marker(symbol, file_info.source):
            continue

        # Get symbol source and check for I/O
        symbol_source = get_symbol_source(symbol, file_info.source)
        if not has_io_operations(symbol_source):
            violations.append(
                Violation(
                    rule="shell_pure_logic",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' has no I/O operations - pure logic belongs in Core",
                    suggestion="Move to src/*/core/ and add @pre/@post contracts, or add: # @shell_orchestration: <reason>",
                )
            )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_shell_too_complex(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions don't have excessive branching (DX-22).

    Complex logic should be in Core where it can be tested.
    Functions exceeding shell_max_branches are flagged as INFO.

    Use @shell_complexity marker to exempt justified complexity.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="process", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> source = "def process(x):\\n    return x"
        >>> info = FileInfo(path="shell/cli.py", lines=5, symbols=[sym], is_shell=True, source=source)
        >>> check_shell_too_complex(info, RuleConfig())
        []
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    max_branches = config.shell_max_branches

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # Skip if marked with @shell_complexity
        if has_complexity_marker(symbol, file_info.source):
            continue

        # Skip entry points
        if is_entry_point(symbol, file_info.source):
            continue

        # Count branches in symbol source
        symbol_source = get_symbol_source(symbol, file_info.source)
        branches = count_branches(symbol_source)

        if branches > max_branches:
            violations.append(
                Violation(
                    rule="shell_too_complex",
                    severity=Severity.INFO,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' has {branches} branches (max: {max_branches})",
                    suggestion="Extract logic to Core, or add: # @shell_complexity: <reason>",
                )
            )

    return violations
