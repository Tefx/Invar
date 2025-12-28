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

from invar.shell.prove.cache import ProveCache

# DX-12: Import from prove module
# DX-13: Added get_files_to_prove, run_crosshair_parallel
# DX-48b: Relocated to shell/prove/
from invar.shell.prove.crosshair import (
    CrossHairStatus,
    get_files_to_prove,
    run_crosshair_on_files,
    run_crosshair_parallel,
    run_hypothesis_fallback,
    run_prove_with_fallback,
)
from invar.shell.subprocess_env import build_subprocess_env

console = Console()

# Re-export for backwards compatibility
# DX-13: Added get_files_to_prove, run_crosshair_parallel, ProveCache
__all__ = [
    "CrossHairStatus",
    "ProveCache",
    "VerificationLevel",
    "VerificationResult",
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

    DX-19: Simplified to 2 levels (Agent-Native: Zero decisions).
    - STATIC: Quick debug mode (~0.5s)
    - STANDARD: Full verification including CrossHair + Hypothesis (~5s)
    """

    STATIC = 0  # Static analysis only (--static, quick debug)
    STANDARD = 1  # Full: static + doctests + CrossHair + Hypothesis (default)  # Static + doctests + property tests (--thorough, DX-08)


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


# @shell_orchestration: Verifier discovery helper
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


# @shell_complexity: Doctest execution with subprocess and result parsing
def run_doctests_on_files(
    files: list[Path],
    verbose: bool = False,
    timeout: int = 60,
    collect_coverage: bool = False,
) -> Result[dict, str]:
    """
    Run doctests on a list of Python files.

    Args:
        files: List of Python file paths to test
        verbose: Show verbose output
        timeout: Maximum time in seconds (default: 60, from RuleConfig.timeout_doctest)
        collect_coverage: DX-37: If True, run with coverage.py and return coverage data

    Returns:
        Success with test results or Failure with error message
    """
    if not files:
        return Success({"status": "skipped", "reason": "no files", "files": []})

    # Filter to Python files only
    # Exclude: conftest.py (pytest config), templates/examples/ (source templates),
    # .invar/examples/ (documentation examples with intentionally "bad" patterns)
    def is_excluded(f: Path) -> bool:
        """Check if path matches excluded patterns using path parts (not substring)."""
        parts = f.parts
        # Check for consecutive "templates/examples" or ".invar/examples"
        for i in range(len(parts) - 1):
            if (parts[i] == "templates" and parts[i + 1] == "examples") or \
               (parts[i] == ".invar" and parts[i + 1] == "examples"):
                return True
        return False

    py_files = [
        f for f in files
        if f.suffix == ".py"
        and f.exists()
        and f.name != "conftest.py"
        and not is_excluded(f)
    ]
    if not py_files:
        return Success({"status": "skipped", "reason": "no Python files", "files": []})

    # DX-37: Build command with optional coverage
    if collect_coverage:
        # Use coverage run to wrap pytest
        cmd = [
            sys.executable, "-m", "coverage", "run",
            "--branch",  # Enable branch coverage
            "--parallel-mode",  # For merging with hypothesis later
            "-m", "pytest",
            "--doctest-modules", "-x", "--tb=short",
        ]
    else:
        cmd = [
            sys.executable, "-m", "pytest",
            "--doctest-modules", "-x", "--tb=short",
        ]
    cmd.extend(str(f) for f in py_files)
    if verbose:
        cmd.append("-v")

    try:
        # DX-52: Inject project venv site-packages for uvx compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_subprocess_env(),
        )
        # Pytest exit codes: 0=passed, 5=no tests collected (also OK)
        is_passed = result.returncode in (0, 5)
        return Success({
            "status": "passed" if is_passed else "failed",
            "files": [str(f) for f in py_files],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "coverage_collected": collect_coverage,  # DX-37: Flag for caller
        })
    except subprocess.TimeoutExpired:
        return Failure(f"Doctest timeout ({timeout}s)")
    except Exception as e:
        return Failure(f"Doctest error: {e}")


# @shell_complexity: Property test orchestration with subprocess
def run_test(
    target: str, json_output: bool = False, verbose: bool = False, timeout: int = 300
) -> Result[dict, str]:
    """
    Run property-based tests using Hypothesis via deal.cases.

    Args:
        target: File path or module to test
        json_output: Output as JSON
        verbose: Show verbose output
        timeout: Maximum time in seconds (default: 300, from RuleConfig.timeout_hypothesis)

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
        # DX-52: Inject project venv site-packages for uvx compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_subprocess_env(),
        )
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
        return Failure(f"Test timeout ({timeout}s): {target}")
    except Exception as e:
        return Failure(f"Test error: {e}")


# @shell_complexity: CrossHair verification with subprocess
def run_verify(
    target: str,
    json_output: bool = False,
    total_timeout: int = 300,
    per_condition_timeout: int = 30,
) -> Result[dict, str]:
    """
    Run symbolic verification using CrossHair.

    Args:
        target: File path or module to verify
        json_output: Output as JSON
        total_timeout: Total timeout in seconds (default: 300, from RuleConfig.timeout_crosshair)
        per_condition_timeout: Per-contract timeout (default: 30, from RuleConfig.timeout_crosshair_per_condition)

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
        str(target_path), f"--per_condition_timeout={per_condition_timeout}",
    ]

    try:
        # DX-52: Inject project venv site-packages for uvx compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=total_timeout,
            env=build_subprocess_env(),
        )

        # CrossHair format: "file:line: error: Err when calling func(...)"
        counterexamples = [
            line.strip() for line in result.stdout.split("\n")
            if ": error:" in line.lower() or "counterexample" in line.lower()
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
        return Failure(f"Verification timeout ({total_timeout}s): {target}")
    except Exception as e:
        return Failure(f"Verification error: {e}")
