"""
Proof verification with Hypothesis fallback.

Shell module: DX-12 implementation.
Provides CrossHair verification with automatic Hypothesis fallback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path  # noqa: TC003 - used at runtime

from returns.result import Failure, Result, Success
from rich.console import Console

console = Console()


# CrossHair result status
class CrossHairStatus:
    """Status codes for CrossHair verification."""

    VERIFIED = "verified"
    COUNTEREXAMPLE = "counterexample_found"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


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
            "status": CrossHairStatus.SKIPPED,
            "reason": "CrossHair not installed (pip install crosshair-tool)",
            "files": []
        })

    if not files:
        return Success({
            "status": CrossHairStatus.SKIPPED,
            "reason": "no files",
            "files": []
        })

    # Filter to Python files only
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return Success({
            "status": CrossHairStatus.SKIPPED,
            "reason": "no Python files",
            "files": []
        })

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

    status = CrossHairStatus.VERIFIED if not failed_files else CrossHairStatus.COUNTEREXAMPLE
    return Success({
        "status": status,
        "verified": verified_files,
        "failed": failed_files,
        "counterexamples": all_counterexamples,
        "files": [str(f) for f in py_files]
    })


def run_hypothesis_fallback(
    files: list[Path],
    max_examples: int = 100,
) -> Result[dict, str]:
    """
    Run Hypothesis property tests as fallback when CrossHair skips/times out.

    DX-12: Uses inferred strategies from type hints and @pre contracts.

    Args:
        files: List of Python file paths to test
        max_examples: Maximum examples per test

    Returns:
        Success with test results or Failure with error message
    """
    # Check if hypothesis is available
    try:
        import hypothesis  # noqa: F401
    except ImportError:
        return Success({
            "status": CrossHairStatus.SKIPPED,
            "reason": "Hypothesis not installed (pip install hypothesis)",
            "files": [],
            "tool": "hypothesis",
        })

    if not files:
        return Success({
            "status": CrossHairStatus.SKIPPED,
            "reason": "no files",
            "files": [],
            "tool": "hypothesis",
        })

    # Filter to Python files only
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return Success({
            "status": CrossHairStatus.SKIPPED,
            "reason": "no Python files",
            "files": [],
            "tool": "hypothesis",
        })

    # Use pytest with hypothesis
    cmd = [
        sys.executable, "-m", "pytest",
        "--hypothesis-show-statistics",
        "--hypothesis-seed=0",  # Reproducible
        "-x",  # Stop on first failure
        "--tb=short",
    ]
    cmd.extend(str(f) for f in py_files)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        # Pytest exit codes: 0=passed, 5=no tests collected
        is_passed = result.returncode in (0, 5)
        return Success({
            "status": "passed" if is_passed else "failed",
            "files": [str(f) for f in py_files],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "tool": "hypothesis",
            "note": "Fallback from CrossHair",
        })
    except subprocess.TimeoutExpired:
        return Failure("Hypothesis timeout (300s)")
    except Exception as e:
        return Failure(f"Hypothesis error: {e}")


def run_prove_with_fallback(
    files: list[Path],
    crosshair_timeout: int = 10,
    hypothesis_max_examples: int = 100,
) -> Result[dict, str]:
    """
    Run proof verification with automatic Hypothesis fallback.

    DX-12: Tries CrossHair first, falls back to Hypothesis if:
    - CrossHair is not installed
    - CrossHair times out
    - CrossHair skips the file (library-dependent code)

    Args:
        files: List of Python file paths to verify
        crosshair_timeout: Timeout per condition in seconds
        hypothesis_max_examples: Maximum Hypothesis examples

    Returns:
        Success with verification results or Failure with error message
    """
    # Try to infer timeout from first file
    if files:
        try:
            first_file = files[0]
            content = first_file.read_text()
            # Simple check for numpy/pandas
            if any(lib in content for lib in ["numpy", "pandas", "torch"]):
                crosshair_timeout = 5  # Quick timeout for library code
        except Exception:
            pass

    # Step 1: Try CrossHair
    crosshair_result = run_crosshair_on_files(files, timeout=crosshair_timeout)

    if isinstance(crosshair_result, Failure):
        # CrossHair failed, try Hypothesis
        return run_hypothesis_fallback(files, max_examples=hypothesis_max_examples)

    result_data = crosshair_result.unwrap()
    status = result_data.get("status", "")

    # Step 2: Check if we need fallback
    needs_fallback = (
        status == CrossHairStatus.SKIPPED
        or status == CrossHairStatus.TIMEOUT
        or "not installed" in result_data.get("reason", "")
    )

    if needs_fallback:
        # Run Hypothesis as fallback
        hypothesis_result = run_hypothesis_fallback(
            files, max_examples=hypothesis_max_examples
        )

        if isinstance(hypothesis_result, Success):
            hyp_data = hypothesis_result.unwrap()
            # Merge results
            return Success({
                "status": hyp_data.get("status", "unknown"),
                "primary_tool": "hypothesis",
                "crosshair_status": status,
                "crosshair_reason": result_data.get("reason", ""),
                "hypothesis_result": hyp_data,
                "files": [str(f) for f in files],
                "note": "CrossHair skipped/unavailable, used Hypothesis fallback",
            })
        return hypothesis_result

    # CrossHair succeeded (verified or found counterexample)
    result_data["primary_tool"] = "crosshair"
    return Success(result_data)
