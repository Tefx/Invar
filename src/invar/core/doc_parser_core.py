"""Core parsing types and functions for markdown documents."""

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

    title: str
    slug: str
    level: int
    line_start: int
    line_end: int
    char_count: int
    path: str
    children: list[Section] = field(default_factory=list)


@dataclass
class FrontMatter:
    """YAML front matter metadata.

    Examples:
        >>> fm = FrontMatter(line_start=1, line_end=5, content="title: Hello")
        >>> fm.line_start
        1
    """

    line_start: int
    line_end: int
    content: str


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


@pre(lambda title: len(title) <= 1000)
@post(lambda result: result == "" or bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", result)))
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
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


@skip_property_test(
    "crosshair_incompatible: Unicode character validation conflicts with symbolic execution"
)
@pre(lambda text: len(text) <= 1000)
@post(lambda result: result == "" or all(c.isalnum() or c == "_" or ord(c) > 127 for c in result))
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
    ascii_lower = "".join(c.lower() if c.isascii() else c for c in text)
    return re.sub(r"[^\w]", "", ascii_lower, flags=re.UNICODE)


@pre(lambda sections: all(1 <= s.level <= 6 for s in sections))
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

        >>> _build_section_tree([])
        []
    """
    if not sections:
        return []

    result: list[Section] = []
    stack: list[Section] = []

    for section in sections:
        while stack and stack[-1].level >= section.level:
            stack.pop()

        if stack:
            section.path = f"{stack[-1].path}/{section.slug}"
            stack[-1].children.append(section)
        else:
            result.append(section)

        stack.append(section)

    return result


@skip_property_test("external_io: hypothesis inspect module incompatibility with Python 3.14")
@pre(lambda source: len(source) <= 10_000_000)
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

        >>> toc2 = parse_toc("# A\\n## B\\n## C\\n# D")
        >>> len(toc2.sections)
        2
        >>> toc2.sections[0].title
        'A'
        >>> len(toc2.sections[0].children)
        2
        >>> toc2.sections[0].children[0].title
        'B'

        >>> toc3 = parse_toc("")
        >>> len(toc3.sections)
        0

        >>> toc4 = parse_toc("Title\\n=====\\n\\nSubtitle\\n--------")
        >>> toc4.sections[0].title
        'Title'
        >>> toc4.sections[0].level
        1
        >>> toc4.sections[0].children[0].title
        'Subtitle'
        >>> toc4.sections[0].children[0].level
        2

        >>> toc5 = parse_toc("---\\ntitle: Test\\n---\\n# Heading")
        >>> toc5.frontmatter is not None
        True
        >>> toc5.frontmatter.content
        'title: Test'
    """
    lines = source.split("\n")
    total_lines = len(lines)

    frontmatter = None
    content_start_line = 0

    if source.startswith("---\n") or source.startswith("---\r\n"):
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                fm_content = "\n".join(lines[1:i])
                frontmatter = FrontMatter(
                    line_start=1,
                    line_end=i + 1,
                    content=fm_content,
                )
                content_start_line = i + 1
                break

    content_to_parse = "\n".join(lines[content_start_line:])
    md = MarkdownIt()
    tokens = md.parse(content_to_parse)

    headings: list[tuple[str, int, int, int]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            level = int(token.tag[1])
            token_map = token.map or [0, 1]
            start_line = token_map[0] + content_start_line + 1
            end_line = token_map[1] + content_start_line

            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                title = tokens[i + 1].content or ""
                headings.append((title, level, start_line, end_line))
            i += 1
        i += 1

    if not headings:
        return DocumentToc(sections=[], frontmatter=frontmatter)

    sections_flat: list[Section] = []
    for idx, (title, level, start, _) in enumerate(headings):
        end = headings[idx + 1][2] - 1 if idx + 1 < len(headings) else total_lines
        section_lines = lines[start - 1 : end]
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
                path=slug,
                children=[],
            )
        )

    root_sections = _build_section_tree(sections_flat)
    return DocumentToc(sections=root_sections, frontmatter=frontmatter)
