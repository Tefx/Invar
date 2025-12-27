"""Postcondition scope validation for Guard. No I/O operations."""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.lambda_helpers import (
    extract_func_param_names,
    extract_used_names,
    find_lambda,
)
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation


@pre(lambda node: isinstance(node, ast.expr))
@post(lambda result: isinstance(result, set))
def _extract_comprehension_bound_names(node: ast.expr) -> set[str]:
    """Extract names bound by comprehensions (generator expressions, list comps, etc.).

    Examples:
        >>> import ast
        >>> expr = ast.parse("all(v.rule for v in result)", mode="eval").body
        >>> sorted(_extract_comprehension_bound_names(expr))
        ['v']
    """
    bound: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.comprehension):
            # Extract bound variable(s) from the target
            for name in ast.walk(child.target):
                if isinstance(name, ast.Name):
                    bound.add(name.id)
    return bound


@post(lambda result: isinstance(result, set))
def _extract_used_names_from_expression(expression: str) -> set[str]:
    """Extract free variable names from a lambda expression string.

    Excludes comprehension-bound variables like 'v' in 'all(v.x for v in result)'.

    Examples:
        >>> sorted(_extract_used_names_from_expression("lambda result: len(result) > 0"))
        ['len', 'result']
        >>> _extract_used_names_from_expression("lambda x: x > 0")
        {'x'}
        >>> _extract_used_names_from_expression("not a lambda")
        set()
        >>> sorted(_extract_used_names_from_expression("lambda result: all(v.rule for v in result)"))
        ['all', 'result']
    """
    if not expression.strip() or "lambda" not in expression:
        return set()
    try:
        tree = ast.parse(expression, mode="eval")
        lambda_node = find_lambda(tree)
        if lambda_node is None:
            return set()
        # Extract all names from lambda body
        all_names = extract_used_names(lambda_node.body)
        # Subtract comprehension-bound names
        bound_names = _extract_comprehension_bound_names(lambda_node.body)
        return all_names - bound_names
    except (SyntaxError, TypeError, ValueError):
        return set()


@post(lambda result: all(v.rule == "postcondition_scope_error" for v in result))
def check_postcondition_scope(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Check @post lambdas for references to function parameters.

    @post lambdas cannot access function parameters (except via 'result').
    They can access module-level imports and builtins via closure.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract, RuleConfig
        >>> c = Contract(kind="post", expression="lambda result: result > x", line=5)
        >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=10,
        ...     signature="(x: int) -> int", contracts=[c])
        >>> info = FileInfo(path="test.py", lines=10, symbols=[s], is_core=True)
        >>> vs = check_postcondition_scope(info, RuleConfig())
        >>> len(vs) == 1 and "x" in vs[0].message
        True
        >>> # Module imports are allowed
        >>> c2 = Contract(kind="post", expression="lambda result: isinstance(result, Violation)", line=5)
        >>> s2 = Symbol(name="g", kind=SymbolKind.FUNCTION, line=1, end_line=10,
        ...     signature="(data: str) -> Violation", contracts=[c2])
        >>> info2 = FileInfo(path="test.py", lines=10, symbols=[s2], is_core=True)
        >>> check_postcondition_scope(info2, RuleConfig())
        []
    """
    violations: list[Violation] = []
    if not file_info.is_core:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue

        # Extract function parameter names from signature
        param_names = extract_func_param_names(symbol.signature) or []
        # Exclude 'self', 'cls', and 'result' (valid in @post)
        invalid_params = set(param_names) - {"self", "cls", "result"}

        for contract in symbol.contracts:
            if contract.kind != "post":
                continue

            used_names = _extract_used_names_from_expression(contract.expression)
            # Check if any function parameters are used (they shouldn't be)
            param_references = used_names & invalid_params

            if param_references:
                kind = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                violations.append(
                    Violation(
                        rule="postcondition_scope_error",
                        severity=Severity.ERROR,
                        file=file_info.path,
                        line=contract.line,
                        message=f"{kind} '{symbol.name}' @post references function parameters: {', '.join(sorted(param_references))}",
                        suggestion="@post lambdas can only use 'result', not function parameters",
                    )
                )

    return violations
