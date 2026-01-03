"""
LX-05: Language detection and SyncConfig validation tests.

Part 1 of LX-05 test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invar.core.sync_helpers import VALID_LANGUAGES, SyncConfig
from invar.shell.commands.init import (
    FUTURE_LANGUAGES,
    SUPPORTED_LANGUAGES,
    detect_language,
)

# =============================================================================
# Language Detection Tests
# =============================================================================


class TestDetectLanguage:
    """Test auto-detection of project language from marker files."""

    def test_detect_python_from_pyproject(self, tmp_path: Path):
        """pyproject.toml → python."""
        (tmp_path / "pyproject.toml").touch()
        assert detect_language(tmp_path) == "python"

    def test_detect_python_from_setup_py(self, tmp_path: Path):
        """setup.py → python."""
        (tmp_path / "setup.py").touch()
        assert detect_language(tmp_path) == "python"

    def test_detect_typescript_from_tsconfig(self, tmp_path: Path):
        """tsconfig.json → typescript."""
        (tmp_path / "tsconfig.json").touch()
        assert detect_language(tmp_path) == "typescript"

    def test_detect_typescript_from_package_json(self, tmp_path: Path):
        """package.json → typescript."""
        (tmp_path / "package.json").touch()
        assert detect_language(tmp_path) == "typescript"

    def test_detect_rust_from_cargo(self, tmp_path: Path):
        """Cargo.toml → rust (future language)."""
        (tmp_path / "Cargo.toml").touch()
        assert detect_language(tmp_path) == "rust"

    def test_detect_go_from_gomod(self, tmp_path: Path):
        """go.mod → go (future language)."""
        (tmp_path / "go.mod").touch()
        assert detect_language(tmp_path) == "go"

    def test_detect_default_empty_dir(self, tmp_path: Path):
        """Empty directory → python (default)."""
        assert detect_language(tmp_path) == "python"

    def test_python_priority_over_typescript(self, tmp_path: Path):
        """When both exist, pyproject.toml wins over tsconfig.json."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "tsconfig.json").touch()
        assert detect_language(tmp_path) == "python"

    def test_python_priority_over_package_json(self, tmp_path: Path):
        """When both exist, pyproject.toml wins over package.json."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()
        assert detect_language(tmp_path) == "python"


# =============================================================================
# SyncConfig Language Validation Tests
# =============================================================================


class TestSyncConfigLanguage:
    """Test SyncConfig language field validation."""

    def test_default_language_is_python(self):
        """Default language should be python."""
        config = SyncConfig()
        assert config.language == "python"

    def test_valid_language_python(self):
        """Python is a valid language."""
        config = SyncConfig(language="python")
        assert config.language == "python"

    def test_valid_language_typescript(self):
        """TypeScript is a valid language."""
        config = SyncConfig(language="typescript")
        assert config.language == "typescript"

    def test_invalid_language_raises_error(self):
        """Invalid language should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid language"):
            SyncConfig(language="rust")

    def test_invalid_language_go_raises_error(self):
        """Go is not yet supported."""
        with pytest.raises(ValueError, match="Invalid language"):
            SyncConfig(language="go")

    def test_invalid_language_random_raises_error(self):
        """Random string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid language"):
            SyncConfig(language="javascript")

    def test_valid_languages_constant(self):
        """VALID_LANGUAGES should contain python and typescript."""
        assert "python" in VALID_LANGUAGES
        assert "typescript" in VALID_LANGUAGES
        assert len(VALID_LANGUAGES) == 2

    def test_supported_vs_valid_languages(self):
        """SUPPORTED_LANGUAGES should match VALID_LANGUAGES."""
        assert SUPPORTED_LANGUAGES == VALID_LANGUAGES

    def test_future_languages_not_valid(self):
        """Future languages should not be in VALID_LANGUAGES."""
        for lang in FUTURE_LANGUAGES:
            assert lang not in VALID_LANGUAGES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
