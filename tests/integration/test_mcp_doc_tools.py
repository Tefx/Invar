"""
DX-76: Integration tests for MCP document tools.

Tests the MCP handlers for doc_toc, doc_read, doc_find, doc_replace,
doc_insert, and doc_delete to ensure they work end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invar.mcp.handlers import (
    _run_doc_delete,
    _run_doc_find,
    _run_doc_insert,
    _run_doc_read,
    _run_doc_read_many,
    _run_doc_replace,
    _run_doc_toc,
)

# Mark all tests in this module as async
pytestmark = pytest.mark.anyio


@pytest.fixture
def sample_markdown_file(tmp_path: Path) -> Path:
    """Create a sample markdown file for testing."""
    content = """# Main Title

Introduction paragraph.

## Section 1

Content for section 1.

### Subsection 1.1

Nested content.

## Section 2

Content for section 2.
"""
    md_file = tmp_path / "test.md"
    md_file.write_text(content)
    return md_file


class TestDocToc:
    """Test invar_doc_toc MCP handler."""


    async def test_doc_toc_basic(self, sample_markdown_file: Path):
        """Test basic TOC extraction."""
        args = {"file": str(sample_markdown_file)}
        result = await _run_doc_toc(args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Main Title" in result[0].text
        assert "Section 1" in result[0].text
        assert "Section 2" in result[0].text


    async def test_doc_toc_missing_file(self):
        """Test TOC extraction with missing file."""
        args = {"file": "/nonexistent/file.md"}
        result = await _run_doc_toc(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()


    async def test_doc_toc_no_file_arg(self):
        """Test TOC extraction without file argument."""
        args = {}
        result = await _run_doc_toc(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "required" in result[0].text.lower()


class TestDocRead:
    """Test invar_doc_read MCP handler."""


    async def test_doc_read_section_by_slug(self, sample_markdown_file: Path):
        """Test reading section by slug."""
        args = {
            "file": str(sample_markdown_file),
            "section": "section-1"
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        assert "Section 1" in result[0].text
        assert "Content for section 1" in result[0].text


    async def test_doc_read_section_not_found(self, sample_markdown_file: Path):
        """Test reading non-existent section."""
        args = {
            "file": str(sample_markdown_file),
            "section": "nonexistent"
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()


class TestDocFind:
    """Test invar_doc_find MCP handler."""


    async def test_doc_find_pattern(self, sample_markdown_file: Path):
        """Test finding sections by pattern."""
        args = {
            "file": str(sample_markdown_file),
            "pattern": "*Section*"
        }
        result = await _run_doc_find(args)

        assert len(result) == 1
        assert "Section 1" in result[0].text
        assert "Section 2" in result[0].text


    async def test_doc_find_no_matches(self, sample_markdown_file: Path):
        """Test finding with no matches."""
        args = {
            "file": str(sample_markdown_file),
            "pattern": "*Nonexistent*"
        }
        result = await _run_doc_find(args)

        assert len(result) == 1
        # Should return empty matches, not an error
        assert "matches" in result[0].text.lower()


class TestDocReplace:
    """Test invar_doc_replace MCP handler."""


    async def test_doc_replace_section(self, tmp_path: Path):
        """Test replacing section content."""
        # Create test file
        content = "# Title\n\nOld content\n\n# Next\n"
        md_file = tmp_path / "replace_test.md"
        md_file.write_text(content)

        args = {
            "file": str(md_file),
            "section": "title",
            "content": "New content\n",
            "keep_heading": True
        }
        result = await _run_doc_replace(args)

        assert len(result) == 1
        assert "success" in result[0].text.lower()

        # Verify file was modified
        new_content = md_file.read_text()
        assert "New content" in new_content
        assert "Old content" not in new_content
        assert "# Title" in new_content  # Heading preserved


    async def test_doc_replace_section_not_found(self, sample_markdown_file: Path):
        """Test replacing non-existent section."""
        args = {
            "file": str(sample_markdown_file),
            "section": "nonexistent",
            "content": "New content"
        }
        result = await _run_doc_replace(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()


class TestDocInsert:
    """Test invar_doc_insert MCP handler."""


    async def test_doc_insert_after(self, tmp_path: Path):
        """Test inserting content after a section."""
        content = "# Title\n\nContent\n\n# Next\n"
        md_file = tmp_path / "insert_test.md"
        md_file.write_text(content)

        args = {
            "file": str(md_file),
            "anchor": "title",
            "content": "## Inserted\n\nNew section\n",
            "position": "after"
        }
        result = await _run_doc_insert(args)

        assert len(result) == 1
        assert "success" in result[0].text.lower()

        # Verify insertion
        new_content = md_file.read_text()
        assert "## Inserted" in new_content
        assert "New section" in new_content


    async def test_doc_insert_invalid_position(self, sample_markdown_file: Path):
        """Test inserting with invalid position."""
        args = {
            "file": str(sample_markdown_file),
            "anchor": "section-1",
            "content": "New content",
            "position": "invalid"  # type: ignore[dict-item]
        }
        # Note: This might raise validation error at MCP level
        # or be caught by our handler
        result = await _run_doc_insert(args)

        assert len(result) == 1
        # Should return an error
        assert "Error" in result[0].text or "error" in result[0].text.lower()


class TestDocDelete:
    """Test invar_doc_delete MCP handler."""


    async def test_doc_delete_section(self, tmp_path: Path):
        """Test deleting a section."""
        content = "# Title\n\nContent\n\n## Delete Me\n\nGone\n\n# Next\n"
        md_file = tmp_path / "delete_test.md"
        md_file.write_text(content)

        args = {
            "file": str(md_file),
            "section": "delete-me"
        }
        result = await _run_doc_delete(args)

        assert len(result) == 1
        assert "success" in result[0].text.lower()

        # Verify deletion
        new_content = md_file.read_text()
        assert "Delete Me" not in new_content
        assert "Gone" not in new_content
        assert "# Title" in new_content
        assert "# Next" in new_content


    async def test_doc_delete_section_not_found(self, sample_markdown_file: Path):
        """Test deleting non-existent section."""
        args = {
            "file": str(sample_markdown_file),
            "section": "nonexistent"
        }
        result = await _run_doc_delete(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()


class TestErrorHandling:
    """Test error handling across all handlers."""


    async def test_path_validation_shell_chars(self):
        """Test that shell metacharacters are rejected."""
        dangerous_paths = [
            "; rm -rf /",
            "file.md && echo evil",
            "file.md | cat",
            "-flag.md"
        ]

        for dangerous_path in dangerous_paths:
            args = {"file": dangerous_path}
            result = await _run_doc_toc(args)

            assert len(result) == 1
            assert "Error" in result[0].text
            assert ("Invalid path" in result[0].text or "forbidden" in result[0].text.lower())


    async def test_directory_instead_of_file(self, tmp_path: Path):
        """Test handling directory path instead of file."""
        args = {"file": str(tmp_path)}
        result = await _run_doc_toc(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert ("directory" in result[0].text.lower() or "not a file" in result[0].text.lower())


    async def test_size_limit(self, tmp_path: Path):
        """Test that files exceeding size limit are rejected by @pre contract."""
        # Create a file larger than 10MB
        large_file = tmp_path / "large.md"
        large_content = "# Title\n" + ("x" * 11_000_000)
        large_file.write_text(large_content)

        args = {"file": str(large_file)}

        # The @pre contract on parse_toc will raise PreContractError
        # This is the correct behavior - contracts enforce size limits
        with pytest.raises(Exception) as exc_info:
            await _run_doc_toc(args)

        # Verify it's a contract error about size
        assert "len(source) <= 10_000_000" in str(exc_info.value) or "PreContractError" in str(exc_info.type)


class TestUnicodeFuzzyMatching:
    """Test DX-77 Phase A: Unicode-aware fuzzy matching."""

    @pytest.fixture
    def unicode_markdown_file(self, tmp_path: Path) -> Path:
        """Create markdown file with Unicode (Chinese/Japanese) section titles."""
        content = """# Main Title

Introduction paragraph.

## Phase A 实现计划

Chinese section content about implementation plan.

### 验证计划

Nested verification plan.

## Phase B テスト

Japanese section content about testing.

## Phase C Проверка

Cyrillic section content about verification.
"""
        md_file = tmp_path / "unicode_test.md"
        md_file.write_text(content, encoding="utf-8")
        return md_file

    async def test_fuzzy_match_chinese(self, unicode_markdown_file: Path):
        """Test fuzzy matching with Chinese characters."""
        import json

        args = {
            "file": str(unicode_markdown_file),
            "section": "实现计划"  # Should match "Phase A 实现计划"
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "Phase A 实现计划" in data["content"]
        assert "Chinese section content" in data["content"]

    async def test_fuzzy_match_japanese(self, unicode_markdown_file: Path):
        """Test fuzzy matching with Japanese characters."""
        import json

        args = {
            "file": str(unicode_markdown_file),
            "section": "テスト"  # Should match "Phase B テスト"
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "Phase B テスト" in data["content"]
        assert "Japanese section content" in data["content"]

    async def test_fuzzy_match_cyrillic(self, unicode_markdown_file: Path):
        """Test fuzzy matching with Cyrillic characters."""
        import json

        args = {
            "file": str(unicode_markdown_file),
            "section": "Проверка"  # Should match "Phase C Проверка"
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "Phase C Проверка" in data["content"]
        assert "Cyrillic section content" in data["content"]

    async def test_fuzzy_match_mixed_ascii_chinese(self, unicode_markdown_file: Path):
        """Test fuzzy matching with mixed ASCII and Chinese."""
        import json

        args = {
            "file": str(unicode_markdown_file),
            "section": "phasea"  # Should match "Phase A 实现计划" (case-insensitive, no spaces)
        }
        result = await _run_doc_read(args)

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "Phase A 实现计划" in data["content"]


class TestDocReadMany:
    """Test DX-77 Phase A: Batch section reading."""

    @pytest.fixture
    def multi_section_file(self, tmp_path: Path) -> Path:
        """Create markdown file with multiple sections for batch reading."""
        content = """# Main Title

Introduction.

## Section A

Content A.

## Section B

Content B.

## Section C

Content C.

### Subsection C.1

Nested content.
"""
        md_file = tmp_path / "multi_test.md"
        md_file.write_text(content)
        return md_file

    async def test_read_many_sections(self, multi_section_file: Path):
        """Test reading multiple sections in one call."""
        args = {
            "file": str(multi_section_file),
            "sections": ["section-a", "section-b", "section-c"]
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        # Result should be JSON array of section dicts
        import json
        sections = json.loads(result[0].text)

        assert len(sections) == 3
        assert sections[0]["path"] == "section-a"
        assert "Content A" in sections[0]["content"]
        assert sections[1]["path"] == "section-b"
        assert "Content B" in sections[1]["content"]
        assert sections[2]["path"] == "section-c"
        assert "Content C" in sections[2]["content"]

    async def test_read_many_with_children(self, multi_section_file: Path):
        """Test reading section with children included."""
        args = {
            "file": str(multi_section_file),
            "sections": ["section-c"],
            "include_children": True
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        import json
        sections = json.loads(result[0].text)

        assert len(sections) == 1
        # Should include subsection content
        assert "Subsection C.1" in sections[0]["content"]
        assert "Nested content" in sections[0]["content"]

    async def test_read_many_without_children(self, multi_section_file: Path):
        """Test reading section without children."""
        args = {
            "file": str(multi_section_file),
            "sections": ["section-c"],
            "include_children": False
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        import json
        sections = json.loads(result[0].text)

        assert len(sections) == 1
        # Should NOT include subsection content
        assert "Subsection C.1" not in sections[0]["content"]

    async def test_read_many_section_not_found(self, multi_section_file: Path):
        """Test batch reading with non-existent section."""
        args = {
            "file": str(multi_section_file),
            "sections": ["section-a", "nonexistent", "section-b"]
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()

    async def test_read_many_empty_sections_list(self, multi_section_file: Path):
        """Test batch reading with empty sections list."""
        args = {
            "file": str(multi_section_file),
            "sections": []
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "required" in result[0].text.lower()

    async def test_read_many_missing_file(self):
        """Test batch reading with missing file."""
        args = {
            "file": "/nonexistent/file.md",
            "sections": ["section-a"]
        }
        result = await _run_doc_read_many(args)

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "not found" in result[0].text.lower()
