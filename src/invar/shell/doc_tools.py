"""
Shell layer for document tools.

DX-76: File I/O operations for structured document queries.
Returns Result[T, E] for error handling.
"""

from pathlib import Path

from returns.result import Failure, Result, Success

from invar.core.doc_parser import (
    DocumentToc,
    Section,
    extract_content,
    find_section,
    parse_toc,
)


def read_toc(path: Path) -> Result[DocumentToc, str]:
    """Read and parse document table of contents.

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Hello\\n\\nWorld")
        ...     p = Path(f.name)
        >>> result = read_toc(p)
        >>> isinstance(result, Success)
        True
        >>> result.unwrap().sections[0].title
        'Hello'
        >>> p.unlink()
    """
    try:
        content = path.read_text(encoding="utf-8")
        toc = parse_toc(content)
        return Success(toc)
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")


# @shell_complexity: Multiple I/O error types require separate handling
def read_section(path: Path, section_path: str) -> Result[str, str]:
    """Read a specific section from a document.

    Args:
        path: Path to markdown file
        section_path: Section path (slug, fuzzy, index, or line anchor)

    Returns:
        Result containing section content or error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Title\\n\\nContent here")
        ...     p = Path(f.name)
        >>> result = read_section(p, "title")
        >>> isinstance(result, Success)
        True
        >>> "Title" in result.unwrap()
        True
        >>> p.unlink()
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")

    toc = parse_toc(content)
    section = find_section(toc.sections, section_path)

    if section is None:
        return Failure(f"Section not found: {section_path}")

    return Success(extract_content(content, section))


# @shell_complexity: Pattern matching + content filtering orchestration
def find_sections(
    path: Path, pattern: str, content_pattern: str | None = None
) -> Result[list[Section], str]:
    """Find sections matching a pattern.

    Args:
        path: Path to markdown file
        pattern: Title pattern (glob-style)
        content_pattern: Optional content search pattern

    Returns:
        Result containing list of matching sections

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Intro\\n\\n## Overview\\n\\n# Summary")
        ...     p = Path(f.name)
        >>> result = find_sections(p, "*")
        >>> isinstance(result, Success)
        True
        >>> len(result.unwrap()) >= 2
        True
        >>> p.unlink()
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")

    toc = parse_toc(content)

    # Collect all sections recursively
    def collect_all(sections: list[Section]) -> list[Section]:
        result: list[Section] = []
        for s in sections:
            result.append(s)
            result.extend(collect_all(s.children))
        return result

    all_sections = collect_all(toc.sections)

    # Filter by pattern
    import fnmatch

    matches = [s for s in all_sections if fnmatch.fnmatch(s.title.lower(), pattern.lower())]

    # Filter by content if specified
    if content_pattern:
        content_matches = []
        for s in matches:
            section_content = extract_content(content, s)
            if content_pattern.lower() in section_content.lower():
                content_matches.append(s)
        matches = content_matches

    return Success(matches)
