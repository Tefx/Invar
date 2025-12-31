"""Contract coverage analysis for DX-63 - Shell layer.

I/O operations for checking contract coverage, detecting batch creation,
and formatting reports. Different from coverage.py which handles branch coverage.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 - used at runtime

from returns.result import Failure, Result, Success

from invar.core.trivial_detection import (
    TrivialContract,
    analyze_contracts_in_source,
)


@dataclass
class BatchWarning:
    """Warning for batch file creation without contracts.

    Examples:
        >>> bw = BatchWarning(
        ...     file_count=5,
        ...     files=[("src/a.py", 3, 0), ("src/b.py", 4, 1)],
        ...     message="Multiple new files with low coverage"
        ... )
        >>> bw.file_count
        5
    """

    file_count: int
    files: list[tuple[str, int, int]]  # (file, total_funcs, with_contracts)
    message: str


@dataclass
class ContractCoverageReport:
    """Contract coverage check result.

    Examples:
        >>> report = ContractCoverageReport(
        ...     files_checked=3,
        ...     total_functions=10,
        ...     functions_with_contracts=8,
        ...     trivial_contracts=[],
        ...     batch_warning=None
        ... )
        >>> report.coverage_pct
        80
        >>> report.ready_for_build
        True
    """

    files_checked: int = 0
    total_functions: int = 0
    functions_with_contracts: int = 0
    trivial_contracts: list[TrivialContract] = field(default_factory=list)
    batch_warning: BatchWarning | None = None

    @property
    def coverage_pct(self) -> int:
        """Get coverage percentage.

        Examples:
            >>> ContractCoverageReport(total_functions=10, functions_with_contracts=7).coverage_pct
            70
            >>> ContractCoverageReport(total_functions=0, functions_with_contracts=0).coverage_pct
            100
        """
        if self.total_functions == 0:
            return 100
        return int(100 * self.functions_with_contracts / self.total_functions)

    @property
    def trivial_count(self) -> int:
        """Count of trivial contracts."""
        return len(self.trivial_contracts)

    @property
    def ready_for_build(self) -> bool:
        """Check if ready for BUILD phase.

        Ready when:
        - Coverage >= 80%
        - No trivial contracts
        - No batch warning

        Examples:
            >>> ContractCoverageReport(total_functions=10, functions_with_contracts=10).ready_for_build
            True
            >>> ContractCoverageReport(total_functions=10, functions_with_contracts=5).ready_for_build
            False
        """
        if self.trivial_contracts:
            return False
        if self.batch_warning:
            return False
        return self.coverage_pct >= 80


def count_contracts_in_file(
    file_path: Path,
) -> Result[tuple[int, int, list[TrivialContract]], str]:
    """Count functions and contracts in a file.

    Returns: Result containing (total_functions, functions_with_contracts, trivial_contracts)
    """
    if not file_path.exists():
        return Failure(f"File not found: {file_path}")

    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return Failure(f"Encoding error: {e}")

    result = analyze_contracts_in_source(source, str(file_path))
    return Success(result)


# @shell_complexity: Git status parsing requires multiple branch conditions
def get_changed_python_files(path: Path) -> Result[list[Path], str]:
    """Get Python files changed in git."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=path,
            check=False,
        )
        if result.returncode != 0:
            return Failure(f"Git error: {result.stderr}")

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Status is first 2 chars, then space, then filename
            status = line[:2]
            filename = line[3:].strip()

            # Include new, modified, or untracked Python files
            if filename.endswith(".py") and status.strip():
                file_path = path / filename
                if file_path.exists():
                    files.append(file_path)

        return Success(files)
    except FileNotFoundError:
        return Failure("Git not found")


# @shell_complexity: Coverage calculation with multiple file/directory handling paths
def calculate_contract_coverage(
    path: Path, changed_only: bool = False
) -> Result[ContractCoverageReport, str]:
    """Calculate contract coverage for a path (file or directory)."""
    report = ContractCoverageReport()

    if path.is_file():
        if path.suffix == ".py":
            result = count_contracts_in_file(path)
            if isinstance(result, Failure):
                return result
            total, with_contracts, trivials = result.unwrap()
            report.files_checked = 1
            report.total_functions = total
            report.functions_with_contracts = with_contracts
            report.trivial_contracts = trivials
    else:
        # Get files to check
        if changed_only:
            files_result = get_changed_python_files(path)
            if isinstance(files_result, Failure):
                return files_result
            files = files_result.unwrap()
        else:
            files = list(path.rglob("*.py"))

        # Filter out test files, __pycache__, etc.
        files = [
            f
            for f in files
            if "__pycache__" not in str(f)
            and "test_" not in f.name
            and "_test.py" not in f.name
            and ".venv" not in str(f)
        ]

        for file_path in files:
            result = count_contracts_in_file(file_path)
            if isinstance(result, Failure):
                continue  # Skip files with errors
            total, with_contracts, trivials = result.unwrap()
            report.files_checked += 1
            report.total_functions += total
            report.functions_with_contracts += with_contracts
            report.trivial_contracts.extend(trivials)

        # Check for batch creation
        batch_result = detect_batch_creation(path)
        if isinstance(batch_result, Success):
            report.batch_warning = batch_result.unwrap()

    return Success(report)


# @shell_complexity: Batch detection with git status parsing and threshold logic
def detect_batch_creation(
    path: Path, threshold: int = 3
) -> Result[BatchWarning | None, str]:
    """Detect batch file creation without contracts.

    Returns BatchWarning if >= threshold new/untracked files have < 50% coverage.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=path,
            check=False,
        )
        if result.returncode != 0:
            return Success(None)

        uncovered_files: list[tuple[str, int, int]] = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            status = line[:2]
            filename = line[3:].strip()

            # Check new/untracked Python files (status starts with ? or A)
            if filename.endswith(".py") and status[0] in ("?", "A"):
                file_path = path / filename
                if file_path.exists():
                    count_result = count_contracts_in_file(file_path)
                    if isinstance(count_result, Success):
                        total, with_contracts, _ = count_result.unwrap()
                        if total > 0:
                            coverage_pct = int(100 * with_contracts / total)
                            if coverage_pct < 50:
                                uncovered_files.append(
                                    (filename, total, with_contracts)
                                )

        if len(uncovered_files) >= threshold:
            return Success(
                BatchWarning(
                    file_count=len(uncovered_files),
                    files=uncovered_files,
                    message="Multiple new files with low contract coverage",
                )
            )

        return Success(None)

    except FileNotFoundError:
        return Success(None)


# @shell_orchestration: Report formatting for CLI output display
# @shell_complexity: Report formatting with multiple conditional sections
def format_contract_coverage_report(report: ContractCoverageReport) -> str:
    """Format coverage report for human-readable output."""
    lines = [
        "Contract Coverage Check",
        "=" * 40,
        f"Files: {report.files_checked} | Functions: {report.total_functions}",
        "",
    ]

    # Coverage line
    coverage_pct = report.coverage_pct
    if coverage_pct >= 80:
        lines.append(
            f"Coverage: {report.functions_with_contracts}/{report.total_functions} "
            f"({coverage_pct}%) \u2713"
        )
    else:
        lines.append(
            f"Coverage: {report.functions_with_contracts}/{report.total_functions} "
            f"({coverage_pct}%) \u2717"
        )

    # Trivial contracts
    total = max(1, report.total_functions)
    if report.trivial_contracts:
        trivial_pct = int(100 * report.trivial_count / total)
        lines.append(f"Trivial:  {report.trivial_count}/{report.total_functions} ({trivial_pct}%) \u2717")
        lines.append("")
        lines.append("\u2717 Trivial contracts detected:")
        for tc in report.trivial_contracts:
            lines.append(
                f"  - {tc.file}:{tc.line} {tc.function_name} "
                f"@{tc.contract_type}({tc.expression})"
            )
    else:
        lines.append(f"Trivial:  0/{report.total_functions} (0%) \u2713")

    # Batch warning
    if report.batch_warning:
        lines.append("")
        lines.append(
            f"\u26a0 BATCH WARNING: {report.batch_warning.file_count} "
            "new files with low coverage"
        )
        for filename, total_f, with_c in report.batch_warning.files:
            lines.append(f"  - {filename} ({with_c}/{total_f})")
        lines.append("")
        lines.append("Recommendation: Add contracts incrementally, one file at a time.")

    # Final status
    lines.append("")
    if report.ready_for_build:
        lines.append("Ready for BUILD phase.")
    else:
        lines.append("Not ready for BUILD phase.")

    return "\n".join(lines)


# @shell_orchestration: Output formatting for CLI integration
def format_contract_coverage_agent(report: ContractCoverageReport) -> dict:
    """Format coverage report for agent JSON output."""
    return {
        "status": "passed" if report.ready_for_build else "failed",
        "contract_coverage": {
            "files_checked": report.files_checked,
            "total_functions": report.total_functions,
            "functions_with_contracts": report.functions_with_contracts,
            "coverage_pct": report.coverage_pct,
            "trivial_count": report.trivial_count,
            "trivial_contracts": [
                {
                    "file": tc.file,
                    "line": tc.line,
                    "function": tc.function_name,
                    "type": tc.contract_type,
                    "expression": tc.expression,
                }
                for tc in report.trivial_contracts
            ],
            "batch_warning": (
                {
                    "file_count": report.batch_warning.file_count,
                    "files": report.batch_warning.files,
                    "message": report.batch_warning.message,
                }
                if report.batch_warning
                else None
            ),
            "ready_for_build": report.ready_for_build,
        },
    }
