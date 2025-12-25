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
        lambda_node = find_lambda(tree)
        if lambda_node is None:
            return (False, "")
        return _check_tautology_patterns(lambda_node.body)
    except (SyntaxError, TypeError, ValueError):
        return (False, "")


@pre(lambda node: isinstance(node, ast.expr))
@post(lambda result: isinstance(result, tuple) and len(result) == 2)
def _check_tautology_patterns(node: ast.expr) -> tuple[bool, str]:
    """Check for common tautology patterns in AST node."""
    # Identity comparison pattern (e.g., x == x)
    if (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], (ast.Eq, ast.Is))
    ):
        left = ast.unparse(node.left)
        right = ast.unparse(node.comparators[0])
        if left == right:
            return (True, f"{left} == {right} is always True")

    # Length non-negative pattern (e.g., len(x) >= 0)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        left = node.left
        op = node.ops[0]
        right = node.comparators[0]
        if (
            isinstance(left, ast.Call)
            and isinstance(left.func, ast.Name)
            and left.func.id == "len"
            and isinstance(op, ast.GtE)
            and isinstance(right, ast.Constant)
            and right.value == 0
        ):
            arg = ast.unparse(left.args[0]) if left.args else "x"
            return (True, f"len({arg}) >= 0 is always True for any sequence")

    # isinstance with object pattern (always True)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "isinstance"
        and len(node.args) == 2
    ):
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
