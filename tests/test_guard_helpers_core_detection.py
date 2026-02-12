"""Regression tests for core file detection in runtime phases.

This guards against a path-normalization bug where Path.relative_to() raises
ValueError due to unresolved project_root (e.g. containing ".."), causing the
code to fall back to absolute paths that can never match configured core_paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

from returns.result import Success

from invar.shell.guard_helpers import run_crosshair_phase, run_property_tests_phase


@dataclass(frozen=True)
class _FakePropertyResult:
    passed: bool
    function_name: str = "f"
    file_path: str = ""
    error: str = ""
    seed: int | None = None


@dataclass(frozen=True)
class _FakePropertyReport:
    results: list[_FakePropertyResult]
    functions_tested: int
    functions_passed: int
    functions_failed: int
    total_examples: int
    errors: list[str]

    def all_passed(self) -> bool:
        return True


def _write_min_pyproject(project_root: Path) -> None:
    (project_root / "pyproject.toml").write_text(
        (
            """
[project]
name = "tmp"
version = "0.0.0"

[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
""".lstrip()
        ),
        encoding="utf-8",
    )


def test_crosshair_phase_detects_core_files_with_unresolved_root(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    (project_root / "src" / "core").mkdir(parents=True)
    (project_root / "src" / "shell").mkdir(parents=True)
    _write_min_pyproject(project_root)

    core_file = project_root / "src" / "core" / "a.py"
    core_file.write_text("x = 1\n", encoding="utf-8")

    # Unresolved root path: contains ".." and would previously break relative_to().
    (project_root / "sub").mkdir()
    unresolved_root = Path(str(project_root / "sub" / ".."))

    with patch(
        "invar.shell.testing.get_files_to_prove",
        autospec=True,
        return_value=[],
    ) as get_files_to_prove:
        passed, output = run_crosshair_phase(
            path=unresolved_root,
            checked_files=[core_file.resolve()],
            doctest_passed=True,
            static_exit_code=0,
        )

    assert passed is True
    assert output.get("status") == "verified"

    called_args, called_kwargs = get_files_to_prove.call_args
    called_path, called_core_files = called_args
    assert called_path == unresolved_root
    assert any(p.resolve() == core_file.resolve() for p in called_core_files)
    assert called_kwargs.get("changed_only") is False


def test_property_tests_phase_detects_core_files_with_unresolved_root(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    (project_root / "src" / "core").mkdir(parents=True)
    _write_min_pyproject(project_root)

    core_file = project_root / "src" / "core" / "a.py"
    core_file.write_text(
        (
            """
from deal import pre, post


@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def f(x: int) -> int:
    return x
""".lstrip()
        ),
        encoding="utf-8",
    )

    (project_root / "sub").mkdir()
    unresolved_root = Path(str(project_root / "sub" / ".."))

    fake_report = _FakePropertyReport(
        results=[],
        functions_tested=1,
        functions_passed=1,
        functions_failed=0,
        total_examples=1,
        errors=[],
    )

    def _fake_run_property_tests_on_files(*args: Any, **kwargs: Any) -> Success:
        core_files = args[0]
        assert any(Path(p).resolve() == core_file.resolve() for p in core_files)
        return Success((fake_report, None))

    with patch(
        "invar.shell.property_tests.run_property_tests_on_files",
        autospec=True,
        side_effect=_fake_run_property_tests_on_files,
    ):
        passed, output, coverage_data = run_property_tests_phase(
            project_root=unresolved_root,
            checked_files=[core_file.resolve()],
            doctest_passed=True,
            static_exit_code=0,
            max_examples=1,
        )

    assert passed is True
    assert output.get("status") == "passed"
    assert coverage_data is None
