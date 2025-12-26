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


def pre(*contracts: Contract) -> Callable[[Callable], Callable]:
    """
    Decorator accepting Contract objects for preconditions.

    Works with deal.pre under the hood.

    Examples:
        >>> from invar_runtime.contracts import pre, NonEmpty
        >>> @pre(NonEmpty)
        ... def first(xs): return xs[0]
        >>> first([1, 2, 3])
        1
    """

    def combined(*args: Any, **kwargs: Any) -> bool:
        if not args and not kwargs:
            raise ValueError("Precondition requires at least one argument")
        value = args[0] if args else next(iter(kwargs.values()))
        return all(c.check(value) for c in contracts)

    return deal.pre(combined)


def post(*contracts: Contract) -> Callable[[Callable], Callable]:
    """
    Decorator accepting Contract objects for postconditions.

    Works with deal.post under the hood.

    Examples:
        >>> from invar_runtime.contracts import post, NonEmpty
        >>> @post(NonEmpty)
        ... def get_list(): return [1]
        >>> get_list()
        [1]
    """

    def combined(result: Any) -> bool:
        return all(c.check(result) for c in contracts)

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
