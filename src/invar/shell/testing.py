"""
Testing commands for Invar.

Shell module: handles I/O for testing operations.
Includes Smart Guard verification (DX-06).
DX-12: Hypothesis as CrossHair fallback (see prove.py).
"""

from __future__ import annotations

import json as json_lib
import subprocess
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from returns.result import Failure, Result, Success
from rich.console import Console

# DX-12: Import from prove module
# DX-13: Added get_files_to_prove, run_crosshair_parallel
# DX-13: ProveCache extracted to prove_cache.py
from invar.shell.prove import (
    CrossHairStatus,
    get_files_to_prove,
    run_crosshair_on_files,
    run_crosshair_parallel,
    run_hypothesis_fallback,
    run_prove_with_fallback,
)
from invar.shell.prove_cache import ProveCache

console = Console()

# Re-export for backwards compatibility
# DX-13: Added get_files_to_prove, run_crosshair_parallel, ProveCache
__all__ = [
    "CrossHairStatus",
    "ProveCache",
    "VerificationLevel",
    "VerificationResult",
    "detect_verification_context",
    "get_available_verifiers",
    "get_files_to_prove",
    "run_crosshair_on_files",
    "run_crosshair_parallel",
    "run_doctests_on_files",
    "run_hypothesis_fallback",
    "run_prove_with_fallback",
    "run_test",
    "run_verify",
]


class VerificationLevel(IntEnum):
    """Verification depth levels for Smart Guard.

    Agent-Native design: Only levels with implemented verification.
    DX-08: Added THOROUGH level for property testing.
    """

    STATIC = 0  # Static analysis only (--quick)
    STANDARD = 1  # Static + doctests (default)
    PROVE = 2  # Static + doctests + CrossHair (--prove)
    THOROUGH = 3  # Static + doctests + property tests (--thorough, DX-08)


@dataclass
class VerificationResult:
    """Results from Smart Guard verification."""

    static_passed: bool = True
    doctest_passed: bool | None = None
    hypothesis_passed: bool | None = None
    crosshair_passed: bool | None = None
    doctest_output: str = ""
    hypothesis_output: str = ""
    crosshair_output: str = ""
    files_tested: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def get_available_verifiers() -> list[str]:
    """
    Detect installed verification tools.

    Returns:
        List of available verifier names.

    >>> "static" in get_available_verifiers()
    True
    >>> "doctest" in get_available_verifiers()
    True
    """
    available = ["static", "doctest"]  # Always available

    try:
        import hypothesis  # noqa: F401

        available.append("hypothesis")
    except ImportError:
        pass

    try:
        import crosshair  # noqa: F401

        available.append("crosshair")
    except ImportError:
        pass

    return available


def detect_verification_context() -> VerificationLevel:
    """
    Auto-detect appropriate verification depth based on context.

    Agent-Native design: Only 3 levels exist (STATIC, STANDARD, PROVE).

    DX-15 Note: Primary auto-detection logic is now in cli._determine_verification_level()
    which has access to changed_files_count. This function remains as fallback.

    >>> detect_verification_context() == VerificationLevel.STANDARD
    True
    """
    import os

    # DX-15: CI environment always uses PROVE
    if os.getenv("CI"):
        return VerificationLevel.PROVE

    # Otherwise use STANDARD level
    return VerificationLevel.STANDARD


def run_doctests_on_files(
    files: list[Path], verbose: bool = False
) -> Result[dict, str]:
    """
    Run doctests on a list of Python files.

    Args:
        files: List of Python file paths to test
        verbose: Show verbose output

    Returns:
        Success with test results or Failure with error message
    """
    if not files:
        return Success({"status": "skipped", "reason": "no files", "files": []})

    # Filter to Python files only
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return Success({"status": "skipped", "reason": "no Python files", "files": []})

    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "--doctest-modules", "-x", "--tb=short",
    ]
    cmd.extend(str(f) for f in py_files)
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # Pytest exit codes: 0=passed, 5=no tests collected (also OK)
        is_passed = result.returncode in (0, 5)
        return Success({
            "status": "passed" if is_passed else "failed",
            "files": [str(f) for f in py_files],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    except subprocess.TimeoutExpired:
        return Failure("Doctest timeout (120s)")
    except Exception as e:
        return Failure(f"Doctest error: {e}")


def run_test(
    target: str, json_output: bool = False, verbose: bool = False
) -> Result[dict, str]:
    """
    Run property-based tests using Hypothesis via deal.cases.

    Args:
        target: File path or module to test
        json_output: Output as JSON
        verbose: Show verbose output

    Returns:
        Success with test results or Failure with error message
    """
    target_path = Path(target)
    if not target_path.exists():
        return Failure(f"Target not found: {target}")
    if target_path.suffix != ".py":
        return Failure(f"Target must be a Python file: {target}")

    cmd = [
        sys.executable, "-m", "pytest",
        str(target_path), "--doctest-modules", "-x", "--tb=short",
    ]
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        test_result = {
            "status": "passed" if result.returncode == 0 else "failed",
            "target": str(target_path),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        if json_output:
            console.print(json_lib.dumps(test_result, indent=2))
        else:
            if result.returncode == 0:
                console.print(f"[green]✓[/green] Tests passed: {target}")
                if verbose:
                    console.print(result.stdout)
            else:
                console.print(f"[red]✗[/red] Tests failed: {target}")
                console.print(result.stdout)
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")

        return Success(test_result)
    except subprocess.TimeoutExpired:
        return Failure(f"Test timeout (300s): {target}")
    except Exception as e:
        return Failure(f"Test error: {e}")


def run_verify(
    target: str, json_output: bool = False, timeout: int = 30
) -> Result[dict, str]:
    """
    Run symbolic verification using CrossHair.

    Args:
        target: File path or module to verify
        json_output: Output as JSON
        timeout: Timeout per function in seconds

    Returns:
        Success with verification results or Failure with error message
    """
    try:
        import crosshair  # noqa: F401
    except ImportError:
        return Failure(
            "CrossHair not installed. Run: pip install crosshair-tool\n"
            "Note: CrossHair requires Python 3.8-3.12 (not 3.14)"
        )

    target_path = Path(target)
    if not target_path.exists():
        return Failure(f"Target not found: {target}")
    if target_path.suffix != ".py":
        return Failure(f"Target must be a Python file: {target}")

    cmd = [
        sys.executable, "-m", "crosshair", "check",
        str(target_path), f"--per_condition_timeout={timeout}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 10)

        counterexamples = [
            line.strip() for line in result.stdout.split("\n")
            if "error" in line.lower() or "counterexample" in line.lower()
        ]

        verify_result = {
            "status": "verified" if result.returncode == 0 else "counterexample_found",
            "target": str(target_path),
            "exit_code": result.returncode,
            "counterexamples": counterexamples,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        if json_output:
            console.print(json_lib.dumps(verify_result, indent=2))
        else:
            if result.returncode == 0:
                console.print(f"[green]✓[/green] Verified: {target}")
            else:
                console.print(f"[yellow]![/yellow] Counterexamples found: {target}")
                for ce in counterexamples:
                    console.print(f"  {ce}")

        return Success(verify_result)
    except subprocess.TimeoutExpired:
        return Failure(f"Verification timeout ({timeout * 10}s): {target}")
    except Exception as e:
        return Failure(f"Verification error: {e}")
