"""
Strategy inference for property-based testing.

Core module: parses @pre contract lambdas to infer Hypothesis strategies.
Inspired by icontract-hypothesis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from deal import post, pre

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class StrategyHint:
    """Inferred strategy hint for a parameter."""

    param_name: str
    param_type: type | None
    constraints: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    @post(lambda result: all(isinstance(k, str) for k in result))  # Keys are strings
    def to_hypothesis_args(self) -> dict[str, Any]:
        """Convert constraints to Hypothesis strategy arguments.

        >>> hint = StrategyHint("x", int, {"min_value": 0, "max_value": 100})
        >>> hint.to_hypothesis_args()
        {'min_value': 0, 'max_value': 100}
        """
        return self.constraints.copy()


# Helper to parse numbers (int or float, including scientific notation)
# Pattern matches valid number literals extracted from regex patterns
# Uses [0-9] instead of \d to avoid matching Unicode digits
# Requires at least one digit before optional decimal/exponent parts
_NUMBER_PATTERN = re.compile(r"^-?[0-9]+\.?[0-9]*(?:e[+-]?[0-9]+)?$", re.IGNORECASE)


@pre(lambda s: _NUMBER_PATTERN.match(s.strip()))  # Valid number format
def _parse_number(s: str) -> int | float:
    """Parse a number string to int or float.

    >>> _parse_number("42")
    42
    >>> _parse_number("-3.14")
    -3.14
    >>> _parse_number("1e-5")
    1e-05
    """
    s = s.strip()
    if "." in s or "e" in s.lower():
        return float(s)
    return int(s)


# Pattern → Constraint extraction
# Each pattern maps to a function that extracts constraints from regex match
# DX-12: Added float support with exclude_min/exclude_max for precise bounds
PATTERNS: list[tuple[str, Callable[[re.Match, str], dict[str, Any] | None]]] = [
    # Numeric comparisons: x > 5, x >= 5 (supports int, float, scientific notation)
    (
        r"(\w+)\s*>\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {"min_value": _parse_number(m.group(2)), "exclude_min": True}
        if m.group(1) == p
        else None,
    ),
    (
        r"(\w+)\s*>=\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {"min_value": _parse_number(m.group(2))} if m.group(1) == p else None,
    ),
    (
        r"(\w+)\s*<\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {"max_value": _parse_number(m.group(2)), "exclude_max": True}
        if m.group(1) == p
        else None,
    ),
    (
        r"(\w+)\s*<=\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {"max_value": _parse_number(m.group(2))} if m.group(1) == p else None,
    ),
    # Reversed comparisons: 5 < x, 5 <= x
    (
        r"(-?[\d.]+(?:e[+-]?\d+)?)\s*<\s*(\w+)(?!\s*<)",
        lambda m, p: {"min_value": _parse_number(m.group(1)), "exclude_min": True}
        if m.group(2) == p
        else None,
    ),
    (
        r"(-?[\d.]+(?:e[+-]?\d+)?)\s*<=\s*(\w+)(?!\s*<)",
        lambda m, p: {"min_value": _parse_number(m.group(1))} if m.group(2) == p else None,
    ),
    # Pattern: Range comparison (e.g. 0 < x < 10)
    (
        r"(-?[\d.]+(?:e[+-]?\d+)?)\s*<\s*(\w+)\s*<\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {
            "min_value": _parse_number(m.group(1)),
            "max_value": _parse_number(m.group(3)),
            "exclude_min": True,
            "exclude_max": True,
        }
        if m.group(2) == p
        else None,
    ),
    (
        r"(-?[\d.]+(?:e[+-]?\d+)?)\s*<=\s*(\w+)\s*<=\s*(-?[\d.]+(?:e[+-]?\d+)?)",
        lambda m, p: {"min_value": _parse_number(m.group(1)), "max_value": _parse_number(m.group(3))}
        if m.group(2) == p
        else None,
    ),
    # Length constraints: len(x) > 0
    (
        r"len\((\w+)\)\s*>\s*(\d+)",
        lambda m, p: {"min_size": int(m.group(2)) + 1} if m.group(1) == p else None,
    ),
    (
        r"len\((\w+)\)\s*>=\s*(\d+)",
        lambda m, p: {"min_size": int(m.group(2))} if m.group(1) == p else None,
    ),
    (
        r"len\((\w+)\)\s*<\s*(\d+)",
        lambda m, p: {"max_size": int(m.group(2)) - 1} if m.group(1) == p else None,
    ),
    (
        r"len\((\w+)\)\s*<=\s*(\d+)",
        lambda m, p: {"max_size": int(m.group(2))} if m.group(1) == p else None,
    ),
    # Non-empty: len(x) > 0 or just x
    (
        r"len\((\w+)\)\s*>\s*0",
        lambda m, p: {"min_size": 1} if m.group(1) == p else None,
    ),
]


@pre(lambda pre_source, param_name, param_type=None: len(param_name) > 0)  # Param must be named
@post(lambda result: isinstance(result.constraints, dict))  # Returns valid hint
def infer_from_lambda(
    pre_source: str,
    param_name: str,
    param_type: type | None = None,
) -> StrategyHint:
    """
    Parse @pre lambda source to infer strategy constraints.

    DX-12: Now returns exclude_min/exclude_max for strict inequalities,
    allowing Hypothesis to generate precise bounds for floats.

    >>> hint = infer_from_lambda("lambda x: x > 0", "x", int)
    >>> hint.constraints['min_value']
    0
    >>> hint.constraints.get('exclude_min')
    True

    >>> hint = infer_from_lambda("lambda x: 0 < x < 100", "x", float)
    >>> hint.constraints['min_value'], hint.constraints['max_value']
    (0, 100)
    >>> hint.constraints.get('exclude_min'), hint.constraints.get('exclude_max')
    (True, True)

    >>> hint = infer_from_lambda("lambda x: len(x) > 0", "x", list)
    >>> hint.constraints
    {'min_size': 1}

    >>> hint = infer_from_lambda("lambda x, y: x > 5 and y < 10", "x", int)
    >>> hint.constraints['min_value']
    5
    """
    constraints: dict[str, Any] = {}
    hints: list[str] = []

    for pattern, extractor in PATTERNS:
        for match in re.finditer(pattern, pre_source):
            extracted = extractor(match, param_name)
            if extracted:
                constraints.update(extracted)
                hints.append(f"Matched: {pattern}")

    description = "; ".join(hints) if hints else "No patterns matched"

    return StrategyHint(
        param_name=param_name,
        param_type=param_type,
        constraints=constraints,
        description=description,
    )


@pre(lambda pre_sources, param_name, param_type=None: len(param_name) > 0)  # Param must be named
@post(lambda result: isinstance(result.constraints, dict))  # Returns valid hint
def infer_from_multiple(
    pre_sources: list[str],
    param_name: str,
    param_type: type | None = None,
) -> StrategyHint:
    """
    Combine constraints from multiple @pre contracts.

    >>> hints = infer_from_multiple(["lambda x: x > 0", "lambda x: x < 100"], "x", float)
    >>> hints.constraints['min_value'], hints.constraints['max_value']
    (0, 100)
    >>> hints.constraints.get('exclude_min'), hints.constraints.get('exclude_max')
    (True, True)
    """
    combined: dict[str, Any] = {}
    descriptions: list[str] = []

    for source in pre_sources:
        hint = infer_from_lambda(source, param_name, param_type)
        combined.update(hint.constraints)
        if hint.description != "No patterns matched":
            descriptions.append(hint.description)

    return StrategyHint(
        param_name=param_name,
        param_type=param_type,
        constraints=combined,
        description="; ".join(descriptions) if descriptions else "No patterns matched",
    )


@post(lambda result: ":" in result)  # Format is "name: strategy"
def format_strategy_hint(hint: StrategyHint) -> str:
    """
    Format a strategy hint as a human-readable string.

    >>> hint = StrategyHint("x", int, {"min_value": 0, "max_value": 100})
    >>> format_strategy_hint(hint)
    'x: integers(min_value=0, max_value=100)'

    >>> hint = StrategyHint("y", float, {"min_value": 0, "exclude_min": True})
    >>> 'floats' in format_strategy_hint(hint)
    True
    """
    if not hint.constraints:
        if hint.param_type:
            return f"{hint.param_name}: from_type({hint.param_type.__name__})"
        return f"{hint.param_name}: <unknown>"

    type_name = hint.param_type.__name__ if hint.param_type else "unknown"

    if type_name in ("int", "float"):
        strategy = "integers" if type_name == "int" else "floats"
        args = ", ".join(f"{k}={v}" for k, v in hint.constraints.items())
        return f"{hint.param_name}: {strategy}({args})"

    if type_name in ("list", "str", "tuple"):
        strategy = "lists" if type_name == "list" else "text"
        args = ", ".join(f"{k}={v}" for k, v in hint.constraints.items())
        return f"{hint.param_name}: {strategy}({args})"

    args = ", ".join(f"{k}={v}" for k, v in hint.constraints.items())
    return f"{hint.param_name}: {args}"
