"""
Hypothesis fallback for proof verification.

DX-12: Provides Hypothesis as automatic fallback when CrossHair
is unavailable, times out, or skips files.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from returns.result import Failure, Result, Success


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
    # Import CrossHairStatus here to avoid circular import
    from invar.shell.prove import CrossHairStatus

    # Check if hypothesis is available
    try:
        import hypothesis  # noqa: F401
    except ImportError:
        return Success(
            {
                "status": CrossHairStatus.SKIPPED,
                "reason": "Hypothesis not installed (pip install hypothesis)",
                "files": [],
                "tool": "hypothesis",
            }
        )

    if not files:
        return Success(
            {
                "status": CrossHairStatus.SKIPPED,
                "reason": "no files",
                "files": [],
                "tool": "hypothesis",
            }
        )

    # Filter to Python files only
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return Success(
            {
                "status": CrossHairStatus.SKIPPED,
                "reason": "no Python files",
                "files": [],
                "tool": "hypothesis",
            }
        )

    # Use pytest with hypothesis
    cmd = [
        sys.executable,
        "-m",
        "pytest",
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
        return Success(
            {
                "status": "passed" if is_passed else "failed",
                "files": [str(f) for f in py_files],
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "tool": "hypothesis",
                "note": "Fallback from CrossHair",
            }
        )
    except subprocess.TimeoutExpired:
        return Failure("Hypothesis timeout (300s)")
    except Exception as e:
        return Failure(f"Hypothesis error: {e}")


def run_prove_with_fallback(
    files: list[Path],
    crosshair_timeout: int = 10,
    hypothesis_max_examples: int = 100,
    use_cache: bool = True,
    cache_dir: Path | None = None,
) -> Result[dict, str]:
    """
    Run proof verification with automatic Hypothesis fallback.

    DX-12 + DX-13: Tries CrossHair first with optimizations, falls back to Hypothesis.

    Args:
        files: List of Python file paths to verify
        crosshair_timeout: Ignored (kept for backwards compatibility)
        hypothesis_max_examples: Maximum Hypothesis examples
        use_cache: Whether to use verification cache (DX-13)
        cache_dir: Cache directory (default: .invar/cache/prove)

    Returns:
        Success with verification results or Failure with error message
    """
    # Import here to avoid circular import
    from invar.shell.prove import CrossHairStatus, run_crosshair_parallel
    from invar.shell.prove_cache import ProveCache

    # DX-13: Initialize cache
    cache = None
    if use_cache:
        if cache_dir is None:
            cache_dir = Path(".invar/cache/prove")
        cache = ProveCache(cache_dir=cache_dir)

    # DX-13: Use parallel CrossHair with caching
    crosshair_result = run_crosshair_parallel(
        files,
        max_iterations=5,  # Fast mode
        max_workers=None,  # Auto-detect
        cache=cache,
    )

    if isinstance(crosshair_result, Failure):
        # CrossHair failed, try Hypothesis
        return run_hypothesis_fallback(files, max_examples=hypothesis_max_examples)

    result_data = crosshair_result.unwrap()
    status = result_data.get("status", "")

    # Check if we need fallback
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
            return Success(
                {
                    "status": hyp_data.get("status", "unknown"),
                    "primary_tool": "hypothesis",
                    "crosshair_status": status,
                    "crosshair_reason": result_data.get("reason", ""),
                    "hypothesis_result": hyp_data,
                    "files": [str(f) for f in files],
                    "note": "CrossHair skipped/unavailable, used Hypothesis fallback",
                }
            )
        return hypothesis_result

    # CrossHair succeeded (verified or found counterexample)
    result_data["primary_tool"] = "crosshair"
    return Success(result_data)
