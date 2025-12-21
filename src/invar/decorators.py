"""
Invar contract decorators.

Provides decorators that extend deal's contract system for additional
static analysis by Guard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)


def must_use(reason: str | None = None) -> Callable[[F], F]:
    """
    Mark a function's return value as must-use.

    Guard will warn if calls to this function discard the return value.
    Inspired by Move's lack of drop ability and Rust's #[must_use].

    Args:
        reason: Explanation of why the return value must be used.

    Returns:
        A decorator that marks the function.

    >>> @must_use("Error must be handled")
    ... def may_fail() -> int:
    ...     return 42
    >>> may_fail.__invar_must_use__
    'Error must be handled'

    >>> @must_use()
    ... def important() -> str:
    ...     return "result"
    >>> important.__invar_must_use__
    'Return value must be used'
    """

    def decorator(func: F) -> F:
        func.__invar_must_use__ = reason or "Return value must be used"  # type: ignore[attr-defined]
        return func

    return decorator
