"""
Composable contracts for Invar.

Provides Contract class with &, |, ~ operators for combining conditions,
and a standard library of common predicates. Works with deal decorators.

Inspired by Idris' dependent types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import deal

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class Contract:
    """
    Composable contract with &, |, ~ operators.

    Contracts encapsulate predicates that can be combined and reused.
    Works with deal.pre for runtime checking.

    Security Warning:
        Predicates execute during validation and can run arbitrary code.
        NEVER use predicates from: user input, untrusted files, network data.
        A malicious predicate like `lambda x: __import__('os').system('rm -rf /')`
        would execute when check() is called. Use only hardcoded predicates
        defined in your source code.

    Examples:
        >>> NonEmpty = Contract(lambda x: len(x) > 0, "non-empty")
        >>> Sorted = Contract(lambda x: list(x) == sorted(x), "sorted")
        >>> combined = NonEmpty & Sorted
        >>> combined.check([1, 2, 3])
        True
        >>> combined.check([])
        False
        >>> combined.check([3, 1, 2])
        False
        >>> (NonEmpty | Sorted).check([])  # Empty but sorted
        True
        >>> (~NonEmpty).check([])  # NOT non-empty
        True
    """

    predicate: Callable[[Any], bool]
    description: str

    def check(self, value: Any) -> bool:
        """Check if value satisfies the contract."""
        return self.predicate(value)

    def __and__(self, other: Contract) -> Contract:
        """Combine contracts with AND."""
        return Contract(
            predicate=lambda x: self.check(x) and other.check(x),
            description=f"({self.description} AND {other.description})",
        )

    def __or__(self, other: Contract) -> Contract:
        """Combine contracts with OR."""
        return Contract(
            predicate=lambda x: self.check(x) or other.check(x),
            description=f"({self.description} OR {other.description})",
        )

    def __invert__(self) -> Contract:
        """Negate the contract."""
        return Contract(
            predicate=lambda x: not self.check(x),
            description=f"NOT({self.description})",
        )

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """
        Allow using as deal.pre predicate directly.

        Examples:
            >>> c = Contract(lambda x: x > 0, "positive")
            >>> c(5)
            True
            >>> c(-1)
            False
            >>> c(x=10)
            True
            >>> c()
            Traceback (most recent call last):
                ...
            ValueError: Contract requires at least one argument
            >>> c(*[], **{})  # Explicit empty args and kwargs
            Traceback (most recent call last):
                ...
            ValueError: Contract requires at least one argument
        """
        if not args and not kwargs:
            raise ValueError("Contract requires at least one argument")
        value = args[0] if args else next(iter(kwargs.values()))
        return self.check(value)

    def __repr__(self) -> str:
        return f"Contract({self.description!r})"


def pre(*args: Contract | Callable) -> Callable[[Callable], Callable]:
    """
    Decorator for preconditions. Accepts lambda or Contract objects.

    Works with deal.pre under the hood.

    Examples:
        >>> from invar_runtime.contracts import pre, NonEmpty, Positive

        Lambda usage (like deal.pre):
        >>> @pre(lambda x: x > 0)
        ... def double(x): return x * 2
        >>> double(5)
        10

        Contract usage:
        >>> @pre(NonEmpty)
        ... def first(xs): return xs[0]
        >>> first([1, 2, 3])
        1

        Combined Contract:
        >>> @pre(Positive)
        ... def sqrt(x): return x ** 0.5
        >>> sqrt(4)
        2.0

        Multiple contracts:
        >>> @pre(NonEmpty, Positive)  # doctest: +SKIP
        ... def bounded(x): return x
    """
    # M4 fix: Reject empty args
    if not args:
        raise TypeError("pre() requires at least one Contract or callable")

    # Single callable (not Contract) → delegate to deal.pre directly
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Contract):
        return deal.pre(args[0])

    # C1 fix: Handle mixed Contract and callable
    def combined(*a: Any, **kw: Any) -> bool:
        if not a and not kw:
            raise ValueError("Precondition requires at least one argument")
        value = a[0] if a else next(iter(kw.values()))
        results = []
        for c in args:
            if isinstance(c, Contract):
                results.append(c.check(value))
            elif callable(c):
                results.append(c(value))
            else:
                raise TypeError(f"Expected Contract or callable, got {type(c)}")
        return all(results)

    return deal.pre(combined)


def post(*args: Contract | Callable) -> Callable[[Callable], Callable]:
    """
    Decorator for postconditions. Accepts lambda or Contract objects.

    Works with deal.post under the hood.

    Examples:
        >>> from invar_runtime.contracts import post, NonEmpty, NonNegative

        Lambda usage (like deal.post):
        >>> @post(lambda result: result >= 0)
        ... def abs_val(x): return abs(x)
        >>> abs_val(-5)
        5

        Contract usage:
        >>> @post(NonEmpty)
        ... def get_list(): return [1]
        >>> get_list()
        [1]

        >>> @post(NonNegative)
        ... def square(x): return x * x
        >>> square(-3)
        9

        Multiple contracts:
        >>> @post(NonEmpty, NonNegative)  # doctest: +SKIP
        ... def get_count(): return [1, 2]
    """
    # M4 fix: Reject empty args
    if not args:
        raise TypeError("post() requires at least one Contract or callable")

    # Single callable (not Contract) → delegate to deal.post directly
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Contract):
        return deal.post(args[0])

    # C1 fix: Handle mixed Contract and callable
    def combined(result: Any) -> bool:
        results = []
        for c in args:
            if isinstance(c, Contract):
                results.append(c.check(result))
            elif callable(c):
                results.append(c(result))
            else:
                raise TypeError(f"Expected Contract or callable, got {type(c)}")
        return all(results)

    return deal.post(combined)


# =============================================================================
# Standard Library of Contracts
# =============================================================================

# --- Collections ---
NonEmpty: Contract = Contract(lambda x: len(x) > 0, "non-empty")
Sorted: Contract = Contract(lambda x: list(x) == sorted(x), "sorted")
Unique: Contract = Contract(lambda x: len(x) == len(set(x)), "unique")
SortedNonEmpty: Contract = NonEmpty & Sorted

# --- Numbers ---
Positive: Contract = Contract(lambda x: x > 0, "positive")
NonNegative: Contract = Contract(lambda x: x >= 0, "non-negative")
Negative: Contract = Contract(lambda x: x < 0, "negative")


def InRange(lo: float, hi: float) -> Contract:
    """Create a contract checking value is in [lo, hi]."""
    return Contract(lambda x: lo <= x <= hi, f"[{lo},{hi}]")


Percentage: Contract = InRange(0, 100)

# --- Strings ---
NonBlank: Contract = Contract(lambda s: bool(s and s.strip()), "non-blank")

# --- Lists with elements ---
AllPositive: Contract = Contract(lambda xs: all(x > 0 for x in xs), "all positive")
AllNonNegative: Contract = Contract(lambda xs: all(x >= 0 for x in xs), "all non-negative")
NoNone: Contract = Contract(lambda xs: None not in xs, "no None")
