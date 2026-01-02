"""Utility functions with mixed planted bugs.

DX-74 Test Scenario - File 6/6
Bugs: 9 mixed issues (to reach 50 total)
"""

import random
import string
import time
from typing import Any


def generate_id(length: int = 8) -> str:
    """Generate a random ID.

    # BUG-42: Using weak random (not cryptographically secure)
    """
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def retry_operation(func: callable, max_retries: int = 3) -> Any:
    """Retry an operation on failure.

    # BUG-43: No exponential backoff
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # Fixed delay, should be exponential


def format_error(error: Exception) -> str:
    """Format an error for logging.

    # BUG-44: May expose sensitive information in stack trace
    """
    import traceback
    return traceback.format_exc()


def parse_boolean(value: str) -> bool:
    """Parse a boolean value from string.

    # BUG-45: Incomplete handling of falsy values
    """
    return value.lower() in ("true", "1", "yes")
    # Missing: explicit False for "false", "0", "no"


def memoize(func: callable) -> callable:
    """Simple memoization decorator.

    # BUG-46: Unbounded cache growth (memory leak)
    """
    cache = {}

    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]

    return wrapper


def truncate_string(s: str, max_length: int) -> str:
    """Truncate a string to maximum length.

    # BUG-47: No validation of max_length (negative values)
    """
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s


def deep_merge(dict1: dict, dict2: dict) -> dict:
    """Deep merge two dictionaries.

    # BUG-48: Doesn't handle list values properly
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def rate_limit(calls_per_second: float) -> callable:
    """Rate limiting decorator.

    # BUG-49: Not thread-safe
    """
    min_interval = 1.0 / calls_per_second
    last_call = [0.0]

    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper

    return decorator


def validate_dict_schema(data: dict, schema: dict) -> list[str]:
    """Validate a dictionary against a schema.

    # BUG-50: Only validates top-level keys, not nested structure
    """
    errors = []
    for key, expected_type in schema.items():
        if key not in data:
            errors.append(f"Missing required key: {key}")
        elif not isinstance(data[key], expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}")
    return errors


def safe_divide(a: float, b: float) -> float:
    """Safely divide two numbers.

    This one is OK - proper handling
    """
    if b == 0:
        return 0.0
    return a / b


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max.

    This one is OK - correct implementation
    """
    return max(min_val, min(value, max_val))


def flatten_list(nested: list) -> list:
    """Flatten a nested list.

    This one is OK - correct implementation
    """
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result
