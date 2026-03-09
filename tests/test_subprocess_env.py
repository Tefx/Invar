"""Tests for DX-52 subprocess environment preparation.

Tests PYTHONPATH injection, re-spawn detection, and version mismatch detection.
"""

from __future__ import annotations

import importlib
import os
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from returns.result import Success

from invar.shell.guard_helpers import collect_files_to_check
from invar.shell.property_tests import (
    _import_module_from_path,
    _inject_project_site_packages,
    run_property_tests_on_file,
)
from invar.shell.subprocess_env import (
    build_subprocess_env,
    check_version_mismatch,
    detect_local_invar_source,
    detect_project_python_with_invar,
    detect_project_venv,
    detect_running_invar_source,
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
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.0"
        (venv / "pyvenv.cfg").write_text(f"version = {py_version}\n")

        site_packages = (
            venv
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
        dep_pkg = site_packages / "dummydep"
        dep_pkg.mkdir(parents=True)
        (dep_pkg / "__init__.py").write_text("VALUE = 123\n")

        mod = tmp_path / "src" / "core" / "m.py"
        mod.parent.mkdir(parents=True)
        (mod.parent / "__init__.py").write_text("")
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

    def test_import_module_from_path_extends_loaded_package_paths(self, tmp_path: Path) -> None:
        site_root = tmp_path / "site"
        installed_pkg = site_root / "demo" / "core"
        installed_pkg.mkdir(parents=True)
        (site_root / "demo" / "__init__.py").write_text("")
        (installed_pkg / "__init__.py").write_text("")

        local_module = tmp_path / "src" / "demo" / "core" / "dead_param.py"
        local_module.parent.mkdir(parents=True)
        (local_module.parent / "__init__.py").write_text("")
        (local_module.parent / "dead_param_helpers.py").write_text("VALUE = 7\n")
        local_module.write_text("from demo.core.dead_param_helpers import VALUE\nANSWER = VALUE\n")

        inserted = str(site_root)
        sys.path.insert(0, inserted)
        try:
            demo_core = importlib.import_module("demo.core")
            module = _import_module_from_path(local_module, project_root=tmp_path)

            assert module is not None
            assert getattr(module, "ANSWER", None) == 7
            assert str(tmp_path / "src" / "demo" / "core") in list(demo_core.__path__)
        finally:
            sys.modules.pop("demo.core.dead_param", None)
            sys.modules.pop("demo.core.dead_param_helpers", None)
            sys.modules.pop("demo.core", None)
            sys.modules.pop("demo", None)
            if inserted in sys.path:
                sys.path.remove(inserted)

    def test_import_module_from_path_prioritizes_workspace_overlay(self, tmp_path: Path) -> None:
        site_root = tmp_path / "site"
        installed_pkg = site_root / "demo" / "core"
        installed_pkg.mkdir(parents=True)
        (site_root / "demo" / "__init__.py").write_text("")
        (installed_pkg / "__init__.py").write_text("")
        (installed_pkg / "dead_param_helpers.py").write_text("VALUE = 1\n")

        local_module = tmp_path / "src" / "demo" / "core" / "dead_param.py"
        local_module.parent.mkdir(parents=True)
        (local_module.parent / "__init__.py").write_text("")
        (local_module.parent / "dead_param_helpers.py").write_text("VALUE = 7\n")
        local_module.write_text("from demo.core.dead_param_helpers import VALUE\nANSWER = VALUE\n")

        inserted = str(site_root)
        sys.path.insert(0, inserted)
        try:
            demo_core = importlib.import_module("demo.core")
            module = _import_module_from_path(local_module, project_root=tmp_path)

            assert module is not None
            assert getattr(module, "ANSWER", None) == 7
            assert str(tmp_path / "src" / "demo" / "core") == list(demo_core.__path__)[0]
        finally:
            sys.modules.pop("demo.core.dead_param", None)
            sys.modules.pop("demo.core.dead_param_helpers", None)
            sys.modules.pop("demo.core", None)
            sys.modules.pop("demo", None)
            if inserted in sys.path:
                sys.path.remove(inserted)

    def test_inject_project_site_packages_keeps_src_before_site_packages(
        self, tmp_path: Path
    ) -> None:
        package_name = "overlaydemo"
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.0"
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text(f"version = {py_version}\n")

        site_packages = (
            venv
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
        installed_core = site_packages / package_name / "core"
        installed_core.mkdir(parents=True)
        (site_packages / package_name / "__init__.py").write_text("")
        (installed_core / "__init__.py").write_text("")

        local_module = tmp_path / "src" / package_name / "core" / "dead_param.py"
        local_module.parent.mkdir(parents=True)
        (local_module.parent.parent / "__init__.py").write_text("")
        (local_module.parent / "__init__.py").write_text("")
        (local_module.parent / "dead_param_helpers.py").write_text("VALUE = 7\n")
        local_module.write_text(
            f"from {package_name}.core.dead_param_helpers import VALUE\nANSWER = VALUE\n"
        )

        for name in (
            f"{package_name}.core.dead_param",
            f"{package_name}.core.dead_param_helpers",
            f"{package_name}.core",
            package_name,
        ):
            sys.modules.pop(name, None)

        with _inject_project_site_packages(tmp_path):
            module = _import_module_from_path(local_module, project_root=tmp_path)

        assert module is not None
        assert getattr(module, "ANSWER", None) == 7


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

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                return_value=None,
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ),
        ):
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

    def test_normalizes_non_console_tool_name_to_invar(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                return_value=None,
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ),
        ):
            cmd = get_uvx_respawn_command(
                project_root=tmp_path,
                argv=["guard", str(tmp_path), "--all"],
                tool_name="guard.py",
                invar_tools_version="1.2.3",
            )

        assert cmd == [
            "uvx",
            "--python",
            str(python_path),
            "--from",
            "invar-tools==1.2.3",
            "invar",
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

        with (
            patch.dict(os.environ, {"INVAR_UVX_RESPAWNED": "1"}, clear=True),
            patch("shutil.which", return_value="uvx"),
        ):
            cmd = get_uvx_respawn_command(
                project_root=tmp_path,
                argv=["guard", str(tmp_path)],
                tool_name="invar-tools",
                invar_tools_version="1.2.3",
            )
        assert cmd is None

    def test_skips_respawn_when_pinned_source_cannot_resolve(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                return_value=None,
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.subprocess.run",
                return_value=SimpleNamespace(returncode=1),
            ) as probe,
        ):
            cmd = get_uvx_respawn_command(
                project_root=tmp_path,
                argv=["guard", str(tmp_path), "--all"],
                tool_name="invar-tools",
                invar_tools_version="1.2.3",
            )

        assert cmd is None
        probe.assert_called_once()

    def test_builds_respawn_when_pinned_source_probe_passes(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                return_value=None,
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as probe,
        ):
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
        probe.assert_called_once()

    def test_prefers_local_source_checkout(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        local_src = tmp_path / "local-invar"
        (local_src / "src" / "invar").mkdir(parents=True)
        (local_src / "pyproject.toml").write_text(
            '[project]\nname = "invar-tools"\nversion = "1.2.3"\n'
        )

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                side_effect=[local_src, None],
            ),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
        ):
            cmd = get_uvx_respawn_command(
                project_root=tmp_path,
                argv=["guard", str(tmp_path), "--all"],
                tool_name="invar",
                invar_tools_version="1.2.3",
            )

        assert cmd == [
            "uvx",
            "--python",
            str(python_path),
            "--from",
            str(local_src),
            "invar",
            "guard",
            str(tmp_path),
            "--all",
        ]

    def test_prefers_local_source_even_without_version_mismatch(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        local_src = tmp_path / "local-invar"
        (local_src / "src" / "invar").mkdir(parents=True)
        (local_src / "pyproject.toml").write_text(
            '[project]\nname = "invar-tools"\nversion = "1.2.3"\n'
        )

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                side_effect=[local_src, None],
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=12),
            ),
        ):
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
            str(local_src),
            "invar-tools",
            "guard",
            str(tmp_path),
            "--all",
        ]

    def test_prefers_invocation_root_checkout_for_external_project(self, tmp_path: Path) -> None:
        external_project = tmp_path / "external-project"
        external_project.mkdir()
        (external_project / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = external_project / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        local_src = tmp_path / "invar-checkout"
        (local_src / "src" / "invar").mkdir(parents=True)
        (local_src / "pyproject.toml").write_text(
            '[project]\nname = "invar-tools"\nversion = "1.2.3"\n'
        )

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                side_effect=[None, local_src, None],
            ),
            patch("invar.shell.subprocess_env.detect_running_invar_source", return_value=None),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=12),
            ),
        ):
            cmd = get_uvx_respawn_command(
                project_root=external_project,
                argv=["guard", "--all", str(external_project)],
                tool_name="invar",
                invar_tools_version="1.2.3",
                invocation_root=local_src,
            )

        assert cmd == [
            "uvx",
            "--python",
            str(python_path),
            "--from",
            str(local_src),
            "invar",
            "guard",
            "--all",
            str(external_project),
        ]

    def test_uses_running_source_for_version_mismatch_respawn(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.0'\n")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.12.0\n")
        python_path = venv / "bin" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.write_text("")

        running_src = tmp_path / "running-invar"
        (running_src / "src" / "invar").mkdir(parents=True)
        (running_src / "pyproject.toml").write_text(
            '[project]\nname = "invar-tools"\nversion = "1.2.3"\n'
        )

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("shutil.which", return_value="uvx"),
            patch(
                "invar.shell.subprocess_env.sys.version_info",
                SimpleNamespace(major=3, minor=11),
            ),
            patch(
                "invar.shell.subprocess_env.detect_local_invar_source",
                side_effect=[None, running_src],
            ),
            patch(
                "invar.shell.subprocess_env.detect_running_invar_source", return_value=running_src
            ),
        ):
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
            str(running_src),
            "invar-tools",
            "guard",
            str(tmp_path),
            "--all",
        ]


class TestDetectRunningInvarSource:
    def test_returns_none_when_direct_url_missing(self) -> None:
        dist = SimpleNamespace(read_text=lambda _name: None)
        with patch("invar.shell.subprocess_env.metadata.distribution", return_value=dist):
            assert detect_running_invar_source() is None

    def test_detects_local_source_from_direct_url(self, tmp_path: Path) -> None:
        repo = tmp_path / "invar-repo"
        (repo / "src" / "invar").mkdir(parents=True)
        (repo / "pyproject.toml").write_text('[project]\nname = "invar-tools"\nversion = "0.0.0"\n')

        direct_url = '{"url":"file://' + str(repo) + '"}'
        dist = SimpleNamespace(read_text=lambda _name: direct_url)
        with patch("invar.shell.subprocess_env.metadata.distribution", return_value=dist):
            assert detect_running_invar_source() == repo


class TestDetectLocalInvarSource:
    def test_returns_none_when_not_checkout(self, tmp_path: Path) -> None:
        fake_module = tmp_path / "site-packages" / "invar" / "shell" / "subprocess_env.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("")

        assert detect_local_invar_source(fake_module) is None

    def test_detects_checkout_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "invar-repo"
        module_path = repo / "src" / "invar" / "shell" / "subprocess_env.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")
        (repo / "src" / "invar" / "__init__.py").write_text("")
        (repo / "pyproject.toml").write_text('[project]\nname = "invar-tools"\nversion = "0.0.0"\n')

        assert detect_local_invar_source(module_path) == repo

    def test_detects_checkout_root_from_project_root_hint(self, tmp_path: Path) -> None:
        repo = tmp_path / "invar-repo"
        module_path = tmp_path / "site-packages" / "invar" / "shell" / "subprocess_env.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")

        (repo / "src" / "invar" / "__init__.py").parent.mkdir(parents=True)
        (repo / "src" / "invar" / "__init__.py").write_text("")
        (repo / "pyproject.toml").write_text('[project]\nname = "invar-tools"\nversion = "0.0.0"\n')

        nested_cwd = repo / "packages" / "demo"
        nested_cwd.mkdir(parents=True)

        assert detect_local_invar_source(module_path, project_root=nested_cwd) == repo

    def test_detects_checkout_root_when_project_root_is_repo_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "invar-repo"
        module_path = tmp_path / "site-packages" / "invar" / "shell" / "subprocess_env.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")

        (repo / "src" / "invar" / "__init__.py").parent.mkdir(parents=True)
        (repo / "src" / "invar" / "__init__.py").write_text("")
        (repo / "pyproject.toml").write_text('[project]\nname = "invar-tools"\nversion = "0.0.0"\n')

        assert detect_local_invar_source(module_path, project_root=repo) == repo


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
