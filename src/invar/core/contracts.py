"""Contract quality detection for Guard (Phase 7, 8). No I/O operations."""

from __future__ import annotations

import ast
import re

from deal import pre

from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.suggestions import format_suggestion_for_violation


@pre(lambda expression: "lambda" in expression or not expression.strip())
def is_empty_contract(expression: str) -> bool:
    """Check if a contract expression is always True (tautological).

    Examples:
        >>> is_empty_contract("lambda: True"), is_empty_contract("lambda x: True")
        (True, True)
        >>> is_empty_contract("lambda x: x > 0"), is_empty_contract("")
        (False, False)
    """
    if not expression.strip():
        return False
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = _find_lambda(tree)
        return lambda_node is not None and isinstance(lambda_node.body, ast.Constant) and lambda_node.body.value is True
    except SyntaxError:
        return False


# P7: Semantic tautology detection


@pre(lambda expression: "lambda" in expression or not expression.strip())
def is_semantic_tautology(expression: str) -> tuple[bool, str]:
    """Check if a contract expression is a semantic tautology.

    Returns (is_tautology, pattern_description).

    P7: Detects patterns that are always true:
    - x == x (identity comparison)
    - len(x) >= 0 (length always non-negative)
    - isinstance(x, object) (everything is object)
    - x or True (always true due to True)
    - True and x (simplifies but starts with True)

    Examples:
        >>> is_semantic_tautology("lambda x: x == x")
        (True, 'x == x is always True')
        >>> is_semantic_tautology("lambda x: len(x) >= 0")
        (True, 'len(x) >= 0 is always True for any sequence')
        >>> is_semantic_tautology("lambda x: isinstance(x, object)")
        (True, 'isinstance(x, object) is always True')
        >>> is_semantic_tautology("lambda x: x > 0")
        (False, '')
        >>> is_semantic_tautology("lambda x: x or True")
        (True, 'expression contains unconditional True')
    """
    if not expression.strip():
        return (False, "")
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = _find_lambda(tree)
        if lambda_node is None:
            return (False, "")
        return _check_tautology_patterns(lambda_node.body)
    except SyntaxError:
        return (False, "")


def _check_tautology_patterns(node: ast.expr) -> tuple[bool, str]:
    """Check for common tautology patterns in AST node."""
    # Pattern: x == x (identity comparison)
    if isinstance(node, ast.Compare):
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.Is)):
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if left == right:
                return (True, f"{left} == {right} is always True")

    # Pattern: len(x) >= 0 or len(x) > -1 (length always non-negative)
    if isinstance(node, ast.Compare):
        if len(node.ops) == 1 and len(node.comparators) == 1:
            left = node.left
            op = node.ops[0]
            right = node.comparators[0]
            # len(x) >= 0
            if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                    and left.func.id == "len" and isinstance(op, ast.GtE)
                    and isinstance(right, ast.Constant) and right.value == 0):
                arg = ast.unparse(left.args[0]) if left.args else "x"
                return (True, f"len({arg}) >= 0 is always True for any sequence")

    # Pattern: isinstance(x, object)
    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name) and node.func.id == "isinstance"
                and len(node.args) == 2):
            type_arg = node.args[1]
            if isinstance(type_arg, ast.Name) and type_arg.id == "object":
                arg = ast.unparse(node.args[0])
                return (True, f"isinstance({arg}, object) is always True")

    # Pattern: x or True, True or x (always true)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        for val in node.values:
            if isinstance(val, ast.Constant) and val.value is True:
                return (True, "expression contains unconditional True")

    return (False, "")


def _find_lambda(tree: ast.Expression) -> ast.Lambda | None:
    """Find the lambda node in an expression tree."""
    return next((n for n in ast.walk(tree) if isinstance(n, ast.Lambda)), None)


@pre(lambda expression, annotations: "lambda" in expression or not expression.strip())
def is_redundant_type_contract(expression: str, annotations: dict[str, str]) -> bool:
    """Check if a contract only checks types already in annotations.

    Examples:
        >>> is_redundant_type_contract("lambda x: isinstance(x, int)", {"x": "int"})
        True
        >>> is_redundant_type_contract("lambda x: isinstance(x, int) and x > 0", {"x": "int"})
        False
    """
    if not expression.strip() or not annotations:
        return False
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = _find_lambda(tree)
        if lambda_node is None:
            return False
        checks = _extract_isinstance_checks(lambda_node.body)
        if checks is None:
            return False
        return all(p in annotations and _types_match(annotations[p], t) for p, t in checks)
    except SyntaxError:
        return False


def _extract_isinstance_checks(node: ast.expr) -> list[tuple[str, str]] | None:
    """Extract isinstance checks. Returns None if other logic present."""
    if isinstance(node, ast.Call):
        check = _parse_isinstance_call(node)
        return [check] if check else None
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        checks = [_parse_isinstance_call(v) for v in node.values if isinstance(v, ast.Call)]
        return checks if len(checks) == len(node.values) and all(checks) else None
    return None


def _parse_isinstance_call(node: ast.Call) -> tuple[str, str] | None:
    """Parse isinstance(x, Type) call. Returns (param, type) or None."""
    if not (isinstance(node.func, ast.Name) and node.func.id == "isinstance"):
        return None
    if len(node.args) != 2 or not isinstance(node.args[0], ast.Name):
        return None
    param, type_arg = node.args[0].id, node.args[1]
    if isinstance(type_arg, ast.Name):
        return (param, type_arg.id)
    if isinstance(type_arg, ast.Attribute):
        return (param, type_arg.attr)
    return None


def _types_match(annotation: str, type_name: str) -> bool:
    """Check if type annotation matches isinstance check.

    Examples:
        >>> _types_match("int", "int"), _types_match("list[int]", "list")
        (True, True)
    """
    if annotation == type_name:
        return True
    base_match = re.match(r"^(\w+)\[", annotation)
    return bool(base_match and base_match.group(1) == type_name)


@pre(lambda signature: signature.startswith("("))
def _extract_annotations(signature: str) -> dict[str, str]:
    """Extract parameter type annotations from signature.

    Examples:
        >>> _extract_annotations("(x: int, y: str) -> bool")
        {'x': 'int', 'y': 'str'}
    """
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


# Phase 8.3: Parameter mismatch detection


@pre(lambda expression, signature: "lambda" in expression or not expression.strip())
def has_param_mismatch(expression: str, signature: str) -> tuple[bool, str]:
    """
    Check if lambda params don't match function params.

    Returns (has_mismatch, error_description).

    Examples:
        >>> has_param_mismatch("lambda x: x > 0", "(x: int, y: int) -> int")
        (True, 'lambda has 1 param(s) but function has 2')
        >>> has_param_mismatch("lambda x, y: x > 0", "(x: int, y: int) -> int")
        (False, '')
        >>> has_param_mismatch("lambda x, y=0: x > 0", "(x: int, y: int = 0) -> int")
        (False, '')
        >>> has_param_mismatch("lambda: True", "() -> bool")
        (False, '')
    """
    if not expression.strip() or not signature:
        return (False, "")

    lambda_params = _extract_lambda_params(expression)
    func_params = _extract_func_param_names(signature)

    if lambda_params is None or func_params is None:
        return (False, "")  # Can't determine, skip

    if len(lambda_params) != len(func_params):
        return (True, f"lambda has {len(lambda_params)} param(s) but function has {len(func_params)}")

    return (False, "")


@pre(lambda expression: "lambda" in expression or not expression.strip())
def _extract_lambda_params(expression: str) -> list[str] | None:
    """Extract parameter names from a lambda expression."""
    if not expression.strip():
        return None
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = _find_lambda(tree)
        return [arg.arg for arg in lambda_node.args.args] if lambda_node else None
    except SyntaxError:
        return None


@pre(lambda signature: signature.startswith("(") or signature == "")
def _extract_func_param_names(signature: str) -> list[str] | None:
    """Extract parameter names from a function signature (handles nested brackets)."""
    if not signature:
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


# Rule checking functions


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_empty_contracts(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check for empty/tautological contracts. Core files only.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x: True", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[c])
        >>> check_empty_contracts(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())[0].rule
        'empty_contract'
    """
    violations: list[Violation] = []
    if not file_info.is_core:
        return violations
    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue
        for contract in symbol.contracts:
            if is_empty_contract(contract.expression):
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(Violation(
                    rule="empty_contract", severity=Severity.WARNING, file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' has empty contract: @{contract.kind}({contract.expression})",
                    suggestion=format_suggestion_for_violation(symbol, "empty_contract"),
                ))
    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_semantic_tautology(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check for semantic tautology contracts. Core files only.

    P7: Detects contracts that are always true due to semantic patterns:
    - x == x, len(x) >= 0, isinstance(x, object), x or True

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x: x == x", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[c])
        >>> vs = check_semantic_tautology(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())
        >>> vs[0].rule
        'semantic_tautology'
    """
    violations: list[Violation] = []
    if not file_info.is_core:
        return violations
    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue
        for contract in symbol.contracts:
            is_tautology, pattern_desc = is_semantic_tautology(contract.expression)
            if is_tautology:
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(Violation(
                    rule="semantic_tautology", severity=Severity.WARNING, file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' has tautological contract: {pattern_desc}",
                    suggestion=format_suggestion_for_violation(symbol, "semantic_tautology"),
                ))
    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_redundant_type_contracts(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check for contracts that only check types in annotations. Core files only. INFO severity.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x: isinstance(x, int)", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, signature="(x: int) -> int", contracts=[c])
        >>> check_redundant_type_contracts(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())[0].severity.value
        'info'
    """
    violations: list[Violation] = []
    if not file_info.is_core:
        return violations
    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue
        annotations = _extract_annotations(symbol.signature)
        if not annotations:
            continue
        for contract in symbol.contracts:
            if is_redundant_type_contract(contract.expression, annotations):
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(Violation(
                    rule="redundant_type_contract", severity=Severity.INFO, file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' contract only checks types already in annotations",
                    suggestion=format_suggestion_for_violation(symbol, "redundant_type_contract"),
                ))
    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_param_mismatch(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check @pre lambda params match function params. Core files only. ERROR severity.

    Only checks @pre contracts (@post takes 'result' param, different signature).

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x: x > 0", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, signature="(x: int, y: int) -> int", contracts=[c])
        >>> check_param_mismatch(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())[0].rule
        'param_mismatch'
    """
    violations: list[Violation] = []
    if not file_info.is_core:
        return violations
    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD) or not symbol.signature:
            continue
        for contract in symbol.contracts:
            # Only check @pre contracts (not @post which takes 'result')
            if contract.kind != "pre":
                continue
            mismatch, desc = has_param_mismatch(contract.expression, symbol.signature)
            if mismatch:
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(Violation(
                    rule="param_mismatch", severity=Severity.ERROR, file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' @pre {desc}",
                    suggestion="Lambda must include ALL function parameters",
                ))
    return violations
