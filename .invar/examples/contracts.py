"""
Invar Contract Examples

Reference patterns for @pre/@post contracts and doctests.
Managed by Invar - do not edit directly.
"""

# For lambda-based contracts, use deal directly
# invar_runtime.pre/post are for Contract objects (NonEmpty, IsInstance, etc.)
from deal import post, pre

# =============================================================================
# GOOD: Complete Contract
# =============================================================================


@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    Apply discount to price.

    >>> discounted_price(100.0, 0.2)
    80.0
    >>> discounted_price(100.0, 0)      # Edge: no discount
    100.0
    >>> discounted_price(100.0, 1)      # Edge: full discount
    0.0
    """
    return price * (1 - discount)


# =============================================================================
# GOOD: List Processing with Length Constraint
# =============================================================================


@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def average(items: list[float]) -> float:
    """
    Calculate average of non-empty list.

    >>> average([1, 2, 3])
    2.0
    >>> average([5])        # Edge: single element
    5.0
    >>> average([0, 0, 0])  # Edge: all zeros
    0.0
    """
    return sum(items) / len(items)


# =============================================================================
# GOOD: Dict Comparison in Doctests
# =============================================================================


@pre(lambda data: len(data) > 0)  # Non-empty input (type is in annotation)
@post(lambda result: len(result) > 0)  # Preserves non-emptiness
def normalize_keys(data: dict[str, int]) -> dict[str, int]:
    """
    Lowercase all keys.

    # GOOD: Use sorted() for deterministic output
    >>> sorted(normalize_keys({'A': 1, 'B': 2}).items())
    [('a', 1), ('b', 2)]

    # GOOD: Or use equality comparison
    >>> normalize_keys({'X': 10}) == {'x': 10}
    True
    """
    return {k.lower(): v for k, v in data.items()}


# =============================================================================
# BAD: Incomplete Contract (anti-pattern)
# =============================================================================

# DON'T: Empty contract tells nothing
# @pre(lambda: True)
# @post(lambda result: True)
# def process(x): ...  # noqa: ERA001

# DON'T: Missing edge cases in doctests
# def divide(a, b):
#     """
#     >>> divide(10, 2)
#     5.0
#     # Missing: what about b=0?
#     """


# =============================================================================
# GOOD: Multiple @pre for Clarity
# =============================================================================


@pre(lambda start, end: start >= 0)
@pre(lambda start, end: end >= start)
@post(lambda result: result >= 0)
def range_size(start: int, end: int) -> int:
    """
    Calculate size of range [start, end).

    >>> range_size(0, 10)
    10
    >>> range_size(5, 5)    # Edge: empty range
    0
    >>> range_size(0, 1)    # Edge: single element
    1
    """
    return end - start
