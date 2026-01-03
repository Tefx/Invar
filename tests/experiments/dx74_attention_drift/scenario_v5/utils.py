"""
Utility functions module.
This is a CONTROL file - contains NO intentional bugs.
Used to verify false positive rates in review strategies.
"""
import re
from datetime import datetime
from typing import Any, TypeVar


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


T = TypeVar('T')


# =============================================================================
# STRING UTILITIES (Clean implementation)
# =============================================================================

@pre(lambda text: isinstance(text, str))
@post(lambda result: isinstance(result, str))
def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    >>> truncate("Hello World", 8)
    'Hello...'
    >>> truncate("Hi", 10)
    'Hi'
    >>> truncate("Hello", 5)
    'Hello'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


@pre(lambda text: isinstance(text, str))
@post(lambda result: isinstance(result, str))
def snake_to_camel(text: str) -> str:
    """
    Convert snake_case to camelCase.

    >>> snake_to_camel("hello_world")
    'helloWorld'
    >>> snake_to_camel("already")
    'already'
    >>> snake_to_camel("")
    ''
    """
    if not text:
        return text
    components = text.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


@pre(lambda text: isinstance(text, str))
@post(lambda result: isinstance(result, str))
def camel_to_snake(text: str) -> str:
    """
    Convert camelCase to snake_case.

    >>> camel_to_snake("helloWorld")
    'hello_world'
    >>> camel_to_snake("already")
    'already'
    >>> camel_to_snake("")
    ''
    """
    if not text:
        return text
    result = re.sub('([A-Z])', r'_\1', text).lower()
    return result.lstrip('_')


# =============================================================================
# LIST UTILITIES (Clean implementation)
# =============================================================================

@pre(lambda items: isinstance(items, list))
@post(lambda result: isinstance(result, list))
def flatten(items: list[list[T]]) -> list[T]:
    """
    Flatten nested list one level.

    >>> flatten([[1, 2], [3, 4]])
    [1, 2, 3, 4]
    >>> flatten([])
    []
    >>> flatten([[1]])
    [1]
    """
    return [item for sublist in items for item in sublist]


@pre(lambda items: isinstance(items, list))
@pre(lambda size: size > 0)
def chunk(items: list[T], size: int) -> list[list[T]]:
    """
    Split list into chunks of given size.

    >>> chunk([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
    >>> chunk([], 3)
    []
    >>> chunk([1], 5)
    [[1]]
    """
    return [items[i:i + size] for i in range(0, len(items), size)]


@pre(lambda items: isinstance(items, list))
@post(lambda result: isinstance(result, list))
def unique(items: list[T]) -> list[T]:
    """
    Remove duplicates while preserving order.

    >>> unique([1, 2, 2, 3, 1])
    [1, 2, 3]
    >>> unique([])
    []
    >>> unique([1])
    [1]
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# =============================================================================
# DICT UTILITIES (Clean implementation)
# =============================================================================

@pre(lambda d: isinstance(d, dict))
@pre(lambda keys: isinstance(keys, list))
def pick(d: dict[str, T], keys: list[str]) -> dict[str, T]:
    """
    Pick specified keys from dictionary.

    >>> pick({"a": 1, "b": 2, "c": 3}, ["a", "c"])
    {'a': 1, 'c': 3}
    >>> pick({}, ["a"])
    {}
    >>> pick({"a": 1}, [])
    {}
    """
    return {k: d[k] for k in keys if k in d}


@pre(lambda d: isinstance(d, dict))
@pre(lambda keys: isinstance(keys, list))
def omit(d: dict[str, T], keys: list[str]) -> dict[str, T]:
    """
    Omit specified keys from dictionary.

    >>> omit({"a": 1, "b": 2, "c": 3}, ["b"])
    {'a': 1, 'c': 3}
    >>> omit({}, ["a"])
    {}
    >>> omit({"a": 1}, [])
    {'a': 1}
    """
    return {k: v for k, v in d.items() if k not in keys}


def deep_get(d: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get value from nested dictionary using dot notation.

    >>> deep_get({"a": {"b": {"c": 1}}}, "a.b.c")
    1
    >>> deep_get({"a": 1}, "b", "default")
    'default'
    >>> deep_get({}, "a.b")
    """
    keys = path.split(".")
    result = d

    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default

    return result


# =============================================================================
# DATE UTILITIES (Clean implementation)
# =============================================================================

def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """
    Format datetime to string.

    >>> from datetime import datetime
    >>> format_date(datetime(2024, 1, 15))
    '2024-01-15'
    >>> format_date(datetime(2024, 12, 31), "%d/%m/%Y")
    '31/12/2024'
    """
    return dt.strftime(fmt)


def parse_date(text: str, fmt: str = "%Y-%m-%d") -> datetime | None:
    """
    Parse string to datetime.

    >>> parse_date("2024-01-15")
    datetime.datetime(2024, 1, 15, 0, 0)
    >>> parse_date("invalid")
    """
    try:
        return datetime.strptime(text, fmt)
    except ValueError:
        return None


# =============================================================================
# VALIDATION UTILITIES (Clean implementation)
# =============================================================================

def is_valid_email(email: str) -> bool:
    """
    Validate email format.

    >>> is_valid_email("test@example.com")
    True
    >>> is_valid_email("invalid")
    False
    >>> is_valid_email("")
    False
    """
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.

    >>> is_valid_url("https://example.com")
    True
    >>> is_valid_url("not-a-url")
    False
    >>> is_valid_url("")
    False
    """
    if not url:
        return False
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


# =============================================================================
# NUMBER UTILITIES (Clean implementation)
# =============================================================================

@pre(lambda value: isinstance(value, (int, float)))
@pre(lambda min_val: isinstance(min_val, (int, float)))
@pre(lambda max_val: isinstance(max_val, (int, float)))
@post(lambda result: isinstance(result, (int, float)))
def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp value to range.

    >>> clamp(5, 0, 10)
    5
    >>> clamp(-5, 0, 10)
    0
    >>> clamp(15, 0, 10)
    10
    """
    return max(min_val, min(value, max_val))


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers.

    >>> safe_divide(10, 2)
    5.0
    >>> safe_divide(10, 0)
    0.0
    >>> safe_divide(10, 0, -1)
    -1
    """
    if b == 0:
        return default
    return a / b
