"""
Guard command helper functions.

Extracted from cli.py to reduce function sizes and improve maintainability.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Path used at runtime for path operations
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success
from rich.console import Console

if TYPE_CHECKING:
    from invar.shell.testing import VerificationLevel


console = Console()


# @shell_complexity: Git changed mode with file collection
def handle_changed_mode(
    path: Path,
) -> Result[tuple[set[Path], list[Path]], str]:
    """Handle --changed flag: get modified files from git.

    Returns (only_files set, checked_files list) on success.
    """
    from invar.shell.git import get_changed_files, is_git_repo

    if not is_git_repo(path):
        return Failure("--changed requires a git repository")

    changed_result = get_changed_files(path)
    if isinstance(changed_result, Failure):
        return Failure(changed_result.failure())

    only_files = changed_result.unwrap()
    if not only_files:
        return Failure("NO_CHANGES")  # Special marker for "no changes"

    return Success((only_files, list(only_files)))


# @shell_orchestration: Coordinates path classification and file collection
# @shell_complexity: File collection with path normalization
def collect_files_to_check(
    path: Path, checked_files: list[Path]
) -> list[Path]:
    """Collect Python files to check when not in --changed mode."""
    from invar.shell.config import get_path_classification

    if checked_files:
        return checked_files

    result_files: list[Path] = []

    path_result = get_path_classification(path)
    if isinstance(path_result, Success):
        core_paths, shell_paths = path_result.unwrap()
    else:
        core_paths, shell_paths = ["src/core"], ["src/shell"]

    # Scan core/shell paths
    for core_path in core_paths:
        full_path = path / core_path
        if full_path.exists():
            result_files.extend(full_path.rglob("*.py"))

    for shell_path in shell_paths:
        full_path = path / shell_path
        if full_path.exists():
            result_files.extend(full_path.rglob("*.py"))

    # Fallback: scan path directly
    if not result_files and path.exists():
        result_files.extend(path.rglob("*.py"))

    return result_files


# @shell_orchestration: Coordinates doctest execution via testing module
def run_doctests_phase(
    checked_files: list[Path],
    explain: bool,
    timeout: int = 60,
    collect_coverage: bool = False,
) -> tuple[bool, str, dict | None]:
    """Run doctests on collected files.

    Args:
        checked_files: Files to run doctests on
        explain: Show verbose output
        timeout: Maximum time in seconds (default: 60, from RuleConfig.timeout_doctest)
        collect_coverage: DX-37: If True, collect branch coverage data

    Returns (passed, output, coverage_data).
    """
    from invar.shell.testing import run_doctests_on_files

    if not checked_files:
        return True, "", None

    doctest_result = run_doctests_on_files(
        checked_files, verbose=explain, timeout=timeout, collect_coverage=collect_coverage
    )
    if isinstance(doctest_result, Success):
        result_data = doctest_result.unwrap()
        passed = result_data.get("status") in ("passed", "skipped")
        output = result_data.get("stdout", "")
        # DX-37: Return coverage data if collected
        coverage_data = {"collected": result_data.get("coverage_collected", False)}
        return passed, output, coverage_data if collect_coverage else None

    return False, doctest_result.failure(), None


# @shell_orchestration: Coordinates CrossHair verification via prove module
# @shell_complexity: CrossHair phase with conditional execution
def run_crosshair_phase(
    path: Path,
    checked_files: list[Path],
    doctest_passed: bool,
    static_exit_code: int,
    changed_mode: bool = False,
    timeout: int = 300,
    per_condition_timeout: int = 30,
) -> tuple[bool, dict]:
    """Run CrossHair verification phase.

    Args:
        path: Project root path
        checked_files: Files to potentially verify
        doctest_passed: Whether doctests passed
        static_exit_code: Exit code from static analysis
        changed_mode: If True, only verify git-changed files (--changed flag)
        timeout: Max time per file in seconds (default: 300)
        per_condition_timeout: Max time per contract in seconds (default: 30)

    Returns (passed, output_dict).
    """
    from invar.shell.prove.cache import ProveCache
    from invar.shell.testing import get_files_to_prove, run_crosshair_parallel

    # Skip if prior failures
    if not doctest_passed or static_exit_code != 0:
        return True, {"status": "skipped", "reason": "prior failures"}

    if not checked_files:
        return True, {"status": "skipped", "reason": "no files to verify"}

    # Only verify Core files (pure logic)
    core_files = [f for f in checked_files if "core" in str(f)]
    if not core_files:
        return True, {"status": "skipped", "reason": "no core files found"}

    # DX-13 fix: Only use git-based incremental when --changed is specified
    # Cache-based incremental still applies in run_crosshair_parallel
    files_to_prove = get_files_to_prove(path, core_files, changed_only=changed_mode)

    if not files_to_prove:
        return True, {
            "status": "verified",
            "reason": "no changes to verify",
            "files_verified": 0,
            "files_cached": len(core_files),
        }

    # Create cache and run parallel verification
    cache = ProveCache(path / ".invar" / "cache" / "prove")
    crosshair_result = run_crosshair_parallel(
        files_to_prove,
        max_iterations=5,
        max_workers=None,
        cache=cache,
        timeout=timeout,
        per_condition_timeout=per_condition_timeout,
    )

    if isinstance(crosshair_result, Success):
        output = crosshair_result.unwrap()
        passed = output.get("status") in ("verified", "skipped")
        return passed, output

    return False, {"status": "error", "error": crosshair_result.failure()}


# @shell_complexity: Status output with multiple phases
def output_verification_status(
    verification_level: VerificationLevel,
    static_exit_code: int,
    doctest_passed: bool,
    doctest_output: str,
    crosshair_output: dict,
    explain: bool,
    property_output: dict | None = None,
    strict: bool = False,
) -> None:
    """Output verification status for human-readable mode.

    DX-19: Simplified - STANDARD runs all phases (doctests + CrossHair + Hypothesis).
    DX-26: Shows combined conclusion after all phase results.
    """
    from invar.shell.testing import VerificationLevel

    # STATIC mode: no runtime tests to report (conclusion shown by output_rich)
    if verification_level == VerificationLevel.STATIC:
        return

    # DX-26: Extract passed status from phase outputs
    crosshair_passed = True
    if crosshair_output:
        crosshair_status = crosshair_output.get("status", "verified")
        crosshair_passed = crosshair_status in ("verified", "skipped")

    property_passed = True
    if property_output:
        property_status = property_output.get("status", "passed")
        property_passed = property_status in ("passed", "skipped")

    # STANDARD mode: report all test results
    if static_exit_code == 0:
        # Doctest results
        if doctest_passed:
            console.print("[green]✓ Doctests passed[/green]")
        else:
            console.print("[red]✗ Doctests failed[/red]")
            if doctest_output and explain:
                console.print(doctest_output)

        # CrossHair results
        _output_crosshair_status(
            static_exit_code, doctest_passed, crosshair_output
        )

        # Property tests results
        if property_output:
            _output_property_tests_status(
                static_exit_code, doctest_passed, property_output
            )
    else:
        console.print("[dim]⊘ Runtime tests skipped (static errors)[/dim]")

    # DX-26: Combined conclusion after all phases
    console.print("-" * 40)
    all_passed = (
        static_exit_code == 0
        and doctest_passed
        and crosshair_passed
        and property_passed
    )
    # In strict mode, warnings also cause failure (but exit code already reflects this)
    status = "passed" if all_passed else "failed"
    color = "green" if all_passed else "red"
    console.print(f"[{color}]Guard {status}.[/{color}]")


# @shell_orchestration: Coordinates shell module calls for property testing
# @shell_complexity: Property tests with result aggregation
def run_property_tests_phase(
    checked_files: list[Path],
    doctest_passed: bool,
    static_exit_code: int,
    max_examples: int = 100,
    collect_coverage: bool = False,
) -> tuple[bool, dict, dict | None]:
    """Run property tests phase (DX-08).

    Args:
        checked_files: Files to test
        doctest_passed: Whether doctests passed
        static_exit_code: Exit code from static analysis
        max_examples: Maximum Hypothesis examples per function
        collect_coverage: DX-37: If True, collect branch coverage data

    Returns (passed, output_dict, coverage_data).
    """
    from invar.shell.property_tests import run_property_tests_on_files

    # Skip if prior failures
    if not doctest_passed or static_exit_code != 0:
        return True, {"status": "skipped", "reason": "prior failures"}, None

    if not checked_files:
        return True, {"status": "skipped", "reason": "no files"}, None

    # Only test Core files (with contracts)
    core_files = [f for f in checked_files if "core" in str(f)]
    if not core_files:
        return True, {"status": "skipped", "reason": "no core files"}, None

    result = run_property_tests_on_files(core_files, max_examples, collect_coverage=collect_coverage)

    if isinstance(result, Success):
        report, coverage_data = result.unwrap()
        # DX-26: Build structured failures array for actionable output
        failures = [
            {
                "function": r.function_name,
                "file_path": r.file_path,
                "error": r.error,
                "seed": r.seed,
            }
            for r in report.results
            if not r.passed
        ]
        return report.all_passed(), {
            "status": "passed" if report.all_passed() else "failed",
            "functions_tested": report.functions_tested,
            "functions_passed": report.functions_passed,
            "functions_failed": report.functions_failed,
            "total_examples": report.total_examples,
            "failures": failures,  # DX-26: Structured failure info
            "errors": report.errors,
        }, coverage_data

    return False, {"status": "error", "error": result.failure()}, None


# @shell_complexity: Property test status formatting
def _output_property_tests_status(
    static_exit_code: int,
    doctest_passed: bool,
    property_output: dict,
) -> None:
    """Output property tests status (DX-08, DX-26).

    DX-26: Show file::function format and reproduction command for failures.
    """
    if static_exit_code != 0 or not doctest_passed:
        console.print("[dim]⊘ Property tests skipped (prior failures)[/dim]")
        return

    status = property_output.get("status", "unknown")

    if status == "passed":
        tested = property_output.get("functions_tested", 0)
        examples = property_output.get("total_examples", 0)
        console.print(
            f"[green]✓ Property tests passed[/green] "
            f"[dim]({tested} functions, {examples} examples)[/dim]"
        )
    elif status == "skipped":
        reason = property_output.get("reason", "no contracted functions")
        console.print(f"[dim]⊘ Property tests skipped ({reason})[/dim]")
    elif status == "failed":
        failed = property_output.get("functions_failed", 0)
        console.print(f"[red]✗ Property tests failed ({failed} functions)[/red]")
        # DX-26: Show actionable failure info
        for failure in property_output.get("failures", [])[:5]:
            file_path = failure.get("file_path", "")
            func_name = failure.get("function", "unknown")
            seed = failure.get("seed")
            error = failure.get("error", "")

            # Show file::function format
            location = f"{file_path}::{func_name}" if file_path else func_name
            console.print(f"  [red]✗[/red] {location}")

            # Show truncated error
            if error:
                short_error = error[:100] + "..." if len(error) > 100 else error
                console.print(f"    {short_error}")

            # Show reproduction command with seed
            if seed:
                console.print(
                    f"    [dim]Reproduce: python -c \"from hypothesis import reproduce_failure; "
                    f"import {func_name}\" --seed={seed}[/dim]"
                )
        # Fallback for errors without structured failures
        for error in property_output.get("errors", [])[:5]:
            console.print(f"  [yellow]![/yellow] {error}")
    else:
        console.print(f"[yellow]! Property tests: {status}[/yellow]")


# @shell_complexity: CrossHair status formatting
def _output_crosshair_status(
    static_exit_code: int,
    doctest_passed: bool,
    crosshair_output: dict,
) -> None:
    """Output CrossHair verification status."""
    if static_exit_code != 0 or not doctest_passed:
        console.print("[dim]⊘ CrossHair skipped (prior failures)[/dim]")
        return

    status = crosshair_output.get("status", "unknown")

    if status == "verified":
        verified_count = crosshair_output.get("files_verified", 0)
        cached_count = crosshair_output.get("files_cached", 0)
        time_ms = crosshair_output.get("total_time_ms", 0)
        workers = crosshair_output.get("workers", 1)

        if verified_count == 0 and cached_count > 0:
            reason = crosshair_output.get("reason", "cached")
            console.print(f"[green]✓ CrossHair verified ({reason})[/green]")
        elif time_ms > 0:
            time_sec = time_ms / 1000
            stats = f"{verified_count} verified"
            if cached_count > 0:
                stats += f", {cached_count} cached"
            if workers > 1:
                stats += f", {workers} workers"
            console.print(
                f"[green]✓ CrossHair verified[/green] "
                f"[dim]({stats}, {time_sec:.1f}s)[/dim]"
            )
        else:
            console.print("[green]✓ CrossHair verified[/green]")
    elif status == "skipped":
        reason = crosshair_output.get("reason", "no files")
        console.print(f"[dim]⊘ CrossHair skipped ({reason})[/dim]")
    else:
        console.print("[yellow]! CrossHair found counterexamples[/yellow]")
        for ce in crosshair_output.get("counterexamples", [])[:5]:
            console.print(f"  {ce}")
