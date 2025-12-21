"""
Testing commands for Invar.

Shell module: handles I/O for testing operations.
Includes Smart Guard verification (DX-06).
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

console = Console()


class VerificationLevel(IntEnum):
    """Verification depth levels for Smart Guard.

    Agent-Native design: Only levels with implemented verification.
    """

    STATIC = 0  # Static analysis only (--quick)
    STANDARD = 1  # Static + doctests (default)
    PROVE = 2  # Static + doctests + CrossHair (--prove)


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
    All contexts default to STANDARD. Use --prove explicitly for deeper verification.

    >>> detect_verification_context() == VerificationLevel.STANDARD
    True
    """
    # All contexts: STANDARD (static + doctests)
    # Use --prove explicitly for CrossHair verification
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
        sys.executable,
        "-m",
        "pytest",
        "--doctest-modules",
        "-x",  # Stop on first failure
        "--tb=short",
    ]
    cmd.extend(str(f) for f in py_files)

    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # Pytest exit codes: 0=passed, 5=no tests collected (also OK)
        # DX-09: Treat "no tests collected" as passed, not failed
        is_passed = result.returncode in (0, 5)
        return Success(
            {
                "status": "passed" if is_passed else "failed",
                "files": [str(f) for f in py_files],
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

    except subprocess.TimeoutExpired:
        return Failure("Doctest timeout (120s)")
    except Exception as e:
        return Failure(f"Doctest error: {e}")


def run_crosshair_on_files(
    files: list[Path], timeout: int = 10
) -> Result[dict, str]:
    """
    Run CrossHair symbolic verification on a list of Python files.

    Args:
        files: List of Python file paths to verify
        timeout: Timeout per condition in seconds

    Returns:
        Success with verification results or Failure with error message
    """
    # Check if crosshair is available
    try:
        import crosshair  # noqa: F401
    except ImportError:
        return Success({
            "status": "skipped",
            "reason": "CrossHair not installed (pip install crosshair-tool)",
            "files": []
        })

    if not files:
        return Success({"status": "skipped", "reason": "no files", "files": []})

    # Filter to Python files only
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return Success({"status": "skipped", "reason": "no Python files", "files": []})

    # Run crosshair on each file, collect results
    all_counterexamples: list[str] = []
    verified_files: list[str] = []
    failed_files: list[str] = []

    for py_file in py_files:
        cmd = [
            sys.executable, "-m", "crosshair", "check",
            str(py_file), f"--per_condition_timeout={timeout}"
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout * 20
            )
            if result.returncode == 0:
                verified_files.append(str(py_file))
            else:
                failed_files.append(str(py_file))
                for line in result.stdout.split("\n"):
                    if line.strip():
                        all_counterexamples.append(f"{py_file.name}: {line.strip()}")
        except subprocess.TimeoutExpired:
            failed_files.append(f"{py_file} (timeout)")
        except Exception as e:
            failed_files.append(f"{py_file} ({e})")

    status = "verified" if not failed_files else "counterexample_found"
    return Success({
        "status": status,
        "verified": verified_files,
        "failed": failed_files,
        "counterexamples": all_counterexamples,
        "files": [str(f) for f in py_files]
    })


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
    # Resolve target to a file path
    target_path = Path(target)
    if not target_path.exists():
        return Failure(f"Target not found: {target}")

    if target_path.suffix != ".py":
        return Failure(f"Target must be a Python file: {target}")

    # Build pytest command with doctest and hypothesis
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(target_path),
        "--doctest-modules",
        "-x",  # Stop on first failure
        "--tb=short",
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
    # Check if crosshair is available
    try:
        import crosshair  # noqa: F401
    except ImportError:
        return Failure(
            "CrossHair not installed. Run: pip install crosshair-tool\n"
            "Note: CrossHair requires Python 3.8-3.12 (not 3.14)"
        )

    # Resolve target
    target_path = Path(target)
    if not target_path.exists():
        return Failure(f"Target not found: {target}")

    if target_path.suffix != ".py":
        return Failure(f"Target must be a Python file: {target}")

    # Build crosshair command
    cmd = [
        sys.executable,
        "-m",
        "crosshair",
        "check",
        str(target_path),
        f"--per_condition_timeout={timeout}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 10)

        # Parse crosshair output
        counterexamples = []
        for line in result.stdout.split("\n"):
            if "error" in line.lower() or "counterexample" in line.lower():
                counterexamples.append(line.strip())

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
