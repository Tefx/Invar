"""
Property test runner for files and directories.

DX-08: Shell module for running auto-generated property tests.
Handles I/O and file scanning, returns Result[T, E].
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success
from rich.console import Console

from invar.core.property_gen import (
    PropertyTestReport,
    PropertyTestResult,
    find_contracted_functions,
    run_property_test,
)

if TYPE_CHECKING:
    from collections.abc import Callable

console = Console()


def run_property_tests_on_file(
    file_path: Path,
    max_examples: int = 100,
    verbose: bool = False,
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

    # Import the module to get actual function objects
    module = _import_module_from_path(file_path)
    if module is None:
        return Failure(f"Could not import module: {file_path}")

    # Run tests on each contracted function
    report = PropertyTestReport()

    for func_info in contracted:
        func_name = func_info["name"]
        func = getattr(module, func_name, None)

        if func is None or not callable(func):
            report.functions_skipped += 1
            continue

        # Run property test
        result = run_property_test(func, max_examples)
        report.results.append(result)
        report.functions_tested += 1
        report.total_examples += result.examples_run

        if result.passed:
            report.functions_passed += 1
        else:
            report.functions_failed += 1

    return Success(report)


def run_property_tests_on_files(
    files: list[Path],
    max_examples: int = 100,
    verbose: bool = False,
) -> Result[PropertyTestReport, str]:
    """
    Run property tests on multiple files.

    Args:
        files: List of Python file paths
        max_examples: Maximum Hypothesis examples per function
        verbose: Show detailed output

    Returns:
        Combined PropertyTestReport
    """
    # Check hypothesis availability first
    try:
        import hypothesis  # noqa: F401
    except ImportError:
        return Success(PropertyTestReport(
            errors=["Hypothesis not installed (pip install hypothesis)"]
        ))

    combined_report = PropertyTestReport()

    for file_path in files:
        result = run_property_tests_on_file(file_path, max_examples, verbose)

        if isinstance(result, Failure):
            combined_report.errors.append(result.failure())
            continue

        file_report = result.unwrap()
        combined_report.functions_tested += file_report.functions_tested
        combined_report.functions_passed += file_report.functions_passed
        combined_report.functions_failed += file_report.functions_failed
        combined_report.functions_skipped += file_report.functions_skipped
        combined_report.total_examples += file_report.total_examples
        combined_report.results.extend(file_report.results)
        combined_report.errors.extend(file_report.errors)

    return Success(combined_report)


def _import_module_from_path(file_path: Path) -> object | None:
    """
    Import a Python module from a file path.

    Returns None if import fails.
    """
    try:
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        # Suppress output during import
        spec.loader.exec_module(module)
        return module

    except Exception:
        return None


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
        return json.dumps({
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
                }
                for r in report.results
            ],
            "errors": report.errors,
        }, indent=2)

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

    # Show failures
    for result in report.results:
        if not result.passed:
            lines.append(f"  [red]✗[/red] {result.function_name}: {result.error}")

    # Show errors
    for error in report.errors:
        lines.append(f"  [yellow]![/yellow] {error}")

    return "\n".join(lines)
