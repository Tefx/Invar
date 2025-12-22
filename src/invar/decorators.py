"""
Invar contract decorators.

Provides decorators that extend deal's contract system for additional
static analysis by Guard.

DX-12-B: Added @strategy for custom Hypothesis strategies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

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


def strategy(**param_strategies: Any) -> Callable[[F], F]:
    """
    Specify custom Hypothesis strategies for function parameters.

    DX-12-B: Escape hatch when automatic strategy inference fails or
    when you need precise control over generated values.

    Args:
        **param_strategies: Mapping of parameter names to Hypothesis strategies.

    Returns:
        A decorator that attaches strategies to the function.

    Examples:
        >>> from hypothesis import strategies as st
        >>> @strategy(x=st.floats(min_value=1e-10, max_value=1e10))
        ... def sqrt(x: float) -> float:
        ...     return x ** 0.5
        >>> hasattr(sqrt, '__invar_strategies__')
        True
        >>> 'x' in sqrt.__invar_strategies__
        True

        >>> # NumPy array with specific shape
        >>> @strategy(arr="arrays(dtype=float64, shape=(10,))")
        ... def normalize(arr):
        ...     return arr / arr.sum()
        >>> 'arr' in normalize.__invar_strategies__
        True

    Note:
        Strategies can be either:
        - Hypothesis strategy objects (e.g., st.floats())
        - String representations (e.g., "floats(min_value=0)")

        String representations are useful when you don't want to import
        Hypothesis at module load time.
    """

    def decorator(func: F) -> F:
        func.__invar_strategies__ = param_strategies  # type: ignore[attr-defined]
        return func

    return decorator
