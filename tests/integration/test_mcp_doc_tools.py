"""
DX-76: Integration tests for MCP document tools.

Tests the MCP handlers for doc_toc, doc_read, doc_find, doc_replace,
doc_insert, and doc_delete to ensure they work end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from returns.result import Success

from invar.mcp.handlers import (
    _run_doc_delete,
    _run_doc_find,
    _run_doc_insert,
    _run_doc_read,
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
