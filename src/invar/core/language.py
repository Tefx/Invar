"""Language detection for multi-language support.

This module provides language detection based on project marker files.
Part of LX-05 language-agnostic architecture.
"""

from deal import post, pre

# Supported languages for Invar verification
SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"python", "typescript"})

# Future languages (detected but not yet supported)
FUTURE_LANGUAGES: frozenset[str] = frozenset({"rust", "go"})

# All detectable languages
ALL_DETECTABLE: frozenset[str] = SUPPORTED_LANGUAGES | FUTURE_LANGUAGES


@pre(lambda markers: isinstance(markers, (set, frozenset)))
@post(lambda result: result in ALL_DETECTABLE)
def detect_language_from_markers(markers: frozenset[str]) -> str:
    """Detect project language from marker file names (pure logic).

    Args:
        markers: Set of marker file names present in the project root.

    Returns:
        Detected language identifier string.

    Examples:
        >>> detect_language_from_markers(frozenset({"pyproject.toml"}))
        'python'

        >>> detect_language_from_markers(frozenset({"setup.py", "README.md"}))
        'python'

        >>> detect_language_from_markers(frozenset({"tsconfig.json"}))
        'typescript'

        >>> detect_language_from_markers(frozenset({"package.json"}))
        'typescript'

        >>> detect_language_from_markers(frozenset({"Cargo.toml"}))
        'rust'

        >>> detect_language_from_markers(frozenset({"go.mod"}))
        'go'

        >>> detect_language_from_markers(frozenset())  # Empty defaults to python
        'python'

        >>> detect_language_from_markers(frozenset({"README.md"}))  # Unknown defaults to python
        'python'
    """
    # Detection order matters - first match wins
    if "pyproject.toml" in markers or "setup.py" in markers:
        return "python"
    if "tsconfig.json" in markers or "package.json" in markers:
        return "typescript"
    if "Cargo.toml" in markers:
        return "rust"
    if "go.mod" in markers:
        return "go"
    return "python"  # Default


@pre(lambda lang: isinstance(lang, str) and len(lang) > 0)
@post(lambda result: isinstance(result, bool))
def is_supported(lang: str) -> bool:
    """Check if a language is currently supported for verification.

    Args:
        lang: Language identifier to check.

    Returns:
        True if the language has full Invar support.

    Examples:
        >>> is_supported("python")
        True
        >>> is_supported("typescript")
        True
        >>> is_supported("rust")
        False
        >>> is_supported("go")
        False
    """
    return lang in SUPPORTED_LANGUAGES
