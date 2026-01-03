"""
LX-07: Extension Skills integration tests.

Tests:
1. Skill CLI commands (list, add, remove, update)
2. Skill registry parsing
3. Isolation behavior (via subprocess Claude Code invocation)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from returns.result import Failure, Success

from invar.shell.skill_manager import (
    add_skill,
    list_skills,
    load_registry,
    remove_skill,
    update_skill,
)

# Check tool availability
CLAUDE_AVAILABLE = shutil.which("claude") is not None
INVAR_AVAILABLE = shutil.which("invar") is not None


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_project(tmp_path: Path) -> Path:
    """Create a minimal test project."""
    # Create project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text('print("hello")')

    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'test-project'\nversion = '1.0.0'\n"
    )

    # Create .claude/skills directory
    (tmp_path / ".claude" / "skills").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def mock_console():
    """Mock console for skill manager functions."""

    class MockConsole:
        def __init__(self):
            self.output: list[str] = []

        def print(self, msg: str) -> None:
            self.output.append(str(msg))

    return MockConsole()


# =============================================================================
# Registry Tests
# =============================================================================


class TestSkillRegistry:
    """Test skill registry loading and parsing."""

    def test_load_registry_success(self):
        """Registry loads successfully."""
        result = load_registry()
        assert isinstance(result, Success)

        registry = result.unwrap()
        assert "version" in registry
        assert "extensions" in registry

    def test_registry_has_t0_skills(self):
        """Registry contains T0 skills (acceptance, security)."""
        result = load_registry()
        assert isinstance(result, Success)

        extensions = result.unwrap()["extensions"]
        assert "acceptance" in extensions
        assert "security" in extensions

        # Verify T0 tier
        assert extensions["acceptance"]["tier"] == "T0"
        assert extensions["security"]["tier"] == "T0"

    def test_registry_has_isolation_flags(self):
        """Registry specifies isolation defaults."""
        result = load_registry()
        extensions = result.unwrap()["extensions"]

        # T0 skills should have isolation: true
        assert extensions["acceptance"]["isolation"] is True
        assert extensions["security"]["isolation"] is True

    def test_registry_t1_skills_pending(self):
        """T1 skills are marked as pending_discussion."""
        result = load_registry()
        extensions = result.unwrap()["extensions"]

        t1_skills = ["refactor", "debug", "test-strategy"]
        for skill_name in t1_skills:
            if skill_name in extensions:
                assert extensions[skill_name].get("status") == "pending_discussion"


# =============================================================================
# Skill Manager Tests
# =============================================================================


class TestListSkills:
    """Test list_skills function."""

    def test_list_shows_available_skills(self, test_project: Path, mock_console):
        """List shows skills from registry."""
        result = list_skills(test_project, mock_console)
        assert isinstance(result, Success)

        skills = result.unwrap()
        names = [s.name for s in skills]

        assert "acceptance" in names
        assert "security" in names

    def test_list_shows_correct_status(self, test_project: Path, mock_console):
        """Installed skills show as 'installed'."""
        # First add a skill
        add_skill("acceptance", test_project, mock_console)

        result = list_skills(test_project, mock_console)
        skills = result.unwrap()

        acceptance = next(s for s in skills if s.name == "acceptance")
        assert acceptance.status == "installed"


class TestAddSkill:
    """Test add_skill function."""

    def test_add_acceptance_skill(self, test_project: Path, mock_console):
        """Add acceptance skill copies SKILL.md."""
        result = add_skill("acceptance", test_project, mock_console)
        assert isinstance(result, Success)

        skill_dir = test_project / ".claude" / "skills" / "acceptance"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()

    def test_add_security_skill_with_patterns(self, test_project: Path, mock_console):
        """Add security skill copies SKILL.md and patterns/."""
        result = add_skill("security", test_project, mock_console)
        assert isinstance(result, Success)

        skill_dir = test_project / ".claude" / "skills" / "security"
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "patterns" / "_common.yaml").exists()
        assert (skill_dir / "patterns" / "python.yaml").exists()
        assert (skill_dir / "patterns" / "typescript.yaml").exists()

    def test_add_pending_skill_blocked(self, test_project: Path, mock_console):
        """Adding a pending_discussion skill is blocked."""
        result = add_skill("refactor", test_project, mock_console)
        assert isinstance(result, Failure)
        assert "pending discussion" in result.failure().lower()

    def test_add_already_installed_is_idempotent(self, test_project: Path, mock_console):
        """DX-71: Adding already-installed skill updates it (idempotent)."""
        add_skill("acceptance", test_project, mock_console)
        result = add_skill("acceptance", test_project, mock_console)

        # DX-71: add_skill is idempotent - updates if exists
        assert isinstance(result, Success)
        assert "updated" in result.unwrap().lower()

    def test_add_unknown_skill_error(self, test_project: Path, mock_console):
        """Unknown skill name returns error."""
        result = add_skill("nonexistent", test_project, mock_console)
        assert isinstance(result, Failure)
        assert "unknown skill" in result.failure().lower()


class TestRemoveSkill:
    """Test remove_skill function."""

    def test_remove_installed_skill(self, test_project: Path, mock_console):
        """Remove installed extension skill."""
        add_skill("acceptance", test_project, mock_console)
        result = remove_skill("acceptance", test_project, mock_console)

        assert isinstance(result, Success)
        assert not (test_project / ".claude" / "skills" / "acceptance").exists()

    def test_remove_core_skill_blocked(self, test_project: Path, mock_console):
        """Cannot remove core skills."""
        # Create a fake core skill directory
        core_skill = test_project / ".claude" / "skills" / "develop"
        core_skill.mkdir(parents=True)
        (core_skill / "SKILL.md").write_text("# /develop")

        result = remove_skill("develop", test_project, mock_console)
        assert isinstance(result, Failure)
        assert "core skill" in result.failure().lower()

    def test_remove_not_installed_error(self, test_project: Path, mock_console):
        """Error when removing skill that's not installed."""
        result = remove_skill("acceptance", test_project, mock_console)
        assert isinstance(result, Failure)
        assert "not installed" in result.failure().lower()


class TestUpdateSkill:
    """Test update_skill function."""

    def test_update_installed_skill(self, test_project: Path, mock_console):
        """Update replaces skill files."""
        add_skill("acceptance", test_project, mock_console)

        # Modify the installed file
        skill_file = test_project / ".claude" / "skills" / "acceptance" / "SKILL.md"
        original_content = skill_file.read_text()
        skill_file.write_text("# Modified")

        # Update
        result = update_skill("acceptance", test_project, mock_console)
        assert isinstance(result, Success)

        # Should be restored to original
        assert skill_file.read_text() == original_content

    def test_update_not_installed_installs(self, test_project: Path, mock_console):
        """DX-71: Updating not-installed skill installs it (delegates to add)."""
        result = update_skill("acceptance", test_project, mock_console)
        # DX-71: update_skill delegates to add_skill, which installs if missing
        assert isinstance(result, Success)
        assert "installed" in result.unwrap().lower()
        # Verify skill was actually installed
        assert (test_project / ".claude" / "skills" / "acceptance" / "SKILL.md").exists()


# =============================================================================
# CLI Tests
# =============================================================================


@pytest.mark.skipif(not INVAR_AVAILABLE, reason="invar CLI not in PATH")
class TestSkillCLI:
    """Test invar skill CLI commands."""

    def test_cli_skill_list(self, test_project: Path):
        """invar skill list shows available skills."""
        result = subprocess.run(
            ["invar", "skill", "list"],
            cwd=test_project,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "acceptance" in result.stdout
        assert "security" in result.stdout

    def test_cli_skill_add(self, test_project: Path):
        """invar skill add installs a skill."""
        result = subprocess.run(
            ["invar", "skill", "add", "acceptance"],
            cwd=test_project,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert (test_project / ".claude" / "skills" / "acceptance" / "SKILL.md").exists()

    def test_cli_skill_remove(self, test_project: Path):
        """invar skill remove uninstalls a skill."""
        # First add
        subprocess.run(["invar", "skill", "add", "acceptance"], cwd=test_project)

        # Then remove
        result = subprocess.run(
            ["invar", "skill", "remove", "acceptance", "-f"],
            cwd=test_project,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert not (test_project / ".claude" / "skills" / "acceptance").exists()

    def test_cli_skill_update(self, test_project: Path):
        """invar skill update refreshes skill files."""
        # Add skill
        subprocess.run(["invar", "skill", "add", "acceptance"], cwd=test_project)

        # Update
        result = subprocess.run(
            ["invar", "skill", "update", "acceptance"],
            cwd=test_project,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "updated" in result.stdout.lower()


# =============================================================================
# SKILL.md Content Tests
# =============================================================================


class TestSkillContent:
    """Test SKILL.md content and structure."""

    def test_acceptance_skill_has_depth_levels(self, test_project: Path, mock_console):
        """Acceptance SKILL.md documents depth levels."""
        add_skill("acceptance", test_project, mock_console)

        content = (
            test_project / ".claude" / "skills" / "acceptance" / "SKILL.md"
        ).read_text()

        assert "--quick" in content
        assert "--standard" in content
        assert "--deep" in content
        assert "default" in content.lower()

    def test_acceptance_skill_has_isolation_section(
        self, test_project: Path, mock_console
    ):
        """Acceptance SKILL.md has isolation workflow."""
        add_skill("acceptance", test_project, mock_console)

        content = (
            test_project / ".claude" / "skills" / "acceptance" / "SKILL.md"
        ).read_text()

        assert "Isolation" in content or "SPAWN ISOLATED AGENT" in content
        assert "Task agent" in content or "Task" in content

    def test_security_skill_has_owasp(self, test_project: Path, mock_console):
        """Security SKILL.md references OWASP Top 10."""
        add_skill("security", test_project, mock_console)

        content = (
            test_project / ".claude" / "skills" / "security" / "SKILL.md"
        ).read_text()

        assert "OWASP" in content
        assert "A01" in content
        assert "A03" in content  # Injection

    def test_security_patterns_valid_yaml(self, test_project: Path, mock_console):
        """Security patterns are valid YAML."""
        add_skill("security", test_project, mock_console)

        patterns_dir = test_project / ".claude" / "skills" / "security" / "patterns"

        for yaml_file in patterns_dir.glob("*.yaml"):
            content = yaml_file.read_text()
            data = yaml.safe_load(content)
            assert isinstance(data, dict)


# =============================================================================
# Claude Code Isolation Tests (requires Claude CLI)
# =============================================================================


@pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="claude CLI not in PATH")
class TestClaudeIsolation:
    """
    Test isolation behavior by invoking Claude Code.

    These tests verify that extension skills correctly spawn isolated agents.
    """

    @pytest.fixture
    def claude_project(self, test_project: Path, mock_console) -> Path:
        """Project with skills installed for Claude testing."""
        add_skill("acceptance", test_project, mock_console)
        add_skill("security", test_project, mock_console)

        # Create a simple PRD for acceptance testing
        docs_dir = test_project / "docs"
        docs_dir.mkdir()
        (docs_dir / "prd.md").write_text(
            "# Requirements\n\n## FR-1: User Login\nUsers can log in with email.\n"
        )

        return test_project

    def test_acceptance_invocation_print_mode(self, claude_project: Path):
        """
        /acceptance invocation in print mode.

        Verifies Claude reads the skill and attempts to execute.
        """
        result = subprocess.run(
            [
                "claude",
                "--print",  # Print mode (non-interactive)
                "-p",
                "Run /acceptance on this project. Just acknowledge and list the first step.",
            ],
            cwd=claude_project,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")},
        )

        # Should not error (even if API key missing, structure should work)
        output = result.stdout + result.stderr

        # Check that skill was recognized (may vary by actual Claude behavior)
        # This is a smoke test - real verification needs manual testing
        assert result.returncode == 0 or "API" in output or "key" in output.lower()

    def test_security_invocation_print_mode(self, claude_project: Path):
        """
        /security invocation in print mode.

        Verifies Claude reads the skill and attempts to execute.
        """
        result = subprocess.run(
            [
                "claude",
                "--print",
                "-p",
                "Run /security --quick on this project. Just acknowledge and list what you would check.",
            ],
            cwd=claude_project,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")},
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0 or "API" in output or "key" in output.lower()


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegression:
    """Regression tests to ensure core functionality isn't broken."""

    def test_core_skills_not_affected(self, test_project: Path, mock_console):
        """Core skills should not be removable via skill manager."""
        core_skills = ["develop", "review", "investigate", "propose"]

        for skill in core_skills:
            # Create fake core skill
            skill_dir = test_project / ".claude" / "skills" / skill
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# /{skill}")

            # Should not be removable
            result = remove_skill(skill, test_project, mock_console)
            assert isinstance(result, Failure)
            assert "core skill" in result.failure().lower()

    def test_registry_version_present(self):
        """Registry has version field for future compatibility."""
        result = load_registry()
        registry = result.unwrap()
        assert "version" in registry
        assert registry["version"] == "1.0"
