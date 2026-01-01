"""
Pattern Detector Registry (DX-61).

Central registry for all pattern detectors. Provides unified API
for running detection across multiple patterns.
"""

import ast
from functools import lru_cache

from deal import post, pre

from invar.core.patterns.detector import PatternDetector
from invar.core.patterns.p0_exhaustive import ExhaustiveMatchDetector
from invar.core.patterns.p0_literal import LiteralDetector
from invar.core.patterns.p0_newtype import NewTypeDetector
from invar.core.patterns.p0_nonempty import NonEmptyDetector
from invar.core.patterns.p0_validation import ValidationDetector
from invar.core.patterns.types import (
    Confidence,
    DetectionResult,
    PatternID,
    PatternSuggestion,
    Priority,
)


class PatternRegistry:
    """
    Registry for pattern detectors.

    Manages registration and execution of all pattern detectors.
    Provides filtering by priority and confidence levels.

    >>> registry = PatternRegistry()
    >>> len(registry.detectors) > 0
    True
    >>> PatternID.NEWTYPE in [d.pattern_id for d in registry.detectors]
    True
    """

    # @invar:allow missing_contract: __init__ takes only self, no inputs to validate
    def __init__(self) -> None:
        """Initialize with all P0 detectors."""
        self._detectors: list[PatternDetector] = [
            NewTypeDetector(),
            ValidationDetector(),
            NonEmptyDetector(),
            LiteralDetector(),
            ExhaustiveMatchDetector(),
        ]

    @property
    @post(lambda result: len(result) > 0)
    def detectors(self) -> list[PatternDetector]:
        """Get all registered detectors.

        >>> len(PatternRegistry().detectors) >= 5
        True
        """
        return self._detectors

    @post(lambda result: result is not None)
    def get_detectors_by_priority(self, priority: Priority) -> list[PatternDetector]:
        """
        Get detectors filtered by priority.

        >>> registry = PatternRegistry()
        >>> p0_detectors = registry.get_detectors_by_priority(Priority.P0)
        >>> len(p0_detectors) >= 5
        True
        """
        return [d for d in self._detectors if d.priority == priority]

    @pre(lambda self, file_path, source, min_confidence=None, priority_filter=None: len(file_path) > 0)
    @post(lambda result: result is not None)
    def detect_file(
        self,
        file_path: str,
        source: str,
        min_confidence: Confidence = Confidence.LOW,
        priority_filter: Priority | None = None,
    ) -> DetectionResult:
        """
        Run all detectors on a file's source code.

        Args:
            file_path: Path to the Python file (for location reporting)
            source: Source code to analyze
            min_confidence: Minimum confidence level to include
            priority_filter: Optional priority filter (None = all priorities)

        Returns:
            DetectionResult with all suggestions

        >>> registry = PatternRegistry()
        >>> code = '''
        ... def process(user_id: str, order_id: str, product_id: str):
        ...     pass
        ... '''
        >>> result = registry.detect_file("test.py", source=code)
        >>> result.has_suggestions
        True
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # Skip files with syntax errors
            return DetectionResult(
                file=file_path,
                suggestions=[],
                patterns_checked=[],
            )

        detectors = self._detectors
        if priority_filter is not None:
            detectors = self.get_detectors_by_priority(priority_filter)

        all_suggestions: list[PatternSuggestion] = []
        patterns_checked: list[PatternID] = []

        for detector in detectors:
            patterns_checked.append(detector.pattern_id)
            suggestions = detector.detect(tree, file_path)
            all_suggestions.extend(suggestions)

        # Filter by confidence
        result = DetectionResult(
            file=file_path,
            suggestions=all_suggestions,
            patterns_checked=patterns_checked,
        )

        filtered_suggestions = result.filter_by_confidence(min_confidence)

        return DetectionResult(
            file=file_path,
            suggestions=filtered_suggestions,
            patterns_checked=patterns_checked,
        )

    @post(lambda result: result is not None)
    def detect_sources(
        self,
        sources: list[tuple[str, str]],
        min_confidence: Confidence = Confidence.LOW,
        priority_filter: Priority | None = None,
    ) -> list[DetectionResult]:
        """
        Run detection on multiple sources.

        Args:
            sources: List of (file_path, source_code) tuples

        >>> registry = PatternRegistry()
        >>> results = registry.detect_sources([])
        >>> len(results)
        0
        """
        results = []
        for file_path, source in sources:
            result = self.detect_file(
                file_path,
                source,
                min_confidence=min_confidence,
                priority_filter=priority_filter,
            )
            results.append(result)
        return results

    @post(lambda result: result is not None)
    def format_suggestions(
        self, suggestions: list[PatternSuggestion], verbose: bool = False
    ) -> str:
        """
        Format suggestions for display.

        >>> from invar.core.patterns.types import PatternSuggestion, PatternID, Confidence, Priority, Location
        >>> registry = PatternRegistry()
        >>> suggestions = [
        ...     PatternSuggestion(
        ...         pattern_id=PatternID.NEWTYPE,
        ...         location=Location(file="test.py", line=10),
        ...         message="Test",
        ...         confidence=Confidence.HIGH,
        ...         priority=Priority.P0,
        ...         current_code="def f(a, b, c): pass",
        ...         suggested_pattern="NewType",
        ...         reference_file=".invar/examples/functional.py",
        ...         reference_pattern="Pattern 1",
        ...     )
        ... ]
        >>> output = registry.format_suggestions(suggestions)
        >>> "SUGGEST" in output
        True
        """
        if not suggestions:
            return ""

        if verbose:
            return "\n\n".join(s.format_for_guard() for s in suggestions)
        else:
            # Compact format
            lines = []
            for s in suggestions:
                lines.append(f"[{s.severity}] {s.location}: {s.message}")
            return "\n".join(lines)


@lru_cache(maxsize=1)
@post(lambda result: result is not None)
def get_registry() -> PatternRegistry:
    """
    Get the global pattern registry (thread-safe via lru_cache).

    >>> registry = get_registry()
    >>> isinstance(registry, PatternRegistry)
    True
    """
    return PatternRegistry()


@pre(lambda file_path, source, min_confidence=None: len(file_path) > 0)
@post(lambda result: result is not None)
def detect_patterns(
    file_path: str,
    source: str,
    min_confidence: Confidence = Confidence.LOW,
) -> DetectionResult:
    """
    Convenience function for pattern detection.

    >>> code = "def f(a: str, b: str, c: str): pass"
    >>> result = detect_patterns("test.py", source=code)
    >>> isinstance(result, DetectionResult)
    True
    """
    return get_registry().detect_file(file_path, source, min_confidence)
