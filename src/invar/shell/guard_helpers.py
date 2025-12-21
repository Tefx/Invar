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


def run_doctests_phase(
    checked_files: list[Path], explain: bool
) -> tuple[bool, str]:
    """Run doctests on collected files.

    Returns (passed, output).
    """
    from invar.shell.testing import run_doctests_on_files

    if not checked_files:
        return True, ""

    doctest_result = run_doctests_on_files(checked_files, verbose=explain)
    if isinstance(doctest_result, Success):
        result_data = doctest_result.unwrap()
        passed = result_data.get("status") in ("passed", "skipped")
        output = result_data.get("stdout", "")
        return passed, output

    return False, doctest_result.failure()


def run_crosshair_phase(
    path: Path,
    checked_files: list[Path],
    doctest_passed: bool,
    static_exit_code: int,
) -> tuple[bool, dict]:
    """Run CrossHair verification phase.

    Returns (passed, output_dict).
    """
    from invar.shell.prove_cache import ProveCache
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

    # Automatic incremental mode - only verify changed files
    files_to_prove = get_files_to_prove(path, core_files, changed_only=True)

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
    )

    if isinstance(crosshair_result, Success):
        output = crosshair_result.unwrap()
        passed = output.get("status") in ("verified", "skipped")
        return passed, output

    return False, {"status": "error", "error": crosshair_result.failure()}


def output_verification_status(
    verification_level: VerificationLevel,
    static_exit_code: int,
    doctest_passed: bool,
    doctest_output: str,
    crosshair_output: dict,
    explain: bool,
) -> None:
    """Output verification status for human-readable mode."""
    from invar.shell.testing import VerificationLevel

    # Doctest results
    if verification_level >= VerificationLevel.STANDARD:
        if static_exit_code == 0:
            if doctest_passed:
                console.print("[green]✓ Doctests passed[/green]")
            else:
                console.print("[red]✗ Doctests failed[/red]")
                if doctest_output and explain:
                    console.print(doctest_output)
        else:
            console.print("[dim]⊘ Doctests skipped (static errors)[/dim]")

    # CrossHair results
    if verification_level >= VerificationLevel.PROVE:
        _output_crosshair_status(
            static_exit_code, doctest_passed, crosshair_output
        )


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
