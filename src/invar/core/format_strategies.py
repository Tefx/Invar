"""
Hypothesis strategies for format-driven property testing.

DX-28: Strategies that generate realistic test data matching
production formats, enabling property tests to catch semantic bugs.

These strategies are optional - they require Hypothesis to be installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from deal import post, pre
from invar_runtime import skip_property_test

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

try:
    from hypothesis import strategies as st

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


@skip_property_test("no_params: Zero-parameter function, property testing cannot vary inputs")
@post(lambda result: result is not None)
def crosshair_line() -> SearchStrategy[str]:
    """
    Generate a CrossHair counterexample line.

    Format: `file.py:line: error: ErrorType when calling func(args)`

    Examples:
        >>> if HYPOTHESIS_AVAILABLE:
        ...     line = crosshair_line().example()
        ...     assert ": error:" in line.lower()
    """
    if not HYPOTHESIS_AVAILABLE:
        raise ImportError("Hypothesis required: pip install hypothesis")

    filenames = st.from_regex(r"[a-z_]{1,20}\.py", fullmatch=True)
    line_nums = st.integers(min_value=1, max_value=1000)
    error_types = st.sampled_from(
        [
            "IndexError",
            "KeyError",
            "ValueError",
            "TypeError",
            "AssertionError",
            "ZeroDivisionError",
        ]
    )
    func_names = st.from_regex(r"[a-z_]{1,15}", fullmatch=True)
    args = st.from_regex(r"[a-z]=-?\d{1,5}", fullmatch=True)

    return st.builds(
        lambda f, ln, e, fn, a: f"{f}:{ln}: error: {e} when calling {fn}({a})",
        filenames,
        line_nums,
        error_types,
        func_names,
        args,
    )


@pre(lambda min_errors, max_errors: min_errors >= 0 and max_errors >= min_errors)
@post(lambda result: result is not None)
def crosshair_output(
    min_errors: int = 0,
    max_errors: int = 5,
) -> SearchStrategy[str]:
    """
    Generate complete CrossHair output with multiple lines.

    Args:
        min_errors: Minimum number of error lines
        max_errors: Maximum number of error lines

    Examples:
        >>> if HYPOTHESIS_AVAILABLE:
        ...     output = crosshair_output(min_errors=1, max_errors=3).example()
        ...     assert ": error:" in output.lower()
    """
    if not HYPOTHESIS_AVAILABLE:
        raise ImportError("Hypothesis required: pip install hypothesis")

    headers = st.sampled_from(
        [
            "Checking module...",
            "Running crosshair check...",
            "",
        ]
    )

    error_lines = st.lists(crosshair_line(), min_size=min_errors, max_size=max_errors)

    footers = st.sampled_from(
        [
            "",
            "Done.",
        ]
    )

    return st.builds(
        lambda h, errors, f: "\n".join([h, *errors, f]),
        headers,
        error_lines,
        footers,
    )


@pre(lambda pattern, min_occurrences, max_occurrences: len(pattern) > 0 and min_occurrences >= 0)
@post(lambda result: result is not None)
def text_with_pattern(
    pattern: str,
    min_occurrences: int = 1,
    max_occurrences: int = 5,
) -> SearchStrategy[str]:
    """
    Generate text that contains a specific pattern.

    Useful for testing extraction functions that should find
    occurrences of a pattern in text.

    Args:
        pattern: The pattern that must appear in the output
        min_occurrences: Minimum times pattern appears
        max_occurrences: Maximum times pattern appears

    Examples:
        >>> if HYPOTHESIS_AVAILABLE:
        ...     text = text_with_pattern(": error:", 2, 5).example()
        ...     assert text.count(": error:") >= 2
    """
    if not HYPOTHESIS_AVAILABLE:
        raise ImportError("Hypothesis required: pip install hypothesis")

    # Generate lines that contain the pattern
    prefix = st.from_regex(r"[a-z0-9_.]{1,30}", fullmatch=True)
    suffix = st.from_regex(r"[a-zA-Z0-9 ]{1,50}", fullmatch=True)

    pattern_line = st.builds(
        lambda p, s: f"{p}{pattern}{s}",
        prefix,
        suffix,
    )

    # Generate noise lines without the pattern
    noise_line = st.from_regex(r"[a-zA-Z0-9 ]{1,80}", fullmatch=True).filter(
        lambda x: pattern not in x
    )

    # Combine into full output
    pattern_lines = st.lists(
        pattern_line, min_size=min_occurrences, max_size=max_occurrences
    )
    noise_lines = st.lists(noise_line, min_size=0, max_size=10)

    # Note: Hypothesis will automatically explore different orderings of the lines,
    # so explicit shuffling is unnecessary. The concatenation order is sufficient.
    return st.builds(
        lambda p, n: "\n".join(p + n),
        pattern_lines,
        noise_lines,
    )


@pre(lambda pattern: len(pattern) > 0)
@post(lambda result: result is not None)
def extraction_test_case(
    pattern: str,
) -> SearchStrategy[tuple[str, int]]:
    """
    Generate (text, expected_count) pairs for testing extraction functions.

    The expected_count is the number of lines that should be extracted.

    Examples:
        >>> if HYPOTHESIS_AVAILABLE:
        ...     text, count = extraction_test_case(": error:").example()
        ...     actual = len([l for l in text.split("\\n") if ": error:" in l])
        ...     assert actual == count
    """
    if not HYPOTHESIS_AVAILABLE:
        raise ImportError("Hypothesis required: pip install hypothesis")

    count = st.integers(min_value=0, max_value=10)

    return count.flatmap(
        lambda c: st.tuples(
            text_with_pattern(pattern, min_occurrences=c, max_occurrences=c)
            if c > 0
            else st.just("no matches here"),
            st.just(c),
        )
    )
