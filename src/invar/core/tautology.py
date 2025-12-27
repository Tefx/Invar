"""Semantic tautology detection for contract quality (P7). No I/O operations."""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.lambda_helpers import find_lambda
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.suggestions import format_suggestion_for_violation


@pre(lambda expression: ("lambda" in expression and ":" in expression) or not expression.strip())
def is_semantic_tautology(expression: str) -> tuple[bool, str]:
    """Check if a contract expression is a semantic tautology.

    Returns (is_tautology, pattern_description).

    P7: Detects patterns that are always true:
    - x == x (identity comparison)
    - len(x) >= 0 (length always non-negative)
    - isinstance(x, object) (everything is object)
    - x or True (always true due to True)
    - True and x (simplifies but starts with True)

    DX-38 Tier 1: Also detects obvious violations:
    - lambda x: True (no constraint)
    - lambda x: False (contradiction)
    - lambda: ... (no parameters - doesn't validate function inputs)

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
        >>> is_semantic_tautology("lambda x: True")
        (True, 'contract always returns True (no constraint)')
        >>> is_semantic_tautology("lambda x: False")
        (True, 'contract always returns False (contradiction - will always fail)')
        >>> is_semantic_tautology("lambda: len([1,2]) > 0")
        (True, "contract has no parameters (doesn't validate function inputs)")
        >>> is_semantic_tautology("lambda result: result or not result")
        (True, "'result or not result' is always True (tautology)")
        >>> is_semantic_tautology("lambda x: x and not x")
        (True, "'x and not x' is always False (contradiction)")
    """
    if not expression.strip():
        return (False, "")
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = find_lambda(tree)
        if lambda_node is None:
            return (False, "")

        # DX-38 Tier 1: Check for no-parameter lambda
        args = lambda_node.args
        if not args.args and not args.posonlyargs and not args.kwonlyargs and not args.vararg and not args.kwarg:
            return (True, "contract has no parameters (doesn't validate function inputs)")

        return _check_tautology_patterns(lambda_node.body)
    except (SyntaxError, TypeError, ValueError):
        return (False, "")


@pre(lambda node: isinstance(node, ast.expr))
def _check_literal_patterns(node: ast.expr) -> tuple[bool, str] | None:
    """Check for literal True/False patterns."""
    if isinstance(node, ast.Constant) and node.value is True:
        return (True, "contract always returns True (no constraint)")
    if isinstance(node, ast.Constant) and node.value is False:
        return (True, "contract always returns False (contradiction - will always fail)")
    return None


@pre(lambda node: isinstance(node, ast.expr))
def _check_comparison_patterns(node: ast.expr) -> tuple[bool, str] | None:
    """Check for identity and len >= 0 patterns."""
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return None
    # Identity comparison pattern
    if isinstance(node.ops[0], (ast.Eq, ast.Is)):
        left, right = ast.unparse(node.left), ast.unparse(node.comparators[0])
        if left == right:
            return (True, f"{left} == {right} is always True")
    # Length non-negative pattern
    if len(node.comparators) == 1:
        left, op, right = node.left, node.ops[0], node.comparators[0]
        if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and
            left.func.id == "len" and isinstance(op, ast.GtE) and
            isinstance(right, ast.Constant) and right.value == 0):
            arg = ast.unparse(left.args[0]) if left.args else "x"
            return (True, f"len({arg}) >= 0 is always True for any sequence")
    return None


@pre(lambda node: isinstance(node, ast.expr))
def _check_isinstance_object(node: ast.expr) -> tuple[bool, str] | None:
    """Check for isinstance(x, object) pattern."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
        node.func.id == "isinstance" and len(node.args) == 2):
        type_arg = node.args[1]
        if isinstance(type_arg, ast.Name) and type_arg.id == "object":
            return (True, f"isinstance({ast.unparse(node.args[0])}, object) is always True")
    return None


@pre(lambda node: isinstance(node, ast.expr))
def _check_boolop_patterns(node: ast.expr) -> tuple[bool, str] | None:
    """Check for boolean operation patterns: x or True, x or not x, x and not x."""
    if not isinstance(node, ast.BoolOp):
        return None
    if isinstance(node.op, ast.Or):
        # x or True
        for val in node.values:
            if isinstance(val, ast.Constant) and val.value is True:
                return (True, "expression contains unconditional True")
        # Complement tautology pattern
        values_unparsed = {ast.unparse(v): v for v in node.values}
        for val in node.values:
            if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.Not):
                negated = ast.unparse(val.operand)
                if negated in values_unparsed:
                    return (True, f"'{negated} or not {negated}' is always True (tautology)")
    if isinstance(node.op, ast.And):
        # Complement contradiction pattern
        values_unparsed = {ast.unparse(v): v for v in node.values}
        for val in node.values:
            if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.Not):
                negated = ast.unparse(val.operand)
                if negated in values_unparsed:
                    return (True, f"'{negated} and not {negated}' is always False (contradiction)")
    return None


@pre(lambda node: isinstance(node, ast.expr) and hasattr(node, '__class__'))
@post(lambda result: isinstance(result, tuple) and len(result) == 2)
def _check_tautology_patterns(node: ast.expr) -> tuple[bool, str]:
    """Check for common tautology patterns in AST node.

    DX-38 Tier 1: Detects obvious violations:
    - Literal True (always passes, no constraint)
    - Literal False (always fails, contradiction)
    - x == x, len(x) >= 0, isinstance(x, object), x or True
    - x or not x (tautology), x and not x (contradiction)

    Examples:
        >>> import ast
        >>> _check_tautology_patterns(ast.Constant(value=True))
        (True, 'contract always returns True (no constraint)')
        >>> _check_tautology_patterns(ast.Constant(value=False))
        (True, 'contract always returns False (contradiction - will always fail)')
    """
    for checker in [_check_literal_patterns, _check_comparison_patterns,
                    _check_isinstance_object, _check_boolop_patterns]:
        result = checker(node)
        if result:
            return result
    return (False, "")


@pre(lambda file_info, config: len(file_info.path) > 0)
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
                violations.append(
                    Violation(
                        rule="semantic_tautology",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' has tautological contract: {pattern_desc}",
                        suggestion=format_suggestion_for_violation(symbol, "semantic_tautology"),
                    )
                )
    return violations
