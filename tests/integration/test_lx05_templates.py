"""
LX-05: Template rendering tests for Python vs TypeScript.

Part 2 of LX-05 test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from returns.result import Success

from invar.shell.template_engine import get_templates_dir, render_template_file

# =============================================================================
# INVAR.md Template Rendering Tests
# =============================================================================


class TestINVARTemplateRendering:
    """Test INVAR.md rendering for different languages."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        return get_templates_dir()

    def test_python_invar_has_pre_post(self, templates_dir: Path):
        """Python INVAR.md should have @pre/@post content."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"
        result = render_template_file(template, {"language": "python", "version": "5.0"})

        assert isinstance(result, Success)
        content = result.unwrap()

        # Python-specific markers
        assert "@pre" in content
        assert "@post" in content
        assert "deal" in content or "lambda" in content
        assert "doctest" in content.lower() or ">>>" in content

    def test_python_invar_no_zod(self, templates_dir: Path):
        """Python INVAR.md should NOT have Zod content."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"
        result = render_template_file(template, {"language": "python", "version": "5.0"})

        assert isinstance(result, Success)
        content = result.unwrap()

        # Should NOT have TypeScript markers
        assert "Zod" not in content
        assert "neverthrow" not in content
        assert "z.object" not in content

    def test_typescript_invar_has_zod(self, templates_dir: Path):
        """TypeScript INVAR.md should have Zod content."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"
        result = render_template_file(template, {"language": "typescript", "version": "5.0"})

        assert isinstance(result, Success)
        content = result.unwrap()

        # TypeScript-specific markers
        assert "Zod" in content
        assert "neverthrow" in content
        assert "z.number()" in content or "z.object" in content

    def test_typescript_invar_no_pre_post(self, templates_dir: Path):
        """TypeScript INVAR.md should NOT have @pre/@post decorators."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"
        result = render_template_file(template, {"language": "typescript", "version": "5.0"})

        assert isinstance(result, Success)
        content = result.unwrap()

        # Should NOT have Python decorators
        assert "@pre(lambda" not in content
        assert "@post(lambda" not in content
        assert "from deal import" not in content

    def test_both_have_six_laws(self, templates_dir: Path):
        """Both languages should have Six Laws (universal content)."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"

        for lang in ["python", "typescript"]:
            result = render_template_file(template, {"language": lang, "version": "5.0"})
            assert isinstance(result, Success)
            content = result.unwrap()

            # Universal content
            assert "Six Laws" in content
            assert "USBV" in content or "Understand" in content
            assert "Core" in content and "Shell" in content

    def test_both_have_check_in_final(self, templates_dir: Path):
        """Both languages should have Check-In/Final protocol."""
        template = templates_dir / "protocol" / "INVAR.md.jinja"

        for lang in ["python", "typescript"]:
            result = render_template_file(template, {"language": lang, "version": "5.0"})
            assert isinstance(result, Success)
            content = result.unwrap()

            assert "Check-In" in content
            assert "Final" in content


# =============================================================================
# CLAUDE.md Template Rendering Tests
# =============================================================================


class TestCLAUDETemplateRendering:
    """Test CLAUDE.md rendering for different languages."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        return get_templates_dir()

    def test_python_claude_has_result_returns(self, templates_dir: Path):
        """Python CLAUDE.md should reference returns library."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "python", "syntax": "cli", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # Python-specific
        assert "Result[T, E]" in content
        assert "returns" in content

    def test_typescript_claude_has_neverthrow(self, templates_dir: Path):
        """TypeScript CLAUDE.md should reference neverthrow."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "typescript", "syntax": "cli", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # TypeScript-specific
        assert "Result<T, E>" in content
        assert "neverthrow" in content

    def test_python_claude_critical_rules(self, templates_dir: Path):
        """Python CLAUDE.md should have Python critical rules."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "python", "syntax": "cli", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # Python critical rules
        assert "@pre/@post" in content or "@pre" in content
        assert "doctests" in content.lower() or "doctest" in content.lower()

    def test_typescript_claude_critical_rules(self, templates_dir: Path):
        """TypeScript CLAUDE.md should have TypeScript critical rules."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "typescript", "syntax": "cli", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # TypeScript critical rules
        assert "Zod" in content
        assert "JSDoc" in content or "@example" in content

    def test_mcp_syntax_python(self, templates_dir: Path):
        """MCP syntax should use invar_guard (underscore)."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "python", "syntax": "mcp", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # MCP uses underscore
        assert "invar_guard" in content

    def test_cli_syntax_python(self, templates_dir: Path):
        """CLI syntax should use invar guard (space) or invar_guard."""
        template = templates_dir / "config" / "CLAUDE.md.jinja"
        result = render_template_file(
            template, {"language": "python", "syntax": "cli", "version": "5.0"}
        )

        assert isinstance(result, Success)
        content = result.unwrap()

        # CLI uses space or underscore
        assert "invar guard" in content or "invar_guard" in content


# =============================================================================
# Cross-Language Consistency Tests
# =============================================================================


class TestCrossLanguageConsistency:
    """Test consistency across Python and TypeScript templates."""

    def test_no_raw_jinja_in_output(self, tmp_path: Path):
        """Output should not contain raw Jinja syntax."""
        from invar.core.sync_helpers import SyncConfig
        from invar.shell.commands.template_sync import sync_templates

        for lang in ["python", "typescript"]:
            config = SyncConfig(language=lang)
            sync_templates(tmp_path, config)

            for file in ["INVAR.md", "CLAUDE.md"]:
                content = (tmp_path / file).read_text()
                assert "{%" not in content, f"Raw Jinja in {file}"
                assert "{{" not in content or "}}" not in content, f"Unclosed Jinja in {file}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
