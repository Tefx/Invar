"""
Tests for get_changed_lines in shell/git.py (DX-97).

Focused tests for staged/unstaged/untracked/deleted/non-Core changed-line selection.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from returns.result import Failure, Success
from invar.shell.git import (
    get_changed_lines,
    _parse_hunk_header,
    _extract_hunks_from_diff,
    matches_path_prefix,
    _is_core_file,
)


# ---------------------------------------------------------------------------
# Unit tests for _parse_hunk_header (zero-context safe)
# ---------------------------------------------------------------------------


class TestParseHunkHeader:
    """Zero-context hunk parsing — off-by-one prevention."""

    def test_standard_hunk(self) -> None:
        """Normal hunk with explicit count."""
        result = _parse_hunk_header("@@ -12,3 +14,4 @@")
        assert result == (12, 14)

    def test_zero_context_single_line(self) -> None:
        """Zero-context: single line added at position 5."""
        result = _parse_hunk_header("@@ -5 +5 @@")
        assert result == (5, 5)

    def test_zero_context_range(self) -> None:
        """Zero-context: range that results in end=start."""
        result = _parse_hunk_header("@@ -10 +10 @@")
        assert result == (10, 10)

    def test_multi_line_zero_context(self) -> None:
        """Zero-context with count 0 omitted — defaults to 1."""
        result = _parse_hunk_header("@@ -7 +7 @@ extra")
        assert result == (7, 7)

    def test_invalid_header(self) -> None:
        """Garbage header returns None."""
        assert _parse_hunk_header("not a hunk") is None
        assert _parse_hunk_header("@@ -1,2 @@") is None  # missing + side

    def test_leading_whitespace_stripped(self) -> None:
        """Leading spaces are stripped."""
        result = _parse_hunk_header("  @@ -3 +3 @@")
        assert result == (3, 3)


# ---------------------------------------------------------------------------
# Unit tests for _extract_hunks_from_diff
# ---------------------------------------------------------------------------


class TestExtractHunksFromDiff:
    """Multi-hunk extraction."""

    def test_single_hunk(self) -> None:
        diff = """some context
@@ -5,2 +5,2 @@
unchanged line
"""
        hunks = _extract_hunks_from_diff(diff)
        assert hunks == [(5, 6)]

    def test_multiple_hunks(self) -> None:
        diff = """@@ -1,3 +1,3 @@
line 1
@@ -10,2 +10,2 @@
line 2
"""
        hunks = _extract_hunks_from_diff(diff)
        assert hunks == [(1, 3), (10, 11)]

    def test_no_hunks(self) -> None:
        """Plain text with no hunk markers."""
        hunks = _extract_hunks_from_diff("just some text\nno markers here")
        assert hunks == []


# ---------------------------------------------------------------------------
# Unit tests for matches_path_prefix
# ---------------------------------------------------------------------------


class TestMatchesPathPrefix:
    """Core path classification."""

    def test_exact_match(self) -> None:
        assert matches_path_prefix("src/core/foo.py", ["src/core"]) is True

    def test_deep_match(self) -> None:
        assert matches_path_prefix("src/core/a/b/bar.py", ["src/core"]) is True

    def test_non_match(self) -> None:
        assert matches_path_prefix("src/shell/foo.py", ["src/core"]) is False

    def test_non_prefix_match(self) -> None:
        assert matches_path_prefix("src/core_extra/foo.py", ["src/core"]) is False

    def test_empty_prefix(self) -> None:
        assert matches_path_prefix("foo.py", []) is False


# ---------------------------------------------------------------------------
# Integration-style tests for get_changed_lines
# ---------------------------------------------------------------------------


class TestGetChangedLinesIntegration:
    """DX-97: verify staged/unstaged/untracked/deleted/non-Core exclusion."""

    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        """Create a temp git repo with a src/core structure."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
        )
        core_dir = tmp_path / "src" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "__init__.py").write_text("# core\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)
        return tmp_path

    def test_staged_lines_returned(self, repo: Path) -> None:
        """Staged hunks produce correct line ranges."""
        core_file = repo / "src" / "core" / "__init__.py"
        core_file.write_text("# modified\n# line2\n# line3\n")

        subprocess.run(["git", "add", "."], cwd=repo, check=True)

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()
        assert core_file in data

    def test_untracked_whole_file(self, repo: Path) -> None:
        """Untracked Core Python files return None (whole file)."""
        new_file = repo / "src" / "core" / "new.py"
        new_file.write_text("# new file\n")

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()
        assert new_file in data
        assert data[new_file] is None  # whole file

    def test_deleted_file_excluded(self, repo: Path) -> None:
        """Deleted files are excluded from changed lines."""
        subprocess.run(
            ["git", "rm", "src/core/__init__.py"], cwd=repo, check=True, capture_output=True
        )

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()
        deleted = repo / "src" / "core" / "__init__.py"
        assert deleted not in data

    def test_non_core_file_excluded(self, repo: Path) -> None:
        """Non-Core Python files are excluded."""
        shell_dir = repo / "src" / "shell"
        shell_dir.mkdir(parents=True)
        (shell_dir / "__init__.py").write_text("# shell\n")

        subprocess.run(["git", "add", "src/shell"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "add shell"], cwd=repo, check=True)

        # Modify a shell file
        (shell_dir / "__init__.py").write_text("# modified shell\n")
        subprocess.run(["git", "add", "src/shell"], cwd=repo, check=True)

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()
        shell_file = repo / "src" / "shell" / "__init__.py"
        for fpath in data:
            assert "shell" not in str(fpath)

    def test_mixed_staged_and_untracked(self, repo: Path) -> None:
        """Both staged and untracked files are returned correctly."""
        core_file = repo / "src" / "core" / "__init__.py"
        core_file.write_text("# changed staged\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)

        new_file = repo / "src" / "core" / "new.py"
        new_file.write_text("# new untracked\n")

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()

        assert core_file in data
        assert new_file in data
        assert data[new_file] is None

    def test_strips_repo_prefix_from_keys(self, repo: Path) -> None:
        """Returned dict keys are absolute Path objects under repo_root."""
        core_file = repo / "src" / "core" / "__init__.py"
        core_file.write_text("# modified\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)

        result = get_changed_lines(repo)
        if isinstance(result, Failure):
            pytest.fail(f"get_changed_lines failed: {result.failure()}")
        data = result.unwrap()

        for fpath in data.keys():
            assert fpath.is_absolute()
            assert str(fpath).startswith(str(repo))


# ---------------------------------------------------------------------------
# Doctest for _parse_hunk_header
# ---------------------------------------------------------------------------


def test_doctest_parse_hunk_header():
    """Doctest for _parse_hunk_header."""
    # Standard hunk
    assert _parse_hunk_header("@@ -12,3 +14,4 @@") == (12, 14)
    # Zero-context single line (git -U0 default)
    assert _parse_hunk_header("@@ -5 +5 @@") == (5, 5)
    # Zero-context with count 0 omitted — defaults to 1
    assert _parse_hunk_header("@@ -7 +7 @@") == (7, 7)
    # Invalid
    assert _parse_hunk_header("@@garbage@@") is None
