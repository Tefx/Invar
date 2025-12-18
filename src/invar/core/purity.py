"""
Purity detection for Guard Enhancement (Phase 3).

This module provides functions to detect:
- Internal imports (imports inside function bodies)
- Impure function calls (datetime.now, random.*, open, print, etc.)
- Code line counting (excluding docstrings)

No I/O operations - receives AST nodes only.
"""

from __future__ import annotations

import ast

from deal import pre

from invar.core.models import FileInfo, Severity, Symbol, SymbolKind, Violation


# Known impure functions that indicate side effects
IMPURE_FUNCTIONS: set[str] = {
    # Time-related
    "now", "today", "utcnow", "time",
    # Randomness
    "random", "randint", "randrange", "choice", "shuffle", "sample",
    # I/O
    "open", "print", "input",
    # System
    "getenv", "environ",
}

# Known impure method calls (object.method patterns)
IMPURE_PATTERNS: set[tuple[str, str]] = {
    ("datetime", "now"),
    ("datetime", "today"),
    ("datetime", "utcnow"),
    ("date", "today"),
    ("time", "time"),
    ("random", "random"),
    ("random", "randint"),
    ("random", "randrange"),
    ("random", "choice"),
    ("random", "shuffle"),
    ("random", "sample"),
    ("os", "getenv"),
}


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef))
def extract_internal_imports(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Extract imports inside a function body.

    Examples:
        >>> import ast
        >>> code = '''
        ... def foo():
        ...     import os
        ...     from pathlib import Path
        ...     return Path(".")
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> sorted(extract_internal_imports(func))
        ['os', 'pathlib']
    """
    imports: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(child, ast.ImportFrom):
            if child.module:
                imports.append(child.module.split(".")[0])

    return list(set(imports))


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef))
def extract_impure_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Extract calls to known impure functions.

    Examples:
        >>> import ast
        >>> code = '''
        ... def foo():
        ...     x = datetime.now()
        ...     print("hello")
        ...     return x
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> sorted(extract_impure_calls(func))
        ['datetime.now', 'print']
    """
    impure: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            call_name = _get_call_name(child)
            if call_name and _is_impure_call(call_name):
                impure.append(call_name)

    return list(set(impure))


def _get_call_name(call: ast.Call) -> str | None:
    """Get the name of a function call as a string."""
    func = call.func

    # Simple name: print(), open()
    if isinstance(func, ast.Name):
        return func.id

    # Attribute: datetime.now(), random.randint()
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"

    return None


def _is_impure_call(call_name: str) -> bool:
    """Check if a call name represents an impure function."""
    # Check simple names
    if call_name in IMPURE_FUNCTIONS:
        return True

    # Check patterns like datetime.now
    if "." in call_name:
        parts = call_name.split(".")
        if len(parts) == 2 and (parts[0], parts[1]) in IMPURE_PATTERNS:
            return True

    return False


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef))
def count_code_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Count lines of code excluding docstring.

    The total function lines minus docstring lines gives the actual code lines.

    Examples:
        >>> import ast
        >>> code = '''
        ... def foo():
        ...     \"\"\"This is a docstring.\"\"\"
        ...     x = 1
        ...     return x
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> count_code_lines(func)
        3
    """
    total_lines = (node.end_lineno or node.lineno) - node.lineno + 1

    # Check for docstring
    docstring_lines = 0
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        docstring_node = node.body[0]
        docstring_lines = (
            (docstring_node.end_lineno or docstring_node.lineno)
            - docstring_node.lineno
            + 1
        )

    return total_lines - docstring_lines


# Rule checking functions


@pre(lambda file_info, strict_pure: isinstance(file_info, FileInfo))
def check_internal_imports(file_info: FileInfo, strict_pure: bool) -> list[Violation]:
    """
    Check for imports inside function bodies.

    Only applies to Core files when strict_pure is enabled.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(
        ...     name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     internal_imports=["os"]
        ... )
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_internal_imports(info, strict_pure=True)
        >>> len(violations)
        1
    """
    violations: list[Violation] = []

    if not file_info.is_core or not strict_pure:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind == SymbolKind.FUNCTION and symbol.internal_imports:
            violations.append(
                Violation(
                    rule="internal_import",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=(
                        f"Function '{symbol.name}' has internal imports: "
                        f"{', '.join(symbol.internal_imports)}"
                    ),
                    suggestion="Move imports to top of file or move function to Shell",
                )
            )

    return violations


@pre(lambda file_info, strict_pure: isinstance(file_info, FileInfo))
def check_impure_calls(file_info: FileInfo, strict_pure: bool) -> list[Violation]:
    """
    Check for calls to known impure functions.

    Only applies to Core files when strict_pure is enabled.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(
        ...     name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     impure_calls=["datetime.now", "print"]
        ... )
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_impure_calls(info, strict_pure=True)
        >>> len(violations)
        1
    """
    violations: list[Violation] = []

    if not file_info.is_core or not strict_pure:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind == SymbolKind.FUNCTION and symbol.impure_calls:
            violations.append(
                Violation(
                    rule="impure_call",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=(
                        f"Function '{symbol.name}' calls impure functions: "
                        f"{', '.join(symbol.impure_calls)}"
                    ),
                    suggestion="Inject dependencies or move function to Shell",
                )
            )

    return violations
