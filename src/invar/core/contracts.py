"""
Contract quality detection for Guard (Phase 7).

Detects Agent-specific failure modes:
- Empty contracts (@pre(lambda: True))
- Redundant type contracts (isinstance when types are annotated)

No I/O operations - receives parsed data only.
"""

from __future__ import annotations

import ast
import re

from deal import pre

from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.suggestions import format_suggestion_for_violation


@pre(lambda expression: "lambda" in expression or not expression.strip())
def is_empty_contract(expression: str) -> bool:
    """
    Check if a contract expression is always True (tautological).

    Examples:
        >>> is_empty_contract("lambda: True")
        True
        >>> is_empty_contract("lambda x: True")
        True
        >>> is_empty_contract("lambda x, y: True")
        True
        >>> is_empty_contract("lambda x: x > 0")
        False
        >>> is_empty_contract("lambda x: isinstance(x, int)")
        False
        >>> is_empty_contract("")
        False
    """
    if not expression.strip():
        return False
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return False

    lambda_node = _find_lambda(tree)
    if lambda_node is None:
        return False
    return isinstance(lambda_node.body, ast.Constant) and lambda_node.body.value is True


@pre(lambda tree: hasattr(tree, "body"))
def _find_lambda(tree: ast.Expression) -> ast.Lambda | None:
    """Find the lambda node in an expression tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Lambda):
            return node
    return None


@pre(lambda expression, annotations: "lambda" in expression or not expression.strip())
def is_redundant_type_contract(expression: str, annotations: dict[str, str]) -> bool:
    """
    Check if a contract only checks types that are already in annotations.

    Examples:
        >>> is_redundant_type_contract("lambda x: isinstance(x, int)", {"x": "int"})
        True
        >>> is_redundant_type_contract("lambda x: isinstance(x, int)", {"x": "str"})
        False
        >>> is_redundant_type_contract("lambda x: isinstance(x, int)", {})
        False
        >>> is_redundant_type_contract("lambda x: isinstance(x, int) and x > 0", {"x": "int"})
        False
        >>> is_redundant_type_contract("lambda x: x > 0", {"x": "int"})
        False
    """
    if not expression.strip() or not annotations:
        return False
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return False

    lambda_node = _find_lambda(tree)
    if lambda_node is None:
        return False

    isinstance_checks = _extract_isinstance_checks(lambda_node.body)
    if isinstance_checks is None:
        return False

    for param, type_name in isinstance_checks:
        if param not in annotations or not _types_match(annotations[param], type_name):
            return False
    return True


@pre(lambda node: hasattr(node, "__class__"))
def _extract_isinstance_checks(node: ast.expr) -> list[tuple[str, str]] | None:
    """Extract isinstance checks. Returns None if other logic present."""
    if isinstance(node, ast.Call):
        check = _parse_isinstance_call(node)
        return [check] if check else None

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        checks = []
        for value in node.values:
            if not isinstance(value, ast.Call):
                return None
            check = _parse_isinstance_call(value)
            if not check:
                return None
            checks.append(check)
        return checks if checks else None
    return None


@pre(lambda node: hasattr(node, "func") and hasattr(node, "args"))
def _parse_isinstance_call(node: ast.Call) -> tuple[str, str] | None:
    """Parse isinstance(x, Type) call. Returns (param, type) or None."""
    if not (isinstance(node.func, ast.Name) and node.func.id == "isinstance"):
        return None
    if len(node.args) != 2 or not isinstance(node.args[0], ast.Name):
        return None

    param = node.args[0].id
    type_arg = node.args[1]
    if isinstance(type_arg, ast.Name):
        return (param, type_arg.id)
    elif isinstance(type_arg, ast.Attribute):
        return (param, type_arg.attr)
    return None


@pre(lambda annotation, type_name: len(annotation) > 0 and len(type_name) > 0)
def _types_match(annotation: str, type_name: str) -> bool:
    """
    Check if a type annotation matches an isinstance type check.

    Examples:
        >>> _types_match("int", "int")
        True
        >>> _types_match("list[int]", "list")
        True
        >>> _types_match("Optional[str]", "str")
        False
    """
    if annotation == type_name:
        return True
    base_match = re.match(r"^(\w+)\[", annotation)
    return bool(base_match and base_match.group(1) == type_name)


@pre(lambda signature: signature.startswith("("))
def _extract_annotations(signature: str) -> dict[str, str]:
    """
    Extract parameter type annotations from a function signature.

    Examples:
        >>> _extract_annotations("(x: int, y: str) -> bool")
        {'x': 'int', 'y': 'str'}
        >>> _extract_annotations("(x, y)")
        {}
        >>> _extract_annotations("(items: list[int]) -> int")
        {'items': 'list[int]'}
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


# Rule checking functions


@pre(lambda file_info, config: file_info.is_core or True)  # Accept all, filter inside
def check_empty_contracts(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for empty/tautological contracts. Applies to Core files only.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> contract = Contract(kind="pre", expression="lambda x: True", line=1)
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     contracts=[contract])
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_empty_contracts(info, RuleConfig())
        >>> len(violations)
        1
        >>> violations[0].rule
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
                suggestion = format_suggestion_for_violation(symbol, "empty_contract")
                violations.append(Violation(
                    rule="empty_contract", severity=Severity.WARNING,
                    file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' has empty contract: @{contract.kind}({contract.expression})",
                    suggestion=suggestion,
                ))
    return violations


@pre(lambda file_info, config: file_info.is_core or True)  # Accept all, filter inside
def check_redundant_type_contracts(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for contracts that only check types already in annotations.
    Applies to Core files only. Uses INFO severity.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> contract = Contract(kind="pre", expression="lambda x: isinstance(x, int)", line=1)
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(x: int) -> int", contracts=[contract])
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> violations = check_redundant_type_contracts(info, RuleConfig())
        >>> len(violations)
        1
        >>> violations[0].severity.value
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
                suggestion = format_suggestion_for_violation(symbol, "redundant_type_contract")
                violations.append(Violation(
                    rule="redundant_type_contract", severity=Severity.INFO,
                    file=file_info.path, line=contract.line,
                    message=f"{kind} '{symbol.name}' contract only checks types already in annotations",
                    suggestion=suggestion,
                ))
    return violations
