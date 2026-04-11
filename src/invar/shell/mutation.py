"""
Mutation testing integration for Invar.

DX-28: Wraps mutmut to detect undertested code by automatically
mutating code (e.g., `in` → `not in`) and checking if tests catch it.

DX-97: Shell mutation orchestration for one-at-a-time mutant execution
with bounded survivor evidence and fail-closed aggregation.

Shell module: handles subprocess execution and result parsing.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

# DX-97: Re-export Core types for orchestration
from invar.core.mutation_sites import (
    MutationCandidate,
    collect_mutation_candidates,
    rewrite_mutation_site,
)
from invar.shell.mutation_runtime import MutantOutcome, MutantResult, execute_mutant_tests

if TYPE_CHECKING:
    from invar.core.models import FileInfo, RuleConfig

# DX-97: Survivor evidence is bounded to avoid unbounded output growth
MAX_SURVIVOR_EVIDENCE = 5


@dataclass
class MutationAggregation:
    """Aggregated results from mutation orchestration.

    Attributes:
        total: Total candidates processed
        killed: Mutants killed by tests
        survived: Mutants that survived tests (bounded evidence)
        timeout: Mutants that timed out (fail-closed)
        error: Internal errors (fail-closed)
        survivor_evidence: Bounded list of actionable survivor details
        internal_errors: List of internal errors encountered
        candidates_order: Deterministic ordering of candidates processed
        eligible_files: Files that had mutation sites and were tested (DX-97)
        ineligible_files: Files skipped due to parse/import errors (DX-97)
        files_with_zero_sites: Files eligible but containing zero mutation sites (DX-97)

    Examples:
        >>> agg = MutationAggregation(total=10, killed=8, survived=2)
        >>> agg.score
        80.0
        >>> agg.passed
        True
        >>> agg = MutationAggregation(total=0, eligible_files=2, files_with_zero_sites=2)
        >>> agg.passed
        True
        >>> agg.files_with_zero_sites
        2
    """

    total: int = 0
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    error: int = 0
    survivor_evidence: list[str] = field(default_factory=list)
    internal_errors: list[str] = field(default_factory=list)
    candidates_order: list[str] = field(default_factory=list)
    # DX-97: Additive mutation file classification
    eligible_files: int = 0
    ineligible_files: int = 0
    files_with_zero_sites: int = 0

    @property
    def score(self) -> float:
        """Mutation score as percentage of killed mutants.

        Examples:
            >>> MutationAggregation(total=10, killed=10).score
            100.0
            >>> MutationAggregation(total=10, killed=8).score
            80.0
            >>> MutationAggregation(total=0).score
            100.0
        """
        if self.total == 0:
            return 100.0
        return (self.killed / self.total) * 100

    @property
    def passed(self) -> bool:
        """Check if mutation score meets threshold (80%).

        Fail-closed: timeouts and errors count as failures.

        Examples:
            >>> MutationAggregation(total=10, killed=8).passed
            True
            >>> MutationAggregation(total=10, killed=7).passed
            False
            >>> MutationAggregation(total=10, survived=2, timeout=0, error=0).passed
            False
            >>> MutationAggregation(total=0, timeout=0, error=0).passed
            True
            >>> MutationAggregation(total=0, timeout=1, error=0).passed
            False
            >>> MutationAggregation(total=0, error=1).passed
            False
        """
        # Fail-closed: any timeout or error fails regardless of score
        if self.timeout > 0 or self.error > 0:
            return False
        return self.score >= 80.0

    def add_candidate(self, candidate: MutationCandidate) -> None:
        """Record candidate processing order for determinism.

        Args:
            candidate: The mutation candidate being processed

        Examples:
            >>> from invar.core.mutation_sites import MutationCandidate
            >>> c = MutationCandidate(file="a.py", line=1, col_offset=0,
            ...                      operator="Add", original_source="x + y",
            ...                      mutated_source="x - y")
            >>> agg = MutationAggregation()
            >>> agg.add_candidate(c)
            >>> "a.py:1:Add" in agg.candidates_order
            True
        """
        self.candidates_order.append(f"{candidate.file}:{candidate.line}:{candidate.operator}")

    def add_result(self, result: MutantResult) -> None:
        """Aggregate a single mutant result.

        Fail-closed: timeouts and errors are counted as failures.

        Args:
            result: The result from executing tests on a mutant

        Examples:
            >>> from invar.shell.mutation_runtime import MutantOutcome, MutantResult
            >>> agg = MutationAggregation()
            >>> r = MutantResult(outcome=MutantOutcome.KILLED, detail="Tests caught mutation")
            >>> agg.add_result(r)
            >>> agg.killed
            1
        """
        if result.outcome == MutantOutcome.KILLED:
            self.killed += 1
        elif result.outcome == MutantOutcome.SURVIVED:
            self.survived += 1
            # Bounded survivor evidence
            if len(self.survivor_evidence) < MAX_SURVIVOR_EVIDENCE:
                self.survivor_evidence.append(result.detail)
        elif result.outcome == MutantOutcome.TIMEOUT:
            self.timeout += 1
        elif result.outcome == MutantOutcome.ERROR:
            self.error += 1
            if result.errors:
                self.internal_errors.extend(result.errors)

    def add_error(self, error_msg: str) -> None:
        """Record an internal error during orchestration.

        Args:
            error_msg: Error message describing the failure

        Examples:
            >>> agg = MutationAggregation()
            >>> agg.add_error("Failed to collect candidates")
            >>> "Failed to collect candidates" in agg.internal_errors
            True
            >>> agg.error
            1
        """
        self.error += 1
        self.internal_errors.append(error_msg)

    # DX-97: Output serialization for agent JSON and deferred report parity
    def to_output_dict(self) -> dict[str, object]:
        """Convert to additive top-level mutation output dict.

        Returns dict suitable for inclusion in agent JSON output and
        deferred final-report parity. survivor_evidence is bounded to
        MAX_SURVIVOR_EVIDENCE entries.

        Examples:
            >>> agg = MutationAggregation(total=5, killed=4, survived=1,
            ...                          eligible_files=3, ineligible_files=1,
            ...                          files_with_zero_sites=1,
            ...                          survivor_evidence=["a.py:2:Add"])
            >>> d = agg.to_output_dict()
            >>> d["total"]
            5
            >>> d["eligible_files"]
            3
            >>> d["score"]
            80.0
        """
        return {
            "total": self.total,
            "killed": self.killed,
            "survived": self.survived,
            "timeout": self.timeout,
            "error": self.error,
            "score": self.score,
            "passed": self.passed,
            "eligible_files": self.eligible_files,
            "ineligible_files": self.ineligible_files,
            "files_with_zero_sites": self.files_with_zero_sites,
            "survivor_evidence": self.survivor_evidence[:MAX_SURVIVOR_EVIDENCE],
        }


# DX-97: Mutation orchestration requires isolated temp workspace per mutant
def orchestrate_mutations(
    file_infos: list[FileInfo],
    config: RuleConfig,
    changed_lines: list[tuple[int, int]] | None = None,
    timeout: int = 60,
    project_root: Path | None = None,
) -> Result[MutationAggregation, str]:
    """Orchestrate mutation testing on candidates one at a time.

    DX-97: Materializes each mutant in an isolated temp workspace,
    executes tests, and aggregates results with bounded survivor evidence.

    Fail-closed behavior:
    - TIMEEOUT: Counts as failure (score impact)
    - ERROR: Counts as failure, internal errors recorded
    - SURVIVED: Recorded with bounded evidence (first 5 only)

    Args:
        file_infos: List of FileInfo objects with source code
        config: RuleConfig for candidate collection
        changed_lines: Optional line spans for changed-path filtering
        timeout: Maximum time per mutant execution (seconds)
        project_root: Project root directory (defaults to cwd)

    Returns:
        Success with MutationAggregation or Failure with error message

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> source = "def add(a, b):\\n    return a + b\\n"
        >>> fi = FileInfo(path="test.py", lines=3, source=source)
        >>> result = orchestrate_mutations([fi], RuleConfig())
        >>> isinstance(result, Success)
        True
        >>> result.unwrap().total >= 0
        True
    """
    root = project_root or Path.cwd()

    # Collect candidates deterministically
    try:
        candidates = collect_mutation_candidates(file_infos, config, changed_lines)
    except Exception as e:
        return Failure(f"Failed to collect mutation candidates: {e}")

    # Sort candidates for deterministic ordering (file, line, col_offset)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (c.file, c.line, c.col_offset),
    )

    aggregation = MutationAggregation(total=len(sorted_candidates))

    for candidate in sorted_candidates:
        aggregation.add_candidate(candidate)

        # Get original source from file_infos
        original_source = ""
        for fi in file_infos:
            if fi.path == candidate.file:
                original_source = fi.source or ""
                break

        if not original_source:
            aggregation.add_error(f"Could not find source for {candidate.file}")
            continue

        # Rewrite the mutation site
        rewrite_result = rewrite_mutation_site(original_source, candidate)
        if rewrite_result.is_err():
            aggregation.add_error(f"Rewrite failed for {candidate}: {rewrite_result.source}")
            continue

        mutated_source = rewrite_result.unwrap()

        # Materialize in isolated temp workspace
        tmp_path: Path | None = None
        try:
            with tempfile.TemporaryDirectory(prefix="invar_mutant_", dir=root) as tmp_dir:
                tmp_path = Path(tmp_dir) / candidate.file
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.write_text(mutated_source, encoding="utf-8")

                # Execute tests on the mutant
                mutant_result = execute_mutant_tests(
                    mutated_source=mutated_source,
                    file_path=tmp_path,
                    timeout=timeout,
                    project_root=root,
                )

                aggregation.add_result(mutant_result)

        except Exception as e:
            aggregation.add_error(f"Internal error processing {candidate}: {e}")
        finally:
            # Ensure temp file is cleaned up
            if tmp_path and tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink(missing_ok=True)

    return Success(aggregation)


# =============================================================================
# Legacy mutmut-based implementation (retained for backwards compatibility)
# =============================================================================


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


# Legacy mutmut wrapper (retained for backwards compatibility)
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
                    result.survived = int(line.split("Survived:")[1].split(",")[0].strip())

        result.total = result.killed + result.survived + result.timeout

    # Check for errors
    if stderr and "error" in stderr.lower():
        result.errors.append(stderr.strip())

    if returncode != 0 and not result.errors:
        result.errors.append(f"mutmut exited with status {returncode}")

    return Success(result)


# Legacy mutmut results query (retained for backwards compatibility)
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
            cwd=target.parent if target.is_file() else target,
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
                    break

        return Success(survivors)

    except subprocess.TimeoutExpired:
        return Failure("Results query timed out")
    except Exception as e:
        return Failure(f"Failed to get results: {e}")


# Legacy mutmut diff viewer (retained for backwards compatibility)
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
