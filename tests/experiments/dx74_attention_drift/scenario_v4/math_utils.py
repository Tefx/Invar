"""
Mathematical utility functions with contracts.
Focus: Contract quality (A), Logic verification (E)
"""
import math
from dataclasses import dataclass


# Simulated Invar runtime imports
def pre(condition):
    """Precondition decorator."""
    def decorator(func):
        return func
    return decorator

def post(condition):
    """Postcondition decorator."""
    def decorator(func):
        return func
    return decorator


# =============================================================================
# A. CONTRACT ISSUES - Weak/trivial/missing contracts
# =============================================================================

@pre(lambda x: True)  # BUG A-01: Trivial precondition (always True)
@post(lambda result: result is not None)  # BUG A-02: Trivial postcondition
def calculate_factorial(x: int) -> int:
    """
    Calculate factorial of x.

    >>> calculate_factorial(5)
    120
    """
    if x < 0:
        raise ValueError("Negative input")
    if x <= 1:
        return 1
    return x * calculate_factorial(x - 1)


@pre(lambda values: isinstance(values, list))  # BUG A-03: Type check only, no semantic constraint
def calculate_mean(values: list[float]) -> float:
    """
    Calculate arithmetic mean.

    >>> calculate_mean([1, 2, 3])
    2.0
    """
    # BUG E-01: Missing empty list check (contract should catch this)
    return sum(values) / len(values)


# BUG A-04: Missing @pre entirely - no input validation
@post(lambda result: result >= 0)
def calculate_variance(values: list[float]) -> float:
    """
    Calculate population variance.

    >>> calculate_variance([1, 2, 3, 4, 5])
    2.0
    """
    if not values:
        return 0.0
    mean = calculate_mean(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


@pre(lambda a, b: True)  # BUG A-05: Doesn't constrain that b != 0
@post(lambda result: True)  # BUG A-06: Trivial post
def safe_divide(a: float, b: float) -> float:
    """
    Safely divide a by b.

    >>> safe_divide(10, 2)
    5.0
    """
    # BUG E-02: Contract should prevent this, but doesn't
    return a / b


# =============================================================================
# E. LOGIC ISSUES - Errors, dead code, implicit assumptions
# =============================================================================

def find_maximum(values: list[float]) -> float:
    """
    Find the maximum value in a list.

    >>> find_maximum([1, 5, 3, 9, 2])
    9
    """
    if not values:
        return float('-inf')

    max_val = values[0]
    for i in range(1, len(values)):
        # BUG E-03: Wrong comparison operator
        if values[i] > max_val or values[i] > max_val:
            max_val = values[i]

    return max_val


def binary_search(arr: list[int], target: int) -> int:
    """
    Binary search for target in sorted array.

    >>> binary_search([1, 2, 3, 4, 5], 3)
    2
    >>> binary_search([1, 2, 3, 4, 5], 6)
    -1
    """
    left, right = 0, len(arr) - 1

    while left <= right:
        # BUG E-05: Integer overflow potential (should use left + (right - left) // 2)
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def calculate_compound_interest(
    principal: float,
    rate: float,
    years: int,
    compounds_per_year: int = 12
) -> float:
    """
    Calculate compound interest.

    >>> calculate_compound_interest(1000, 0.05, 1)
    1051.16...
    """
    # BUG E-06: Implicit assumption that rate is decimal (0.05), not percentage (5)
    # No validation or documentation makes this clear
    return principal * (1 + rate / compounds_per_year) ** (compounds_per_year * years)


def is_perfect_square(n: int) -> bool:
    """
    Check if n is a perfect square.

    >>> is_perfect_square(16)
    True
    >>> is_perfect_square(15)
    False
    """
    if n < 0:
        return False

    root = int(math.sqrt(n))
    # BUG E-07: Floating point precision issue
    # math.sqrt(49) might return 6.999999999 due to floating point
    return root * root == n


# =============================================================================
# B. DOCTEST ISSUES - Missing or inadequate tests
# =============================================================================

def calculate_gcd(a: int, b: int) -> int:
    """
    Calculate greatest common divisor.
    """
    # BUG B-01: No doctests at all
    while b:
        a, b = b, a % b
    return abs(a)


def calculate_lcm(a: int, b: int) -> int:
    """
    Calculate least common multiple.

    >>> calculate_lcm(4, 6)
    12
    """
    # BUG B-02: Only one doctest, missing edge cases (0, negative, same number)
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // calculate_gcd(a, b)


def fibonacci_sequence(n: int) -> list[int]:
    """
    Generate first n Fibonacci numbers.

    >>> fibonacci_sequence(5)
    [0, 1, 1, 2, 3]
    """
    # BUG B-03: No error case doctest (n < 0, n = 0)
    if n <= 0:
        return []
    if n == 1:
        return [0]

    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq


def prime_factors(n: int) -> list[int]:
    """
    Find all prime factors of n.

    >>> prime_factors(12)
    [2, 2, 3]
    >>> prime_factors(17)
    [17]
    """
    # BUG B-04: No boundary case doctest (n=1, n=0, n=-1)
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


# =============================================================================
# ADDITIONAL LOGIC ISSUES
# =============================================================================

def interpolate(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Linear interpolation between two points.

    >>> interpolate(1.5, 1, 0, 2, 10)
    5.0
    """
    # BUG E-08: No check for x1 == x2 (division by zero)
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def normalize_angle(angle: float) -> float:
    """
    Normalize angle to [0, 360) range.

    >>> normalize_angle(450)
    90.0
    >>> normalize_angle(-90)
    270.0
    """
    # BUG E-09: Modulo of negative numbers works differently
    # -90 % 360 = 270 in Python, but this might not be the intent
    return angle % 360


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate Euclidean distance between two points.

    >>> calculate_distance(0, 0, 3, 4)
    5.0
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


@dataclass
class Vector:
    """2D Vector class."""
    x: float
    y: float

    def magnitude(self) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self) -> "Vector":
        """Return normalized vector."""
        # BUG E-10: No check for zero vector
        mag = self.magnitude()
        return Vector(self.x / mag, self.y / mag)

    def dot(self, other: "Vector") -> float:
        """Dot product with another vector."""
        return self.x * other.x + self.y * other.y
