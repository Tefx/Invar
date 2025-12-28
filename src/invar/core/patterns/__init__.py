"""
Functional Pattern Detection (DX-61).

This module provides pattern detection for suggesting functional programming
improvements in Python code. Guard integrates with this module to provide
SUGGEST-level feedback when it detects opportunities for patterns like:

P0 (Core Patterns):
    - NewType: Semantic clarity for multiple same-type parameters
    - Validation: Error accumulation instead of fail-fast
    - NonEmpty: Compile-time non-empty guarantees
    - Literal: Type-safe finite value sets
    - ExhaustiveMatch: assert_never for enum matching

P1 (Extended Patterns - future):
    - SmartConstructor: Validation at construction time
    - StructuredError: Typed errors for programmatic handling

Usage:
    >>> from invar.core.patterns import detect_patterns
    >>> source = "def f(a: str, b: str, c: str): pass"
    >>> result = detect_patterns("test.py", source)
    >>> result.has_suggestions
    True

See .invar/examples/functional.py for pattern examples.
"""

from invar.core.patterns.registry import (
    PatternRegistry,
    detect_patterns,
    get_registry,
)
from invar.core.patterns.types import (
    Confidence,
    DetectionResult,
    Location,
    PatternID,
    PatternSuggestion,
    Priority,
)

__all__ = [
    "Confidence",
    "DetectionResult",
    "Location",
    "PatternID",
    "PatternRegistry",
    "PatternSuggestion",
    "Priority",
    "detect_patterns",
    "get_registry",
]
