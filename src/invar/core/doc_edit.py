"""
Markdown document editing functions.

DX-76 Phase A-2: Section-level document editing.
Core module - pure logic, no I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from deal import pre

if TYPE_CHECKING:
    from invar.core.doc_parser import Section


@pre(lambda source, section, new_content, keep_heading=True: section.line_start >= 1)
@pre(lambda source, section, new_content, keep_heading=True: section.line_end >= section.line_start)
@pre(lambda source, section, new_content, keep_heading=True: section.line_end <= len(source.split("\n")))
def replace_section(
    source: str,
    section: Section,
    new_content: str,
    keep_heading: bool = True,
) -> str:
    """Replace a section's content with new content.

    Args:
        source: Original document source
        section: Section to replace
        new_content: New content to insert
        keep_heading: If True, preserve the original heading line

    Returns:
        Modified document source

    Examples:
        >>> from invar.core.doc_parser import Section
        >>> source = "# Title\\n\\nOld content\\n\\n# Next"
        >>> section = Section("Title", "title", 1, 1, 3, 20, "title", [])
        >>> result = replace_section(source, section, "New content")
        >>> "# Title" in result
        True
        >>> "New content" in result
        True
        >>> "Old content" not in result
        True

        >>> # Without keeping heading
        >>> result2 = replace_section(source, section, "# New Title\\n\\nNew content", keep_heading=False)
        >>> "# New Title" in result2
        True
    """
    lines = source.split("\n")

    # Calculate line indices (0-indexed)
    if keep_heading:
        # Keep the heading line, replace content after it
        start_idx = section.line_start  # Skip heading (0-indexed after heading)
        end_idx = section.line_end  # 1-indexed inclusive
    else:
        # Replace everything including heading
        start_idx = section.line_start - 1  # 0-indexed
        end_idx = section.line_end  # 1-indexed inclusive

    # Split new content into lines
    new_lines = new_content.split("\n") if new_content else []

    # Build result
    result_lines = lines[:start_idx] + new_lines + lines[end_idx:]

    return "\n".join(result_lines)


@pre(lambda source, anchor, content, position="after": anchor.line_start >= 1)
@pre(lambda source, anchor, content, position="after": anchor.line_end <= len(source.split("\n")))
@pre(lambda source, anchor, content, position="after": position in ("before", "after", "first_child", "last_child"))
def insert_section(
    source: str,
    anchor: Section,
    content: str,
    position: Literal["before", "after", "first_child", "last_child"] = "after",
) -> str:
    """Insert new content relative to an anchor section.

    Args:
        source: Original document source
        anchor: Reference section for insertion
        content: Content to insert (should include heading if adding a section)
        position: Where to insert relative to anchor:
            - "before": Before the anchor section
            - "after": After the anchor section (including children)
            - "first_child": As first child of anchor
            - "last_child": As last child of anchor

    Returns:
        Modified document source

    Examples:
        >>> from invar.core.doc_parser import Section
        >>> source = "# Title\\n\\nContent\\n\\n# Next"
        >>> anchor = Section("Title", "title", 1, 1, 3, 20, "title", [])
        >>> result = insert_section(source, anchor, "\\n## Subsection\\n\\nNew text", "after")
        >>> "## Subsection" in result
        True

        >>> # Insert before
        >>> result2 = insert_section(source, anchor, "# Preface\\n\\nIntro\\n", "before")
        >>> result2.startswith("# Preface")
        True
    """
    lines = source.split("\n")
    content_lines = content.split("\n") if content else []

    if position == "before":
        # Insert before anchor's line_start
        insert_idx = anchor.line_start - 1  # 0-indexed
    elif position == "after":
        # Insert after anchor's line_end
        insert_idx = anchor.line_end  # After this line (0-indexed = line_end since it's 1-indexed)
    elif position == "first_child":
        # Insert right after the heading line
        insert_idx = anchor.line_start  # Right after heading (0-indexed)
    else:  # last_child
        # Insert before the end of the section (before next sibling or EOF)
        insert_idx = anchor.line_end  # At the end of section

    # Build result
    result_lines = lines[:insert_idx] + content_lines + lines[insert_idx:]

    return "\n".join(result_lines)


@pre(lambda source, section, include_children=True: section.line_start >= 1)
@pre(lambda source, section, include_children=True: section.line_end >= section.line_start)
@pre(lambda source, section, include_children=True: section.line_end <= len(source.split("\n")))
def delete_section(source: str, section: Section, include_children: bool = True) -> str:
    """Delete a section from the document.

    Removes content from line_start to line_end inclusive.
    When include_children=False, preserves child sections.

    Args:
        source: Original document source
        section: Section to delete
        include_children: If True, delete children too (default)

    Returns:
        Modified document source

    Examples:
        >>> from invar.core.doc_parser import Section
        >>> source = "# Keep\\n\\n# Delete\\n\\nContent\\n\\n# Also Keep"
        >>> section = Section("Delete", "delete", 1, 3, 5, 20, "delete", [])
        >>> result = delete_section(source, section)
        >>> "# Keep" in result
        True
        >>> "# Delete" not in result
        True
        >>> "# Also Keep" in result
        True

        >>> # Without children - preserves child sections
        >>> parent = Section("Parent", "parent", 1, 1, 4, 100, "parent", [
        ...     Section("Child", "child", 2, 3, 4, 50, "parent/child", [])
        ... ])
        >>> src = "# Parent\\nIntro\\n## Child\\nBody"
        >>> result = delete_section(src, parent, include_children=False)
        >>> "# Parent" not in result
        True
        >>> "## Child" in result
        True
    """
    lines = source.split("\n")
    start_idx = section.line_start - 1

    if include_children or not section.children:
        end_idx = section.line_end
    else:
        # Stop before first child
        first_child_line = section.children[0].line_start
        end_idx = first_child_line - 1

    result_lines = lines[:start_idx] + lines[end_idx:]

    return "\n".join(result_lines)
