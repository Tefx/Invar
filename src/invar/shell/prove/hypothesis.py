"""
Hypothesis fallback for proof verification.

DX-12: Provides Hypothesis as automatic fallback when CrossHair
is unavailable, times out, or skips files.

DX-22: Smart routing - detects C extension imports and routes
directly to Hypothesis without wasting time on CrossHair.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from returns.result import Failure, Result, Success

from invar.core.verification_routing import get_incompatible_imports
from invar.shell.subprocess_env import build_subprocess_env


@dataclass
class FileRouting:
    """DX-22: Classification of files for smart verification routing."""

    crosshair_files: list[Path] = field(default_factory=list)
    hypothesis_files: list[Path] = field(default_factory=list)
    skip_files: list[Path] = field(default_factory=list)
    incompatible_reasons: dict[str, set[str]] = field(default_factory=dict)


# @shell_complexity: File I/O with error handling for import detection
def classify_files_for_verification(files: list[Path]) -> FileRouting:
    """
    Classify files for smart verification routing.

    DX-22: Detects C extension imports and routes files appropriately:
    - Pure Python with contracts -> CrossHair (can prove)
    - C extensions (numpy, pandas, etc.) -> Hypothesis (cannot prove)
    - No contracts -> Skip

    Returns FileRouting with classified files.
    """
    routing = FileRouting()

    for file_path in files:
        if not file_path.exists() or file_path.suffix != ".py":
            routing.skip_files.append(file_path)
            continue

        try:
            source = file_path.read_text()
        except Exception:
            routing.skip_files.append(file_path)
            continue

        # Check for incompatible imports
        incompatible = get_incompatible_imports(source)
        if incompatible:
            routing.hypothesis_files.append(file_path)
            routing.incompatible_reasons[str(file_path)] = incompatible
        else:
            routing.crosshair_files.append(file_path)

    return routing


# @shell_complexity: Fallback verification with hypothesis availability check
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
    from invar.shell.prove.crosshair import CrossHairStatus

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
        # DX-52: Inject project venv site-packages for uvx compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=build_subprocess_env(),
        )
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


# @shell_orchestration: DX-22 smart routing + DX-12/13 fallback chain
# @shell_complexity: Multiple verification phases with error handling paths
def run_prove_with_fallback(
    files: list[Path],
    crosshair_timeout: int = 10,
    hypothesis_max_examples: int = 100,
    use_cache: bool = True,
    cache_dir: Path | None = None,
) -> Result[dict, str]:
    """
    Run proof verification with smart routing and automatic fallback.

    DX-22: Smart routing - routes C extension code directly to Hypothesis.
    DX-12 + DX-13: CrossHair with caching, falls back to Hypothesis on failure.

    Flow:
        1. Classify files (CrossHair-compatible vs C-extension)
        2. Run CrossHair on compatible files only
        3. Run Hypothesis on incompatible files (no wasted CrossHair attempt)
        4. Merge results with de-duplicated statistics

    Args:
        files: List of Python file paths to verify
        crosshair_timeout: Ignored (kept for backwards compatibility)
        hypothesis_max_examples: Maximum Hypothesis examples
        use_cache: Whether to use verification cache (DX-13)
        cache_dir: Cache directory (default: .invar/cache/prove)

    Returns:
        Success with verification results including routing statistics
    """
    # Import here to avoid circular import
    from invar.shell.prove.cache import ProveCache
    from invar.shell.prove.crosshair import CrossHairStatus, run_crosshair_parallel

    # DX-22: Smart routing - classify files before verification
    routing = classify_files_for_verification(files)

    # Initialize result structure with DX-22 routing stats
    result = {
        "status": "passed",
        "routing": {
            "crosshair_files": len(routing.crosshair_files),
            "hypothesis_files": len(routing.hypothesis_files),
            "skip_files": len(routing.skip_files),
            "incompatible_reasons": {
                k: list(v) for k, v in routing.incompatible_reasons.items()
            },
        },
        "crosshair": None,
        "hypothesis": None,
        "files": [str(f) for f in files],
    }

    # DX-13: Initialize cache for CrossHair
    cache = None
    if use_cache:
        if cache_dir is None:
            cache_dir = Path(".invar/cache/prove")
        cache = ProveCache(cache_dir=cache_dir)

    # Phase 1: Run CrossHair on compatible files
    if routing.crosshair_files:
        crosshair_result = run_crosshair_parallel(
            routing.crosshair_files,
            max_iterations=5,  # Fast mode
            max_workers=None,  # Auto-detect
            cache=cache,
        )

        if isinstance(crosshair_result, Success):
            xh_data = crosshair_result.unwrap()
            result["crosshair"] = xh_data

            # Check if CrossHair needs fallback for any files
            xh_status = xh_data.get("status", "")
            needs_fallback = (
                xh_status == CrossHairStatus.SKIPPED
                or xh_status == CrossHairStatus.TIMEOUT
                or "not installed" in xh_data.get("reason", "")
            )

            if needs_fallback:
                # CrossHair failed, add these files to Hypothesis batch
                routing.hypothesis_files.extend(routing.crosshair_files)
                result["crosshair"]["fallback_triggered"] = True
        else:
            # CrossHair error, fallback all to Hypothesis
            routing.hypothesis_files.extend(routing.crosshair_files)
            result["crosshair"] = {
                "status": "error",
                "error": str(crosshair_result.failure()),
                "fallback_triggered": True,
            }

    # Phase 2: Run Hypothesis on incompatible files + fallback files
    if routing.hypothesis_files:
        hypothesis_result = run_hypothesis_fallback(
            routing.hypothesis_files, max_examples=hypothesis_max_examples
        )

        if isinstance(hypothesis_result, Success):
            result["hypothesis"] = hypothesis_result.unwrap()
        else:
            result["hypothesis"] = {
                "status": "error",
                "error": str(hypothesis_result.failure()),
            }
            result["status"] = "failed"

    # Determine overall status
    xh_status = result.get("crosshair", {}).get("status", "passed")
    hyp_status = result.get("hypothesis", {}).get("status", "passed")

    if xh_status == "counterexample_found" or hyp_status == "failed":
        result["status"] = "failed"
    elif xh_status in ("error",) or hyp_status in ("error",):
        result["status"] = "error"

    # DX-22: Add de-duplicated statistics
    result["stats"] = {
        "crosshair_proven": len(
            result.get("crosshair", {}).get("verified", [])
        ),
        "hypothesis_tested": len(routing.hypothesis_files),
        "total_verified": len(files) - len(routing.skip_files),
    }

    return Success(result)
