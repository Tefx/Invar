"""
Calculator module for various mathematical operations.
"""
import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class CalculationResult:
    """Result of a calculation."""
    value: int | float | Decimal
    precision: int
    operation: str
    inputs: list


class BasicCalculator:
    """Basic arithmetic calculator."""

    def __init__(self, precision: int = 2):
        self.precision = precision
        self.history: list[CalculationResult] = []

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self._record("add", result, [a, b])
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        self._record("subtract", result, [a, b])
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self._record("multiply", result, [a, b])
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        # BUG: Wrong check - should check b == 0, not a == 0
        if a == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self._record("divide", result, [a, b])
        return result

    def _record(self, operation: str, result: float, inputs: list):
        """Record a calculation in history."""
        self.history.append(CalculationResult(
            value=result,
            precision=self.precision,
            operation=operation,
            inputs=inputs
        ))


class StatisticsCalculator:
    """Calculator for statistical operations."""

    def mean(self, values: list[float]) -> float:
        """Calculate arithmetic mean."""
        # BUG: No check for empty list - ZeroDivisionError
        return sum(values) / len(values)

    def weighted_mean(self, values: list[float], weights: list[float]) -> float:
        """Calculate weighted mean."""
        # BUG: No check that values and weights have same length
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(v * w for v, w in zip(values, weights))
        return weighted_sum / total_weight

    def variance(self, values: list[float]) -> float:
        """Calculate variance."""
        if len(values) < 2:
            return 0.0

        mean = self.mean(values)
        # BUG: Should divide by n-1 for sample variance, not n
        squared_diffs = [(x - mean) ** 2 for x in values]
        return sum(squared_diffs) / len(values)

    def standard_deviation(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        return math.sqrt(self.variance(values))

    def correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n != len(y):
            raise ValueError("Lists must have same length")

        if n < 2:
            return 0.0

        mean_x = self.mean(x)
        mean_y = self.mean(y)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = math.sqrt(sum_sq_x * sum_sq_y)

        # BUG: No check for zero denominator
        return numerator / denominator


class FinancialCalculator:
    """Calculator for financial operations."""

    def __init__(self, decimal_places: int = 2):
        self.decimal_places = decimal_places

    def compound_interest(
        self,
        principal: Decimal,
        rate: Decimal,
        time: int,
        n: int = 12
    ) -> Decimal:
        """Calculate compound interest."""
        # A = P(1 + r/n)^(nt)
        # BUG: Integer division in exponent calculation
        # time * n should use Decimal or float
        factor = (1 + rate / n) ** (time * n)
        return principal * factor

    def present_value(
        self,
        future_value: Decimal,
        rate: Decimal,
        periods: int
    ) -> Decimal:
        """Calculate present value."""
        # BUG: Wrong formula - should be FV / (1 + r)^n, not FV * (1 + r)^n
        return future_value * (1 + rate) ** periods

    def loan_payment(
        self,
        principal: Decimal,
        annual_rate: Decimal,
        months: int
    ) -> Decimal:
        """Calculate monthly loan payment."""
        if annual_rate == 0:
            return principal / months

        monthly_rate = annual_rate / 12

        # PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
        factor = (1 + monthly_rate) ** months
        payment = principal * (monthly_rate * factor) / (factor - 1)

        return Decimal(str(payment)).quantize(
            Decimal(10) ** -self.decimal_places,
            rounding=ROUND_HALF_UP
        )

    def roi(self, initial: Decimal, final: Decimal) -> Decimal:
        """Calculate return on investment."""
        # BUG: No check for zero initial investment
        return (final - initial) / initial * 100


class GeometryCalculator:
    """Calculator for geometric operations."""

    def circle_area(self, radius: float) -> float:
        """Calculate circle area."""
        # BUG: No check for negative radius
        return math.pi * radius ** 2

    def circle_circumference(self, radius: float) -> float:
        """Calculate circle circumference."""
        return 2 * math.pi * radius

    def rectangle_area(self, width: float, height: float) -> float:
        """Calculate rectangle area."""
        # BUG: No check for negative dimensions
        return width * height

    def triangle_area(self, base: float, height: float) -> float:
        """Calculate triangle area."""
        return 0.5 * base * height

    def sphere_volume(self, radius: float) -> float:
        """Calculate sphere volume."""
        return (4 / 3) * math.pi * radius ** 3

    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class ExpressionEvaluator:
    """Evaluates mathematical expressions."""

    def __init__(self):
        self.operators = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b,
        }
        self.precedence = {'+': 1, '-': 1, '*': 2, '/': 2}

    def evaluate_simple(self, expression: str) -> float:
        """Evaluate a simple expression like '2 + 3'."""
        parts = expression.split()

        if len(parts) != 3:
            raise ValueError("Invalid expression format")

        a = float(parts[0])
        op = parts[1]
        b = float(parts[2])

        if op not in self.operators:
            raise ValueError(f"Unknown operator: {op}")

        return self.operators[op](a, b)

    def evaluate_chain(self, values: list[float], operators: list[str]) -> float:
        """Evaluate a chain of operations left to right."""
        # BUG: Ignores operator precedence
        # 2 + 3 * 4 should be 14, but this gives 20
        if len(values) != len(operators) + 1:
            raise ValueError("Invalid chain")

        result = values[0]
        for i, op in enumerate(operators):
            result = self.operators[op](result, values[i + 1])

        return result


class UnitConverter:
    """Converts between units."""

    CONVERSIONS = {
        "km_to_miles": 0.621371,
        "miles_to_km": 1.60934,
        "kg_to_lbs": 2.20462,
        "lbs_to_kg": 0.453592,
        "celsius_to_fahrenheit": lambda c: c * 9/5 + 32,
        "fahrenheit_to_celsius": lambda f: (f - 32) * 5/9,
    }

    def convert(self, value: float, conversion: str) -> float:
        """Convert a value using the specified conversion."""
        if conversion not in self.CONVERSIONS:
            raise ValueError(f"Unknown conversion: {conversion}")

        factor = self.CONVERSIONS[conversion]

        if callable(factor):
            return factor(value)

        return value * factor

    def convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature between units."""
        # BUG: Missing Kelvin conversions
        if from_unit == to_unit:
            return value

        if from_unit == "C" and to_unit == "F":
            return value * 9/5 + 32
        elif from_unit == "F" and to_unit == "C":
            return (value - 32) * 5/9
        elif from_unit == "C" and to_unit == "K":
            return value + 273.15
        elif from_unit == "K" and to_unit == "C":
            return value - 273.15
        # BUG: Missing F to K and K to F conversions
        # Falls through to implicit None return
        else:
            # BUG: Returns None instead of raising exception
            return None


def factorial(n: int) -> int:
    """Calculate factorial."""
    # BUG: No check for negative numbers
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    # BUG: Off-by-one - fib(0) should be 0, fib(1) should be 1
    # But this returns fib(1) = 1, fib(2) = 1
    if n <= 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    # BUG: Doesn't handle n <= 1 correctly
    # 0 and 1 are not prime, but this returns True for 1
    if n < 2:
        return n == 1  # Wrong! 1 is not prime

    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False

    return True


def gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor."""
    # BUG: Doesn't handle negative numbers
    while b:
        a, b = b, a % b
    return a
