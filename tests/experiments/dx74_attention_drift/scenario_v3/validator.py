"""
Validation module for various data types.
"""
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

T = TypeVar('T')


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(is_valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, error: str) -> "ValidationResult":
        return cls(is_valid=False, errors=[error], warnings=[])


class StringValidator:
    """Validates string values."""

    def validate_length(
        self,
        value: str,
        min_length: int = 0,
        max_length: int = None
    ) -> ValidationResult:
        """Validate string length."""
        if len(value) < min_length:
            return ValidationResult.failure(
                f"String too short: {len(value)} < {min_length}"
            )

        # BUG: Wrong comparison - should be > not >=
        if max_length and len(value) >= max_length:
            return ValidationResult.failure(
                f"String too long: {len(value)} >= {max_length}"
            )

        return ValidationResult.success()

    def validate_pattern(self, value: str, pattern: str) -> ValidationResult:
        """Validate string matches pattern."""
        if not re.match(pattern, value):
            return ValidationResult.failure(
                f"String does not match pattern: {pattern}"
            )
        return ValidationResult.success()

    def validate_email(self, email: str) -> ValidationResult:
        """Validate email format."""
        # BUG: Overly permissive regex - allows invalid emails
        pattern = r".+@.+\..+"
        return self.validate_pattern(email, pattern)

    def validate_phone(self, phone: str) -> ValidationResult:
        """Validate phone number format."""
        # Remove common separators
        digits_only = re.sub(r"[\s\-\(\)]", "", phone)

        # BUG: Wrong length check - should be 10-15, not exactly 10
        if len(digits_only) != 10:
            return ValidationResult.failure("Invalid phone number length")

        if not digits_only.isdigit():
            return ValidationResult.failure("Phone must contain only digits")

        return ValidationResult.success()


class NumberValidator:
    """Validates numeric values."""

    def validate_range(
        self,
        value: float,
        min_value: float = None,
        max_value: float = None
    ) -> ValidationResult:
        """Validate number is within range."""
        # BUG: Logic error - should use 'and' not 'or' for range check
        # Current logic: if min set OR max set, do checks
        # Should be: if min set, check min; if max set, check max
        if min_value is not None or max_value is not None:
            if value < min_value:
                return ValidationResult.failure(
                    f"Value {value} below minimum {min_value}"
                )
            if value > max_value:
                return ValidationResult.failure(
                    f"Value {value} above maximum {max_value}"
                )

        return ValidationResult.success()

    def validate_positive(self, value: float) -> ValidationResult:
        """Validate number is positive."""
        # BUG: Should be > 0, not >= 0 for "positive"
        # Zero is not positive
        if value >= 0:
            return ValidationResult.success()
        return ValidationResult.failure("Value must be positive")

    def validate_integer(self, value: float) -> ValidationResult:
        """Validate value is an integer."""
        if value != int(value):
            return ValidationResult.failure("Value must be an integer")
        return ValidationResult.success()

    def validate_percentage(self, value: float) -> ValidationResult:
        """Validate value is a valid percentage (0-100)."""
        # BUG: Doesn't check upper bound 100
        if value < 0:
            return ValidationResult.failure("Percentage cannot be negative")
        return ValidationResult.success()


class DateValidator:
    """Validates date values."""

    def validate_not_future(self, value: date) -> ValidationResult:
        """Validate date is not in the future."""
        if value > date.today():
            return ValidationResult.failure("Date cannot be in the future")
        return ValidationResult.success()

    def validate_not_past(self, value: date) -> ValidationResult:
        """Validate date is not in the past."""
        # BUG: Should use < not <=, today is not "past"
        if value <= date.today():
            return ValidationResult.failure("Date cannot be in the past")
        return ValidationResult.success()

    def validate_range(
        self,
        value: date,
        min_date: date = None,
        max_date: date = None
    ) -> ValidationResult:
        """Validate date is within range."""
        if min_date and value < min_date:
            return ValidationResult.failure(
                f"Date before minimum: {value} < {min_date}"
            )

        if max_date and value > max_date:
            return ValidationResult.failure(
                f"Date after maximum: {value} > {max_date}"
            )

        return ValidationResult.success()

    def validate_weekday(self, value: date) -> ValidationResult:
        """Validate date is a weekday."""
        # BUG: weekday() returns 0-4 for Mon-Fri, 5-6 for Sat-Sun
        # This logic is inverted
        if value.weekday() < 5:
            return ValidationResult.failure("Date must be a weekday")
        return ValidationResult.success()


class CollectionValidator:
    """Validates collections."""

    def validate_not_empty(self, collection: list | dict | set) -> ValidationResult:
        """Validate collection is not empty."""
        if not collection:
            return ValidationResult.failure("Collection cannot be empty")
        return ValidationResult.success()

    def validate_length(
        self,
        collection: list,
        min_length: int = 0,
        max_length: int = None
    ) -> ValidationResult:
        """Validate collection length."""
        if len(collection) < min_length:
            return ValidationResult.failure(
                f"Collection too short: {len(collection)} < {min_length}"
            )

        if max_length and len(collection) > max_length:
            return ValidationResult.failure(
                f"Collection too long: {len(collection)} > {max_length}"
            )

        return ValidationResult.success()

    def validate_unique(self, collection: list) -> ValidationResult:
        """Validate all elements are unique."""
        # BUG: Doesn't handle unhashable elements (like dicts)
        if len(collection) != len(set(collection)):
            return ValidationResult.failure("Collection contains duplicates")
        return ValidationResult.success()

    def validate_all_match(
        self,
        collection: list,
        predicate: Callable[[Any], bool]
    ) -> ValidationResult:
        """Validate all elements match predicate."""
        for i, item in enumerate(collection):
            if not predicate(item):
                return ValidationResult.failure(
                    f"Element at index {i} does not match predicate"
                )
        return ValidationResult.success()


class CompositeValidator(Generic[T]):
    """Combines multiple validators."""

    def __init__(self):
        self.validators: list[Callable[[T], ValidationResult]] = []

    def add_validator(self, validator: Callable[[T], ValidationResult]):
        """Add a validator to the chain."""
        self.validators.append(validator)
        return self  # For chaining

    def validate(self, value: T) -> ValidationResult:
        """Run all validators."""
        all_errors = []
        all_warnings = []

        for validator in self.validators:
            result = validator(value)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

            # BUG: Should continue checking all validators
            # but breaks on first failure, missing other errors
            if not result.is_valid:
                break

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )


class SchemaValidator:
    """Validates objects against a schema."""

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, obj: dict) -> ValidationResult:
        """Validate object against schema."""
        errors = []

        for field, rules in self.schema.items():
            value = obj.get(field)

            # Check required
            if rules.get("required", False) and value is None:
                errors.append(f"Missing required field: {field}")
                continue

            if value is None:
                continue

            # Check type
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(
                    f"Invalid type for {field}: expected {expected_type.__name__}"
                )

            # BUG: Doesn't validate nested objects recursively
            # If rules has "schema" for nested validation, it's ignored

        # BUG: Doesn't check for extra fields not in schema
        # Should warn or error on unexpected fields

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[]
        )


def create_email_validator() -> CompositeValidator[str]:
    """Create a validator for email addresses."""
    validator = CompositeValidator[str]()
    string_validator = StringValidator()

    validator.add_validator(
        lambda v: string_validator.validate_length(v, min_length=5, max_length=254)
    )
    validator.add_validator(
        lambda v: string_validator.validate_email(v)
    )

    return validator


def create_age_validator() -> CompositeValidator[int]:
    """Create a validator for age values."""
    validator = CompositeValidator[int]()
    number_validator = NumberValidator()

    # BUG: Uses validate_positive which allows 0
    # Age should be > 0
    validator.add_validator(
        lambda v: number_validator.validate_positive(v)
    )
    validator.add_validator(
        lambda v: number_validator.validate_range(v, max_value=150)
    )

    return validator


def validate_config(config: dict) -> ValidationResult:
    """Validate a configuration dictionary."""
    required_keys = ["name", "version", "settings"]
    errors = []

    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required config key: {key}")

    if "version" in config:
        version = config["version"]
        # BUG: Doesn't validate version format properly
        # Just checks it's a string, not semver format
        if not isinstance(version, str):
            errors.append("Version must be a string")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=[]
    )
