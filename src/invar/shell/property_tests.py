"""
Property test runner for files and directories.

DX-08: Shell module for running auto-generated property tests.
Handles I/O and file scanning, returns Result[T, E].
"""

from __future__ import annotations

import sys
import tomllib
from contextlib import contextmanager, suppress
from pathlib import Path

from returns.result import Failure, Result, Success
from rich.console import Console

from invar.core.property_gen import PropertyTestReport, find_contracted_functions
from invar.core.property_runner import run_property_test
from invar.shell.subprocess_env import detect_project_venv, find_site_packages

console = Console()


def _extract_src_dirs_from_paths(project_root: Path, paths: list[str]) -> set[str]:
    """
    Extract unique src directories from configured paths.

    For monorepo structures like 'packages/pkg-a/src/pkg_a/core',
    extracts 'packages/pkg-a/src' as the directory to add to sys.path.

    Examples:
        >>> from pathlib import Path
        >>> root = Path("/project")
        >>> paths = ["packages/a/src/pkg/core", "packages/b/src/pkg/shell"]
        >>> # Returns src dirs (would check existence in real use)
        >>> sorted(_extract_src_dirs_from_paths(root, paths))  # doctest: +SKIP
        ['/project/packages/a/src', '/project/packages/b/src']
    """
    src_dirs: set[str] = set()
    for p in paths:
        parts = Path(p).parts
        if "src" in parts:
            idx = parts.index("src")
            src_dir = project_root / Path(*parts[: idx + 1])
            if src_dir.exists():
                src_dirs.add(str(src_dir))
    return src_dirs


# @shell_complexity: Config fallthrough requires checking 2 sources with error handling
def _get_invar_paths_from_config(project_root: Path) -> list[str]:
    """
    Get 'paths' from [tool.invar] config across all config locations.

    Checks in priority order:
    1. pyproject.toml [tool.invar].paths
    2. invar.toml [invar].paths (root level)

    Returns first found, or empty list.
    """
    # 1. pyproject.toml [tool.invar].paths
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
            paths = data.get("tool", {}).get("invar", {}).get("paths", [])
            if paths:
                return paths
        except Exception:
            pass

    # 2. invar.toml [invar].paths (root level, since no [tool] wrapper)
    invar_toml = project_root / "invar.toml"
    if invar_toml.exists():
        try:
            with invar_toml.open("rb") as f:
                data = tomllib.load(f)
            # In invar.toml, paths could be at root or under [invar]
            paths = data.get("paths", []) or data.get("invar", {}).get("paths", [])
            if paths:
                return paths
        except Exception:
            pass

    return []


# @shell_orchestration: Temporarily inject venv site-packages for module imports
# @shell_complexity: Monorepo support requires reading config and extracting src dirs
@contextmanager
def _inject_project_site_packages(project_root: Path):
    """
    Context manager that temporarily injects project dependencies into sys.path.

    Supports:
    - Standard layout: project_root/src
    - Monorepo layout: paths from config (pyproject.toml, invar.toml)
    - Configured paths: extracted from core_paths/shell_paths in [tool.invar.guard]
    """
    from invar.shell.config import get_path_classification

    venv = detect_project_venv(project_root)
    site_packages = find_site_packages(venv) if venv is not None else None

    if site_packages is None:
        yield
        return

    added: list[str] = []

    # 1. Read 'paths' from config (supports pyproject.toml, invar.toml)
    invar_paths = _get_invar_paths_from_config(project_root)
    for p in invar_paths:
        src_dir = project_root / p
        if src_dir.exists():
            src_dir_str = str(src_dir)
            if src_dir_str not in added:
                sys.path.insert(0, src_dir_str)
                added.append(src_dir_str)

    # 2. Extract src dirs from core_paths and shell_paths config
    path_result = get_path_classification(project_root)
    if isinstance(path_result, Success):
        core_paths, shell_paths = path_result.unwrap()
        src_dirs = _extract_src_dirs_from_paths(project_root, core_paths + shell_paths)
        for src_dir_str in src_dirs:
            if src_dir_str not in added:
                sys.path.insert(0, src_dir_str)
                added.append(src_dir_str)

    # 3. Fallback to project_root/src (standard layout)
    src_dir = project_root / "src"
    if src_dir.exists():
        src_dir_str = str(src_dir)
        if src_dir_str not in added:
            sys.path.insert(0, src_dir_str)
            added.append(src_dir_str)

    site_packages_str = str(site_packages)
    sys.path.insert(0, site_packages_str)
    added.append(site_packages_str)

    try:
        yield
    finally:
        for p in added:
            with suppress(ValueError):
                sys.path.remove(p)


# @shell_complexity: Property test orchestration with module import
def run_property_tests_on_file(
    file_path: Path,
    max_examples: int = 100,
    verbose: bool = False,
    project_root: Path | None = None,
) -> Result[PropertyTestReport, str]:
    """
    Run property tests on all contracted functions in a file.

    Scans file for @pre/@post decorated functions, generates
    Hypothesis tests, and runs them.

    Args:
        file_path: Path to Python file
        max_examples: Maximum Hypothesis examples per function
        verbose: Show detailed output

    Returns:
        Success with PropertyTestReport or Failure with error
    """
    if not file_path.exists():
        return Failure(f"File not found: {file_path}")

    if file_path.suffix != ".py":
        return Failure(f"Not a Python file: {file_path}")

    # Read and find contracted functions
    try:
        source = file_path.read_text()
    except OSError as e:
        return Failure(f"Could not read file: {e}")

    # Handle empty files gracefully
    if not source.strip():
        return Success(PropertyTestReport())

    contracted = find_contracted_functions(source)
    if not contracted:
        return Success(PropertyTestReport())  # No contracted functions, skip

    root = project_root or file_path.parent
    with _inject_project_site_packages(root):
        module = _import_module_from_path(file_path, project_root=root)

    if module is None:
        return Failure(f"Could not import module: {file_path}")

    # Run tests on each contracted function
    report = PropertyTestReport()
    file_path_str = str(file_path)  # DX-26: For actionable output

    for func_info in contracted:
        func_name = func_info["name"]
        func = getattr(module, func_name, None)

        if func is None or not callable(func):
            report.functions_skipped += 1
            continue

        # Run property test
        result = run_property_test(func, max_examples)
        # DX-26: Set file_path for actionable failure output
        result.file_path = file_path_str
        report.results.append(result)
        report.functions_tested += 1
        report.total_examples += result.examples_run

        if result.passed:
            report.functions_passed += 1
        else:
            report.functions_failed += 1

    return Success(report)


# @shell_complexity: Property test orchestration with optional coverage collection
def run_property_tests_on_files(
    files: list[Path],
    max_examples: int = 100,
    verbose: bool = False,
    collect_coverage: bool = False,
    project_root: Path | None = None,
) -> Result[tuple[PropertyTestReport, dict | None], str]:
    """
    Run property tests on multiple files.

    Args:
        files: List of Python file paths
        max_examples: Maximum Hypothesis examples per function
        verbose: Show detailed output
        collect_coverage: DX-37: If True, collect branch coverage data

    Returns:
        Tuple of (PropertyTestReport, coverage_data) where coverage_data is dict or None
    """
    # Check hypothesis availability first
    try:
        import hypothesis  # noqa: F401
    except ImportError:
        return Success(
            (PropertyTestReport(errors=["Hypothesis not installed (pip install hypothesis)"]), None)
        )

    combined_report = PropertyTestReport()
    coverage_data = None

    # DX-37: Optional coverage collection for hypothesis tests
    if collect_coverage:
        try:
            from invar.shell.coverage import collect_coverage as cov_ctx
            from invar.shell.coverage import extract_coverage_report

            source_dirs = list({f.parent for f in files})
            with cov_ctx(source_dirs) as cov:
                for file_path in files:
                    result = run_property_tests_on_file(
                        file_path, max_examples, verbose, project_root=project_root
                    )
                    _accumulate_report(combined_report, result)

                # Extract coverage after all tests
                coverage_report = extract_coverage_report(cov, files, "hypothesis")
                coverage_data = {
                    "collected": True,
                    "overall_branch_coverage": coverage_report.overall_branch_coverage,
                    "files": len(coverage_report.files),
                }
        except ImportError:
            # coverage not installed, run without it
            for file_path in files:
                result = run_property_tests_on_file(
                    file_path, max_examples, verbose, project_root=project_root
                )
                _accumulate_report(combined_report, result)
    else:
        for file_path in files:
            result = run_property_tests_on_file(
                file_path, max_examples, verbose, project_root=project_root
            )
            _accumulate_report(combined_report, result)

    return Success((combined_report, coverage_data))


def _accumulate_report(
    combined_report: PropertyTestReport,
    result: Result[PropertyTestReport, str],
) -> None:
    """Accumulate a file result into the combined report."""
    if isinstance(result, Failure):
        combined_report.errors.append(result.failure())
        return

    file_report = result.unwrap()
    combined_report.functions_tested += file_report.functions_tested
    combined_report.functions_passed += file_report.functions_passed
    combined_report.functions_failed += file_report.functions_failed
    combined_report.functions_skipped += file_report.functions_skipped
    combined_report.total_examples += file_report.total_examples
    combined_report.results.extend(file_report.results)
    combined_report.errors.extend(file_report.errors)


# @shell_complexity: Path traversal logic for monorepo src detection
def _find_module_root(file_path: Path, project_root: Path | None) -> Path | None:
    """
    Find the module root directory (the directory that should be in sys.path).

    For monorepo structures, finds the 'src' directory containing the file.
    Falls back to project_root for standard layouts.

    Examples:
        >>> from pathlib import Path
        >>> # Standard layout: project/src/pkg/module.py -> project/src
        >>> # Monorepo: project/packages/a/src/pkg/module.py -> project/packages/a/src
    """
    if project_root is None:
        return None

    # Check if file is under a 'src' directory
    try:
        relative = file_path.relative_to(project_root)
        parts = relative.parts

        if "src" in parts:
            idx = parts.index("src")
            # Return the src directory itself
            return project_root / Path(*parts[: idx + 1])
    except ValueError:
        pass

    # Fallback: check if project_root/src exists and contains the file
    src_dir = project_root / "src"
    if src_dir.exists():
        try:
            file_path.relative_to(src_dir)
            return src_dir
        except ValueError:
            pass

    return project_root


# @shell_complexity: BUG-57 fix requires package hierarchy setup for relative imports
def _import_module_from_path(file_path: Path, project_root: Path | None = None) -> object | None:
    """
    Import a Python module from a file path.

    BUG-57: Properly handles relative imports by setting up package context.
    Monorepo fix: Calculates module name relative to src directory, not project root.

    Returns None if import fails.
    """
    import importlib

    try:
        # Find the module root (src directory) for this file
        module_root = _find_module_root(file_path, project_root)

        # Calculate module name relative to module_root (not project_root!)
        if module_root and file_path.is_relative_to(module_root):
            relative = file_path.relative_to(module_root)
            parts = list(relative.with_suffix("").parts)
            module_name = ".".join(parts)
        elif project_root and file_path.is_relative_to(project_root):
            # Fallback to project_root relative path
            relative = file_path.relative_to(project_root)
            parts = list(relative.with_suffix("").parts)
            module_name = ".".join(parts)
        else:
            module_name = file_path.stem

        # Ensure module root is in sys.path
        if module_root:
            root_str = str(module_root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)

        # Use importlib.import_module which correctly handles relative imports
        # This is simpler and more reliable than manual spec loading
        module = importlib.import_module(module_name)
        return module

    except Exception:
        return None


# @shell_orchestration: Formatting helper tightly coupled to CLI output
# @shell_complexity: Report formatting with JSON/rich output modes
def format_property_test_report(
    report: PropertyTestReport,
    json_output: bool = False,
) -> str:
    """
    Format property test report for display.

    Args:
        report: The test report
        json_output: Output as JSON

    Returns:
        Formatted string
    """
    import json

    if json_output:
        return json.dumps(
            {
                "functions_tested": report.functions_tested,
                "functions_passed": report.functions_passed,
                "functions_failed": report.functions_failed,
                "functions_skipped": report.functions_skipped,
                "total_examples": report.total_examples,
                "all_passed": report.all_passed(),
                "results": [
                    {
                        "function": r.function_name,
                        "passed": r.passed,
                        "examples": r.examples_run,
                        "error": r.error,
                        "file_path": r.file_path,  # DX-26
                        "seed": r.seed,  # DX-26
                    }
                    for r in report.results
                ],
                "errors": report.errors,
            },
            indent=2,
        )

    # Human-readable format
    lines = []

    if report.functions_tested == 0:
        lines.append("No contracted functions found for property testing.")
        return "\n".join(lines)

    status = "✓" if report.all_passed() else "✗"
    color = "green" if report.all_passed() else "red"

    lines.append(
        f"[{color}]{status}[/{color}] Property tests: "
        f"{report.functions_passed}/{report.functions_tested} passed, "
        f"{report.total_examples} examples"
    )

    # Show failures (DX-26: actionable format)
    for result in report.results:
        if not result.passed:
            # DX-26: file::function format
            location = (
                f"{result.file_path}::{result.function_name}"
                if result.file_path
                else result.function_name
            )
            lines.append(f"  [red]✗[/red] {location}")
            if result.error:
                short_error = (
                    result.error[:100] + "..." if len(result.error) > 100 else result.error
                )
                lines.append(f"      {short_error}")
            if result.seed:
                lines.append(f"      [dim]Seed: {result.seed}[/dim]")
            if result.hint:
                lines.append(f"      [dim]Hint: {result.hint}[/dim]")

    # Show errors
    for error in report.errors:
        lines.append(f"  [yellow]![/yellow] {error}")

    return "\n".join(lines)
