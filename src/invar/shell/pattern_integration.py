"""
Pattern Detection Integration for Guard (DX-61).

Shell module: handles file I/O for pattern detection.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - used at runtime (path.exists, rglob, etc)

from deal import post, pre
from returns.result import Failure, Result, Success

from invar.core.models import RuleConfig, Severity, Violation
from invar.core.patterns import PatternSuggestion, detect_patterns
from invar.core.patterns.types import Confidence, Priority


# @shell_complexity: File collection and filtering requires multiple conditions
@pre(lambda path, files: path.exists())
@post(lambda result: isinstance(result, (Success, Failure)))
def run_pattern_detection(
    path: Path,
    files: list[Path] | None = None,
) -> Result[list[PatternSuggestion], str]:
    """
    Run pattern detection on source files.

    DX-61: Detects opportunities for functional patterns like
    NewType, Validation, NonEmpty, Literal, and ExhaustiveMatch.

    Args:
        path: Project root directory
        files: Optional list of specific files to check (None = all Python files)

    Returns:
        Success with list of suggestions, or Failure with error message

    @pre: path exists
    @post: returns Result type
    """
    suggestions: list[PatternSuggestion] = []

    try:
        # Collect Python files
        if files:
            python_files = [f for f in files if f.suffix == ".py"]
        else:
            python_files = list(path.rglob("*.py"))

        # Filter out test files and hidden directories
        python_files = [
            f for f in python_files
            if not any(part.startswith(".") for part in f.parts)
            and "test" not in f.name.lower()
            and "__pycache__" not in str(f)
        ]

        for file_path in python_files:
            try:
                source = file_path.read_text(encoding="utf-8")
                result = detect_patterns(str(file_path), source)
                suggestions.extend(result.suggestions)
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        return Success(suggestions)

    except Exception as e:
        return Failure(f"Pattern detection failed: {e}")


# @shell_orchestration: Converts pattern suggestions to violations for Guard output integration
@pre(lambda suggestion: suggestion is not None)
@post(lambda result: result.severity == Severity.SUGGEST)
def suggestion_to_violation(suggestion: PatternSuggestion) -> Violation:
    """
    Convert pattern suggestion to Guard violation format.

    DX-61: Enables pattern suggestions to appear in Guard output
    alongside other violations.

    Args:
        suggestion: Pattern suggestion from detector

    Returns:
        Violation with SUGGEST severity

    @pre: suggestion is not None
    @post: result has SUGGEST severity

    >>> from invar.core.patterns.types import (
    ...     PatternSuggestion, PatternID, Confidence, Priority, Location
    ... )
    >>> suggestion = PatternSuggestion(
    ...     pattern_id=PatternID.NEWTYPE,
    ...     location=Location(file="test.py", line=10),
    ...     message="3 str params",
    ...     confidence=Confidence.HIGH,
    ...     priority=Priority.P0,
    ...     current_code="def f(a, b, c): pass",
    ...     suggested_pattern="NewType",
    ...     reference_file=".invar/examples/functional.py",
    ...     reference_pattern="Pattern 1",
    ... )
    >>> violation = suggestion_to_violation(suggestion)
    >>> violation.severity == Severity.SUGGEST
    True
    >>> "Pattern 1" in violation.suggestion
    True
    """
    # Build suggestion text with reference
    suggestion_text = (
        f"{suggestion.suggested_pattern}\n"
        f"See: {suggestion.reference_file} - {suggestion.reference_pattern}"
    )

    return Violation(
        file=suggestion.location.file,
        line=suggestion.location.line,
        rule=f"pattern_{suggestion.pattern_id.value}",
        severity=Severity.SUGGEST,
        message=f"[{suggestion.confidence.value.upper()}] {suggestion.message}",
        suggestion=suggestion_text,
    )


# @shell_orchestration: Batch converts pattern suggestions to violations for Guard report
@pre(lambda suggestions: suggestions is not None)
@post(lambda result: all(v.severity == Severity.SUGGEST for v in result))
def suggestions_to_violations(
    suggestions: list[PatternSuggestion],
) -> list[Violation]:
    """
    Convert all pattern suggestions to violations.

    Args:
        suggestions: List of pattern suggestions

    Returns:
        List of violations with SUGGEST severity

    @pre: suggestions is not None
    @post: all results have SUGGEST severity
    """
    return [suggestion_to_violation(s) for s in suggestions]


# DX-61: Confidence level ordering for filtering
_CONFIDENCE_ORDER = {
    Confidence.LOW: 0,
    Confidence.MEDIUM: 1,
    Confidence.HIGH: 2,
}


# @shell_orchestration: Filters suggestions based on RuleConfig settings
# @shell_complexity: Multiple config filters (confidence, priority, exclusion) require branching
@pre(lambda suggestions, config: suggestions is not None and config is not None)
@post(lambda result: isinstance(result, list))
def filter_suggestions(
    suggestions: list[PatternSuggestion],
    config: RuleConfig,
) -> list[PatternSuggestion]:
    """
    Filter suggestions based on configuration.

    DX-61: Applies confidence, priority, and exclusion filters.

    Args:
        suggestions: List of pattern suggestions
        config: Rule configuration with pattern settings

    Returns:
        Filtered list of suggestions

    @pre: suggestions and config are not None
    @post: returns a list

    >>> from invar.core.patterns.types import (
    ...     PatternSuggestion, PatternID, Confidence, Priority, Location
    ... )
    >>> from invar.core.models import RuleConfig
    >>> config = RuleConfig(pattern_min_confidence="high")
    >>> low = PatternSuggestion(
    ...     pattern_id=PatternID.NEWTYPE,
    ...     location=Location(file="t.py", line=1),
    ...     message="msg", confidence=Confidence.LOW, priority=Priority.P0,
    ...     current_code="x", suggested_pattern="X", reference_file="f.py",
    ...     reference_pattern="P1"
    ... )
    >>> high = PatternSuggestion(
    ...     pattern_id=PatternID.VALIDATION,
    ...     location=Location(file="t.py", line=2),
    ...     message="msg", confidence=Confidence.HIGH, priority=Priority.P0,
    ...     current_code="x", suggested_pattern="X", reference_file="f.py",
    ...     reference_pattern="P1"
    ... )
    >>> result = filter_suggestions([low, high], config)
    >>> len(result)
    1
    >>> result[0].confidence == Confidence.HIGH
    True
    """
    # Parse minimum confidence level
    min_conf_str = config.pattern_min_confidence.lower()
    min_conf_map = {"low": Confidence.LOW, "medium": Confidence.MEDIUM, "high": Confidence.HIGH}
    min_confidence = min_conf_map.get(min_conf_str, Confidence.MEDIUM)
    min_conf_order = _CONFIDENCE_ORDER[min_confidence]

    # Parse allowed priorities (only P0 and P1 exist, skip invalid values)
    priority_map = {"P0": Priority.P0, "P1": Priority.P1}
    allowed_priorities = {
        priority_map[p] for p in config.pattern_priorities if p in priority_map
    }

    # Parse excluded patterns
    excluded_patterns = set(config.pattern_exclude)

    filtered = []
    for s in suggestions:
        # Check confidence threshold
        if _CONFIDENCE_ORDER[s.confidence] < min_conf_order:
            continue
        # Check priority filter
        if s.priority not in allowed_priorities:
            continue
        # Check exclusion list
        if s.pattern_id.value in excluded_patterns:
            continue
        filtered.append(s)

    return filtered
