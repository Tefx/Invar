"""
Markdown document parser for structured document queries.

DX-76: Parses markdown into a section tree for precise navigation.
Core module - pure logic, no I/O.
"""
# @invar:allow file_size: DX-77 Phase A adds Unicode fuzzy matching, extraction planned

from __future__ import annotations

import re
from dataclasses import dataclass, field

from deal import post, pre
from invar_runtime import skip_property_test
from markdown_it import MarkdownIt


@dataclass
class Section:
    """A document section (heading + content).

    Represents a heading and its content up to the next same-level or higher heading.

    Examples:
        >>> s = Section(
        ...     title="Introduction",
        ...     slug="introduction",
        ...     level=1,
        ...     line_start=1,
        ...     line_end=10,
        ...     char_count=500,
        ...     path="introduction",
        ... )
        >>> s.title
        'Introduction'
        >>> s.level
        1
    """

    title: str  # "Authentication"
    slug: str  # "authentication"
    level: int  # 1-6
    line_start: int  # 1-indexed
    line_end: int  # 1-indexed, inclusive
    char_count: int  # Content character count
    path: str  # "requirements/functional/authentication"
    children: list[Section] = field(default_factory=list)


@dataclass
class FrontMatter:
    """YAML front matter metadata.

    Examples:
        >>> fm = FrontMatter(line_start=1, line_end=5, content="title: Hello")
        >>> fm.line_start
        1
    """

    line_start: int  # 1-indexed
    line_end: int  # 1-indexed, inclusive
    content: str  # Raw YAML content


@dataclass
class DocumentToc:
    """Table of contents for a document.

    Examples:
        >>> toc = DocumentToc(sections=[], frontmatter=None)
        >>> toc.sections
        []
    """

    sections: list[Section]
    frontmatter: FrontMatter | None


@pre(lambda title: len(title) <= 1000)  # Reasonable max title length
@post(lambda result: result == "" or re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", result))
def _slugify(title: str) -> str:
    """Convert title to URL-friendly slug.

    Examples:
        >>> _slugify("Hello World")
        'hello-world'
        >>> _slugify("API Reference (v2)")
        'api-reference-v2'
        >>> _slugify("  Multiple   Spaces  ")
        'multiple-spaces'
        >>> _slugify("")
        ''
    """
    # Lowercase
    slug = title.lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    return slug


@skip_property_test("crosshair_incompatible: Unicode character validation conflicts with symbolic execution")  # type: ignore[untyped-decorator]
@pre(lambda text: len(text) <= 1000)
@post(lambda result: result == '' or all(c.isalnum() or c == '_' or ord(c) > 127 for c in result))
def _normalize_for_fuzzy(text: str) -> str:
    """
    Normalize text for Unicode-aware fuzzy matching.

    Removes punctuation and whitespace, converts ASCII to lowercase,
    preserves Unicode characters (Chinese, Japanese, etc.).

    Examples:
        >>> _normalize_for_fuzzy("Hello World")
        'helloworld'
        >>> _normalize_for_fuzzy("Phase B")
        'phaseb'
        >>> _normalize_for_fuzzy("验证计划")
        '验证计划'
        >>> _normalize_for_fuzzy("Phase B 验证计划")
        'phaseb验证计划'
        >>> _normalize_for_fuzzy("  Multiple   Spaces  ")
        'multiplespaces'
        >>> _normalize_for_fuzzy("")
        ''
        >>> _normalize_for_fuzzy("API (v2.0)")
        'apiv20'
    """
    # Convert ASCII to lowercase, keep Unicode as-is
    ascii_lower = ''.join(c.lower() if c.isascii() else c for c in text)
    # Remove non-word-chars, but keep Unicode letters/digits (via re.UNICODE)
    return re.sub(r'[^\w]', '', ascii_lower, flags=re.UNICODE)


@pre(lambda sections: all(1 <= s.level <= 6 for s in sections))  # Valid heading levels
@post(lambda result: all(1 <= s.level <= 6 for s in result))
def _build_section_tree(sections: list[Section]) -> list[Section]:
    """Build hierarchical tree from flat section list.

    Uses level to determine parent-child relationships.
    Updates path to include parent slugs.

    Examples:
        >>> s1 = Section("A", "a", 1, 1, 10, 100, "a", [])
        >>> s2 = Section("B", "b", 2, 5, 8, 50, "b", [])
        >>> tree = _build_section_tree([s1, s2])
        >>> len(tree)
        1
        >>> tree[0].children[0].title
        'B'
        >>> tree[0].children[0].path
        'a/b'

        >>> # Empty list
        >>> _build_section_tree([])
        []
    """
    if not sections:
        return []

    result: list[Section] = []
    stack: list[Section] = []

    for section in sections:
        # Pop sections from stack that are not parents of current
        while stack and stack[-1].level >= section.level:
            stack.pop()

        # Update path based on parent
        if stack:
            section.path = f"{stack[-1].path}/{section.slug}"
            stack[-1].children.append(section)
        else:
            result.append(section)

        stack.append(section)

    return result


@skip_property_test("external_io: hypothesis inspect module incompatibility with Python 3.14")  # type: ignore[untyped-decorator]
@pre(lambda source: len(source) <= 10_000_000)  # Max 10MB document
@post(lambda result: all(s.line_start >= 1 for s in result.sections))
@post(lambda result: all(s.line_end >= s.line_start for s in result.sections))
@post(lambda result: all(1 <= s.level <= 6 for s in result.sections))
def parse_toc(source: str) -> DocumentToc:
    """Parse markdown source into a section tree.

    Extracts headings and builds a hierarchical structure.
    Line numbers are 1-indexed for user display.

    Examples:
        >>> toc = parse_toc("# Hello\\n\\nWorld")
        >>> len(toc.sections)
        1
        >>> toc.sections[0].title
        'Hello'
        >>> toc.sections[0].slug
        'hello'
        >>> toc.sections[0].level
        1

        >>> # Nested headings
        >>> toc2 = parse_toc("# A\\n## B\\n## C\\n# D")
        >>> len(toc2.sections)
        2
        >>> toc2.sections[0].title
        'A'
        >>> len(toc2.sections[0].children)
        2
        >>> toc2.sections[0].children[0].title
        'B'

        >>> # Empty document
        >>> toc3 = parse_toc("")
        >>> len(toc3.sections)
        0

        >>> # Setext headings
        >>> toc4 = parse_toc("Title\\n=====\\n\\nSubtitle\\n--------")
        >>> toc4.sections[0].title
        'Title'
        >>> toc4.sections[0].level
        1
        >>> toc4.sections[0].children[0].title
        'Subtitle'
        >>> toc4.sections[0].children[0].level
        2

        >>> # Front matter
        >>> toc5 = parse_toc("---\\ntitle: Test\\n---\\n# Heading")
        >>> toc5.frontmatter is not None
        True
        >>> toc5.frontmatter.content
        'title: Test'
    """
    lines = source.split("\n")
    total_lines = len(lines)

    # Detect and extract front matter
    frontmatter = None
    content_start_line = 0  # 0-indexed

    if source.startswith("---\n") or source.startswith("---\r\n"):
        # Look for closing ---
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                fm_content = "\n".join(lines[1:i])
                frontmatter = FrontMatter(
                    line_start=1,
                    line_end=i + 1,  # 1-indexed, inclusive
                    content=fm_content,
                )
                content_start_line = i + 1
                break

    # Parse markdown (skip front matter if present)
    content_to_parse = "\n".join(lines[content_start_line:])
    md = MarkdownIt()
    tokens = md.parse(content_to_parse)

    # Extract headings
    headings: list[tuple[str, int, int, int]] = []  # (title, level, start, end)
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            token_map = token.map or [0, 1]
            # Adjust for front matter offset
            start_line = token_map[0] + content_start_line + 1  # 1-indexed
            end_line = token_map[1] + content_start_line  # 1-indexed

            # Next token should be inline with content
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                title = tokens[i + 1].content or ""
                headings.append((title, level, start_line, end_line))
            i += 1
        i += 1

    # Build section tree
    if not headings:
        return DocumentToc(sections=[], frontmatter=frontmatter)

    # Calculate end lines for each section (until next heading or EOF)
    sections_flat: list[Section] = []
    for idx, (title, level, start, _) in enumerate(headings):
        # Line before next heading, or EOF
        end = headings[idx + 1][2] - 1 if idx + 1 < len(headings) else total_lines

        # Calculate char count
        section_lines = lines[start - 1 : end]  # Convert to 0-indexed
        char_count = sum(len(line) for line in section_lines)

        slug = _slugify(title)
        sections_flat.append(
            Section(
                title=title,
                slug=slug,
                level=level,
                line_start=start,
                line_end=end,
                char_count=char_count,
                path=slug,  # Will be updated during tree building
                children=[],
            )
        )

    # Build tree from flat list
    root_sections = _build_section_tree(sections_flat)

    return DocumentToc(sections=root_sections, frontmatter=frontmatter)


@pre(lambda sections, target_line: target_line >= 1)
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
        # Search children
        found = _find_by_line(section.children, target_line)
        if found:
            return found
    return None


@pre(lambda sections, path: len(path) > 0 and path.startswith("#"))
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
        if i == len(parts) - 1:  # Last part
            return section
        current_list = section.children

    return None


@skip_property_test("crosshair_incompatible: Calls _normalize_for_fuzzy with Unicode validation")  # type: ignore[untyped-decorator]
@pre(lambda sections, path: len(path) > 0)
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

    # Try exact slug path match first
    def find_exact(secs: list[Section], remaining_path: str) -> Section | None:
        if "/" in remaining_path:
            first, rest = remaining_path.split("/", 1)
            for sec in secs:
                if sec.slug == first:
                    return find_exact(sec.children, rest)
            return None
        else:
            for sec in secs:
                if sec.slug == remaining_path:
                    return sec
            return None

    exact = find_exact(sections, path_lower)
    if exact:
        return exact

    # Fuzzy match with Unicode-aware normalization
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


@skip_property_test("crosshair_incompatible: Calls _find_by_slug_or_fuzzy with Unicode validation")  # type: ignore[untyped-decorator]
@pre(lambda sections, path: len(path) > 0)
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

        >>> # Slug path
        >>> s = find_section(sections, "intro/overview")
        >>> s.title
        'Overview'

        >>> # Fuzzy match
        >>> s2 = find_section(sections, "over")
        >>> s2.title
        'Overview'

        >>> # Index path
        >>> s3 = find_section(sections, "#0/#0")
        >>> s3.title
        'Overview'

        >>> # Line anchor
        >>> s4 = find_section(sections, "@3")
        >>> s4.title
        'Overview'

        >>> # Not found
        >>> find_section(sections, "nonexistent") is None
        True
    """
    # Line anchor: @48
    if path.startswith("@"):
        try:
            target_line = int(path[1:])
            return _find_by_line(sections, target_line)
        except ValueError:
            return None

    # Index path: #0/#1/#2
    if path.startswith("#"):
        return _find_by_index(sections, path)

    # Slug path or fuzzy match
    return _find_by_slug_or_fuzzy(sections, path)  # type: ignore[no-any-return]


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

    # Recursively find the last line of the last child
    last_child = section.children[-1]
    return _get_last_line(last_child)


@pre(lambda source, section, include_children=True: section.line_start >= 1)
@pre(lambda source, section, include_children=True: section.line_end >= section.line_start)
@pre(lambda source, section, include_children=True: section.line_end <= len(source.split("\n")))  # Bounds check
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

        >>> # Without children
        >>> parent = Section("Parent", "parent", 1, 1, 4, 100, "parent", [
        ...     Section("Child", "child", 2, 3, 4, 50, "parent/child", [])
        ... ])
        >>> src = "# Parent\\nIntro\\n## Child\\nBody"
        >>> extract_content(src, parent, include_children=False)
        '# Parent\\nIntro'

        >>> # With children
        >>> extract_content(src, parent, include_children=True)
        '# Parent\\nIntro\\n## Child\\nBody'
    """
    lines = source.split("\n")
    start_idx = section.line_start - 1

    if include_children:
        # Include all descendants
        end_idx = _get_last_line(section)
    elif not section.children:
        # No children to exclude
        end_idx = section.line_end
    else:
        # Stop before first child
        first_child_line = section.children[0].line_start
        end_idx = first_child_line - 1

    return "\n".join(lines[start_idx:end_idx])
