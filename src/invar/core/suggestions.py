"""
Fix suggestion generation for Guard (Phase 7.3).

Generates concrete, usable fix code for violations.
Agents need exact code, not vague descriptions.

No I/O operations - receives parsed data only.
"""

from __future__ import annotations

import re

from deal import pre

from invar.core.models import Symbol, SymbolKind


@pre(lambda signature: signature.startswith("(") or signature == "")
def generate_contract_suggestion(signature: str) -> str:
    """
    Generate a suggested @pre contract based on function signature.

    Uses common patterns:
    - int/float: param >= 0
    - str/list/dict/set/tuple: len(param) > 0
    - Optional/None union: param is not None

    Examples:
        >>> generate_contract_suggestion("(x: int, y: int) -> int")
        '@pre(lambda x, y: x >= 0 and y >= 0)'
        >>> generate_contract_suggestion("(name: str) -> bool")
        '@pre(lambda name: len(name) > 0)'
        >>> generate_contract_suggestion("(items: list[int]) -> int")
        '@pre(lambda items: len(items) > 0)'
        >>> generate_contract_suggestion("(x, y)")
        ''
        >>> generate_contract_suggestion("(value: Optional[str]) -> str")
        '@pre(lambda value: value is not None)'
    """
    params = _extract_params(signature)
    if not params:
        return ""

    constraints = []
    param_names = []

    for name, type_hint in params:
        param_names.append(name)
        if not type_hint:
            continue

        constraint = _suggest_constraint(name, type_hint)
        if constraint:
            constraints.append(constraint)

    if not constraints:
        return ""

    params_str = ", ".join(param_names)
    constraints_str = " and ".join(constraints)
    return f"@pre(lambda {params_str}: {constraints_str})"


@pre(lambda signature: signature.startswith("(") or signature == "")
def _extract_params(signature: str) -> list[tuple[str, str | None]]:
    """
    Extract parameters and their types from a signature.

    Examples:
        >>> _extract_params("(x: int, y: str) -> bool")
        [('x', 'int'), ('y', 'str')]
        >>> _extract_params("(x, y)")
        [('x', None), ('y', None)]
        >>> _extract_params("(items: list[int], n: int = 10) -> list")
        [('items', 'list[int]'), ('n', 'int')]
    """
    if not signature:
        return []

    match = re.match(r"\(([^)]*)\)", signature)
    if not match:
        return []

    params = []
    for param in match.group(1).split(","):
        param = param.strip()
        if not param:
            continue

        if ": " in param:
            name, type_hint = param.split(": ", 1)
            # Handle default values
            if "=" in type_hint:
                type_hint = type_hint.split("=")[0].strip()
            params.append((name.strip(), type_hint.strip()))
        else:
            # No type annotation
            if "=" in param:
                param = param.split("=")[0].strip()
            params.append((param, None))

    return params


@pre(lambda name, type_hint: len(name) > 0 and len(type_hint) > 0)
def _suggest_constraint(name: str, type_hint: str) -> str | None:
    """
    Suggest a constraint for a parameter based on its type.

    Examples:
        >>> _suggest_constraint("x", "int")
        'x >= 0'
        >>> _suggest_constraint("name", "str")
        'len(name) > 0'
        >>> _suggest_constraint("items", "list[str]")
        'len(items) > 0'
        >>> _suggest_constraint("value", "Optional[int]")
        'value is not None'
        >>> _suggest_constraint("x", "SomeCustomType")
    """
    # Numeric types: suggest non-negative
    if type_hint in ("int", "float"):
        return f"{name} >= 0"

    # Collection types: suggest non-empty
    if type_hint in ("str", "list", "dict", "set", "tuple", "bytes"):
        return f"len({name}) > 0"

    # Generic collections: list[X], dict[K, V], etc.
    base_match = re.match(r"^(list|dict|set|tuple)\[", type_hint)
    if base_match:
        return f"len({name}) > 0"

    # Optional types: suggest not None
    if type_hint.startswith("Optional[") or " | None" in type_hint or "None |" in type_hint:
        return f"{name} is not None"

    return None


def _generate_lambda_skeleton(signature: str) -> str:
    """
    Generate a lambda skeleton from function signature (P4).

    Returns skeleton with parameters extracted, condition placeholder.

    Examples:
        >>> _generate_lambda_skeleton("(x: int, y: int) -> int")
        '@pre(lambda x, y: <condition>) or @post(lambda result: <condition>)'
        >>> _generate_lambda_skeleton("(items: list) -> None")
        '@pre(lambda items: <condition>) or @post(lambda result: <condition>)'
        >>> _generate_lambda_skeleton("() -> int")
        '@post(lambda result: <condition>)'
    """
    params = _extract_params(signature)
    param_names = [name for name, _ in params]

    if not param_names:
        return "@post(lambda result: <condition>)"

    params_str = ", ".join(param_names)
    return f"@pre(lambda {params_str}: <condition>) or @post(lambda result: <condition>)"


@pre(lambda symbol, violation_type: violation_type in ("missing_contract", "empty_contract", "redundant_type_contract", "semantic_tautology", ""))
def format_suggestion_for_violation(symbol: Symbol, violation_type: str) -> str:
    """
    Format a complete suggestion message for a violation.

    Phase 9.2 P4: Generate lambda skeletons when no type-based suggestion available.
    P7: Added semantic_tautology support.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(x: int, y: int) -> int")
        >>> msg = format_suggestion_for_violation(sym, "missing_contract")
        >>> "@pre(lambda x, y: x >= 0 and y >= 0)" in msg
        True
        >>> # P4: skeleton when no type-based suggestion
        >>> sym2 = Symbol(name="process", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(data, config)")
        >>> msg2 = format_suggestion_for_violation(sym2, "missing_contract")
        >>> "@pre(lambda data, config: <condition>)" in msg2
        True
    """
    if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
        return ""

    if violation_type == "missing_contract":
        suggestion = generate_contract_suggestion(symbol.signature)
        if suggestion:
            return f"Add: {suggestion}"
        # P4: Generate lambda skeleton when no type-based suggestion
        skeleton = _generate_lambda_skeleton(symbol.signature)
        return f"Add: {skeleton}"

    if violation_type == "empty_contract":
        suggestion = generate_contract_suggestion(symbol.signature)
        if suggestion:
            return f"Replace with: {suggestion}"
        skeleton = _generate_lambda_skeleton(symbol.signature)
        return f"Replace with: {skeleton}"

    if violation_type == "redundant_type_contract":
        suggestion = generate_contract_suggestion(symbol.signature)
        if suggestion:
            return f"Replace with business logic: {suggestion}"
        skeleton = _generate_lambda_skeleton(symbol.signature)
        return f"Replace with: {skeleton}"

    if violation_type == "semantic_tautology":
        # P7: Semantic tautology - suggest meaningful constraint
        suggestion = generate_contract_suggestion(symbol.signature)
        if suggestion:
            return f"Replace tautology with meaningful constraint: {suggestion}"
        skeleton = _generate_lambda_skeleton(symbol.signature)
        return f"Replace tautology with: {skeleton}"

    return ""
