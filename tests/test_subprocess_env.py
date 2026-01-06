"""Tests for DX-52 subprocess environment preparation.

Tests PYTHONPATH injection, re-spawn detection, and version mismatch detection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from returns.result import Success

from invar.shell.guard_helpers import collect_files_to_check
from invar.shell.property_tests import run_property_tests_on_file
from invar.shell.subprocess_env import (
    build_subprocess_env,
    check_version_mismatch,
    detect_project_python_with_invar,
    detect_project_venv,
    find_site_packages,
    get_uvx_respawn_command,
    get_venv_python_version,
    should_respawn,
    should_suppress_prompt,
)

# =============================================================================
# Phase 1: PYTHONPATH Injection Tests
# =============================================================================


class TestDetectProjectVenv:
    """Tests for detect_project_venv function."""

    def test_no_venv_found(self, tmp_path: Path) -> None:
        """Test graceful handling when no venv exists."""
        result = detect_project_venv(tmp_path)
        assert result is None

    def test_detects_dot_venv(self, tmp_path: Path) -> None:
        """Test detection of .venv directory."""
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()
        (venv_path / "pyvenv.cfg").write_text("version = 3.11.5\n")

        result = detect_project_venv(tmp_path)
        assert result == venv_path

    def test_detects_venv(self, tmp_path: Path) -> None:
        """Test detection of venv directory."""
        venv_path = tmp_path / "venv"
        venv_path.mkdir()
        (venv_path / "pyvenv.cfg").write_text("version = 3.11.5\n")

        result = detect_project_venv(tmp_path)
        assert result == venv_path

    def test_prefers_dot_venv_over_venv(self, tmp_path: Path) -> None:
        """Test that .venv is preferred over venv."""
        dot_venv = tmp_path / ".venv"
        dot_venv.mkdir()
        (dot_venv / "pyvenv.cfg").write_text("version = 3.11.5\n")

        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.11.5\n")

        result = detect_project_venv(tmp_path)
        assert result == dot_venv

    def test_requires_pyvenv_cfg(self, tmp_path: Path) -> None:
        """Test that directory without pyvenv.cfg is not detected."""
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()
        # No pyvenv.cfg file

        result = detect_project_venv(tmp_path)
        assert result is None


class TestFindSitePackages:
    """Tests for find_site_packages function."""

    def test_not_found_for_nonexistent(self, tmp_path: Path) -> None:
        """Test handling of nonexistent path."""
        result = find_site_packages(tmp_path / "nonexistent")
        assert result is None

    def test_unix_layout(self, tmp_path: Path) -> None:
        """Test Unix lib/pythonX.Y/site-packages layout."""
        venv = tmp_path / ".venv"
        site_packages = venv / "lib" / "python3.11" / "site-packages"
        site_packages.mkdir(parents=True)

        result = find_site_packages(venv)
        assert result == site_packages

    def test_windows_layout(self, tmp_path: Path) -> None:
        """Test Windows Lib/site-packages layout."""
        venv = tmp_path / ".venv"
        site_packages = venv / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)

        result = find_site_packages(venv)
        assert result == site_packages


class TestBuildSubprocessEnv:
    """Tests for build_subprocess_env function."""

    def test_returns_dict(self) -> None:
        """Test that result is a dict."""
        env = build_subprocess_env()
        assert isinstance(env, dict)

    def test_preserves_existing_env(self) -> None:
        """Test that existing env vars are preserved."""
        env = build_subprocess_env()
        assert "PATH" in env

    def test_injects_pythonpath_when_venv_found(self, tmp_path: Path) -> None:
        """Test PYTHONPATH injection when venv exists."""
        # Create mock venv
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.11.5\n")
        site_packages = venv / "lib" / "python3.11" / "site-packages"
        site_packages.mkdir(parents=True)

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        env = build_subprocess_env(cwd=tmp_path)
        assert "PYTHONPATH" in env
        assert str(site_packages) in env["PYTHONPATH"]
        assert str(src_dir) in env["PYTHONPATH"]

    def test_prepends_to_existing_pythonpath(self, tmp_path: Path) -> None:
        """Test that project packages have priority over existing PYTHONPATH."""
        # Create mock venv
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.11.5\n")
        site_packages = venv / "lib" / "python3.11" / "site-packages"
        site_packages.mkdir(parents=True)

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Set existing PYTHONPATH
        with patch.dict(os.environ, {"PYTHONPATH": "/existing/path"}):
            env = build_subprocess_env(cwd=tmp_path)
            assert env["PYTHONPATH"].startswith(str(src_dir))
            assert str(site_packages) in env["PYTHONPATH"]
            assert "/existing/path" in env["PYTHONPATH"]


class TestRuntimeFileCollectionExcludesVenv:
    def test_collect_files_to_check_excludes_dot_venv(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[project]
name = "tmp"
version = "0.0.0"

[tool.invar.guard]
core_paths = ["does-not-exist"]
shell_paths = ["also-nope"]
""".lstrip()
        )

        venv_file = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "x.py"
        venv_file.parent.mkdir(parents=True)
        venv_file.write_text("print('venv')\n")

        src_file = tmp_path / "src" / "core" / "a.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("x = 1\n")

        files = collect_files_to_check(tmp_path, [])
        paths = {str(p) for p in files}

        assert any(str(src_file) == p for p in paths)
        assert not any("/.venv/" in p or p.endswith("/.venv") for p in paths)


class TestPropertyTestsCanImportFromProjectVenv:
    def test_run_property_tests_on_file_injects_site_packages(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.11.5\n")

        site_packages = venv / "lib" / "python3.11" / "site-packages"
        dep_pkg = site_packages / "dummydep"
        dep_pkg.mkdir(parents=True)
        (dep_pkg / "__init__.py").write_text("VALUE = 123\n")

        mod = tmp_path / "src" / "core" / "m.py"
        mod.parent.mkdir(parents=True)
        mod.write_text(
            """
from deal import pre, post
import dummydep

@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def f(x: int) -> int:
    return x
""".lstrip()
        )

        result = run_property_tests_on_file(mod, max_examples=1, project_root=tmp_path)
        assert isinstance(result, Success)


# =============================================================================
# Phase 2: Smart Re-spawn Tests
# =============================================================================


class TestDetectProjectPythonWithInvar:
    """Tests for detect_project_python_with_invar function."""

    def test_no_venv_returns_none(self, tmp_path: Path) -> None:
        """Test that no venv returns None."""
        result = detect_project_python_with_invar(tmp_path)
        assert result is None

    def test_venv_without_invar_returns_none(self, tmp_path: Path) -> None:
        """Test that venv without invar returns None."""
        # Create mock venv without invar
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.11.5\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        # Create fake python that fails import invar
        python_path.write_text("#!/bin/sh\nexit 1\n")
        python_path.chmod(0o755)

        result = detect_project_python_with_invar(tmp_path)
        # Should return None because import invar fails
        assert result is None


class TestShouldRespawn:
    """Tests for should_respawn function."""

    def test_no_venv_no_respawn(self, tmp_path: Path) -> None:
        """Test that no venv means no respawn."""
        do_respawn, python = should_respawn(tmp_path)
        assert do_respawn is False
        assert python is None


class TestUvxRespawnCommand:
    def test_no_uvx_no_respawn(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        (venv / "bin").mkdir()
        (venv / "bin" / "python").write_text("")

        with patch("shutil.which", return_value=None):
            cmd = get_uvx_respawn_command(
                project_root=tmp_path,
                argv=["guard", str(tmp_path)],
                tool_name="invar-tools",
                invar_tools_version="1.0.0",
            )
            assert cmd is None

    def test_builds_command_with_project_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        with patch.dict(os.environ, {}, clear=True):
            with patch("shutil.which", return_value="uvx"):
                cmd = get_uvx_respawn_command(
                    project_root=tmp_path,
                    argv=["guard", str(tmp_path), "--all"],
                    tool_name="invar-tools",
                    invar_tools_version="1.2.3",
                )

        assert cmd == [
            "uvx",
            "--python",
            str(python_path),
            "--from",
            "invar-tools==1.2.3",
            "invar-tools",
            "guard",
            str(tmp_path),
            "--all",
        ]

    def test_loop_guard(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        with patch.dict(os.environ, {"INVAR_UVX_RESPAWNED": "1"}, clear=True):
            with patch("shutil.which", return_value="uvx"):
                cmd = get_uvx_respawn_command(
                    project_root=tmp_path,
                    argv=["guard", str(tmp_path)],
                    tool_name="invar-tools",
                    invar_tools_version="1.2.3",
                )
        assert cmd is None


# =============================================================================
# Phase 3: Version Mismatch Tests
# =============================================================================


class TestGetVenvPythonVersion:
    """Tests for get_venv_python_version function."""

    def test_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Test that nonexistent path returns None."""
        result = get_venv_python_version(tmp_path / "nonexistent")
        assert result is None

    def test_parses_version_from_pyvenv_cfg(self, tmp_path: Path) -> None:
        """Test parsing version from pyvenv.cfg."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text(
            "home = /usr/bin\nversion = 3.11.5\ninclude-system-site-packages = false\n"
        )

        result = get_venv_python_version(venv)
        assert result == (3, 11)

    def test_handles_version_info_format(self, tmp_path: Path) -> None:
        """Test handling version_info format."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version_info = 3.12.1\n")

        result = get_venv_python_version(venv)
        assert result == (3, 12)


class TestCheckVersionMismatch:
    """Tests for check_version_mismatch function."""

    def test_no_venv_no_mismatch(self, tmp_path: Path) -> None:
        """Test that no venv means no mismatch."""
        mismatch, msg = check_version_mismatch(tmp_path)
        assert mismatch is False
        assert msg == ""

    def test_matching_versions_no_mismatch(self, tmp_path: Path) -> None:
        """Test that matching versions don't trigger mismatch."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        # Use current Python version
        current = f"{sys.version_info.major}.{sys.version_info.minor}.0"
        (venv / "pyvenv.cfg").write_text(f"version = {current}\n")

        mismatch, msg = check_version_mismatch(tmp_path)
        assert mismatch is False
        assert msg == ""

    def test_mismatched_versions_triggers_warning(self, tmp_path: Path) -> None:
        """Test that mismatched versions trigger warning."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        # Use different version
        different_minor = (sys.version_info.minor + 1) % 20
        (venv / "pyvenv.cfg").write_text(
            f"version = {sys.version_info.major}.{different_minor}.0\n"
        )

        mismatch, msg = check_version_mismatch(tmp_path)
        assert mismatch is True
        assert "Python version mismatch" in msg
        assert "pip install invar-tools" in msg


class TestShouldSuppressPrompt:
    """Tests for should_suppress_prompt function."""

    def test_no_invar_dir_not_suppressed(self, tmp_path: Path) -> None:
        """Test that missing .invar dir doesn't suppress."""
        result = should_suppress_prompt(tmp_path)
        # First call should not suppress
        assert result is False

    def test_permanent_disable_file_suppresses(self, tmp_path: Path) -> None:
        """Test that .invar/no-upgrade-prompt suppresses."""
        invar_dir = tmp_path / ".invar"
        invar_dir.mkdir()
        (invar_dir / "no-upgrade-prompt").touch()

        result = should_suppress_prompt(tmp_path)
        assert result is True

    def test_recent_prompt_suppresses(self, tmp_path: Path) -> None:
        """Test that recent prompt suppresses subsequent calls."""
        invar_dir = tmp_path / ".invar"
        invar_dir.mkdir()
        marker = invar_dir / ".last-upgrade-prompt"
        marker.touch()

        result = should_suppress_prompt(tmp_path)
        assert result is True
