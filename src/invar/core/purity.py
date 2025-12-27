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

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation

# Known impure functions and method patterns
# MINOR-3: "time" matches `from time import time; time()` which IS impure.
# May false positive on local functions named `time`, but this is rare.
IMPURE_FUNCTIONS: set[str] = {
    "now",
    "today",
    "utcnow",
    "time",  # from time import time
    "random",
    "randint",
    "randrange",
    "choice",
    "shuffle",
    "sample",
    "open",
    "print",
    "input",
    "getenv",
    "environ",
}
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


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and hasattr(node, "body"))
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
        elif isinstance(child, ast.ImportFrom) and child.module:
            imports.append(child.module.split(".")[0])

    return list(set(imports))


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and hasattr(node, "body"))
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


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and hasattr(node, "body"))
def extract_function_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Extract all function calls from a function body (P25: for extraction analysis).

    Only extracts simple function calls (not method calls on objects).
    Used to build call graph for grouping related functions.

    Examples:
        >>> import ast
        >>> code = '''
        ... def foo():
        ...     helper()
        ...     result = calculate(x)
        ...     return result
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> sorted(extract_function_calls(func))
        ['calculate', 'helper']
        >>> # Method calls are excluded
        >>> code2 = '''
        ... def bar():
        ...     self.method()
        ...     obj.call()
        ...     helper()
        ... '''
        >>> tree2 = ast.parse(code2)
        >>> func2 = tree2.body[0]
        >>> extract_function_calls(func2)
        ['helper']
    """
    calls: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            # Only simple function calls (not x.method())
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)

    return list(set(calls))


@pre(lambda call: isinstance(call, ast.Call) and hasattr(call, "func"))
def _get_call_name(call: ast.Call) -> str | None:
    """Get the name of a function call as a string.

    MINOR-4 Limitation: Only handles one level of attribute access (obj.method).
    Chained access like a.b.method() returns None. This is acceptable since
    IMPURE_PATTERNS only contains two-level patterns like ("datetime", "now").
    """
    func = call.func

    # Simple name: print(), open()
    if isinstance(func, ast.Name):
        return func.id

    # Attribute: datetime.now(), random.randint()
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"

    return None


@pre(lambda call_name: isinstance(call_name, str) and len(call_name) > 0)
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


@pre(
    lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    and hasattr(node, "lineno")
    and hasattr(node, "body")
)
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
            (docstring_node.end_lineno or docstring_node.lineno) - docstring_node.lineno + 1
        )

    return total_lines - docstring_lines


@pre(lambda node: isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and hasattr(node, "body"))
def count_doctest_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Count lines that are doctest examples in the docstring.

    Counts both `>>> ` input lines and their expected output lines.

    Examples:
        >>> import ast
        >>> code = '''
        ... def foo():
        ...     \"\"\"Example.
        ...
        ...     Examples:
        ...         >>> foo()
        ...         42
        ...         >>> foo() + 1
        ...         43
        ...     \"\"\"
        ...     return 42
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> count_doctest_lines(func)
        4
    """
    docstring = ast.get_docstring(node)
    if not docstring:
        return 0

    count = 0
    in_doctest = False
    for line in docstring.split("\n"):
        stripped = line.strip()
        if stripped.startswith(">>> "):
            count += 1
            in_doctest = True
        elif stripped.startswith("... "):
            count += 1  # Continuation line
        elif in_doctest and stripped and not stripped.startswith(">>>"):
            count += 1  # Expected output line
            # Note: Empty line ends doctest, handled by else branch below
        else:
            in_doctest = False
    return count


# Rule checking functions


@post(lambda result: all(v.rule == "internal_import" for v in result))  # Rule consistency
def check_internal_imports(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for imports inside function bodies.

    Only applies to Core files when strict_pure is enabled.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(
        ...     name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     internal_imports=["os"]
        ... )
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_internal_imports(info, RuleConfig(strict_pure=True))
        >>> len(violations)
        1
    """
    violations: list[Violation] = []

    if not file_info.is_core or not config.strict_pure:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and symbol.internal_imports:
            kind_name = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
            violations.append(
                Violation(
                    rule="internal_import",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"{kind_name} '{symbol.name}' has internal imports: {', '.join(symbol.internal_imports)}",
                    suggestion="Move imports to top of file or move function to Shell",
                )
            )

    return violations


@post(lambda result: all(v.rule == "impure_call" for v in result))  # Rule consistency
def check_impure_calls(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for calls to known impure functions.

    Only applies to Core files when strict_pure is enabled.
    Respects config.purity_pure for user-declared pure functions.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(
        ...     name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     impure_calls=["datetime.now", "print"]
        ... )
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_impure_calls(info, RuleConfig(strict_pure=True))
        >>> len(violations)
        1
        >>> # User declares print as pure → no violation
        >>> violations = check_impure_calls(info, RuleConfig(purity_pure=["print"]))
        >>> any("print" in v.message for v in violations)
        False
    """
    violations: list[Violation] = []

    if not file_info.is_core or not config.strict_pure:
        return violations

    # B4: User-declared pure functions override blacklist
    pure_set = set(config.purity_pure)

    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and symbol.impure_calls:
            # Filter out user-declared pure functions
            actual_impure = [c for c in symbol.impure_calls if c not in pure_set]
            if actual_impure:
                kind_name = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(
                    Violation(
                        rule="impure_call",
                        severity=Severity.ERROR,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"{kind_name} '{symbol.name}' calls impure functions: {', '.join(actual_impure)}",
                        suggestion="Inject dependencies or move function to Shell",
                    )
                )

    return violations
