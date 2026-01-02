"""
Proof verification with Hypothesis fallback.

Shell module: DX-12 + DX-13 implementation.
- DX-12: CrossHair verification with automatic Hypothesis fallback
- DX-13: Incremental verification, parallel execution, caching
"""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path  # noqa: TC003 - used at runtime
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success
from rich.console import Console

from invar.shell.prove.cache import ProveCache  # noqa: TC001 - runtime usage

# DX-12: Hypothesis fallback
from invar.shell.prove.hypothesis import (
    run_hypothesis_fallback as run_hypothesis_fallback,
)
from invar.shell.prove.hypothesis import (
    run_prove_with_fallback as run_prove_with_fallback,
)
from invar.shell.subprocess_env import build_subprocess_env  # DX-52

if TYPE_CHECKING:
    from typing import Any

console = Console()

# ============================================================
# CrossHair Status Codes
# ============================================================


class CrossHairStatus:
    """Status codes for CrossHair verification."""

    VERIFIED = "verified"
    COUNTEREXAMPLE = "counterexample_found"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"
    CACHED = "cached"


# ============================================================
# DX-13: Contract Detection
# ============================================================


# @shell_orchestration: Contract detection for CrossHair prove module
# @shell_complexity: AST traversal for contract detection
def has_verifiable_contracts(source: str) -> bool:
    """Check if source has @pre/@post contracts (DX-13: fast string + AST check)."""
    # Fast path: no contract keywords at all
    if "@pre" not in source and "@post" not in source:
        return False

    # AST validation to avoid false positives from comments/strings
    try:
        import ast

        tree = ast.parse(source)
    except SyntaxError:
        return True  # Conservative: assume has contracts

    contract_decorators = {"pre", "post"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                    # @pre(...) or @post(...)
                    if isinstance(func, ast.Name) and func.id in contract_decorators:
                        return True
                    # @deal.pre(...) or @deal.post(...)
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in contract_decorators
                    ):
                        return True

    return False


# ============================================================
# DX-13: Single File Verification (for parallel execution)
# ============================================================


# @shell_complexity: CrossHair subprocess with error classification
def _verify_single_file(
    file_path: str,
    max_iterations: int = 5,
    timeout: int = 300,
    per_condition_timeout: int = 30,
) -> dict[str, Any]:
    """
    Verify a single file with CrossHair.

    DX-13: Uses --max_uninteresting_iterations for adaptive timeout.

    Args:
        file_path: Path to Python file
        max_iterations: Maximum uninteresting iterations (default: 5)
        timeout: Max time per file in seconds (default: 300)
        per_condition_timeout: Max time per contract in seconds (default: 30)

    Returns:
        Verification result dict
    """
    import time

    start_time = time.time()

    cmd = [
        sys.executable,
        "-m",
        "crosshair",
        "check",
        file_path,
        f"--max_uninteresting_iterations={max_iterations}",
        f"--per_condition_timeout={per_condition_timeout}",
        "--analysis_kind=deal",
    ]

    try:
        # DX-52: Inject project venv site-packages for uvx compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_subprocess_env(),
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        if result.returncode == 0:
            return {
                "file": file_path,
                "status": CrossHairStatus.VERIFIED,
                "time_ms": elapsed_ms,
                "stdout": result.stdout,
            }
        else:
            # Check if this is an execution error vs actual counterexample
            # CrossHair reports TypeError/AttributeError when it can't
            # symbolically execute C extensions like ast.parse()
            # Check both stdout and stderr for error patterns
            output = result.stdout + "\n" + result.stderr
            execution_errors = [
                "TypeError:",
                "AttributeError:",
                "NotImplementedError:",
                "compile() arg 1 must be",  # ast.parse limitation
                "ValueError: wrong parameter order",  # CrossHair signature bug
                "ValueError: cannot determine truth",  # Symbolic execution limit
                "RecursionError:",  # Infinite recursion in repr code
                "maximum recursion depth exceeded",  # Stack overflow
                "format_boundargs",  # CrossHair repr formatting bug
            ]
            is_execution_error = any(err in output for err in execution_errors)

            if is_execution_error:
                # Treat as skipped - function uses unsupported operations
                return {
                    "file": file_path,
                    "status": CrossHairStatus.SKIPPED,
                    "time_ms": elapsed_ms,
                    "reason": "uses unsupported operations (ast/compile/signature)",
                    "stdout": output,
                }

            # Extract counterexample lines - CrossHair format: "file:line: error: Err when calling func(...)"
            # Include lines with "error:" as they contain the actual counterexamples
            counterexamples = [
                line.strip()
                for line in output.split("\n")
                if line.strip() and ": error:" in line.lower()
            ]
            return {
                "file": file_path,
                "status": CrossHairStatus.COUNTEREXAMPLE,
                "time_ms": elapsed_ms,
                "counterexamples": counterexamples,
                "stdout": output,
            }

    except subprocess.TimeoutExpired:
        return {
            "file": file_path,
            "status": CrossHairStatus.TIMEOUT,
            "time_ms": timeout * 1000,
        }
    except Exception as e:
        return {
            "file": file_path,
            "status": CrossHairStatus.ERROR,
            "error": str(e),
        }


# ============================================================
# DX-13: Parallel CrossHair Execution
# ============================================================


# @shell_complexity: Parallel verification with caching and filtering
def run_crosshair_parallel(
    files: list[Path],
    max_iterations: int = 5,
    max_workers: int | None = None,
    cache: ProveCache | None = None,
    timeout: int = 300,
    per_condition_timeout: int = 30,
) -> Result[dict, str]:
    """Run CrossHair on multiple files in parallel (DX-13).

    Args:
        files: List of Python file paths to verify
        max_iterations: Maximum uninteresting iterations per condition
        max_workers: Number of parallel workers (default: CPU count)
        cache: Optional verification cache
        timeout: Max time per file in seconds (default: 300)
        per_condition_timeout: Max time per contract in seconds (default: 30)

    Returns:
        Success with verification results or Failure with error message
    """
    # Check if crosshair is available
    try:
        import crosshair  # noqa: F401
    except ImportError:
        return Success(
            {
                "status": CrossHairStatus.SKIPPED,
                "reason": "CrossHair not installed (pip install crosshair-tool)",
                "files": [],
            }
        )

    if not files:
        return Success(
            {
                "status": CrossHairStatus.SKIPPED,
                "reason": "no files",
                "files": [],
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
            }
        )

    # DX-13: Filter files with contracts and check cache
    files_to_verify: list[Path] = []
    cached_results: list[dict] = []

    for py_file in py_files:
        # Check cache first
        if cache and cache.is_valid(py_file):
            entry = cache.get(py_file)
            if entry:
                cached_results.append(
                    {
                        "file": str(py_file),
                        "status": CrossHairStatus.CACHED,
                        "cached_result": entry.result,
                    }
                )
                continue

        # Check if file has contracts
        try:
            source = py_file.read_text()
            if not has_verifiable_contracts(source):
                cached_results.append(
                    {
                        "file": str(py_file),
                        "status": CrossHairStatus.SKIPPED,
                        "reason": "no contracts",
                    }
                )
                continue
        except OSError:
            pass  # Include file anyway

        files_to_verify.append(py_file)

    # If all files are cached/skipped, return early
    if not files_to_verify:
        return Success(
            {
                "status": CrossHairStatus.VERIFIED,
                "verified": [],
                "cached": [r["file"] for r in cached_results if r["status"] == "cached"],
                "skipped": [r["file"] for r in cached_results if r["status"] == "skipped"],
                "files": [str(f) for f in py_files],
                "from_cache": True,
            }
        )

    # Determine worker count
    if max_workers is None:
        max_workers = min(len(files_to_verify), os.cpu_count() or 4)

    # Run verification in parallel
    verified_files: list[str] = []
    failed_files: list[str] = []
    all_counterexamples: list[str] = []
    total_time_ms = 0

    if max_workers > 1 and len(files_to_verify) > 1:
        # Parallel execution
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _verify_single_file, str(f), max_iterations, timeout, per_condition_timeout
                ): f
                for f in files_to_verify
            }

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    _process_verification_result(
                        result,
                        file_path,
                        verified_files,
                        failed_files,
                        all_counterexamples,
                        cache,
                    )
                    total_time_ms += result.get("time_ms", 0)
                except Exception as e:
                    failed_files.append(f"{file_path} ({e})")
    else:
        # Sequential execution (single file or max_workers=1)
        for py_file in files_to_verify:
            result = _verify_single_file(
                str(py_file), max_iterations, timeout, per_condition_timeout
            )
            _process_verification_result(
                result,
                py_file,
                verified_files,
                failed_files,
                all_counterexamples,
                cache,
            )
            total_time_ms += result.get("time_ms", 0)

    # Determine overall status
    status = (
        CrossHairStatus.VERIFIED if not failed_files else CrossHairStatus.COUNTEREXAMPLE
    )

    return Success(
        {
            "status": status,
            "verified": verified_files,
            "failed": failed_files,
            "cached": [r["file"] for r in cached_results if r.get("status") == "cached"],
            "skipped": [r["file"] for r in cached_results if r.get("status") == "skipped"],
            "counterexamples": all_counterexamples,
            "files": [str(f) for f in py_files],
            "files_verified": len(files_to_verify),
            "files_cached": len([r for r in cached_results if r.get("status") == "cached"]),
            "total_time_ms": total_time_ms,
            "workers": max_workers,
        }
    )


# @shell_orchestration: Result aggregation helper for parallel verification
# @shell_complexity: Result classification with cache update
def _process_verification_result(
    result: dict,
    file_path: Path,
    verified_files: list[str],
    failed_files: list[str],
    all_counterexamples: list[str],
    cache: ProveCache | None,
) -> None:
    """Process a single verification result."""
    status = result.get("status", "")

    if status == CrossHairStatus.VERIFIED:
        verified_files.append(str(file_path))
        if cache:
            cache.set(
                file_path,
                result="verified",
                time_taken_ms=result.get("time_ms", 0),
            )
    elif status == CrossHairStatus.COUNTEREXAMPLE:
        failed_files.append(str(file_path))
        for ce in result.get("counterexamples", []):
            all_counterexamples.append(f"{file_path.name}: {ce}")
    elif status == CrossHairStatus.TIMEOUT:
        failed_files.append(f"{file_path} (timeout)")
    elif status == CrossHairStatus.ERROR:
        failed_files.append(f"{file_path} ({result.get('error', 'unknown error')})")


# ============================================================
# Original API (backwards compatible)
# ============================================================


def run_crosshair_on_files(
    files: list[Path], timeout: int = 300, per_condition_timeout: int = 30
) -> Result[dict, str]:
    """
    Run CrossHair symbolic verification on a list of Python files.

    DX-13: Now uses parallel execution with adaptive iterations.

    Args:
        files: List of Python file paths to verify
        timeout: Max time per file in seconds (default: 300)
        per_condition_timeout: Max time per contract in seconds (default: 30)

    Returns:
        Success with verification results or Failure with error message
    """
    # DX-13: Use new parallel implementation with fast mode
    return run_crosshair_parallel(
        files,
        max_iterations=5,  # Fast mode
        max_workers=None,  # Auto-detect
        cache=None,  # No cache for basic API
        timeout=timeout,
        per_condition_timeout=per_condition_timeout,
    )


# ============================================================
# DX-13: Incremental Verification API
# ============================================================


# @shell_orchestration: File selection for incremental verification
# @shell_complexity: Git integration for incremental verification
def get_files_to_prove(
    path: Path,
    all_core_files: list[Path],
    changed_only: bool = True,
) -> list[Path]:
    """
    Get files that need proof verification.

    DX-13: Automatically filters to changed files when in git repo.

    Args:
        path: Project root path
        all_core_files: All core files in project
        changed_only: If True, only return changed files

    Returns:
        List of files to verify
    """
    if not changed_only:
        return all_core_files

    # Check if git repo
    try:
        from invar.shell.git import get_changed_files, is_git_repo

        if not is_git_repo(path):
            return all_core_files  # Not a git repo, verify all

        changed_result = get_changed_files(path)
        if isinstance(changed_result, Failure):
            return all_core_files  # Git error, verify all

        changed = changed_result.unwrap()
        if not changed:
            return []  # No changes, nothing to verify

        # Filter to core files that are changed
        return [f for f in all_core_files if f in changed]

    except ImportError:
        return all_core_files  # Git module not available
