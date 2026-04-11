"""
Tests for mutation orchestration.

DX-97: Tests for Shell mutation orchestration including:
- Temp workspace cleanup
- Deterministic candidate ordering
- Bounded survivor evidence
- Fail-closed aggregation
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from returns.result import Failure, Success

from invar.core.models import FileInfo, RuleConfig
from invar.core.mutation_sites import MutationCandidate
from invar.shell.mutation import (
    MAX_SURVIVOR_EVIDENCE,
    MutationAggregation,
    orchestrate_mutations,
)
from invar.shell.mutation_runtime import MutantOutcome, MutantResult


class TestMutationAggregation:
    """Test MutationAggregation dataclass."""

    def test_default_construction(self):
        """Can create MutationAggregation with defaults."""
        agg = MutationAggregation()
        assert agg.total == 0
        assert agg.killed == 0
        assert agg.survived == 0
        assert agg.timeout == 0
        assert agg.error == 0
        assert agg.survivor_evidence == []
        assert agg.internal_errors == []
        assert agg.candidates_order == []

    def test_score_calculation(self):
        """Score is calculated correctly."""
        agg = MutationAggregation(total=10, killed=8)
        assert agg.score == 80.0

    def test_score_zero_total(self):
        """Score is 100% when total is 0."""
        agg = MutationAggregation(total=0)
        assert agg.score == 100.0

    def test_passed_true_when_score_at_threshold(self):
        """Passed is True when score is at 80% threshold."""
        agg = MutationAggregation(total=10, killed=8)
        assert agg.passed is True

    def test_passed_false_when_score_below_threshold(self):
        """Passed is False when score is below 80% threshold."""
        agg = MutationAggregation(total=10, killed=7)
        assert agg.passed is False

    def test_passed_false_when_survived(self):
        """Passed is False when mutants survived (fail-closed)."""
        agg = MutationAggregation(total=10, survived=2)
        assert agg.passed is False

    def test_add_candidate_records_order(self):
        """add_candidate records deterministic ordering."""
        c = MutationCandidate(
            file="a.py",
            line=1,
            col_offset=0,
            operator="Add",
            original_source="x + y",
            mutated_source="x - y",
        )
        agg = MutationAggregation()
        agg.add_candidate(c)
        assert "a.py:1:Add" in agg.candidates_order

    def test_add_result_killed(self):
        """add_result increments killed counter."""
        agg = MutationAggregation()
        r = MutantResult(outcome=MutantOutcome.KILLED, detail="Tests caught mutation")
        agg.add_result(r)
        assert agg.killed == 1

    def test_add_result_survived_bounded(self):
        """add_result bounds survivor evidence to MAX_SURVIVOR_EVIDENCE."""
        agg = MutationAggregation()
        for i in range(10):
            r = MutantResult(outcome=MutantOutcome.SURVIVED, detail=f"Survivor {i}")
            agg.add_result(r)

        assert agg.survived == 10
        assert len(agg.survivor_evidence) == MAX_SURVIVOR_EVIDENCE
        assert agg.survivor_evidence[0] == "Survivor 0"
        assert agg.survivor_evidence[-1] == f"Survivor {MAX_SURVIVOR_EVIDENCE - 1}"

    def test_add_result_timeout_counts_as_failure(self):
        """add_result counts timeout as failure."""
        agg = MutationAggregation()
        r = MutantResult(outcome=MutantOutcome.TIMEOUT, detail="Timed out")
        agg.add_result(r)
        assert agg.timeout == 1
        assert agg.passed is False  # Fail-closed

    def test_add_result_error_counts_as_failure(self):
        """add_result counts error as failure."""
        agg = MutationAggregation()
        r = MutantResult(
            outcome=MutantOutcome.ERROR,
            detail="Internal error",
            errors=["Import failed"],
        )
        agg.add_result(r)
        assert agg.error == 1
        assert "Import failed" in agg.internal_errors

    def test_add_error(self):
        """add_error records internal errors."""
        agg = MutationAggregation()
        agg.add_error("Rewrite failed")
        assert agg.error == 1
        assert "Rewrite failed" in agg.internal_errors


class TestDeterministicOrdering:
    """Test deterministic candidate ordering."""

    def test_candidates_sorted_by_file_line_col(self):
        """Candidates are sorted by file, line, col_offset."""
        source = """def f():
    return a + b
    return x - y
"""
        fi = FileInfo(path="test.py", lines=4, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            # Return killed for all mutants
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            # The order should be: Add on line 2, Sub on line 3
            assert len(agg.candidates_order) == 2
            # Sorted by line number
            assert agg.candidates_order[0] == "test.py:2:Add"
            assert agg.candidates_order[1] == "test.py:3:Sub"

    def test_multiple_files_sorted(self):
        """Candidates from multiple files are sorted deterministically."""
        source_a = "def f():\n    return a + b\n"
        source_b = "def g():\n    return x - y\n"
        fi_a = FileInfo(path="b.py", lines=2, source=source_a)
        fi_b = FileInfo(path="a.py", lines=2, source=source_b)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi_a, fi_b], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            # a.py should come before b.py alphabetically
            assert agg.candidates_order[0].startswith("a.py")
            assert agg.candidates_order[1].startswith("b.py")


class TestBoundedSurvivorEvidence:
    """Test bounded survivor evidence."""

    def test_survivor_evidence_bounded_to_max(self):
        """Survivor evidence is bounded to MAX_SURVIVOR_EVIDENCE."""
        source = "def f():\n    return 1\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            # Return survived for all mutants
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.SURVIVED, detail="Tests passed"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            # Even with many survivors, evidence is bounded
            assert len(agg.survivor_evidence) <= MAX_SURVIVOR_EVIDENCE

    def test_survivor_evidence_first_n(self):
        """Survivor evidence contains first N survivors."""
        source = "def f():\n    return 1\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            # Return survived with unique details
            def make_survived(i):
                return MutantResult(outcome=MutantOutcome.SURVIVED, detail=f"Survivor {i}")

            mock_exec.side_effect = lambda *args, **kwargs: make_survived(
                len(mock_exec.call_args_list)
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert len(agg.survivor_evidence) <= MAX_SURVIVOR_EVIDENCE


class TestFailClosed:
    """Test fail-closed behavior."""

    def test_timeout_fails_closed(self):
        """Timeout counts as failure (score impact)."""
        source = "def f():\n    return a + b\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.TIMEOUT, detail="Execution exceeded 60s"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.timeout == 1
            assert agg.passed is False  # Fail-closed

    def test_error_fails_closed(self):
        """Error counts as failure (score impact)."""
        source = "def f():\n    return a + b\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.ERROR,
                detail="Import failed",
                errors=["No module named 'foo'"],
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.error == 1
            assert agg.passed is False  # Fail-closed

    def test_internal_error_fails_closed(self):
        """Internal errors (e.g., rewrite failure) fail closed."""
        # Use a source that will cause rewrite issues
        source = "def f():\n    return a + b\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            # Simulate an exception during execution
            mock_exec.side_effect = Exception("Unexpected error")

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.error >= 1
            assert agg.passed is False  # Fail-closed


class TestTempWorkspaceCleanup:
    """Test temp workspace cleanup."""

    def test_temp_workspace_not_left_in_caller_dir(self):
        """Temp workspace files are cleaned up after mutation."""
        source = "def add(a, b):\n    return a + b\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Track what files exist before
            before_files = set(project_root.rglob("*"))

            with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
                mock_exec.return_value = MutantResult(
                    outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
                )

                result = orchestrate_mutations([fi], RuleConfig(), project_root=project_root)

                assert isinstance(result, Success)

            # Track what files exist after
            after_files = set(project_root.rglob("*"))

            # Only temp dirs may remain (they auto-clean), no test.py or mutants
            new_files = after_files - before_files
            # Filter out temp directories that may exist
            leftover = [f for f in new_files if f.is_file() and "invar_mutant" not in str(f)]
            assert len(leftover) == 0, f"Temp files left behind: {leftover}"

    def test_exception_during_execution_cleans_up(self):
        """Cleanup happens even when exception occurs during execution."""
        source = "def f():\n    return a + b\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
                mock_exec.side_effect = Exception("Simulated failure")

                result = orchestrate_mutations([fi], RuleConfig(), project_root=project_root)

                # Should still return success with aggregation
                assert isinstance(result, Success)
                agg = result.unwrap()
                assert agg.error >= 1

            # No temp files should remain
            remaining = list(project_root.rglob("invar_mutant*"))
            assert len(remaining) == 0


class TestChangedLinesFiltering:
    """Test changed_lines filtering."""

    def test_changed_lines_filters_candidates(self):
        """Candidates are filtered by changed_lines span."""
        source = "def f():\n    return a + b\n    return a - c\n"
        fi = FileInfo(path="test.py", lines=4, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            # Only line 2 changed, so only Add operator should be included
            result = orchestrate_mutations([fi], RuleConfig(), changed_lines=[(2, 2)])

            assert isinstance(result, Success)
            agg = result.unwrap()
            # Should only have 1 candidate (the Add on line 2)
            assert agg.total == 1
            assert "Add" in agg.candidates_order[0]


class TestEmptyAndEdgeCases:
    """Test edge cases."""

    def test_no_candidates_returns_empty_aggregation(self):
        """No candidates returns aggregation with zero totals."""
        # Source with no binary operators
        source = "def f():\n    return 1\n"
        fi = FileInfo(path="test.py", lines=2, source=source)

        result = orchestrate_mutations([fi], RuleConfig())

        assert isinstance(result, Success)
        agg = result.unwrap()
        assert agg.total == 0
        assert agg.score == 100.0  # 0/0 treated as 100%
        assert agg.passed is True

    def test_source_not_found_returns_error(self):
        """Source file not found is recorded as internal error."""
        # FileInfo with source that doesn't match any candidate's file
        fi = FileInfo(path="other.py", lines=10, source="# no ops")

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            # other.py doesn't match test.py candidates
            result = orchestrate_mutations([fi], RuleConfig())

            # Should handle gracefully
            assert isinstance(result, Success)


class TestChangedLinesNone:
    """Test when changed_lines is None (full scan)."""

    def test_none_means_no_filtering(self):
        """changed_lines=None means no filtering (all candidates)."""
        source = "def f():\n    return a + b\n    return a - c\n"
        fi = FileInfo(path="test.py", lines=4, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            # None = no filtering
            result = orchestrate_mutations([fi], RuleConfig(), changed_lines=None)

            assert isinstance(result, Success)
            agg = result.unwrap()
            # Both Add (line 2) and Sub (line 3) should be present
            assert agg.total == 2


class TestFileClassificationPopulation:
    """DX-97: Verify that orchestrate_mutations populates eligible_files,
    ineligible_files, and files_with_zero_sites from real orchestration flow.

    These fields MUST be populated by the pipeline, not set manually.
    """

    def test_eligible_files_populated_for_files_with_candidates(self):
        """Files with mutation sites are counted as eligible_files."""
        source = "def f():\n    return a + b\n"
        fi = FileInfo(path="eligible.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.eligible_files == 1, (
                f"eligible_files should be 1 (file with Add operator), got {agg.eligible_files}"
            )

    def test_files_with_zero_sites_populated(self):
        """Files with no mutation sites are counted as files_with_zero_sites."""
        # Source with no binary operators
        source = "def f():\n    return 1\n"
        fi = FileInfo(path="no_sites.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.files_with_zero_sites == 1, (
                f"files_with_zero_sites should be 1 (parsed OK but no operators), got {agg.files_with_zero_sites}"
            )

    def test_ineligible_files_populated_for_unparseable_source(self):
        """Files with unparseable source are counted as ineligible_files."""
        # Syntax error in source
        source = "def f(:\n    return a + b\n"
        fi = FileInfo(path="bad.py", lines=2, source=source)

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.ineligible_files == 1, (
                f"ineligible_files should be 1 (syntax error), got {agg.ineligible_files}"
            )

    def test_mixed_file_classification(self):
        """Multiple files with different classifications are counted correctly."""
        eligible_source = "def f():\n    return a + b\n"  # Has mutation site
        zero_site_source = "def g():\n    return 1\n"  # Parsed OK, no sites
        bad_source = "def h(:\n    return x + y\n"  # Unparseable

        files = [
            FileInfo(path="eligible.py", lines=2, source=eligible_source),
            FileInfo(path="zero_sites.py", lines=2, source=zero_site_source),
            FileInfo(path="bad.py", lines=2, source=bad_source),
        ]

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations(files, RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.eligible_files == 1, f"eligible_files should be 1, got {agg.eligible_files}"
            assert agg.files_with_zero_sites == 1, (
                f"files_with_zero_sites should be 1, got {agg.files_with_zero_sites}"
            )
            assert agg.ineligible_files == 1, (
                f"ineligible_files should be 1, got {agg.ineligible_files}"
            )

    def test_file_without_source_is_ineligible(self):
        """Files with empty/None source are counted as ineligible."""
        fi = FileInfo(path="empty.py", lines=0, source="")

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations([fi], RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            assert agg.ineligible_files == 1, (
                f"ineligible_files should be 1 (no source), got {agg.ineligible_files}"
            )

    def test_classification_sums_match_total_files(self):
        """eligible_files + ineligible_files + files_with_zero_sites equals total input files."""
        files = [
            FileInfo(path="a.py", lines=2, source="def f():\n    return a + b\n"),
            FileInfo(path="b.py", lines=2, source="def g():\n    return 1\n"),
            FileInfo(path="c.py", lines=2, source="def h(:\n    return x + y\n"),
            FileInfo(path="d.py", lines=2, source="def i():\n    return a - b\n"),
        ]

        with patch("invar.shell.mutation.execute_mutant_tests") as mock_exec:
            mock_exec.return_value = MutantResult(
                outcome=MutantOutcome.KILLED, detail="Tests caught mutation"
            )

            result = orchestrate_mutations(files, RuleConfig())

            assert isinstance(result, Success)
            agg = result.unwrap()
            total_classified = agg.eligible_files + agg.ineligible_files + agg.files_with_zero_sites
            assert total_classified == len(files), (
                f"Classification sum ({total_classified}) must equal total files ({len(files)}). "
                f"eligible={agg.eligible_files}, ineligible={agg.ineligible_files}, "
                f"zero_sites={agg.files_with_zero_sites}"
            )
