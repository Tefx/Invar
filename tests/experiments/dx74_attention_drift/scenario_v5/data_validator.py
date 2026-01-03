"""
Data validation module.
Focus: Contract (A) and Doctest (B) issues.
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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
# CONTRACT ISSUES (A)
# =============================================================================

# BUG A-07: @pre(lambda data: True) - trivial precondition
@pre(lambda data: True)
def validate_data(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate data dictionary.

    >>> validate_data({"name": "John", "age": 25})
    (True, [])
    """
    errors = []
    if "name" not in data:
        errors.append("Missing name")
    if "age" not in data:
        errors.append("Missing age")
    return (len(errors) == 0, errors)


# BUG A-08: @pre doesn't check all required fields - incomplete contract
@pre(lambda user: "email" in user)  # Missing: name, age checks
def validate_user(user: dict[str, Any]) -> bool:
    """Validate user data."""
    required = ["email", "name", "age"]
    for field in required:
        if field not in user:
            return False
    return True


# BUG A-09: @post only checks type, not content - weak postcondition
@pre(lambda text: isinstance(text, str))
@post(lambda result: isinstance(result, str))  # Doesn't verify sanitization happened
def sanitize_text(text: str) -> str:
    """Sanitize text input."""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove special characters
    clean = re.sub(r'[<>&"\']', '', clean)
    return clean.strip()


# BUG A-10: No invariant for data consistency
class DataValidator:
    """Validates data against schema."""

    def __init__(self, schema: dict[str, type]):
        self.schema = schema
        self.validated_count = 0
        self.error_count = 0

    def validate(self, data: dict[str, Any]) -> bool:
        """Validate data against schema."""
        for field, field_type in self.schema.items():
            if field not in data:
                self.error_count += 1
                return False
            if not isinstance(data[field], field_type):
                self.error_count += 1
                return False

        self.validated_count += 1
        # Bug: no invariant that validated_count + error_count == total attempts
        return True


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

# BUG B-05: validate_email no doctests
def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# BUG B-06: validate_age no boundary tests
def validate_age(age: int) -> bool:
    """
    Validate age is within acceptable range.

    >>> validate_age(25)
    True
    >>> validate_age(150)
    False
    """
    # Missing: validate_age(0), validate_age(-1), validate_age(120)
    return 0 <= age <= 120


# BUG G-28: Validation can be skipped via exception
def validate_required_fields(data: dict[str, Any], required: list[str]) -> bool:
    """Validate all required fields are present."""
    try:
        for field in required:
            if field not in data:
                return False
            # Bug: if data[field] raises exception, validation is bypassed
            _ = data[field]
        return True
    except Exception:
        return True  # Bug: returns True on error, bypassing validation


# BUG B-07: validate_phone no invalid format test
def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    >>> validate_phone("+1-555-123-4567")
    True
    >>> validate_phone("555-123-4567")
    True
    """
    # Missing: test for "abc", "123", empty string
    if not phone:
        return False
    # Simple pattern for demo
    pattern = r'^[\d\s\-\+\(\)]+$'
    return bool(re.match(pattern, phone)) and len(phone) >= 7


# BUG F-15: File path not sanitized - path traversal
def validate_file_path(path: str) -> bool:
    """Validate file path."""
    # Bug: doesn't check for .. path traversal
    if not path:
        return False
    # Missing: check for "../" or "..\\"
    return True


# BUG B-08: sanitize_input only tests basic case
def sanitize_input(text: str) -> str:
    """
    Sanitize user input.

    >>> sanitize_input("Hello World")
    'Hello World'
    """
    # Missing: test for HTML, special chars, unicode, etc.
    if not text:
        return ""
    return text.strip()


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

# BUG E-10: Regex vulnerable to ReDoS
def validate_complex_pattern(text: str) -> bool:
    """Validate text against complex pattern."""
    # ReDoS vulnerable pattern: nested quantifiers
    pattern = r'^(a+)+$'
    try:
        return bool(re.match(pattern, text))
    except Exception:
        return False


# BUG G-39: Validation errors not aggregated
def validate_form(form_data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate form data."""
    if "email" not in form_data:
        return (False, "Missing email")  # Returns on first error

    if "password" not in form_data:
        return (False, "Missing password")  # Other errors not shown

    if not validate_email(form_data["email"]):
        return (False, "Invalid email")

    return (True, None)


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

# BUG G-10: Returns empty string on validation failure - silent failure
def safe_sanitize(text: str) -> str:
    """Safely sanitize text input."""
    try:
        return sanitize_text(text)
    except Exception:
        # Silent failure - returns empty instead of raising
        return ""


def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Validate data against JSON schema."""
    for field, requirements in schema.items():
        if requirements.get("required", False):
            if field not in data:
                return False

        if field in data:
            expected_type = requirements.get("type")
            if expected_type and not isinstance(data[field], expected_type):
                return False

            min_length = requirements.get("min_length")
            if min_length and len(str(data[field])) < min_length:
                return False

    return True


def validate_list_items(items: list[Any], item_validator) -> list[tuple[int, str]]:
    """Validate each item in list."""
    errors = []
    for i, item in enumerate(items):
        try:
            if not item_validator(item):
                errors.append((i, "Validation failed"))
        except Exception as e:
            errors.append((i, str(e)))
    return errors


def validate_nested_dict(data: dict[str, Any], path: str = "") -> list[str]:
    """Validate nested dictionary structure."""
    errors = []

    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key

        if value is None:
            errors.append(f"{current_path}: null value")
        elif isinstance(value, dict):
            errors.extend(validate_nested_dict(value, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    errors.extend(validate_nested_dict(item, f"{current_path}[{i}]"))

    return errors


def normalize_data(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize data values."""
    normalized = {}
    for key, value in data.items():
        # Normalize strings
        if isinstance(value, str):
            normalized[key] = value.strip().lower()
        # Normalize numbers
        elif isinstance(value, (int, float)):
            normalized[key] = float(value)
        else:
            normalized[key] = value
    return normalized
