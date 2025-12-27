"""
Fix suggestion generation for Guard (Phase 7.3, 11 P27).

Generates concrete, usable fix code for violations.
Agents need exact code, not vague descriptions.

P27: Enhanced Context for Agent Decision
- Show multiple pattern options for constraints
- Guard provides options, Agent decides

No I/O operations - receives parsed data only.
"""

from __future__ import annotations

import re

from deal import post, pre

from invar.core.models import Symbol, SymbolKind

# P27: Common constraint patterns by type (ordered by commonality)
CONSTRAINT_PATTERNS: dict[str, list[str]] = {
    "int": ["{name} >= 0", "{name} > 0", "{name} != 0"],
    "float": ["{name} >= 0", "{name} > 0", "{name} != 0"],
    "str": ["len({name}) > 0", "{name}", "{name}.strip()"],
    "list": ["len({name}) > 0", "{name}"],
    "dict": ["len({name}) > 0", "{name}"],
    "set": ["len({name}) > 0", "{name}"],
    "tuple": ["len({name}) > 0", "{name}"],
    "bytes": ["len({name}) > 0", "{name}"],
    "Optional": ["{name} is not None", "{name}"],
}

# Return-type-aware @post patterns for redundant_type_contract suggestions
RETURN_TYPE_POST_PATTERNS: dict[str, str] = {
    "list[Violation]": '@post(lambda result: all(v.rule == "RULE_NAME" for v in result))',
    "list": '@post(lambda result: all(<predicate> for item in result))',
    "dict": "@post(lambda result: all(isinstance(k, <type>) for k in result))",
    "set": "@post(lambda result: all(<predicate> for item in result))",
    "int": "@post(lambda result: result >= 0)",
    "float": "@post(lambda result: result >= 0.0)",
    "str": "@post(lambda result: len(result) > 0)",
    "bool": "@post(lambda result: <semantic_predicate>)",
    "None": "",  # No meaningful @post for None return
}


@post(lambda result: result is None or isinstance(result, str))
def extract_return_type(signature: str) -> str | None:
    """Extract return type from function signature.

    Examples:
        >>> extract_return_type("(x: int) -> list[Violation]")
        'list[Violation]'
        >>> extract_return_type("(x: int) -> int")
        'int'
        >>> extract_return_type("(x: int) -> None")
        'None'
        >>> extract_return_type("(x: int)")
        >>> extract_return_type("()")
    """
    if not signature or "->" not in signature:
        return None
    match = re.search(r"->\s*(.+)$", signature)
    if match:
        return match.group(1).strip()
    return None


@pre(lambda return_type: return_type is None or isinstance(return_type, str))
@post(lambda result: isinstance(result, str))
def generate_post_suggestion(return_type: str | None) -> str:
    """Generate @post suggestion based on return type.

    Examples:
        >>> generate_post_suggestion("list[Violation]")
        '@post(lambda result: all(v.rule == "RULE_NAME" for v in result))'
        >>> generate_post_suggestion("int")
        '@post(lambda result: result >= 0)'
        >>> generate_post_suggestion("bool")
        '@post(lambda result: <semantic_predicate>)'
        >>> generate_post_suggestion("CustomType")
        '@post(lambda result: <condition>)'
        >>> generate_post_suggestion(None)
        '@post(lambda result: <condition>)'
    """
    if not return_type:
        return "@post(lambda result: <condition>)"

    # Exact match
    if return_type in RETURN_TYPE_POST_PATTERNS:
        pattern = RETURN_TYPE_POST_PATTERNS[return_type]
        return pattern if pattern else "@post(lambda result: <condition>)"

    # Generic match (list[X], dict[K,V], etc.)
    base_match = re.match(r"^(list|dict|set)\[", return_type)
    if base_match:
        base = base_match.group(1)
        if base in RETURN_TYPE_POST_PATTERNS:
            return RETURN_TYPE_POST_PATTERNS[base]

    return "@post(lambda result: <condition>)"


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
        if not name:  # Skip empty names from malformed signatures
            continue
        if name in ("self", "cls"):  # Skip method receiver parameters
            continue
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

    MINOR-2 Limitation: Uses naive comma splitting which breaks for complex types
    like Callable[[int, str], bool] where commas appear inside nested brackets.
    This is acceptable since suggestions are advisory, not strict validation.

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


@pre(lambda name, type_hint: len(name) > 0 and len(type_hint) > 0)
def _get_pattern_alternatives(name: str, type_hint: str) -> list[str]:
    """
    Get multiple constraint pattern alternatives for a parameter (P27).

    Returns up to 3 common patterns for the type.

    Examples:
        >>> _get_pattern_alternatives("x", "int")
        ['x >= 0', 'x > 0', 'x != 0']
        >>> _get_pattern_alternatives("name", "str")
        ['len(name) > 0', 'name', 'name.strip()']
        >>> _get_pattern_alternatives("value", "Optional[int]")
        ['value is not None', 'value']
        >>> _get_pattern_alternatives("x", "CustomType")
        []
    """
    # Check exact type matches
    if type_hint in CONSTRAINT_PATTERNS:
        return [p.format(name=name) for p in CONSTRAINT_PATTERNS[type_hint]]

    # Generic collections: list[X], dict[K, V], etc.
    base_match = re.match(r"^(list|dict|set|tuple)\[", type_hint)
    if base_match:
        base_type = base_match.group(1)
        if base_type in CONSTRAINT_PATTERNS:
            return [p.format(name=name) for p in CONSTRAINT_PATTERNS[base_type]]

    # Optional types
    if type_hint.startswith("Optional[") or " | None" in type_hint or "None |" in type_hint:
        return [p.format(name=name) for p in CONSTRAINT_PATTERNS["Optional"]]

    return []


@pre(lambda signature: signature.startswith("(") or signature == "")
def generate_pattern_options(signature: str) -> str:
    """
    Generate multiple constraint pattern options for each parameter (P27).

    Returns a formatted string showing alternatives for each typed parameter.

    Examples:
        >>> generate_pattern_options("(x: int, y: str) -> int")
        'Patterns: x >= 0 | x > 0 | x != 0, len(y) > 0 | y | y.strip()'
        >>> generate_pattern_options("(data, config)")
        ''
    """
    params = _extract_params(signature)
    if not params:
        return ""

    all_patterns: list[str] = []
    for name, type_hint in params:
        if not name or not type_hint:  # Skip empty names from malformed signatures
            continue
        patterns = _get_pattern_alternatives(name, type_hint)
        if patterns:
            all_patterns.append(" | ".join(patterns))

    if not all_patterns:
        return ""

    return f"Patterns: {', '.join(all_patterns)}"


@pre(lambda signature: signature.startswith("(") or signature == "")
@post(lambda result: isinstance(result, str))
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


# Prefixes for violation type suggestions
_VIOLATION_PREFIXES = {
    "missing_contract": ("Add: ", "Add: "),
    "empty_contract": ("Replace with: ", "Replace with: "),
    "redundant_type_contract": ("Replace with business logic: ", "Replace with: "),
    "semantic_tautology": ("Replace tautology with meaningful constraint: ", "Replace tautology with: "),
}


@pre(lambda prefix, suggestion, patterns: bool(prefix) and bool(suggestion))
@post(lambda result: isinstance(result, str) and len(result) > 0)
def _format_with_patterns(prefix: str, suggestion: str, patterns: str) -> str:
    """Format suggestion with optional patterns.

    >>> _format_with_patterns("Add: ", "check(x)", "Patterns: x > 0")
    'Add: check(x)\\nPatterns: x > 0'
    """
    result = f"{prefix}{suggestion}"
    if patterns:
        result += f"\n{patterns}"
    return result


@pre(
    lambda symbol, violation_type: violation_type
    in ("missing_contract", "empty_contract", "redundant_type_contract", "semantic_tautology", "")
)
def format_suggestion_for_violation(symbol: Symbol, violation_type: str) -> str:
    """
    Format a complete suggestion message for a violation.

    Phase 9.2 P4: Generate lambda skeletons when no type-based suggestion available.
    P7: Added semantic_tautology support.
    P27: Show pattern alternatives (Guard provides options, Agent decides).
    DX-XX: Return-type-aware @post suggestions for redundant_type_contract.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(x: int, y: int) -> int")
        >>> msg = format_suggestion_for_violation(sym, "missing_contract")
        >>> "@pre(lambda x, y: x >= 0 and y >= 0)" in msg
        True
        >>> "Patterns:" in msg  # P27: shows alternatives
        True
        >>> # P4: skeleton when no type-based suggestion
        >>> sym2 = Symbol(name="process", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(data, config)")
        >>> msg2 = format_suggestion_for_violation(sym2, "missing_contract")
        >>> "@pre(lambda data, config: <condition>)" in msg2
        True
        >>> # Return-type-aware @post for redundant_type_contract
        >>> sym3 = Symbol(name="check", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(x: int) -> list[Violation]")
        >>> msg3 = format_suggestion_for_violation(sym3, "redundant_type_contract")
        >>> 'all(v.rule ==' in msg3
        True
    """
    if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
        return ""

    if violation_type not in _VIOLATION_PREFIXES:
        return ""

    # Guard against malformed signatures
    sig = symbol.signature
    if not (sig.startswith("(") or sig == ""):
        return ""

    suggestion_prefix, skeleton_prefix = _VIOLATION_PREFIXES[violation_type]
    patterns = generate_pattern_options(sig)
    suggestion = generate_contract_suggestion(sig)

    # For redundant_type_contract, include return-type-aware @post suggestion
    if violation_type == "redundant_type_contract":
        return_type = extract_return_type(sig)
        post_suggestion = generate_post_suggestion(return_type)
        if suggestion:
            full_suggestion = f"{suggestion}\n  or {post_suggestion}"
            return _format_with_patterns(suggestion_prefix, full_suggestion, patterns)
        return f"{skeleton_prefix}{post_suggestion}"

    if suggestion:
        return _format_with_patterns(suggestion_prefix, suggestion, patterns)

    # P4: Generate lambda skeleton when no type-based suggestion
    skeleton = _generate_lambda_skeleton(sig)
    return f"{skeleton_prefix}{skeleton}"
