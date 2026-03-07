"""
Tests for test_only_export sub-category of dead_export rule.

These tests verify that:
1. Public function used only in test files gets test_only_export sub-category
2. Public function used in production gets normal dead_export (or no warning)
3. test_only_export message is distinct from regular dead_export
4. Severity differs from regular dead_export

Note: These tests initially fail until the fix is implemented.
"""

from __future__ import annotations

from invar.core.dead_export import check_dead_exports
from invar.core.models import FileInfo, RuleConfig, Severity, Symbol, SymbolKind


def test_public_function_used_only_in_test_files_gets_test_only_export():
    """Public function referenced only from tests/ should get test_only_export sub-category."""
    # Symbol defined in shell (production code)
    sym = Symbol(name="helper_for_test", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    # This is in a shell file (production)
    file_info = FileInfo(path="shell/api.py", lines=10, symbols=[sym], is_shell=True)

    # Reference counts show it IS referenced - but only from test files
    # Currently, this would show 1 reference (from tests/)
    # The fix should detect that references are ONLY from tests/ directory
    ref_counts = {"shell/api.py::helper_for_test": 1}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    # Currently there would be no violation (it's referenced)
    # After fix: should have test_only_export violation
    assert len(violations) >= 1, "Expected test_only_export violation for test-only function"
    v = violations[0]
    # The rule should indicate test_only_export sub-category
    assert "test_only" in v.rule.lower() or "test_only" in v.message.lower(), (
        f"Expected test_only_export sub-category, got rule={v.rule}, message={v.message}"
    )


def test_public_function_used_in_production_gets_no_warning():
    """Public function used in production code should get no warning (or normal dead_export if unused)."""
    # Symbol defined in shell
    sym = Symbol(name="used_in_prod", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info = FileInfo(path="shell/api.py", lines=10, symbols=[sym], is_shell=True)

    # Reference count > 0 (referenced from production code)
    ref_counts = {"shell/api.py::used_in_prod": 1}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    # Should have NO violations - it's used in production
    assert len(violations) == 0, (
        f"Expected no violation for production-used function, got {violations}"
    )


def test_unreferenced_public_function_gets_dead_export():
    """Public function with zero references should get normal dead_export."""
    sym = Symbol(name="truly_dead", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info = FileInfo(path="shell/api.py", lines=10, symbols=[sym], is_shell=True)

    # Zero references
    ref_counts = {"shell/api.py::truly_dead": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    assert len(violations) == 1
    v = violations[0]
    assert v.rule == "dead_export"
    assert v.severity == Severity.WARNING


def test_test_only_export_message_distinct_from_regular_dead_export():
    """test_only_export message should be distinct from regular dead_export."""
    # Test-only function (referenced only from tests/)
    sym_test_only = Symbol(name="test_helper", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_test = FileInfo(
        path="shell/utils.py", lines=10, symbols=[sym_test_only], is_shell=True
    )
    ref_counts_test = {"shell/utils.py::test_helper": 1}  # Referenced from tests

    # Truly dead function (no references)
    sym_dead = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_dead = FileInfo(path="shell/api.py", lines=10, symbols=[sym_dead], is_shell=True)
    ref_counts_dead = {"shell/api.py::unused_func": 0}

    violations_test = check_dead_exports([file_info_test], ref_counts_test, RuleConfig())
    violations_dead = check_dead_exports([file_info_dead], ref_counts_dead, RuleConfig())

    # Get messages
    test_only_msg = violations_test[0].message if violations_test else ""
    dead_export_msg = violations_dead[0].message if violations_dead else ""

    # Messages should be distinct
    assert test_only_msg != dead_export_msg, (
        f"Messages should be distinct: test_only='{test_only_msg}', dead_export='{dead_export_msg}'"
    )

    # test_only message should mention "test" or similar
    assert "test" in test_only_msg.lower(), (
        f"test_only message should mention 'test': {test_only_msg}"
    )


def test_test_only_export_severity_differs_from_regular_dead_export():
    """test_only_export should have lower severity than regular dead_export."""
    # Test-only function
    sym_test_only = Symbol(name="test_helper", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_test = FileInfo(
        path="shell/utils.py", lines=10, symbols=[sym_test_only], is_shell=True
    )
    ref_counts_test = {"shell/utils.py::test_helper": 1}

    # Dead function
    sym_dead = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_dead = FileInfo(path="shell/api.py", lines=10, symbols=[sym_dead], is_shell=True)
    ref_counts_dead = {"shell/api.py::unused_func": 0}

    violations_test = check_dead_exports([file_info_test], ref_counts_test, RuleConfig())
    violations_dead = check_dead_exports([file_info_dead], ref_counts_dead, RuleConfig())

    # Both should produce violations
    assert len(violations_test) >= 1, "Expected test_only_export violation"
    assert len(violations_dead) >= 1, "Expected dead_export violation"

    severity_test = violations_test[0].severity
    severity_dead = violations_dead[0].severity

    # Severities should differ
    assert severity_test != severity_dead, (
        f"Severities should differ: test_only={severity_test}, dead_export={severity_dead}"
    )

    # test_only should have lower severity than dead_export (INFO vs WARNING)
    # In Severity enum: INFO < WARNING
    assert severity_test.value < severity_dead.value, (
        f"test_only should have lower severity: got test_only={severity_test}, dead_export={severity_dead}"
    )
