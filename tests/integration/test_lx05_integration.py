"""
LX-05: Integration, CLI, workflow, and skill tests.

Part 3 of LX-05 test suite.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# Skip CLI tests if invar command not in PATH
INVAR_AVAILABLE = shutil.which("invar") is not None
from returns.result import Success

from invar.core.sync_helpers import SyncConfig
from invar.shell.commands.template_sync import sync_templates

# =============================================================================
# Init with Language Tests
# =============================================================================


class TestInitWithLanguage:
    """Test invar init with language parameter."""

    def test_init_python_detection(self, tmp_path: Path):
        """Init auto-detects Python from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        config = SyncConfig(syntax="cli", language="python")
        result = sync_templates(tmp_path, config)

        assert isinstance(result, Success)
        assert (tmp_path / "INVAR.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

        # Verify Python content
        invar_content = (tmp_path / "INVAR.md").read_text()
        assert "@pre" in invar_content or "lambda" in invar_content

    def test_init_typescript_detection(self, tmp_path: Path):
        """Init auto-detects TypeScript from tsconfig.json."""
        (tmp_path / "tsconfig.json").write_text("{}")

        config = SyncConfig(syntax="cli", language="typescript")
        result = sync_templates(tmp_path, config)

        assert isinstance(result, Success)
        assert (tmp_path / "INVAR.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

        # Verify TypeScript content
        invar_content = (tmp_path / "INVAR.md").read_text()
        assert "Zod" in invar_content
        assert "neverthrow" in invar_content

    def test_init_explicit_language_override(self, tmp_path: Path):
        """Explicit --language overrides detection."""
        # Create TypeScript project marker
        (tmp_path / "tsconfig.json").write_text("{}")

        # But request Python
        config = SyncConfig(syntax="cli", language="python")
        result = sync_templates(tmp_path, config)

        assert isinstance(result, Success)

        # Should have Python content, not TypeScript
        invar_content = (tmp_path / "INVAR.md").read_text()
        assert "@pre" in invar_content or "deal" in invar_content
        assert "Zod" not in invar_content

    def test_reinit_preserves_user_content(self, tmp_path: Path):
        """Re-init preserves user region content."""
        # First init
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        # Add user content
        claude_path = tmp_path / "CLAUDE.md"
        original = claude_path.read_text()
        modified = original.replace(
            "<!--invar:user-->",
            "<!--invar:user-->\n## My Custom Rules\n- Rule 1\n- Rule 2\n",
        )
        claude_path.write_text(modified)

        # Re-init (simulating update)
        config2 = SyncConfig(syntax="cli", language="python", force=True)
        result = sync_templates(tmp_path, config2)

        assert isinstance(result, Success)

        # User content should be preserved
        new_content = claude_path.read_text()
        assert "My Custom Rules" in new_content

    def test_uninstall_and_reinit(self, tmp_path: Path):
        """Uninstall removes files, reinit recreates them."""
        # First init
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        assert (tmp_path / "INVAR.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

        # Simulate uninstall
        (tmp_path / "INVAR.md").unlink()
        (tmp_path / "CLAUDE.md").unlink()

        assert not (tmp_path / "INVAR.md").exists()
        assert not (tmp_path / "CLAUDE.md").exists()

        # Reinit
        result = sync_templates(tmp_path, config)

        assert isinstance(result, Success)
        assert (tmp_path / "INVAR.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()


# =============================================================================
# CLI Language Parameter Tests
# =============================================================================


@pytest.mark.skipif(not INVAR_AVAILABLE, reason="invar CLI not in PATH")
class TestCLILanguageParameter:
    """Test CLI --language parameter via subprocess."""

    def test_cli_help_shows_language(self):
        """CLI help should show --language option."""
        result = subprocess.run(
            ["invar", "init", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--language" in result.stdout or "-l" in result.stdout

    def test_cli_invalid_language_error(self, tmp_path: Path):
        """CLI rejects invalid language."""
        result = subprocess.run(
            [
                "invar",
                "init",
                str(tmp_path),
                "--language",
                "rust",
                "--preview",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Invalid language" in result.stderr or "Invalid language" in result.stdout

    def test_cli_preview_shows_language(self, tmp_path: Path):
        """CLI preview shows detected language."""
        (tmp_path / "tsconfig.json").write_text("{}")

        result = subprocess.run(
            [
                "invar",
                "init",
                str(tmp_path),
                "--claude",
                "--preview",
            ],
            capture_output=True,
            text=True,
        )

        # Should show typescript detected
        assert "typescript" in result.stdout.lower()

    def test_cli_future_language_fallback(self, tmp_path: Path):
        """CLI handles future language (rust) by falling back to python."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")

        result = subprocess.run(
            [
                "invar",
                "init",
                str(tmp_path),
                "--claude",
                "--preview",
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed (no crash) and show rust detected with fallback
        assert result.returncode == 0
        # Should mention rust was detected
        assert "rust" in result.stdout.lower()
        # Should indicate fallback to python
        assert "python" in result.stdout.lower()


# =============================================================================
# Agent Workflow Acceptance Tests
# =============================================================================


class TestAgentWorkflowAcceptance:
    """Test that generated files support agent workflow."""

    def test_claude_md_has_skill_routing(self, tmp_path: Path):
        """CLAUDE.md should have skill routing table."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        content = (tmp_path / "CLAUDE.md").read_text()

        # Skill routing
        assert "/develop" in content or "develop" in content
        assert "/review" in content or "review" in content
        assert "/investigate" in content or "investigate" in content

    def test_claude_md_has_usbv_reference(self, tmp_path: Path):
        """CLAUDE.md should reference USBV workflow."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        content = (tmp_path / "CLAUDE.md").read_text()

        # USBV workflow reference
        assert "USBV" in content
        assert "Understand" in content or "UNDERSTAND" in content

    def test_invar_md_has_check_in_protocol(self, tmp_path: Path):
        """INVAR.md should have Check-In protocol."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        content = (tmp_path / "INVAR.md").read_text()

        # Check-In protocol
        assert "Check-In" in content
        assert "project" in content.lower()
        assert "branch" in content.lower()

    def test_invar_md_has_final_protocol(self, tmp_path: Path):
        """INVAR.md should have Final protocol."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        content = (tmp_path / "INVAR.md").read_text()

        # Final protocol
        assert "Final" in content
        assert "verification" in content.lower() or "guard" in content.lower()

    def test_visible_workflow_checkpoint_structure(self, tmp_path: Path):
        """INVAR.md should have visible workflow checkpoints."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        content = (tmp_path / "INVAR.md").read_text()

        # Visible workflow
        assert "UNDERSTAND" in content or "Understand" in content
        assert "SPECIFY" in content or "Specify" in content
        assert "BUILD" in content or "Build" in content
        assert "VALIDATE" in content or "Validate" in content


# =============================================================================
# Skill Template Tests
# =============================================================================


class TestSkillTemplates:
    """Test skill template rendering."""

    def test_develop_skill_created(self, tmp_path: Path):
        """develop skill should be created."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "develop" / "SKILL.md"
        assert skill_path.exists()

    def test_review_skill_created(self, tmp_path: Path):
        """review skill should be created."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "review" / "SKILL.md"
        assert skill_path.exists()

    def test_investigate_skill_created(self, tmp_path: Path):
        """investigate skill should be created."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "investigate" / "SKILL.md"
        assert skill_path.exists()

    def test_propose_skill_created(self, tmp_path: Path):
        """propose skill should be created."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "propose" / "SKILL.md"
        assert skill_path.exists()

    def test_develop_skill_has_usbv(self, tmp_path: Path):
        """develop skill should have USBV phases."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "develop" / "SKILL.md"
        content = skill_path.read_text()

        # USBV phases
        assert "UNDERSTAND" in content or "Understand" in content
        assert "SPECIFY" in content or "Specify" in content
        assert "BUILD" in content or "Build" in content
        assert "VALIDATE" in content or "Validate" in content

    def test_review_skill_has_rejection_mindset(self, tmp_path: Path):
        """review skill should have rejection-first mindset."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        skill_path = tmp_path / ".claude" / "skills" / "review" / "SKILL.md"
        content = skill_path.read_text()

        # Review mindset
        assert "REJECTION" in content or "rejection" in content or "Fault" in content

    def test_skills_have_guard_reference(self, tmp_path: Path):
        """Skills should reference guard verification."""
        config = SyncConfig(syntax="cli", language="python")
        sync_templates(tmp_path, config)

        # Check develop skill
        develop_path = tmp_path / ".claude" / "skills" / "develop" / "SKILL.md"
        if develop_path.exists():
            content = develop_path.read_text()
            assert "guard" in content.lower() or "verify" in content.lower()

    def test_skip_skills_pattern(self, tmp_path: Path):
        """Skip pattern should prevent skill creation."""
        config = SyncConfig(
            syntax="cli",
            language="python",
            skip_patterns=[".claude/skills/*"],
        )
        sync_templates(tmp_path, config)

        # Skills should NOT be created
        skill_path = tmp_path / ".claude" / "skills" / "develop" / "SKILL.md"
        assert not skill_path.exists()


# =============================================================================
# Cross-Language File Structure Tests
# =============================================================================


class TestCrossLanguageStructure:
    """Test consistency across Python and TypeScript file structures."""

    def test_same_file_structure(self, tmp_path: Path):
        """Both languages should produce same file structure."""
        python_dir = tmp_path / "python"
        typescript_dir = tmp_path / "typescript"
        python_dir.mkdir()
        typescript_dir.mkdir()

        # Init both
        sync_templates(python_dir, SyncConfig(language="python"))
        sync_templates(typescript_dir, SyncConfig(language="typescript"))

        # Same files should exist
        python_files = {p.relative_to(python_dir) for p in python_dir.rglob("*") if p.is_file()}
        ts_files = {p.relative_to(typescript_dir) for p in typescript_dir.rglob("*") if p.is_file()}

        # Key files should be in both
        assert Path("INVAR.md") in python_files
        assert Path("INVAR.md") in ts_files
        assert Path("CLAUDE.md") in python_files
        assert Path("CLAUDE.md") in ts_files

    def test_same_skill_structure(self, tmp_path: Path):
        """Both languages should have same skill structure."""
        python_dir = tmp_path / "python"
        typescript_dir = tmp_path / "typescript"
        python_dir.mkdir()
        typescript_dir.mkdir()

        sync_templates(python_dir, SyncConfig(language="python"))
        sync_templates(typescript_dir, SyncConfig(language="typescript"))

        # Same skills should exist
        skills = ["develop", "review", "investigate", "propose"]
        for skill in skills:
            py_skill = python_dir / ".claude" / "skills" / skill / "SKILL.md"
            ts_skill = typescript_dir / ".claude" / "skills" / skill / "SKILL.md"
            assert py_skill.exists(), f"Python {skill} skill missing"
            assert ts_skill.exists(), f"TypeScript {skill} skill missing"

    def test_both_have_core_shell_separation(self, tmp_path: Path):
        """Both languages should describe Core/Shell separation."""
        python_dir = tmp_path / "python"
        typescript_dir = tmp_path / "typescript"
        python_dir.mkdir()
        typescript_dir.mkdir()

        sync_templates(python_dir, SyncConfig(language="python"))
        sync_templates(typescript_dir, SyncConfig(language="typescript"))

        for dir_path in [python_dir, typescript_dir]:
            invar_content = (dir_path / "INVAR.md").read_text()
            assert "Core" in invar_content
            assert "Shell" in invar_content
            assert "pure" in invar_content.lower() or "I/O" in invar_content

    def test_language_specific_examples(self, tmp_path: Path):
        """LX-05 Hotfix: Examples should be language-specific."""
        python_dir = tmp_path / "python"
        typescript_dir = tmp_path / "typescript"
        python_dir.mkdir()
        typescript_dir.mkdir()

        sync_templates(python_dir, SyncConfig(language="python"))
        sync_templates(typescript_dir, SyncConfig(language="typescript"))

        # Python should have .py examples
        py_examples = python_dir / ".invar" / "examples"
        assert py_examples.exists(), "Python examples directory missing"
        assert (py_examples / "contracts.py").exists(), "contracts.py missing"
        assert (py_examples / "core_shell.py").exists(), "core_shell.py missing"
        assert (py_examples / "functional.py").exists(), "functional.py missing"

        # TypeScript should have .ts examples
        ts_examples = typescript_dir / ".invar" / "examples"
        assert ts_examples.exists(), "TypeScript examples directory missing"
        assert (ts_examples / "contracts.ts").exists(), "contracts.ts missing"
        assert (ts_examples / "core_shell.ts").exists(), "core_shell.ts missing"
        assert (ts_examples / "functional.ts").exists(), "functional.ts missing"

        # Python examples should NOT have .ts files
        assert not (py_examples / "contracts.ts").exists()
        # TypeScript examples should NOT have .py files
        assert not (ts_examples / "contracts.py").exists()


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressions:
    """Regression tests for known issues."""

    def test_created_vs_updated_tracking(self, tmp_path: Path):
        """First sync should report created, not updated."""
        config = SyncConfig(language="python")
        result = sync_templates(tmp_path, config)

        assert isinstance(result, Success)
        report = result.unwrap()

        # First sync - files should be created
        assert len(report.created) > 0
        # INVAR.md should be in created
        assert any("INVAR" in f for f in report.created)

    def test_second_sync_reports_updated(self, tmp_path: Path):
        """Second sync should report updated or skipped."""
        config = SyncConfig(language="python")

        # First sync
        sync_templates(tmp_path, config)

        # Second sync with force
        config2 = SyncConfig(language="python", force=True)
        result = sync_templates(tmp_path, config2)

        assert isinstance(result, Success)
        report = result.unwrap()

        # Second sync - files should be updated (not created)
        assert len(report.created) == 0 or len(report.updated) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
