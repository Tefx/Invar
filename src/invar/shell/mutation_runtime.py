"""
Runtime executor for DX-97 mutation testing.

Executes doctest + property tests for a single mutant at a time,
normalizing outcomes into killed/survived/timeout/error.

Shell module: handles I/O for subprocess execution and file operations.
"""

from __future__ import annotations

import contextlib
import signal
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from returns.result import Failure

from invar.shell.property_tests import run_property_tests_on_file
from invar.shell.testing import run_doctests_on_files


class MutantOutcome(Enum):
    """Normalized outcome for a single mutant execution.

    Examples:
        >>> MutantOutcome.KILLED.value
        'killed'
        >>> MutantOutcome.SURVIVED.value
        'survived'
    """

    KILLED = "killed"
    SURVIVED = "survived"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class MutantResult:
    """Result of executing tests against a single mutant.

    Attributes:
        outcome: Normalized result (killed/survived/timeout/error)
        detail: Human-readable explanation
        doctest_passed: Whether doctests passed (None if not run)
        property_passed: Whether property tests passed (None if not run)
        stdout: Captured standard output
        stderr: Captured standard error
        elapsed_seconds: Time taken to execute

    Examples:
        >>> result = MutantResult(outcome=MutantOutcome.KILLED, detail="Tests caught mutation")
        >>> result.outcome
        <MutantOutcome.KILLED: 'killed'>
    """

    outcome: MutantOutcome
    detail: str = ""
    doctest_passed: bool | None = None
    property_passed: bool | None = None
    stdout: str = ""
    stderr: str = ""
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


# @shell_complexity: Mutation execution requires branching on multiple failure modes
def execute_mutant_tests(
    mutated_source: str,
    file_path: Path,
    timeout: int = 60,
    project_root: Path | None = None,
) -> MutantResult:
    """Execute doctest + property tests on a single mutant.

    Writes mutated source to a temporary file (to avoid mutating caller
    workspace), runs doctests and property tests against it, and normalizes
    the result.

    Args:
        mutated_source: The mutated source code to test
        file_path: Original file path (used for module resolution)
        timeout: Maximum time in seconds for each test phase
        project_root: Project root directory

    Returns:
        MutantResult with normalized outcome

    Examples:
        >>> source = "def add(a, b):\\n    return a + b\\n"
        >>> result = execute_mutant_tests(source, Path("test.py"))
        >>> result.outcome in (MutantOutcome.KILLED, MutantOutcome.SURVIVED)
        True
    """
    import time

    start_time = time.monotonic()
    root = project_root or file_path.parent

    # Write mutated source to a temp file to avoid workspace pollution
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        dir=root,
    ) as tmp:
        tmp.write(mutated_source)
        tmp_path = Path(tmp.name)

    try:
        # Run doctests
        doctest_result: MutantResult | None = None
        try:
            dt_result = run_doctests_on_files(
                [tmp_path],
                verbose=False,
                timeout=timeout,
                cwd=root,
            )

            doctest_stdout = ""
            doctest_stderr = ""
            if isinstance(dt_result, Failure):
                # Execution error (timeout, import error, etc.)
                doctest_passed = False
                doctest_outcome = MutantOutcome.ERROR
                doctest_detail = f"Doctest execution error: {dt_result.failure()}"
                doctest_errors = [dt_result.failure()]
            else:
                dt_data = dt_result.unwrap()
                status = dt_data.get("status", "unknown")
                doctest_passed = status == "passed"
                # Test failures are KILLED, not errors (execution continued normally)
                doctest_outcome = MutantOutcome.SURVIVED if doctest_passed else MutantOutcome.KILLED
                doctest_detail = (
                    "Doctests passed" if doctest_passed else "Doctests detected mutation"
                )
                doctest_errors = list(dt_data.get("errors", []))
                doctest_stdout = dt_data.get("stdout", "")
                doctest_stderr = dt_data.get("stderr", "")

            doctest_result = MutantResult(
                outcome=doctest_outcome,
                detail=doctest_detail,
                doctest_passed=doctest_passed,
                stdout=doctest_stdout,
                stderr=doctest_stderr,
                errors=doctest_errors,
            )
        except Exception as e:
            doctest_result = MutantResult(
                outcome=MutantOutcome.ERROR,
                detail=f"Doctest exception: {e}",
                doctest_passed=False,
                errors=[str(e)],
            )

        # Run property tests
        property_result: MutantResult | None = None
        try:
            pt_result = run_property_tests_on_file(
                tmp_path,
                max_examples=100,
                _verbose=False,
                project_root=root,
            )

            if isinstance(pt_result, Failure):
                # Execution error (exception during test run)
                property_passed = False
                property_outcome = MutantOutcome.ERROR
                property_detail = f"Property test execution error: {pt_result.failure()}"
                property_errors = [pt_result.failure()]
            else:
                pt_report = pt_result.unwrap()
                property_passed = pt_report.all_passed()
                # Test failures (counterexamples found) are KILLED, not errors
                # Only execution errors are ERROR
                property_outcome = (
                    MutantOutcome.SURVIVED if property_passed else MutantOutcome.KILLED
                )
                property_detail = (
                    "Property tests passed"
                    if property_passed
                    else "Property tests found counterexample"
                )
                property_errors = pt_report.errors

            property_result = MutantResult(
                outcome=property_outcome,
                detail=property_detail,
                property_passed=property_passed,
                errors=property_errors,
            )
        except Exception as e:
            property_result = MutantResult(
                outcome=MutantOutcome.ERROR,
                detail=f"Property test exception: {e}",
                property_passed=False,
                errors=[str(e)],
            )

        # Normalize final outcome
        # If either test found an error (not just failure), it's an error
        if (
            doctest_result.outcome == MutantOutcome.ERROR
            or property_result.outcome == MutantOutcome.ERROR
        ):
            final_outcome = MutantOutcome.ERROR
            final_detail = "; ".join(
                d
                for d in [doctest_result.detail, property_result.detail]
                if "error" in d.lower() or "exception" in d.lower()
            )
        # If either test killed the mutant, it's killed
        elif not doctest_result.doctest_passed or not property_result.property_passed:
            final_outcome = MutantOutcome.KILLED
            final_detail = "Tests detected mutation"
        else:
            final_outcome = MutantOutcome.SURVIVED
            final_detail = "Tests passed on mutated code"

        elapsed = time.monotonic() - start_time

        # Collect outputs
        combined_stdout = "\n".join(
            filter(None, [doctest_result.stdout, property_result.stdout or ""])
        )
        combined_stderr = "\n".join(
            filter(None, [doctest_result.stderr, "; ".join(property_result.errors)])
        )
        combined_errors = doctest_result.errors + property_result.errors

        return MutantResult(
            outcome=final_outcome,
            detail=final_detail,
            doctest_passed=doctest_result.doctest_passed,
            property_passed=property_result.property_passed,
            stdout=combined_stdout,
            stderr=combined_stderr,
            elapsed_seconds=elapsed,
            errors=combined_errors,
        )

    finally:
        # Clean up temp file
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)


def _execute_mutant_with_timeout(
    mutated_source: str,
    file_path: Path,
    timeout: int = 60,
    project_root: Path | None = None,
) -> MutantResult:
    """Execute mutant tests with hard timeout enforcement.

    This wraps execute_mutant_tests with a signal-based timeout on Unix.
    On timeout, returns MutantOutcome.TIMEOUT without modifying caller workspace.

    Args:
        mutated_source: The mutated source code to test
        file_path: Original file path (used for module resolution)
        timeout: Maximum time in seconds for each test phase
        project_root: Project root directory

    Returns:
        MutantResult with normalized outcome (may be TIMEOUT)

    Examples:
        >>> source = "def add(a, b):\\n    return a + b\\n"
        >>> result = _execute_mutant_with_timeout(source, Path("test.py"), timeout=60)
        >>> result.outcome in (MutantOutcome.KILLED, MutantOutcome.SURVIVED, MutantOutcome.ERROR)
        True
    """
    import time

    start_time = time.monotonic()

    def timeout_handler(signum, frame):
        raise TimeoutError("Mutant execution timed out")

    # Only setup timeout on Unix (signal not available on Windows)
    if sys.platform != "win32":
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout + 1)  # Slightly longer than test timeout

    try:
        result = execute_mutant_tests(
            mutated_source=mutated_source,
            file_path=file_path,
            timeout=timeout,
            project_root=project_root,
        )
        result.elapsed_seconds = time.monotonic() - start_time
        return result
    except TimeoutError:
        elapsed = time.monotonic() - start_time
        return MutantResult(
            outcome=MutantOutcome.TIMEOUT,
            detail=f"Mutant execution exceeded {timeout}s timeout",
            elapsed_seconds=elapsed,
        )
    finally:
        if sys.platform != "win32":
            signal.alarm(0)  # Cancel alarm
            signal.signal(signal.SIGALRM, old_handler)


# @shell_complexity: Output formatting requires branching on outcome enum
def _format_mutant_result(result: MutantResult) -> str:
    """Format a mutant result for display.

    Args:
        result: The mutant result to format

    Returns:
        Human-readable string representation

    Examples:
        >>> result = MutantResult(outcome=MutantOutcome.KILLED, detail="Tests caught mutation")
        >>> "killed" in _format_mutant_result(result).lower()
        True
    """
    status_symbols = {
        MutantOutcome.KILLED: "✗",
        MutantOutcome.SURVIVED: "✓",
        MutantOutcome.TIMEOUT: "⏱",
        MutantOutcome.ERROR: "⚠",
    }

    symbol = status_symbols.get(result.outcome, "?")
    lines = [
        f"{symbol} {result.outcome.value.upper()}: {result.detail}",
    ]

    if result.elapsed_seconds > 0:
        lines.append(f"  Elapsed: {result.elapsed_seconds:.2f}s")

    if result.doctest_passed is not None:
        dt_status = "PASS" if result.doctest_passed else "FAIL"
        lines.append(f"  Doctest: {dt_status}")

    if result.property_passed is not None:
        pt_status = "PASS" if result.property_passed else "FAIL"
        lines.append(f"  Property: {pt_status}")

    if result.errors:
        lines.append(f"  Errors: {len(result.errors)}")

    return "\n".join(lines)
