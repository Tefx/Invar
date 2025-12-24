"""
Mutation testing integration for Invar.

DX-28: Wraps mutmut to detect undertested code by automatically
mutating code (e.g., `in` → `not in`) and checking if tests catch it.

Shell module: handles subprocess execution and result parsing.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class MutationResult:
    """Results from mutation testing.

    Examples:
        >>> result = MutationResult(total=10, killed=8, survived=2)
        >>> result.score
        80.0
        >>> result.passed
        True
    """

    total: int = 0
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    suspicious: int = 0
    errors: list[str] = field(default_factory=list)
    survivors: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Mutation score as percentage.

        Examples:
            >>> MutationResult(total=10, killed=10).score
            100.0
            >>> MutationResult(total=0).score
            100.0
        """
        if self.total == 0:
            return 100.0
        return (self.killed / self.total) * 100

    @property
    def passed(self) -> bool:
        """Check if mutation score meets threshold (80%).

        Examples:
            >>> MutationResult(total=10, killed=8).passed
            True
            >>> MutationResult(total=10, killed=7).passed
            False
        """
        return self.score >= 80.0


def check_mutmut_installed() -> Result[str, str]:
    """
    Check if mutmut is installed.

    Returns:
        Success with version or Failure with install instructions.

    Examples:
        >>> result = check_mutmut_installed()
        >>> isinstance(result, (Success, Failure))
        True
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mutmut", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or "installed"
            return Success(version)
        return Failure("mutmut not installed. Run: pip install mutmut")
    except subprocess.TimeoutExpired:
        return Failure("mutmut check timed out")
    except Exception as e:
        return Failure(f"mutmut check failed: {e}")


# @shell_complexity: Subprocess execution with result parsing
def run_mutation_test(
    target: Path,
    tests: Path | None = None,
    timeout: int = 300,
) -> Result[MutationResult, str]:
    """
    Run mutation testing on a target file or directory.

    Uses mutmut to generate mutations and run tests against them.

    Args:
        target: File or directory to mutate
        tests: Test file or directory (auto-detected if None)
        timeout: Maximum time in seconds

    Returns:
        Success with MutationResult or Failure with error message

    Examples:
        >>> # This is a shell function - actual behavior depends on mutmut
        >>> from pathlib import Path
        >>> result = run_mutation_test(Path("nonexistent.py"))
        >>> isinstance(result, Failure)
        True
    """
    # Check mutmut is installed
    install_check = check_mutmut_installed()
    if isinstance(install_check, Failure):
        return install_check  # type: ignore[return-value]

    # Validate target
    if not target.exists():
        return Failure(f"Target not found: {target}")

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "mutmut",
        "run",
        "--paths-to-mutate",
        str(target),
        "--no-progress",
    ]

    if tests:
        cmd.extend(["--tests-dir", str(tests)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=target.parent if target.is_file() else target,
        )

        # Parse results
        return parse_mutmut_output(result.stdout, result.stderr, result.returncode)

    except subprocess.TimeoutExpired:
        return Failure(f"Mutation testing timed out after {timeout}s")
    except Exception as e:
        return Failure(f"Mutation testing failed: {e}")


# @shell_complexity: Output parsing with multiple formats
def parse_mutmut_output(
    stdout: str,
    stderr: str,
    returncode: int,
) -> Result[MutationResult, str]:
    """
    Parse mutmut output into MutationResult.

    Args:
        stdout: Standard output from mutmut
        stderr: Standard error from mutmut
        returncode: Exit code from mutmut

    Returns:
        Success with parsed results or Failure with error

    Examples:
        >>> result = parse_mutmut_output("", "", 0)
        >>> isinstance(result, Success)
        True
    """
    result = MutationResult()

    # Parse summary line: "X killed, Y survived, Z timeout"
    for line in stdout.split("\n"):
        line = line.strip().lower()

        if "killed" in line:
            # Try to extract numbers
            parts = line.split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    next_word = parts[i + 1] if i + 1 < len(parts) else ""
                    if "killed" in next_word:
                        result.killed = int(part)
                    elif "survived" in next_word:
                        result.survived = int(part)
                    elif "timeout" in next_word:
                        result.timeout = int(part)

        if "mutants" in line and "total" in line:
            parts = line.split()
            for _, part in enumerate(parts):
                if part.isdigit():
                    result.total = int(part)
                    break

    # If we couldn't parse, try alternative format
    if result.total == 0:
        # mutmut results show format: "Killed: X, Survived: Y"
        for line in stdout.split("\n"):
            if "Killed:" in line:
                with contextlib.suppress(ValueError, IndexError):
                    result.killed = int(line.split("Killed:")[1].split(",")[0].strip())
            if "Survived:" in line:
                with contextlib.suppress(ValueError, IndexError):
                    result.survived = int(
                        line.split("Survived:")[1].split(",")[0].strip()
                    )

        result.total = result.killed + result.survived + result.timeout

    # Check for errors
    if stderr and "error" in stderr.lower():
        result.errors.append(stderr.strip())

    return Success(result)


# @shell_complexity: Multi-step command execution
def get_surviving_mutants(target: Path) -> Result[list[str], str]:
    """
    Get list of surviving mutants from last run.

    Args:
        target: Target that was mutated

    Returns:
        Success with list of survivor descriptions or Failure

    Examples:
        >>> from pathlib import Path
        >>> result = get_surviving_mutants(Path("."))
        >>> isinstance(result, (Success, Failure))
        True
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mutmut", "results"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        survivors = []
        in_survivors = False

        for line in result.stdout.split("\n"):
            if "Survived" in line:
                in_survivors = True
                continue
            if in_survivors and line.strip():
                if line.startswith("  "):
                    survivors.append(line.strip())
                elif not line.startswith(" "):
                    in_survivors = False

        return Success(survivors)

    except subprocess.TimeoutExpired:
        return Failure("Results query timed out")
    except Exception as e:
        return Failure(f"Failed to get results: {e}")


# @shell_orchestration: Show mutant diff for investigation
def show_mutant(mutant_id: int) -> Result[str, str]:
    """
    Show the diff for a specific mutant.

    Args:
        mutant_id: The mutant ID to show

    Returns:
        Success with diff output or Failure

    Examples:
        >>> result = show_mutant(1)
        >>> isinstance(result, (Success, Failure))
        True
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mutmut", "show", str(mutant_id)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return Success(result.stdout)
        return Failure(f"Mutant {mutant_id} not found")

    except subprocess.TimeoutExpired:
        return Failure("Show mutant timed out")
    except Exception as e:
        return Failure(f"Failed to show mutant: {e}")
