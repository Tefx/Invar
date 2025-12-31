"""
Invar Core/Shell Separation Examples

Reference patterns for Core vs Shell architecture.
Managed by Invar - do not edit directly.
"""

from pathlib import Path

# For lambda-based contracts, use deal directly
# invar_runtime.pre/post are for Contract objects (NonEmpty, IsInstance, etc.)
from deal import post, pre
from returns.result import Failure, Result, Success

# =============================================================================
# CORE: Pure Logic (no I/O)
# =============================================================================
# Location: src/*/core/
# Requirements: @pre/@post, doctests, no I/O imports
# =============================================================================


# @invar:allow shell_result: Example file - demonstrates Core pattern
# @shell_orchestration: Example file - demonstrates Core pattern
@pre(lambda content: content is not None)  # Accepts any string including empty
@post(lambda result: all(line.strip() == line and line for line in result))  # No whitespace, non-empty
def parse_lines(content: str) -> list[str]:
    """
    Parse content into non-empty lines.

    >>> parse_lines("a\\nb\\nc")
    ['a', 'b', 'c']
    >>> parse_lines("")
    []
    >>> parse_lines("  \\n  ")  # Edge: whitespace only
    []
    """
    return [line.strip() for line in content.split("\n") if line.strip()]


# @invar:allow shell_result: Example file - demonstrates Core pattern
# @shell_orchestration: Example file - demonstrates Core pattern
@pre(lambda items: all(isinstance(i, str) for i in items))  # All items must be strings
@post(lambda result: all(v > 0 for v in result.values()))  # All counts are positive
def count_items(items: list[str]) -> dict[str, int]:
    """
    Count occurrences of each item.

    >>> sorted(count_items(['a', 'b', 'a']).items())
    [('a', 2), ('b', 1)]
    >>> count_items([])
    {}
    """
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


# =============================================================================
# SHELL: I/O Operations
# =============================================================================
# Location: src/*/shell/
# Requirements: Result[T, E] return type, calls Core for logic
# =============================================================================


def read_file(path: Path) -> Result[str, str]:
    """
    Read file content.

    Shell handles I/O, returns Result for error handling.
    """
    try:
        return Success(path.read_text())
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")


def count_lines_in_file(path: Path) -> Result[dict[str, int], str]:
    """
    Count lines in file - demonstrates Core/Shell integration.

    Shell reads file → Core parses content → Shell returns result.
    """
    # Shell: I/O operation
    content_result = read_file(path)

    if isinstance(content_result, Failure):
        return content_result

    content = content_result.unwrap()

    # Core: Pure logic (no I/O)
    lines = parse_lines(content)
    counts = count_items(lines)

    # Shell: Return result
    return Success(counts)


# =============================================================================
# ANTI-PATTERNS
# =============================================================================

# DON'T: I/O in Core
# def parse_file(path: Path):  # BAD: Path in Core
#     content = path.read_text()  # BAD: I/O in Core  # noqa: ERA001
#     return parse_lines(content)  # noqa: ERA001

# DO: Core receives content, not paths
# def parse_content(content: str):  # GOOD: receives data
#     return parse_lines(content)  # noqa: ERA001


# DON'T: Missing Result in Shell
# def load_config(path: Path) -> dict:  # BAD: no Result type
#     return json.loads(path.read_text())  # Exceptions not handled  # noqa: ERA001

# DO: Return Result[T, E]
# def load_config(path: Path) -> Result[dict, str]:  # GOOD
#     try:  # noqa: ERA001
#         return Success(json.loads(path.read_text()))  # noqa: ERA001
#     except Exception as e:  # noqa: ERA001
#         return Failure(str(e))  # noqa: ERA001
