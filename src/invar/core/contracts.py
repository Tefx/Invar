"""Contract quality detection for Guard (Phase 7, 8, 11). No I/O operations."""

from __future__ import annotations

import ast
import re

from deal import post, pre

from invar.core.lambda_helpers import (
    extract_annotations,
    extract_func_param_names,
    extract_lambda_params,
    extract_used_names,
    find_lambda,
    generate_lambda_fix,
)
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.suggestions import format_suggestion_for_violation

# Re-export for backward compatibility (extracted to tautology.py)
from invar.core.tautology import check_semantic_tautology as check_semantic_tautology
from invar.core.tautology import is_semantic_tautology as is_semantic_tautology


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
        lambda_node = find_lambda(tree)
        return (
            lambda_node is not None
            and isinstance(lambda_node.body, ast.Constant)
            and lambda_node.body.value is True
        )
    except SyntaxError:
        return False


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
        lambda_node = find_lambda(tree)
        if lambda_node is None:
            return False
        checks = _extract_isinstance_checks(lambda_node.body)
        if checks is None:
            return False
        return all(p in annotations and _types_match(annotations[p], t) for p, t in checks)
    except SyntaxError:
        return False


@post(lambda result: result is None or isinstance(result, list))
def _extract_isinstance_checks(node: ast.expr) -> list[tuple[str, str]] | None:
    """Extract isinstance checks. Returns None if other logic present."""
    if isinstance(node, ast.Call):
        check = _parse_isinstance_call(node)
        return [check] if check else None
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        checks = [_parse_isinstance_call(v) for v in node.values if isinstance(v, ast.Call)]
        return checks if len(checks) == len(node.values) and all(checks) else None
    return None


@post(lambda result: result is None or (isinstance(result, tuple) and len(result) == 2))
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


@post(lambda result: isinstance(result, bool))
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


# Phase 8.3: Parameter mismatch detection


@pre(lambda expression, signature: "lambda" in expression or not expression.strip())
def has_unused_params(expression: str, signature: str) -> tuple[bool, list[str], list[str]]:
    """
    Check if lambda has params it doesn't use (P28: Partial Contract Detection).

    Returns (has_unused, unused_params, used_params).

    Different from param_mismatch:
    - param_mismatch: lambda param COUNT != function param count (ERROR)
    - unused_params: lambda has all params but doesn't USE all (WARN)

    Examples:
        >>> has_unused_params("lambda x, y: x > 0", "(x: int, y: int) -> int")
        (True, ['y'], ['x'])
        >>> has_unused_params("lambda x, y: x > 0 and y < 10", "(x: int, y: int) -> int")
        (False, [], ['x', 'y'])
        >>> has_unused_params("lambda x: x > 0", "(x: int, y: int) -> int")
        (False, [], [])
        >>> has_unused_params("lambda items: len(items) > 0", "(items: list) -> int")
        (False, [], ['items'])
    """
    if not expression.strip() or not signature:
        return (False, [], [])

    lambda_params = extract_lambda_params(expression)
    func_params = extract_func_param_names(signature)

    if lambda_params is None or func_params is None:
        return (False, [], [])

    # Only check when lambda has same param count as function
    # (if different count, that's param_mismatch, not this check)
    if len(lambda_params) != len(func_params):
        return (False, [], [])

    # Extract used names from lambda body
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = find_lambda(tree)
        if lambda_node is None:
            return (False, [], [])
        used_names = extract_used_names(lambda_node.body)
    except SyntaxError:
        return (False, [], [])

    # Check which params are actually used
    used_params = [p for p in lambda_params if p in used_names]
    unused_params = [p for p in lambda_params if p not in used_names]

    return (len(unused_params) > 0, unused_params, used_params)


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

    lambda_params = extract_lambda_params(expression)
    func_params = extract_func_param_names(signature)

    if lambda_params is None or func_params is None:
        return (False, "")  # Can't determine, skip

    if len(lambda_params) != len(func_params):
        return (
            True,
            f"lambda has {len(lambda_params)} param(s) but function has {len(func_params)}",
        )

    return (False, "")


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
                violations.append(
                    Violation(
                        rule="empty_contract",
                        severity=Severity.ERROR,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' has empty contract: @{contract.kind}({contract.expression})",
                        suggestion=format_suggestion_for_violation(symbol, "empty_contract"),
                    )
                )
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
        annotations = extract_annotations(symbol.signature)
        if not annotations:
            continue
        for contract in symbol.contracts:
            if is_redundant_type_contract(contract.expression, annotations):
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(
                    Violation(
                        rule="redundant_type_contract",
                        severity=Severity.INFO,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' contract only checks types already in annotations",
                        suggestion=format_suggestion_for_violation(
                            symbol, "redundant_type_contract"
                        ),
                    )
                )
    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_param_mismatch(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check @pre lambda params match function params. Core files only. ERROR severity.

    Only checks @pre contracts (@post takes 'result' param, different signature).

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x: x > 0", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, signature="(x: int, y: int) -> int", contracts=[c])
        >>> v = check_param_mismatch(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())[0]
        >>> v.rule
        'param_mismatch'
        >>> v.suggestion  # DX-01: Now includes fix template
        'Fix: @pre(lambda x, y: <condition>)'
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
                # DX-01: Generate copy-pastable lambda fix template
                fix_template = generate_lambda_fix(symbol.signature)
                violations.append(
                    Violation(
                        rule="param_mismatch",
                        severity=Severity.ERROR,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' @pre {desc}",
                        suggestion=f"Fix: {fix_template}",
                    )
                )
    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_partial_contract(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check @pre contracts that don't use all declared params (P28). Core files only. WARN severity.

    P28: Detects hidden formal compliance - lambda declares all params but doesn't use all.
    Forces Agent to think about whether unchecked params need constraints.

    Different from param_mismatch (P8.3):
    - param_mismatch: lambda param COUNT != function param count (ERROR)
    - partial_contract: lambda has all params but doesn't USE all (WARN)

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="pre", expression="lambda x, y: x > 0", line=1)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, signature="(x: int, y: int) -> int", contracts=[c])
        >>> vs = check_partial_contract(FileInfo(path="c.py", lines=10, symbols=[s], is_core=True), RuleConfig())
        >>> vs[0].rule
        'partial_contract'
        >>> vs[0].severity
        <Severity.WARNING: 'warning'>
        >>> "y" in vs[0].message
        True
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
            has_unused, unused, used = has_unused_params(contract.expression, symbol.signature)
            if has_unused:
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                unused_str = ", ".join(f"'{p}'" for p in unused)
                used_str = ", ".join(f"'{p}'" for p in used) if used else "none"
                violations.append(
                    Violation(
                        rule="partial_contract",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' @pre checks {used_str} but not {unused_str}",
                        suggestion=f"Signature: {symbol.signature}\n→ Add constraint for {unused_str} or verify it needs none",
                    )
                )
    return violations
