# ruff: noqa: ERA001
"""
Invar Contract Examples

Reference patterns for @pre/@post contracts and doctests.
Managed by Invar - do not edit directly.
"""
# @invar:allow partial_contract: Educational file showing multiple @pre pattern

# invar_runtime supports both lambda and Contract objects
from invar_runtime import post, pre

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
# def process(x): ...

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


# =============================================================================
# CRITICAL: Default Parameters in Contracts
# =============================================================================
# Lambda signatures MUST include ALL parameters, including defaults!
# This is a common mistake that causes silent contract failures.


# DON'T: Missing default parameter in lambda
# @pre(lambda x: x >= 0)  # BAD: 'y' is missing!
# def calc_bad(x: int, y: int = 0) -> int:
#     return x + y


# DO: Include all parameters with their defaults
@pre(lambda x, y=0: x >= 0 and y >= 0)
@post(lambda result: result >= 0)
def calculate_with_default(x: int, y: int = 0) -> int:
    """
    Calculate sum with optional y.

    The lambda MUST include y=0 to match the function signature.

    >>> calculate_with_default(5)
    5
    >>> calculate_with_default(5, 3)
    8
    >>> calculate_with_default(0, 0)  # Edge: both zero
    0
    """
    return x + y


# =============================================================================
# CRITICAL: @post Cannot Access Parameters
# =============================================================================
# @post only receives the return value, not the original parameters!


# DON'T: Reference parameters in @post
# @post(lambda result: result > x)  # BAD: 'x' is not available!
# def double_bad(x: int) -> int:
#     return x * 2


# DO: @post only validates the result itself
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)  # GOOD: only uses 'result'
def double_positive(x: int) -> int:
    """
    Double a positive number.

    @post can only validate result properties, not relationships to inputs.

    >>> double_positive(5)
    10
    >>> double_positive(0)  # Edge: zero
    0
    """
    return x * 2


# =============================================================================
# Decorator Order with @pre/@post
# =============================================================================
# When combining with other decorators, @pre/@post should be closest to function.


# DO: @pre/@post closest to function
# @other_decorator
# @pre(lambda x: x > 0)
# @post(lambda result: result > 0)
# def my_func(x: int) -> int: ...

# This ensures contracts run BEFORE other decorators modify behavior.
