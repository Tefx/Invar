"""Lookup and content extraction helpers for parsed markdown TOC."""

from __future__ import annotations

from deal import post, pre
from invar_runtime import skip_property_test

from invar.core.doc_parser_core import Section, _normalize_for_fuzzy


@pre(lambda sections, target_line: isinstance(sections, list) and target_line >= 1)
@post(lambda result: result is None or isinstance(result, Section))
def _find_by_line(sections: list[Section], target_line: int) -> Section | None:
    """Find section by line number.

    Examples:
        >>> s = Section("A", "a", 1, 5, 10, 100, "a", [])
        >>> _find_by_line([s], 5).title
        'A'
        >>> _find_by_line([s], 1) is None
        True
        >>> _find_by_line([], 5) is None
        True
    """
    for section in sections:
        if section.line_start == target_line:
            return section
        found = _find_by_line(section.children, target_line)
        if found:
            return found
    return None


@pre(lambda sections, path: isinstance(sections, list) and len(path) > 0 and path.startswith("#"))
@post(lambda result: result is None or isinstance(result, Section))
def _find_by_index(sections: list[Section], path: str) -> Section | None:
    """Find section by index path (#0/#1/#2).

    Examples:
        >>> s = Section("A", "a", 1, 1, 10, 100, "a", [
        ...     Section("B", "b", 2, 3, 8, 50, "a/b", [])
        ... ])
        >>> _find_by_index([s], "#0").title
        'A'
        >>> _find_by_index([s], "#0/#0").title
        'B'
        >>> _find_by_index([s], "#1") is None
        True
        >>> _find_by_index([], "#0") is None
        True
    """
    parts = path.split("/")
    current_list = sections

    for i, part in enumerate(parts):
        if not part.startswith("#"):
            return None
        try:
            idx = int(part[1:])
        except ValueError:
            return None

        if idx < 0 or idx >= len(current_list):
            return None

        section = current_list[idx]
        if i == len(parts) - 1:
            return section
        current_list = section.children

    return None


@skip_property_test("crosshair_incompatible: Calls _normalize_for_fuzzy with Unicode validation")
@pre(lambda sections, path: isinstance(sections, list) and len(path) > 0)
@post(lambda result: result is None or isinstance(result, Section))
def _find_by_slug_or_fuzzy(sections: list[Section], path: str) -> Section | None:
    """Find section by slug path or fuzzy match.

    Examples:
        >>> s = Section("Intro", "intro", 1, 1, 10, 100, "intro", [
        ...     Section("Overview", "overview", 2, 3, 8, 50, "intro/overview", [])
        ... ])
        >>> _find_by_slug_or_fuzzy([s], "intro/overview").title
        'Overview'
        >>> _find_by_slug_or_fuzzy([s], "over").title
        'Overview'
        >>> _find_by_slug_or_fuzzy([s], "nonexistent") is None
        True
        >>> _find_by_slug_or_fuzzy([], "anything") is None
        True
    """
    path_lower = path.lower()

    def find_exact(secs: list[Section], remaining_path: str) -> Section | None:
        if "/" in remaining_path:
            first, rest = remaining_path.split("/", 1)
            for sec in secs:
                if sec.slug == first:
                    return find_exact(sec.children, rest)
            return None
        for sec in secs:
            if sec.slug == remaining_path:
                return sec
        return None

    exact = find_exact(sections, path_lower)
    if exact:
        return exact

    def find_fuzzy(secs: list[Section]) -> Section | None:
        normalized_path = _normalize_for_fuzzy(path)
        for sec in secs:
            normalized_slug = _normalize_for_fuzzy(sec.slug)
            normalized_title = _normalize_for_fuzzy(sec.title)
            if normalized_path in normalized_slug or normalized_path in normalized_title:
                return sec
            found = find_fuzzy(sec.children)
            if found:
                return found
        return None

    return find_fuzzy(sections)


@skip_property_test("crosshair_incompatible: Calls _find_by_slug_or_fuzzy with Unicode validation")
@pre(lambda sections, path: isinstance(sections, list) and len(path) > 0)
@post(lambda result: result is None or isinstance(result, Section))
def find_section(sections: list[Section], path: str) -> Section | None:
    """Find section by path (slug, fuzzy, index, or line anchor).

    Path formats:
    - Slug path: "requirements/functional/auth" (case-insensitive)
    - Fuzzy: "auth" (matches first containing section)
    - Index: "#0/#1" (0-indexed positional)
    - Line anchor: "@48" (section starting at line 48)

    Examples:
        >>> sections = [
        ...     Section("Intro", "intro", 1, 1, 10, 100, "intro", [
        ...         Section("Overview", "overview", 2, 3, 8, 50, "intro/overview", [])
        ...     ])
        ... ]
        >>> find_section(sections, "intro/overview").title
        'Overview'
        >>> find_section(sections, "over").title
        'Overview'
        >>> find_section(sections, "#0/#0").title
        'Overview'
        >>> find_section(sections, "@3").title
        'Overview'
        >>> find_section(sections, "nonexistent") is None
        True
    """
    if path.startswith("@"):
        try:
            target_line = int(path[1:])
            return _find_by_line(sections, target_line)
        except ValueError:
            return None

    if path.startswith("#"):
        return _find_by_index(sections, path)

    return _find_by_slug_or_fuzzy(sections, path)


@pre(lambda section: section.line_end >= section.line_start)
@pre(lambda section: section.line_start >= 1)
@post(lambda result: result >= 1)
def _get_last_line(section: Section) -> int:
    """Get the last line number of a section, including all descendants.

    Examples:
        >>> s = Section("Title", "title", 1, 1, 5, 100, "title", [])
        >>> _get_last_line(s)
        5
        >>> parent = Section("Parent", "parent", 1, 1, 4, 100, "parent", [
        ...     Section("Child", "child", 2, 5, 8, 50, "parent/child", [])
        ... ])
        >>> _get_last_line(parent)
        8
    """
    if not section.children:
        return section.line_end
    return _get_last_line(section.children[-1])


@pre(
    lambda source, section, include_children=True: (
        len(source) > 0
        and isinstance(include_children, bool)
        and section.line_start >= 1
        and section.line_end >= section.line_start
        and section.line_end <= len(source.split("\n"))
    )
)
def extract_content(source: str, section: Section, include_children: bool = True) -> str:
    """Extract section content from source.

    Returns the content from line_start to line_end (1-indexed, inclusive).
    When include_children=False, stops at first child heading.
    When include_children=True, includes all descendant sections.

    Examples:
        >>> source = "# Title\\n\\nParagraph one.\\n\\nParagraph two."
        >>> section = Section("Title", "title", 1, 1, 5, 50, "title", [])
        >>> content = extract_content(source, section)
        >>> "# Title" in content
        True
        >>> "Paragraph one" in content
        True

        >>> parent = Section("Parent", "parent", 1, 1, 4, 100, "parent", [
        ...     Section("Child", "child", 2, 3, 4, 50, "parent/child", [])
        ... ])
        >>> src = "# Parent\\nIntro\\n## Child\\nBody"
        >>> extract_content(src, parent, include_children=False)
        '# Parent\\nIntro'
        >>> extract_content(src, parent, include_children=True)
        '# Parent\\nIntro\\n## Child\\nBody'
    """
    lines = source.split("\n")
    start_idx = section.line_start - 1

    if include_children:
        end_idx = _get_last_line(section)
    elif not section.children:
        end_idx = section.line_end
    else:
        end_idx = section.children[0].line_start - 1

    return "\n".join(lines[start_idx:end_idx])
