"""
Timeout inference for CrossHair based on code characteristics.

Part of DX-12: Hypothesis as CrossHair fallback.
Extracted from hypothesis_strategies.py to reduce file size.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from deal import post, pre

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class TimeoutTier:
    """Timeout tier for CrossHair based on code characteristics."""

    name: str
    timeout: int
    description: str


TIMEOUT_TIERS = {
    "pure_python": TimeoutTier("pure_python", 10, "Pure Python, no external libs"),
    "stdlib_only": TimeoutTier("stdlib_only", 15, "Uses collections, itertools"),
    "numpy_pandas": TimeoutTier("numpy_pandas", 5, "Quick check, likely to skip"),
    "complex_nested": TimeoutTier("complex_nested", 30, "Deep recursion, many branches"),
}

# Libraries that CrossHair cannot handle well
LIBRARY_BLACKLIST = frozenset([
    "numpy", "pandas", "torch", "tensorflow", "scipy",
    "sklearn", "cv2", "PIL", "requests", "aiohttp",
])


@pre(lambda func: callable(func))
@post(lambda result: result > 0)  # Timeout must be positive
def infer_timeout(func: Callable) -> int:
    """
    Infer appropriate CrossHair timeout from function source.

    Args:
        func: The function to analyze

    Returns:
        Timeout in seconds

    >>> def pure_func(x: int) -> int: return x * 2
    >>> infer_timeout(pure_func)
    10
    """
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return TIMEOUT_TIERS["pure_python"].timeout

    # Check for blacklisted libraries
    for lib in LIBRARY_BLACKLIST:
        if re.search(rf"\b{lib}\b", source):
            return TIMEOUT_TIERS["numpy_pandas"].timeout

    # Count complexity indicators
    nesting_depth = _estimate_nesting_depth(source)
    branch_count = _count_branches(source)

    if nesting_depth > 4 or branch_count > 10:
        return TIMEOUT_TIERS["complex_nested"].timeout

    if _uses_only_stdlib(source):
        return TIMEOUT_TIERS["stdlib_only"].timeout

    return TIMEOUT_TIERS["pure_python"].timeout


@post(lambda result: result >= 0)  # Nesting depth is non-negative
def _estimate_nesting_depth(source: str) -> int:
    """Estimate maximum nesting depth from indentation."""
    max_indent = 0
    for line in source.split("\n"):
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(stripped)
            spaces = indent // 4  # Assuming 4-space indent
            max_indent = max(max_indent, spaces)
    return max_indent


@post(lambda result: result >= 0)  # Branch count is non-negative
def _count_branches(source: str) -> int:
    """Count branching statements (if, for, while, try)."""
    return len(re.findall(r"\b(if|for|while|try|elif|except)\b", source))


# @invar:allow missing_contract: Boolean predicate, empty string is valid input
def _uses_only_stdlib(source: str) -> bool:
    """Check if source only uses standard library."""
    stdlib_patterns = ["collections", "itertools", "functools", "typing", "dataclasses"]
    third_party_patterns = ["pandas", "numpy", "requests", "flask", "django"]

    has_stdlib = any(pat in source for pat in stdlib_patterns)
    has_third_party = any(pat in source for pat in third_party_patterns)

    return has_stdlib and not has_third_party
