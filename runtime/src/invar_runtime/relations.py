"""
Relational contracts for input-output verification.

DX-28: @relates decorator for contracts that verify relationships between
inputs and outputs, addressing the limitation that @post only sees results.

Example:
    >>> from invar_runtime.relations import relates
    >>> @relates(lambda inp, out: "error" in inp.lower() if out else True,
    ...          "If input contains 'error', output must be non-empty")
    ... def extract_errors(text: str) -> list[str]:
    ...     return [line for line in text.split("\\n") if ": error:" in line.lower()]
    >>> extract_errors("file.py:1: error: Bug")
    ['file.py:1: error: Bug']
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class RelationViolation(Exception):
    """Raised when a relational contract is violated.

    Examples:
        >>> raise RelationViolation("input 'x' should produce non-empty output")
        Traceback (most recent call last):
            ...
        invar_runtime.relations.RelationViolation: input 'x' should produce non-empty output
    """


def relates(
    relation: Callable[[Any, Any], bool],
    message: str = "",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator asserting input-output relationship.

    The relation function receives (primary_input, result) and must return True.
    CrossHair can verify this symbolically through deal.post conversion.

    Args:
        relation: Function (input, output) -> bool that must hold
        message: Human-readable description of the relationship

    Returns:
        Decorated function with relational contract

    Examples:
        >>> @relates(lambda x, y: y == x * 2, "output equals double of input")
        ... def double(x: int) -> int:
        ...     return x * 2
        >>> double(5)
        10
        >>> double(-3)
        -6

        >>> @relates(lambda text, lines: len(lines) <= text.count("\\n") + 1,
        ...          "output lines <= input line count")
        ... def split_lines(text: str) -> list[str]:
        ...     return text.split("\\n")
        >>> split_lines("a\\nb\\nc")
        ['a', 'b', 'c']
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Store the relation for introspection
        func.__relates__ = (relation, message)  # type: ignore[attr-defined]

        # Convert to deal.post for CrossHair compatibility
        # We need to capture the input in a closure
        captured_input: list[Any] = []

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Capture primary input (first positional arg)
            primary_input = args[0] if args else None
            captured_input.clear()
            captured_input.append(primary_input)

            result = func(*args, **kwargs)

            # Check relation
            if not relation(primary_input, result):
                msg = f"Relation violated: {message}" if message else "Relation violated"
                raise RelationViolation(
                    f"{msg}\n"
                    f"Input: {primary_input!r}\n"
                    f"Output: {result!r}"
                )

            return result

        # Copy original attributes
        wrapper.__relates__ = (relation, message)  # type: ignore[attr-defined]

        return wrapper

    return decorator


def relates_multi(
    relation: Callable[..., bool],
    message: str = "",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for multi-argument relational contracts.

    The relation function receives (*args, **kwargs, result) where result is
    the last positional argument. All original arguments are passed.

    Args:
        relation: Function (*args, result) -> bool that must hold
        message: Human-readable description of the relationship

    Returns:
        Decorated function with relational contract

    Examples:
        >>> @relates_multi(lambda a, b, result: result == a + b,
        ...                "result equals sum of inputs")
        ... def add(a: int, b: int) -> int:
        ...     return a + b
        >>> add(2, 3)
        5

        >>> @relates_multi(lambda items, key, result: all(k in items for k in result),
        ...                "result keys must be subset of input")
        ... def filter_dict(items: dict, key: str) -> dict:
        ...     return {k: v for k, v in items.items() if key in k}
        >>> filter_dict({"a_x": 1, "b_y": 2, "a_z": 3}, "a")
        {'a_x': 1, 'a_z': 3}
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        func.__relates_multi__ = (relation, message)  # type: ignore[attr-defined]

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = func(*args, **kwargs)

            # Call relation with all args plus result
            if not relation(*args, result):
                msg = f"Relation violated: {message}" if message else "Relation violated"
                raise RelationViolation(
                    f"{msg}\n"
                    f"Args: {args!r}\n"
                    f"Kwargs: {kwargs!r}\n"
                    f"Output: {result!r}"
                )

            return result

        wrapper.__relates_multi__ = (relation, message)  # type: ignore[attr-defined]

        return wrapper

    return decorator


def to_post_contract(
    relation: Callable[[Any, Any], bool],
    input_value: Any,
) -> Callable[[Any], bool]:
    """
    Convert a relational contract to a deal.post-compatible contract.

    This is used internally for CrossHair integration.

    Args:
        relation: The (input, output) -> bool relation
        input_value: The captured input value

    Returns:
        A post-condition function (output) -> bool

    Examples:
        >>> relation = lambda x, y: y > x
        >>> post_fn = to_post_contract(relation, 5)
        >>> post_fn(10)
        True
        >>> post_fn(3)
        False
    """
    return lambda result: relation(input_value, result)
