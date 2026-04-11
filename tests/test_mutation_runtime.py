"""
Tests for mutation_runtime module.

DX-97: Runtime executor tests for mutation testing.
Focused on killed/survived/timeout/error normalization.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from invar.shell.mutation_runtime import (
    MutantOutcome,
    MutantResult,
    execute_mutant_tests,
    _execute_mutant_with_timeout as execute_mutant_with_timeout,
    _format_mutant_result as format_mutant_result,
)


class TestMutantOutcome:
    """Test MutantOutcome enum."""

    def test_killed_value(self):
        """Killed outcome has correct value."""
        assert MutantOutcome.KILLED.value == "killed"

    def test_survived_value(self):
        """Survived outcome has correct value."""
        assert MutantOutcome.SURVIVED.value == "survived"

    def test_timeout_value(self):
        """Timeout outcome has correct value."""
        assert MutantOutcome.TIMEOUT.value == "timeout"

    def test_error_value(self):
        """Error outcome has correct value."""
        assert MutantOutcome.ERROR.value == "error"


class TestMutantResult:
    """Test MutantResult dataclass."""

    def test_default_construction(self):
        """Can create MutantResult with defaults."""
        result = MutantResult(outcome=MutantOutcome.KILLED)
        assert result.outcome == MutantOutcome.KILLED
        assert result.detail == ""
        assert result.doctest_passed is None
        assert result.property_passed is None
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.elapsed_seconds == 0.0
        assert result.errors == []

    def test_full_construction(self):
        """Can create MutantResult with all fields."""
        result = MutantResult(
            outcome=MutantOutcome.SURVIVED,
            detail="Tests passed",
            doctest_passed=True,
            property_passed=True,
            stdout="test output",
            stderr="",
            elapsed_seconds=1.5,
            errors=[],
        )
        assert result.outcome == MutantOutcome.SURVIVED
        assert result.detail == "Tests passed"
        assert result.doctest_passed is True
        assert result.property_passed is True
        assert result.stdout == "test output"
        assert result.elapsed_seconds == 1.5


class TestExecuteMutantTests:
    """Test execute_mutant_tests function."""

    def test_killed_when_doctest_fails(self):
        """Mutant is killed when doctest fails."""
        # A function where mutation is likely to break doctest
        source = '''def add(a, b):
    """Add a and b.

    >>> add(1, 2)
    3
    """
    return a + b
'''
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                # Doctest fails (mutant killed it)
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "failed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(all_passed=lambda: True, errors=[])
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.KILLED
                assert result.doctest_passed is False

    def test_survived_when_tests_pass(self):
        """Mutant survives when all tests pass."""
        source = '''def add(a, b):
    """Add a and b.

    >>> add(1, 2)
    3
    """
    return a + b
'''
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(all_passed=lambda: True, errors=[])
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.SURVIVED
                assert result.doctest_passed is True
                assert result.property_passed is True

    def test_error_when_doctest_exception(self):
        """Error when doctest throws exception."""
        source = """def add(a, b):
    return a + b
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.side_effect = Exception("Import error")
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(all_passed=lambda: True, errors=[])
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.ERROR
                assert "Import error" in result.errors

    def test_killed_when_property_test_fails(self):
        """Mutant is killed when property test fails."""
        source = """def add(a, b):
    return a + b
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                # Property test fails (mutant killed it)
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(
                        all_passed=lambda: False, errors=["Property test failed"]
                    )
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.KILLED
                assert result.property_passed is False


class TestExecuteMutantWithTimeout:
    """Test execute_mutant_with_timeout function."""

    def test_timeout_returns_timeout_outcome(self):
        """Returns TIMEOUT outcome when execution times out."""
        # A very slow function that will definitely timeout
        source = """def slow():
    import time
    time.sleep(10)
    return 1
"""
        with patch("invar.shell.mutation_runtime.execute_mutant_tests") as mock_exec:
            mock_exec.side_effect = TimeoutError("timed out")

            result = execute_mutant_with_timeout(source, Path("test.py"), timeout=1)

            assert result.outcome == MutantOutcome.TIMEOUT
            assert "timeout" in result.detail.lower()

    def test_normal_execution_proceeds(self):
        """Normal execution proceeds without timeout."""
        source = '''def add(a, b):
    """Add.

    >>> add(1, 2)
    3
    """
    return a + b
'''
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(all_passed=lambda: True, errors=[])
                )

                result = execute_mutant_with_timeout(source, Path("test.py"), timeout=60)

                # Should not timeout
                assert result.outcome != MutantOutcome.TIMEOUT
                # Should complete normally
                assert result.elapsed_seconds > 0


class TestFormatMutantResult:
    """Test format_mutant_result function."""

    def test_killed_format(self):
        """Format killed result correctly."""
        result = MutantResult(
            outcome=MutantOutcome.KILLED,
            detail="Tests caught mutation",
            doctest_passed=False,
            elapsed_seconds=0.5,
        )
        formatted = format_mutant_result(result)
        assert "KILLED" in formatted
        assert "Tests caught mutation" in formatted
        assert "0.50" in formatted

    def test_survived_format(self):
        """Format survived result correctly."""
        result = MutantResult(
            outcome=MutantOutcome.SURVIVED,
            detail="Tests passed on mutated code",
            doctest_passed=True,
            property_passed=True,
            elapsed_seconds=1.0,
        )
        formatted = format_mutant_result(result)
        assert "SURVIVED" in formatted
        assert "Tests passed" in formatted

    def test_timeout_format(self):
        """Format timeout result correctly."""
        result = MutantResult(
            outcome=MutantOutcome.TIMEOUT,
            detail="Execution exceeded 60s",
            elapsed_seconds=60.0,
        )
        formatted = format_mutant_result(result)
        assert "TIMEOUT" in formatted
        assert "60s" in formatted

    def test_error_format(self):
        """Format error result correctly."""
        result = MutantResult(
            outcome=MutantOutcome.ERROR,
            detail="Import failed",
            errors=["No module named 'foo'"],
            elapsed_seconds=0.1,
        )
        formatted = format_mutant_result(result)
        assert "ERROR" in formatted
        assert "Import failed" in formatted
        assert "1" in formatted  # Error count


class TestOutcomeNormalization:
    """Test outcome normalization across different scenarios."""

    def test_error_takes_precedence_over_killed(self):
        """Error outcome takes precedence over killed."""
        source = """def test():
    return 1
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "failed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.side_effect = Exception("Runtime error")

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.ERROR

    def test_error_takes_precedence_over_survived(self):
        """Error outcome takes precedence over survived."""
        source = """def test():
    return 1
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.side_effect = Exception("Import error")

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.ERROR

    def test_killed_when_either_test_fails(self):
        """Mutant killed if either doctest or property test fails."""
        source = """def test():
    return 1
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                # Doctest passes but property fails
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(
                        all_passed=lambda: False, errors=["Counterexample found"]
                    )
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.KILLED
                assert result.property_passed is False

    def test_survived_only_when_both_pass(self):
        """Mutant survives only when both tests pass."""
        source = """def test():
    return 1
"""
        with patch("invar.shell.mutation_runtime.run_doctests_on_files") as mock_dt:
            with patch("invar.shell.mutation_runtime.run_property_tests_on_file") as mock_pt:
                mock_dt.return_value = MagicMock(
                    unwrap=lambda: {
                        "status": "passed",
                        "stdout": "",
                        "stderr": "",
                        "errors": [],
                    }
                )
                mock_pt.return_value = MagicMock(
                    unwrap=lambda: MagicMock(all_passed=lambda: True, errors=[])
                )

                result = execute_mutant_tests(source, Path("test.py"))

                assert result.outcome == MutantOutcome.SURVIVED
                assert result.doctest_passed is True
                assert result.property_passed is True
