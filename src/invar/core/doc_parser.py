"""Markdown document parser public API.

DX-76: Parses markdown into a section tree for precise navigation.
Core module - pure logic, no I/O.
"""
# mypy: disable-error-code=untyped-decorator

from __future__ import annotations

from invar.core.doc_parser_core import (
    DocumentToc,
    FrontMatter,
    Section,
    parse_toc,
)
from invar.core.doc_parser_query import extract_content, find_section

__all__ = [
    "DocumentToc",
    "FrontMatter",
    "Section",
    "extract_content",
    "find_section",
    "parse_toc",
]
