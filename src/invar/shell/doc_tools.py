"""
Shell layer for document tools.

DX-76: File I/O operations for structured document queries.
Returns Result[T, E] for error handling.
"""

from pathlib import Path
from typing import Literal

from returns.result import Failure, Result, Success

from invar.core.doc_edit import (
    delete_section as core_delete_section,
)
from invar.core.doc_edit import (
    insert_section as core_insert_section,
)
from invar.core.doc_edit import (
    replace_section as core_replace_section,
)
from invar.core.doc_parser import (
    DocumentToc,
    Section,
    extract_content,
    find_section,
    parse_toc,
)


# @shell_complexity: Multiple I/O error types (OSError, IsADirectoryError, etc.) require separate handling
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
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")


# @shell_complexity: Multiple I/O error types require separate handling
def read_section(
    path: Path, section_path: str, include_children: bool = True
) -> Result[str, str]:
    """Read a specific section from a document.

    Args:
        path: Path to markdown file
        section_path: Section path (slug, fuzzy, index, or line anchor)
        include_children: If True, include child sections in output

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
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

    toc = parse_toc(content)
    section = find_section(toc.sections, section_path)

    if section is None:
        return Failure(f"Section not found: {section_path}")

    extracted = extract_content(content, section, include_children=include_children)
    return Success(extracted)


# @shell_complexity: Multiple I/O error types + batch section iteration
def read_sections_batch(
    path: Path,
    section_paths: list[str],
    include_children: bool = True
) -> Result[list[dict[str, str]], str]:
    """
    Read multiple sections from a document in one operation.

    Returns a list of dicts, each containing 'path' and 'content' keys.
    If any section fails to read, returns Failure with error message.

    Args:
        path: Path to markdown file
        section_paths: List of section paths (slug, fuzzy, index, or line anchor)
        include_children: If True, include child sections in output

    Returns:
        Result containing list of section dicts or error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# A\\n\\nContent A\\n\\n# B\\n\\nContent B\\n\\n# C\\n\\nContent C")
        ...     p = Path(f.name)
        >>> result = read_sections_batch(p, ["a", "b"])
        >>> isinstance(result, Success)
        True
        >>> sections = result.unwrap()
        >>> len(sections)
        2
        >>> sections[0]['path']
        'a'
        >>> "Content A" in sections[0]['content']
        True
        >>> p.unlink()
    """
    # Read file once
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

    # Parse TOC once
    toc = parse_toc(content)

    # Extract all requested sections
    results = []
    for section_path in section_paths:
        section = find_section(toc.sections, section_path)

        if section is None:
            return Failure(f"Section not found: {section_path}")

        extracted = extract_content(content, section, include_children=include_children)
        results.append({
            "path": section_path,
            "content": extracted
        })

    return Success(results)


# @shell_complexity: Pattern matching + content filtering orchestration
def find_sections(
    path: Path,
    pattern: str,
    content_pattern: str | None = None,
    level: int | None = None,
) -> Result[list[Section], str]:
    """Find sections matching a pattern.

    Args:
        path: Path to markdown file
        pattern: Title pattern (glob-style)
        content_pattern: Optional content search pattern
        level: Optional filter by heading level (1-6)

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
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

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

    # Filter by level if specified
    if level is not None:
        matches = [s for s in matches if s.level == level]

    # Filter by content if specified
    if content_pattern:
        content_matches = []
        for s in matches:
            section_content = extract_content(content, s)
            if content_pattern.lower() in section_content.lower():
                content_matches.append(s)
        matches = content_matches

    return Success(matches)


# DX-76 Phase A-2: Extended editing tools

# @shell_complexity: Read + find + edit + write orchestration
def replace_section_content(
    path: Path,
    section_path: str,
    new_content: str,
    keep_heading: bool = True,
) -> Result[dict[str, str | int], str]:
    """Replace a section's content in a document.

    Args:
        path: Path to markdown file
        section_path: Section path (slug, fuzzy, index, or line anchor)
        new_content: New content to replace the section with
        keep_heading: If True, preserve the original heading line

    Returns:
        Result containing info about the replacement or error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Title\\n\\nOld content\\n\\n# Next")
        ...     p = Path(f.name)
        >>> result = replace_section_content(p, "title", "New content\\n")
        >>> isinstance(result, Success)
        True
        >>> "New content" in p.read_text()
        True
        >>> p.unlink()
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

    toc = parse_toc(content)
    section = find_section(toc.sections, section_path)

    if section is None:
        return Failure(f"Section not found: {section_path}")

    old_content = extract_content(content, section)
    new_source = core_replace_section(content, section, new_content, keep_heading)

    try:
        path.write_text(new_source, encoding="utf-8")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except OSError as e:
        return Failure(f"OS error writing {path}: {e}")

    return Success({
        "old_content": old_content,
        "new_line_count": len(new_source.split("\n")),
    })


# @shell_complexity: Read + find + insert + write orchestration
def insert_section_content(
    path: Path,
    anchor_path: str,
    content: str,
    position: Literal["before", "after", "first_child", "last_child"] = "after",
) -> Result[dict[str, str | int], str]:
    """Insert new content relative to a section.

    Args:
        path: Path to markdown file
        anchor_path: Section path for the anchor
        content: Content to insert (should include heading if adding a section)
        position: Where to insert relative to anchor

    Returns:
        Result containing info about the insertion or error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Title\\n\\nContent")
        ...     p = Path(f.name)
        >>> result = insert_section_content(p, "title", "\\n## Subsection\\n\\nNew text", "after")
        >>> isinstance(result, Success)
        True
        >>> "## Subsection" in p.read_text()
        True
        >>> p.unlink()
    """
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

    toc = parse_toc(source)
    anchor = find_section(toc.sections, anchor_path)

    if anchor is None:
        return Failure(f"Section not found: {anchor_path}")

    new_source = core_insert_section(source, anchor, content, position)

    try:
        path.write_text(new_source, encoding="utf-8")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except OSError as e:
        return Failure(f"OS error writing {path}: {e}")

    return Success({
        "inserted_at": anchor.line_end if position == "after" else anchor.line_start,
        "new_line_count": len(new_source.split("\n")),
    })


# @shell_complexity: Read + find + delete + write orchestration
def delete_section_content(
    path: Path,
    section_path: str,
    include_children: bool = True,
) -> Result[dict[str, str | int], str]:
    """Delete a section from a document.

    Args:
        path: Path to markdown file
        section_path: Section path (slug, fuzzy, index, or line anchor)
        include_children: If True, delete child sections too

    Returns:
        Result containing info about the deletion or error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write("# Keep\\n\\n# Delete\\n\\nContent\\n\\n# Also Keep")
        ...     p = Path(f.name)
        >>> result = delete_section_content(p, "delete")
        >>> isinstance(result, Success)
        True
        >>> "# Delete" not in p.read_text()
        True
        >>> p.unlink()
    """
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except IsADirectoryError:
        return Failure(f"Path is a directory, not a file: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except UnicodeDecodeError:
        return Failure(f"Failed to decode file as UTF-8: {path}")
    except OSError as e:
        return Failure(f"OS error reading {path}: {e}")

    toc = parse_toc(source)
    section = find_section(toc.sections, section_path)

    if section is None:
        return Failure(f"Section not found: {section_path}")

    deleted_content = extract_content(source, section, include_children=include_children)
    new_source = core_delete_section(source, section, include_children=include_children)

    try:
        path.write_text(new_source, encoding="utf-8")
    except PermissionError:
        return Failure(f"Permission denied: {path}")
    except OSError as e:
        return Failure(f"OS error writing {path}: {e}")

    return Success({
        "deleted_content": deleted_content,
        "deleted_line_start": section.line_start,
        "deleted_line_end": section.line_end,
        "new_line_count": len(new_source.split("\n")),
    })
