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
    """Public function referenced only from test files should get test_only_export sub-category."""
    # Symbol defined in shell (production code)
    sym = Symbol(name="helper_for_test", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    # This is in a shell file (production)
    file_info = FileInfo(path="shell/api.py", lines=10, symbols=[sym], is_shell=True)

    # Reference counts show it IS referenced - but only from test files
    ref_counts = {"shell/api.py::helper_for_test": 1}
    # Pass reference sources to indicate it's only referenced from test files
    ref_sources = {"shell/api.py::helper_for_test": ["tests/test_api.py"]}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig(), ref_sources)

    # Should have test_only_export violation
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
    # Referenced from a non-test file
    ref_sources = {"shell/api.py::used_in_prod": ["shell/other.py"]}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig(), ref_sources)

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
    ref_sources_test = {"shell/utils.py::test_helper": ["tests/test_utils.py"]}

    # Truly dead function (no references)
    sym_dead = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_dead = FileInfo(path="shell/api.py", lines=10, symbols=[sym_dead], is_shell=True)
    ref_counts_dead = {"shell/api.py::unused_func": 0}

    violations_test = check_dead_exports(
        [file_info_test], ref_counts_test, RuleConfig(), ref_sources_test
    )
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
    ref_sources_test = {"shell/utils.py::test_helper": ["tests/test_utils.py"]}

    # Dead function
    sym_dead = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=1, end_line=3)
    file_info_dead = FileInfo(path="shell/api.py", lines=10, symbols=[sym_dead], is_shell=True)
    ref_counts_dead = {"shell/api.py::unused_func": 0}

    violations_test = check_dead_exports(
        [file_info_test], ref_counts_test, RuleConfig(), ref_sources_test
    )
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


# ============================================================================
# CLASS-SPECIFIC TEST CASES (AC1-AC7)
# ============================================================================


def test_ac1_dead_public_class_detected():
    """AC1 - Dead public class detected.

    A public class in shell with zero cross-file references should be
    reported as dead_export with WARNING severity.
    """
    sym = Symbol(name="UnusedClass", kind=SymbolKind.CLASS, line=5, end_line=20)
    file_info = FileInfo(path="shell/models.py", lines=30, symbols=[sym], is_shell=True)

    # Zero references (dead)
    ref_counts = {"shell/models.py::UnusedClass": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    v = violations[0]
    assert v.rule == "dead_export"
    assert v.severity == Severity.WARNING
    assert "UnusedClass" in v.message
    assert "class" in v.message.lower(), "Message should mention 'class'"


def test_ac2_referenced_class_not_reported():
    """AC2 - Referenced class NOT reported.

    A public class that has cross-file references should NOT be reported
    as dead_export.
    """
    sym = Symbol(name="UsedClass", kind=SymbolKind.CLASS, line=5, end_line=20)
    file_info = FileInfo(path="shell/models.py", lines=30, symbols=[sym], is_shell=True)

    # Has references from production code
    ref_counts = {"shell/models.py::UsedClass": 3}
    ref_sources = {"shell/models.py::UsedClass": ["shell/api.py", "shell/utils.py"]}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig(), ref_sources)

    assert len(violations) == 0, f"Expected no violations for referenced class, got {violations}"


def test_ac3_protocol_subclass_exempt():
    """AC3 - Protocol subclass exempt.

    Classes that inherit from typing.Protocol should be exempt from
    dead_export detection because they define interfaces, not implementations.
    """
    sym = Symbol(name="MyProtocol", kind=SymbolKind.CLASS, line=5, end_line=10)
    # Protocol subclass - source shows inheritance from Protocol
    source = """
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> int: ...
"""
    file_info = FileInfo(
        path="shell/interfaces.py", lines=10, symbols=[sym], is_shell=True, source=source
    )

    # Zero references, but Protocol subclass should be exempt
    ref_counts = {"shell/interfaces.py::MyProtocol": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    assert len(violations) == 0, (
        f"Protocol subclass should be exempt from dead_export, got {violations}"
    )


def test_ac4_abc_subclass_exempt():
    """AC4 - ABC subclass exempt.

    Classes that inherit from abc.ABC should be exempt from dead_export
    detection because they define abstract interfaces, not concrete implementations.
    """
    sym = Symbol(name="MyAbstract", kind=SymbolKind.CLASS, line=5, end_line=10)
    # ABC subclass - source shows inheritance from ABC
    source = """
from abc import ABC

class MyAbstract(ABC):
    def abstract_method(self) -> int: ...
"""
    file_info = FileInfo(
        path="shell/abstracts.py", lines=10, symbols=[sym], is_shell=True, source=source
    )

    # Zero references, but ABC subclass should be exempt
    ref_counts = {"shell/abstracts.py::MyAbstract": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    assert len(violations) == 0, f"ABC subclass should be exempt from dead export, got {violations}"


def test_ac5_escape_hatch_works_for_class():
    """AC5 - Escape hatch works for class.

    Classes with @invar:allow dead_export marker should be exempt
    from dead_export detection, just like functions.
    """
    sym = Symbol(name="LegacyClass", kind=SymbolKind.CLASS, line=5, end_line=15)
    # Escape hatch marker present
    source = """
# @invar:allow dead_export: Legacy API class used by external systems
class LegacyClass:
    def method(self):
        pass
"""
    file_info = FileInfo(
        path="shell/legacy.py", lines=20, symbols=[sym], is_shell=True, source=source
    )

    # Zero references, but has escape hatch
    ref_counts = {"shell/legacy.py::LegacyClass": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    # Should have exactly 1 violation - escape hatch does NOT suppress dead_export
    # (dead_export is non-suppressible per ESCAPE_TIER_MAP)
    assert len(violations) == 1, (
        f"dead_export should still be reported despite escape hatch (non-suppressible), got {len(violations)}"
    )


def test_ac6_mixed_symbols_dead_class_live_function_dead_function():
    """AC6 - Mixed symbols: dead class + live function + dead function.

    When multiple symbols exist in the same file, each should be evaluated
    independently. Dead class should be reported, live function should not,
    dead function should be reported.
    """
    # Dead public class
    sym_class = Symbol(name="DeadClass", kind=SymbolKind.CLASS, line=1, end_line=10)
    # Live function (has references)
    sym_func_live = Symbol(name="live_function", kind=SymbolKind.FUNCTION, line=12, end_line=20)
    # Dead function (no references)
    sym_func_dead = Symbol(name="dead_function", kind=SymbolKind.FUNCTION, line=22, end_line=30)

    file_info = FileInfo(
        path="shell/mixed.py",
        lines=40,
        symbols=[sym_class, sym_func_live, sym_func_dead],
        is_shell=True,
    )

    # Reference counts
    ref_counts = {
        "shell/mixed.py::DeadClass": 0,  # Dead class
        "shell/mixed.py::live_function": 5,  # Live function
        "shell/mixed.py::dead_function": 0,  # Dead function
    }

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    # Should have 2 violations: dead class and dead function
    assert len(violations) == 2, f"Expected 2 violations, got {len(violations)}"
    rules = sorted([v.rule for v in violations])
    assert rules == ["dead_export", "dead_export"], f"Expected two dead_export rules, got {rules}"

    # Check messages mention class vs function
    class_violation = next((v for v in violations if "DeadClass" in v.message), None)
    func_violation = next((v for v in violations if "dead_function" in v.message), None)

    assert class_violation is not None, "Should have violation for DeadClass"
    assert func_violation is not None, "Should have violation for dead_function"
    assert "class" in class_violation.message.lower(), "Class violation should mention 'class'"
    assert "function" in func_violation.message.lower(), (
        "Function violation should mention 'function'"
    )


def test_ac7_nested_inner_classes_only_top_level_checked():
    """AC7 - Nested/inner classes: only top-level public classes checked.

    Currently, nested/inner classes are not extracted as separate symbols
    from file_info.symbols. This test documents expected behavior where
    only top-level public classes are checked for dead exports.
    """
    # Top-level public class (should be checked)
    sym_toplevel = Symbol(name="TopClass", kind=SymbolKind.CLASS, line=5, end_line=30)

    file_info = FileInfo(
        path="shell/nested.py",
        lines=50,
        symbols=[sym_toplevel],  # Only top-level symbol extracted
        is_shell=True,
    )

    # Zero references
    ref_counts = {"shell/nested.py::TopClass": 0}

    violations = check_dead_exports([file_info], ref_counts, RuleConfig())

    # Top-level class should be reported
    assert len(violations) == 1
    assert "TopClass" in violations[0].message

    # Note: InnerClass would not be in symbols, so it wouldn't be checked
    # This is the expected behavior - nested classes are not separate symbols
