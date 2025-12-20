"""Lambda expression parsing helpers for contract analysis. No I/O operations."""

from __future__ import annotations

import ast
import re


def find_lambda(tree: ast.Expression) -> ast.Lambda | None:
    """Find the lambda node in an expression tree.

    Examples:
        >>> tree = ast.parse("lambda x: x > 0", mode="eval")
        >>> find_lambda(tree) is not None
        True
        >>> tree = ast.parse("x + y", mode="eval")
        >>> find_lambda(tree) is None
        True
    """
    return next((n for n in ast.walk(tree) if isinstance(n, ast.Lambda)), None)


def extract_annotations(signature: str) -> dict[str, str]:
    """Extract parameter type annotations from signature.

    Examples:
        >>> extract_annotations("(x: int, y: str) -> bool")
        {'x': 'int', 'y': 'str'}
        >>> extract_annotations("(items: list[int]) -> None")
        {'items': 'list[int]'}
        >>> extract_annotations("(x, y)")
        {}
    """
    if not signature or not signature.startswith("("):
        return {}
    annotations = {}
    match = re.match(r"\(([^)]*)\)", signature)
    if not match:
        return annotations
    for param in match.group(1).split(","):
        param = param.strip()
        if ": " in param:
            name, type_hint = param.split(": ", 1)
            if "=" in type_hint:
                type_hint = type_hint.split("=")[0].strip()
            annotations[name.strip()] = type_hint.strip()
    return annotations


def extract_lambda_params(expression: str) -> list[str] | None:
    """Extract parameter names from a lambda expression.

    Examples:
        >>> extract_lambda_params("lambda x, y: x > 0")
        ['x', 'y']
        >>> extract_lambda_params("lambda: True")
        []
        >>> extract_lambda_params("not a lambda") is None
        True
    """
    if not expression.strip() or "lambda" not in expression:
        return None
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = find_lambda(tree)
        return [arg.arg for arg in lambda_node.args.args] if lambda_node else None
    except SyntaxError:
        return None


def extract_func_param_names(signature: str) -> list[str] | None:
    """Extract parameter names from a function signature (handles nested brackets).

    Examples:
        >>> extract_func_param_names("(x: int, y: int) -> int")
        ['x', 'y']
        >>> extract_func_param_names("(items: dict[str, int]) -> None")
        ['items']
        >>> extract_func_param_names("() -> bool")
        []
    """
    if not signature or not signature.startswith("("):
        return None
    match = re.match(r"\(([^)]*)\)", signature)
    if not match:
        return None
    content = match.group(1).strip()
    if not content:
        return []
    # Split by comma, but respect brackets (for dict[K, V], tuple[A, B], etc.)
    params = []
    current = ""
    depth = 0
    for char in content:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            if current.strip():
                params.append(current.strip().split(":")[0].split("=")[0].strip())
            current = ""
            continue
        current += char
    if current.strip():
        params.append(current.strip().split(":")[0].split("=")[0].strip())
    return params


def extract_used_names(node: ast.expr) -> set[str]:
    """Extract all variable names used in an expression (Load context).

    Examples:
        >>> tree = ast.parse("x + y", mode="eval")
        >>> sorted(extract_used_names(tree.body))
        ['x', 'y']
        >>> tree = ast.parse("len(items) > 0", mode="eval")
        >>> sorted(extract_used_names(tree.body))
        ['items', 'len']
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            names.add(child.id)
    return names
