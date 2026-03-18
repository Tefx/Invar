"""Helpers for escape-hatch exemption pattern parsing and matching."""

from __future__ import annotations

import fnmatch
from typing import Any

from deal import post, pre


@post(lambda result: result is None or isinstance(result, dict))
def parse_escape_exempt_patterns(config: dict[str, Any]) -> dict[str, list[str]] | None:
    """Parse escape_exempt_patterns from guard config.

    Supports both mapping shapes:
    - file_glob -> [rules]
    - rule -> [file_or_symbol_patterns]

    >>> parse_escape_exempt_patterns({"escape_exempt_patterns": {"dead_assign": ["legacy/*.py"]}})
    {'dead_assign': ['legacy/*.py']}
    >>> parse_escape_exempt_patterns({"escape_exempt_patterns": {"legacy/*.py": ["dead_assign"]}})
    {'legacy/*.py': ['dead_assign']}
    >>> parse_escape_exempt_patterns({}) is None
    True
    """
    raw = config.get("escape_exempt_patterns")
    if not isinstance(raw, dict):
        return None

    parsed: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, list):
            continue
        patterns = [str(item) for item in value if isinstance(item, str)]
        if patterns:
            parsed[key] = patterns

    return parsed if parsed else None


@pre(
    lambda file_path, symbol_name, pattern: (
        bool(file_path) and bool(pattern) and (symbol_name is None or isinstance(symbol_name, str))
    )
)
@post(lambda result: isinstance(result, bool))
def matches_file_symbol_pattern(file_path: str, symbol_name: str | None, pattern: str) -> bool:
    """Match a (file_path, symbol_name) pair against an exempt pattern.

    Pattern forms:
    - file-only glob: ``path/to/*.py``
    - file::symbol glob: ``path/to.py::symbol_*``

    Symbol matching accepts both dotted and slash-separated forms.

    Examples:
        >>> matches_file_symbol_pattern("cli/commands/run.py", None, "cli/commands/*.py")
        True
        >>> matches_file_symbol_pattern("mcp/server.py", "create_table", "mcp/server.py::create_*")
        True
        >>> matches_file_symbol_pattern(
        ...     "core/patterns/detector.py",
        ...     "PatternDetector.description",
        ...     "core/patterns/detector.py::*.description",
        ... )
        True
        >>> matches_file_symbol_pattern(
        ...     "core/patterns/detector.py",
        ...     "PatternDetector/description",
        ...     "core/patterns/detector.py::*.description",
        ... )
        True
    """
    normalized_file_path = file_path.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")

    if "::" not in normalized_pattern:
        return fnmatch.fnmatch(normalized_file_path, normalized_pattern)

    file_glob, symbol_glob = normalized_pattern.split("::", 1)
    if not fnmatch.fnmatch(normalized_file_path, file_glob):
        return False
    if symbol_name is None:
        return False

    symbol_variants = {
        symbol_name,
        symbol_name.replace("/", "."),
        symbol_name.replace(".", "/"),
    }
    pattern_variants = {
        symbol_glob,
        symbol_glob.replace("/", "."),
        symbol_glob.replace(".", "/"),
    }

    return any(
        fnmatch.fnmatch(symbol, glob) for symbol in symbol_variants for glob in pattern_variants
    )
