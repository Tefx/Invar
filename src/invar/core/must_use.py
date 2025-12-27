"""
Must-use return value detection.

Core module: detects ignored return values of @must_use functions.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Severity, Violation


@pre(lambda source: isinstance(source, str) and len(source) > 0)
def find_must_use_functions(source: str) -> dict[str, str]:
    """
    Find all functions decorated with @must_use in source code.

    Returns a dict mapping function name to the must_use reason.

    >>> code = '''
    ... from invar import must_use
    ... @must_use("Handle the error")
    ... def validate(): pass
    ... '''
    >>> find_must_use_functions(code)
    {'validate': 'Handle the error'}

    >>> code = '''
    ... @must_use()
    ... def check(): pass
    ... '''
    >>> find_must_use_functions(code)
    {'check': 'Return value must be used'}

    >>> find_must_use_functions("def foo(): pass")
    {}
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return {}

    must_use_funcs: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            reason = _extract_must_use_reason(decorator)
            if reason is not None:
                must_use_funcs[node.name] = reason
                break

    return must_use_funcs


@pre(lambda decorator: isinstance(decorator, ast.expr) and hasattr(decorator, '__class__'))
@post(lambda result: result is None or isinstance(result, str))
def _extract_must_use_reason(decorator: ast.expr) -> str | None:
    """Extract reason from @must_use decorator, or None if not a must_use."""
    # Case 1: @must_use("reason")
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == "must_use":
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
            return "Return value must be used"
        if isinstance(func, ast.Attribute) and func.attr == "must_use":
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
            return "Return value must be used"

    # Case 2: @must_use (no parens - though our API requires parens)
    if isinstance(decorator, ast.Name) and decorator.id == "must_use":
        return "Return value must be used"

    return None


@pre(lambda source, must_use_funcs: isinstance(source, str) and len(source) > 0 and isinstance(must_use_funcs, set))
def find_ignored_calls(source: str, must_use_funcs: set[str]) -> list[tuple[str, int]]:
    """
    Find calls to must_use functions whose return values are ignored.

    Returns list of (function_name, line_number) tuples.

    >>> code = '''
    ... validate(data)
    ... result = check(x)
    ... '''
    >>> find_ignored_calls(code, {"validate", "check"})
    [('validate', 2)]

    >>> code = '''
    ... if validate(x):
    ...     pass
    ... '''
    >>> find_ignored_calls(code, {"validate"})
    []
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return []

    ignored: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        # Look for expression statements (standalone calls)
        if not isinstance(node, ast.Expr):
            continue

        call = node.value
        if not isinstance(call, ast.Call):
            continue

        func_name = _get_call_name(call)
        if func_name and func_name in must_use_funcs:
            ignored.append((func_name, node.lineno))

    return ignored


@pre(lambda call: isinstance(call, ast.Call) and hasattr(call, 'func'))
@post(lambda result: result is None or isinstance(result, str))
def _get_call_name(call: ast.Call) -> str | None:
    """Extract function name from a Call node."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


@post(lambda result: all(v.rule == "must_use_ignored" for v in result))  # Rule consistency
def check_must_use(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for ignored return values of @must_use functions.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> code = '''
        ... from invar import must_use
        ... @must_use("Error must be handled")
        ... def validate(x): return x
        ... validate(1)
        ... '''
        >>> info = FileInfo(path="test.py", lines=5, symbols=[], is_core=True, source=code)
        >>> len(check_must_use(info, RuleConfig()))
        1
    """
    violations: list[Violation] = []
    source = file_info.source
    if not source:
        return violations

    must_use_funcs = find_must_use_functions(source)
    if not must_use_funcs:
        return violations

    for func_name, line in find_ignored_calls(source, set(must_use_funcs.keys())):
        reason = must_use_funcs.get(func_name, "Return value must be used")
        violations.append(Violation(
            rule="must_use_ignored", severity=Severity.WARNING, file=file_info.path,
            line=line, message=f"Return value of '{func_name}()' ignored",
            suggestion=f"Hint: {reason}",
        ))
    return violations
