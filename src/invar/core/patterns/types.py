"""
Pattern Detection Types (DX-61).

Core types for the functional pattern guidance system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from deal import post, pre


class PatternID(str, Enum):
    """Unique identifier for each pattern."""

    # P0 - Core patterns
    NEWTYPE = "newtype"
    VALIDATION = "validation"
    NONEMPTY = "nonempty"
    LITERAL = "literal"
    EXHAUSTIVE = "exhaustive"

    # P1 - Extended patterns (future)
    SMART_CONSTRUCTOR = "smart_constructor"
    STRUCTURED_ERROR = "structured_error"


class Confidence(str, Enum):
    """Confidence level for pattern suggestions."""

    HIGH = "high"  # Strong signal, very likely applicable
    MEDIUM = "medium"  # Moderate signal, likely applicable
    LOW = "low"  # Weak signal, possibly applicable


class Priority(str, Enum):
    """Pattern priority tier."""

    P0 = "P0"  # Core patterns, always suggested
    P1 = "P1"  # Extended patterns, suggested when relevant


# Severity for Guard output
Severity = Literal["SUGGEST"]  # Pattern suggestions are always SUGGEST level


@dataclass(frozen=True)
class Location:
    """Source code location for a pattern opportunity."""

    file: str
    line: int
    column: int = 0
    end_line: int | None = None
    end_column: int | None = None

    @post(lambda result: ":" in result)  # Contains file:line separator
    def __str__(self) -> str:
        """Format as file:line for display."""
        return f"{self.file}:{self.line}"


@dataclass(frozen=True)
class PatternSuggestion:
    """
    A suggestion to apply a functional pattern.

    >>> from invar.core.patterns.types import PatternSuggestion, PatternID, Confidence, Priority, Location
    >>> suggestion = PatternSuggestion(
    ...     pattern_id=PatternID.NEWTYPE,
    ...     location=Location(file="src/api.py", line=42),
    ...     message="Consider using NewType for semantic clarity",
    ...     confidence=Confidence.HIGH,
    ...     priority=Priority.P0,
    ...     current_code="def process(user_id: str, order_id: str)",
    ...     suggested_pattern="NewType('UserId', str), NewType('OrderId', str)",
    ...     reference_file=".invar/examples/functional.py",
    ...     reference_pattern="Pattern 1: NewType for Semantic Clarity",
    ... )
    >>> suggestion.severity
    'SUGGEST'
    >>> "NewType" in suggestion.message
    True
    """

    pattern_id: PatternID
    location: Location
    message: str
    confidence: Confidence
    priority: Priority
    current_code: str
    suggested_pattern: str
    reference_file: str
    reference_pattern: str
    severity: Severity = "SUGGEST"

    @post(lambda result: "[SUGGEST]" in result and "Pattern:" in result)
    def format_for_guard(self) -> str:
        """
        Format suggestion for Guard output.

        >>> suggestion = PatternSuggestion(
        ...     pattern_id=PatternID.NEWTYPE,
        ...     location=Location(file="src/api.py", line=42),
        ...     message="3+ str params - consider NewType",
        ...     confidence=Confidence.HIGH,
        ...     priority=Priority.P0,
        ...     current_code="def f(a: str, b: str, c: str)",
        ...     suggested_pattern="NewType",
        ...     reference_file=".invar/examples/functional.py",
        ...     reference_pattern="Pattern 1",
        ... )
        >>> "SUGGEST" in suggestion.format_for_guard()
        True
        >>> "src/api.py:42" in suggestion.format_for_guard()
        True
        """
        return (
            f"[{self.severity}] {self.location}: {self.message}\n"
            f"  Pattern: {self.pattern_id.value} ({self.priority.value})\n"
            f"  Current: {self.current_code[:60]}{'...' if len(self.current_code) > 60 else ''}\n"
            f"  Suggest: {self.suggested_pattern}\n"
            f"  See: {self.reference_file} - {self.reference_pattern}"
        )


@dataclass(frozen=True)
class DetectionResult:
    """
    Result of running pattern detection on a file.

    >>> from invar.core.patterns.types import DetectionResult, PatternSuggestion, PatternID, Confidence, Priority, Location
    >>> result = DetectionResult(
    ...     file="src/api.py",
    ...     suggestions=[],
    ...     patterns_checked=[PatternID.NEWTYPE, PatternID.LITERAL],
    ... )
    >>> len(result.suggestions)
    0
    >>> PatternID.NEWTYPE in result.patterns_checked
    True
    """

    file: str
    suggestions: list[PatternSuggestion]
    patterns_checked: list[PatternID]

    @property
    @post(lambda result: isinstance(result, bool))
    def has_suggestions(self) -> bool:
        """Check if any suggestions were found.

        >>> DetectionResult(file="test.py", suggestions=[], patterns_checked=[]).has_suggestions
        False
        """
        return len(self.suggestions) > 0

    @pre(lambda self, min_confidence: min_confidence in Confidence)
    @post(lambda result: isinstance(result, list))
    def filter_by_confidence(self, min_confidence: Confidence) -> list[PatternSuggestion]:
        """
        Filter suggestions by minimum confidence level.

        >>> result = DetectionResult(file="test.py", suggestions=[], patterns_checked=[])
        >>> result.filter_by_confidence(Confidence.HIGH)
        []
        """
        confidence_order = {Confidence.HIGH: 2, Confidence.MEDIUM: 1, Confidence.LOW: 0}
        min_level = confidence_order[min_confidence]
        return [s for s in self.suggestions if confidence_order[s.confidence] >= min_level]
