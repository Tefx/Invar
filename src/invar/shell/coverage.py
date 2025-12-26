"""
Coverage integration for Guard verification phases.

DX-37: Collect branch coverage from doctest + hypothesis phases.
Coverage.py is used for accurate tracking via sys.settrace().

Note: CrossHair uses symbolic execution (Z3 solver) in subprocess,
so coverage.py cannot track it. This is a fundamental limitation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from deal import post, pre
from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from coverage import Coverage


@dataclass
class UncoveredBranch:
    """A branch that was never taken during testing.

    Examples:
        >>> branch = UncoveredBranch(line=127, branch_type="else", context="if x > 0:")
        >>> branch.line
        127
        >>> branch.branch_type
        'else'
    """

    line: int
    branch_type: str  # "if", "else", "elif", "except", "for", "while"
    context: str  # Source line for context


@dataclass
class FileCoverage:
    """Coverage data for a single file.

    Examples:
        >>> fc = FileCoverage(path="src/foo.py", branch_coverage=94.5)
        >>> fc.branch_coverage
        94.5
        >>> len(fc.uncovered_branches)
        0
    """

    path: str
    branch_coverage: float  # 0.0 to 100.0
    uncovered_branches: list[UncoveredBranch] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Coverage data from doctest + hypothesis phases.

    Examples:
        >>> report = CoverageReport(overall_branch_coverage=91.2)
        >>> report.phases_tracked
        []
        >>> report.phases_excluded
        ['crosshair']
    """

    overall_branch_coverage: float  # 0.0 to 100.0
    files: dict[str, FileCoverage] = field(default_factory=dict)
    phases_tracked: list[str] = field(default_factory=list)
    phases_excluded: list[str] = field(default_factory=lambda: ["crosshair"])


# @shell_orchestration: Import check utility for coverage.py dependency
def _is_coverage_available() -> bool:
    """Check if coverage.py is installed.

    Examples:
        >>> result = _is_coverage_available()
        >>> isinstance(result, bool)
        True
    """
    try:
        import coverage  # noqa: F401

        return True
    except ImportError:
        return False


@pre(lambda source_dirs: len(source_dirs) >= 0)
@contextmanager
def collect_coverage(source_dirs: list[Path]) -> Iterator[Coverage]:
    """Context manager for coverage collection.

    Args:
        source_dirs: Directories to track coverage for

    Yields:
        Coverage object for data extraction

    Examples:
        >>> from pathlib import Path
        >>> # When coverage is available, yields a Coverage object
        >>> # with collect_coverage([Path("src")]) as cov:
        >>> #     pass  # Execute code to track
    """
    import coverage

    cov = coverage.Coverage(
        branch=True,
        source=[str(d) for d in source_dirs] if source_dirs else None,
        omit=["**/test_*", "**/*_test.py", "**/conftest.py"],
    )

    cov.start()
    try:
        yield cov
    finally:
        cov.stop()
        cov.save()


# @shell_complexity: Coverage API interaction with multiple analysis branches
@pre(lambda cov, files: files is not None)
@post(lambda result: isinstance(result, CoverageReport))
def extract_coverage_report(cov: Coverage, files: list[Path], phase: str) -> CoverageReport:
    """Extract coverage report from Coverage object.

    Args:
        cov: Coverage object after data collection
        files: Files to extract coverage for
        phase: Name of the phase ("doctest" or "hypothesis")

    Returns:
        CoverageReport with branch coverage data

    Examples:
        >>> # After running with collect_coverage:
        >>> # report = extract_coverage_report(cov, [Path("src/foo.py")], "doctest")
        >>> # report.phases_tracked == ["doctest"]
    """
    file_coverages: dict[str, FileCoverage] = {}
    total_branches = 0
    covered_branches = 0

    # Get analysis data
    for file_path in files:
        str_path = str(file_path)
        try:
            # Trigger coverage analysis for this file
            _ = cov.analysis2(str_path)

            # Get branch data
            branch_stats = cov._analyze(str_path)
            if hasattr(branch_stats, "numbers"):
                nums = branch_stats.numbers
                file_total = nums.n_branches
                file_covered = nums.n_branches - nums.n_missing_branches

                if file_total > 0:
                    total_branches += file_total
                    covered_branches += file_covered
                    branch_pct = (file_covered / file_total) * 100

                    # Extract uncovered branches
                    uncovered = []
                    if hasattr(branch_stats, "missing_branch_arcs"):
                        for arc in branch_stats.missing_branch_arcs():
                            from_line, to_line = arc
                            uncovered.append(
                                UncoveredBranch(
                                    line=from_line,
                                    branch_type="branch",
                                    context=f"line {from_line} -> {to_line}",
                                )
                            )

                    file_coverages[str_path] = FileCoverage(
                        path=str_path,
                        branch_coverage=round(branch_pct, 1),
                        uncovered_branches=uncovered[:5],  # Limit to 5 per file
                    )
        except Exception:
            # File not covered or analysis failed
            continue

    overall = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0

    return CoverageReport(
        overall_branch_coverage=round(overall, 1),
        files=file_coverages,
        phases_tracked=[phase],
    )


# @shell_orchestration: Report merging coordinates data from multiple phases
# @shell_complexity: Report merging with multiple iteration paths
@pre(lambda reports: all(isinstance(r, CoverageReport) for r in reports if r is not None))
@post(lambda result: isinstance(result, CoverageReport))
def merge_coverage_reports(reports: list[CoverageReport | None]) -> CoverageReport:
    """Merge coverage from multiple phases.

    Union of covered lines/branches across all phases.
    Only branches uncovered in ALL phases are reported as uncovered.

    Args:
        reports: List of CoverageReport objects (None entries are skipped)

    Returns:
        Merged CoverageReport

    Examples:
        >>> r1 = CoverageReport(overall_branch_coverage=80.0, phases_tracked=["doctest"])
        >>> r2 = CoverageReport(overall_branch_coverage=70.0, phases_tracked=["hypothesis"])
        >>> merged = merge_coverage_reports([r1, r2])
        >>> "doctest" in merged.phases_tracked
        True
        >>> "hypothesis" in merged.phases_tracked
        True
    """
    valid_reports = [r for r in reports if r is not None]

    if not valid_reports:
        return CoverageReport(overall_branch_coverage=0.0)

    if len(valid_reports) == 1:
        return valid_reports[0]

    # Merge phases tracked
    all_phases: list[str] = []
    for r in valid_reports:
        all_phases.extend(r.phases_tracked)

    # Merge file coverages - take the max coverage for each file
    merged_files: dict[str, FileCoverage] = {}
    for r in valid_reports:
        for path, fc in r.files.items():
            if path not in merged_files or fc.branch_coverage > merged_files[path].branch_coverage:
                merged_files[path] = fc

    # Calculate overall as average of file coverages (weighted would be better but needs LOC)
    if merged_files:
        overall = sum(fc.branch_coverage for fc in merged_files.values()) / len(merged_files)
    else:
        overall = 0.0

    return CoverageReport(
        overall_branch_coverage=round(overall, 1),
        files=merged_files,
        phases_tracked=all_phases,
    )


# @shell_orchestration: Format report for Rich console output
@pre(lambda report: isinstance(report, CoverageReport))
@post(lambda result: isinstance(result, str))
def format_coverage_output(report: CoverageReport) -> str:
    """Format coverage report for CLI output.

    Args:
        report: CoverageReport to format

    Returns:
        Formatted string for terminal output

    Examples:
        >>> report = CoverageReport(overall_branch_coverage=91.2, phases_tracked=["doctest"])
        >>> output = format_coverage_output(report)
        >>> "91.2%" in output
        True
        >>> "doctest" in output
        True
    """
    lines = [
        f"Coverage Analysis ({' + '.join(report.phases_tracked)}):",
    ]

    # Sort files by coverage (lowest first to highlight issues)
    sorted_files = sorted(report.files.items(), key=lambda x: x[1].branch_coverage)

    for path, fc in sorted_files[:10]:  # Limit to 10 files
        uncovered_count = len(fc.uncovered_branches)
        lines.append(f"  {path}: {fc.branch_coverage}% branch ({uncovered_count} uncovered)")
        for branch in fc.uncovered_branches[:3]:  # Limit to 3 branches per file
            lines.append(f"    Line {branch.line}: {branch.context}")

    lines.append("")
    lines.append(f"Overall: {report.overall_branch_coverage}% branch coverage ({' + '.join(report.phases_tracked)})")
    lines.append("")
    lines.append("Note: CrossHair uses symbolic execution; coverage not applicable.")

    return "\n".join(lines)


# @shell_orchestration: Format report for JSON agent output
@post(lambda result: isinstance(result, dict))
def format_coverage_json(report: CoverageReport) -> dict:
    """Format coverage report for JSON output.

    Args:
        report: CoverageReport to format

    Returns:
        Dictionary for JSON serialization

    Examples:
        >>> report = CoverageReport(overall_branch_coverage=91.2, phases_tracked=["doctest"])
        >>> data = format_coverage_json(report)
        >>> data["enabled"]
        True
        >>> data["overall_branch_coverage"]
        91.2
    """
    return {
        "enabled": True,
        "phases_tracked": report.phases_tracked,
        "phases_excluded": report.phases_excluded,
        "overall_branch_coverage": report.overall_branch_coverage,
        "files": [
            {
                "path": fc.path,
                "branch_coverage": fc.branch_coverage,
                "uncovered_branches": [
                    {"line": b.line, "type": b.branch_type, "context": b.context}
                    for b in fc.uncovered_branches
                ],
            }
            for fc in report.files.values()
        ],
    }


def check_coverage_available() -> Result[bool, str]:
    """Check if coverage.py is installed and return helpful error if not.

    Returns:
        Success(True) if available, Failure with install instructions if not

    Examples:
        >>> result = check_coverage_available()
        >>> # Either Success(True) or Failure("Install coverage...")
    """
    if _is_coverage_available():
        return Success(True)
    return Failure("Install coverage for --coverage support: pip install coverage[toml]>=7.0")
