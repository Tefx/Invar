"""Lambda expression parsing helpers for contract analysis. No I/O operations."""

from __future__ import annotations

import ast
import re

from deal import post, pre


@pre(lambda tree: isinstance(tree, ast.AST) and hasattr(tree, '__class__'))
@post(lambda result: result is None or isinstance(result, ast.Lambda))
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


@post(lambda result: isinstance(result, dict))
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


@post(lambda result: result is None or all(isinstance(p, str) for p in result))  # Valid params
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
    except (SyntaxError, TypeError, ValueError):
        return None


@post(lambda result: result is None or isinstance(result, list))
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


@pre(lambda node: isinstance(node, ast.expr) and hasattr(node, '__class__'))
@post(lambda result: isinstance(result, set))
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


# DX-01: Helper to generate lambda fix templates


@post(lambda result: isinstance(result, str))
def generate_lambda_fix(signature: str) -> str:
    """
    Generate a lambda fix template from function signature.

    DX-01: Provides copy-pastable fix for param_mismatch errors.

    Examples:
        >>> generate_lambda_fix("(x: int, y: str) -> bool")
        '@pre(lambda x, y: <condition>)'
        >>> generate_lambda_fix("(x: int, y: int = 10) -> int")
        '@pre(lambda x, y=10: <condition>)'
        >>> generate_lambda_fix("(items: list[int], n: int = 5, reverse: bool = False) -> list")
        '@pre(lambda items, n=5, reverse=False: <condition>)'
        >>> generate_lambda_fix("() -> bool")
        '@pre(lambda: <condition>)'
        >>> generate_lambda_fix("")
        '@pre(lambda: <condition>)'
    """
    if not signature or signature == "()" or not signature.startswith("("):
        return "@pre(lambda: <condition>)"

    match = re.match(r"\(([^)]*)\)", signature)
    if not match:
        return "@pre(lambda: <condition>)"

    param_parts: list[str] = []
    for param in match.group(1).split(","):
        param = param.strip()
        if not param:
            continue

        # Extract name and default value
        if ": " in param:
            name_part, type_part = param.split(": ", 1)
            name = name_part.strip()
            # Check for default value
            if "=" in type_part:
                default = type_part.split("=", 1)[1].strip()
                param_parts.append(f"{name}={default}")
            else:
                param_parts.append(name)
        elif "=" in param:
            name, default = param.split("=", 1)
            param_parts.append(f"{name.strip()}={default.strip()}")
        else:
            param_parts.append(param)

    if not param_parts:
        return "@pre(lambda: <condition>)"
    params_str = ", ".join(param_parts)
    return f"@pre(lambda {params_str}: <condition>)"
