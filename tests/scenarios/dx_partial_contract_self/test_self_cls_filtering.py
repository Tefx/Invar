"""
Isolated Test Scenario: partial_contract should skip self/cls for methods.

Bug: partial_contract rule was reporting `self` and `cls` as unchecked
parameters in method @pre contracts, causing false positives.

Fix: Filter out self/cls from unused params check for METHOD symbols.

Run: pytest tests/scenarios/dx_partial_contract_self/test_self_cls_filtering.py -v
"""

import pytest

from invar.core.contracts import check_partial_contract, has_unused_params
from invar.core.models import Contract, FileInfo, RuleConfig, Symbol, SymbolKind


class TestHasUnusedParams:
    """Low-level tests for has_unused_params function."""

    def test_function_detects_unused_param(self):
        """Function: should detect unused 'y' parameter."""
        has_unused, unused, used = has_unused_params(
            "lambda x, y: x > 0", "(x: int, y: int) -> int"
        )
        assert has_unused is True
        assert "y" in unused
        assert "x" in used

    def test_method_raw_includes_self_in_unused(self):
        """Raw check: self IS in unused list (low-level behavior)."""
        has_unused, unused, used = has_unused_params(
            "lambda self, x, y: x > 0", "(self, x: int, y: int) -> int"
        )
        # At low level, self is reported as unused
        assert "self" in unused
        assert "y" in unused
        assert "x" in used

    def test_all_params_used(self):
        """No unused params when all are used."""
        has_unused, unused, used = has_unused_params(
            "lambda x, y: x > 0 and y < 10", "(x: int, y: int) -> int"
        )
        assert has_unused is False
        assert unused == []
        assert "x" in used
        assert "y" in used


class TestCheckPartialContractFiltering:
    """Integration tests for self/cls filtering in check_partial_contract."""

    def _make_file_info(self, symbol: Symbol) -> FileInfo:
        """Helper to create FileInfo with a single symbol."""
        return FileInfo(path="test.py", lines=10, symbols=[symbol], is_core=True)

    def test_method_self_not_reported(self):
        """BUG FIX: Method @pre should NOT warn about unchecked 'self'."""
        method = Symbol(
            name="test_method",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(self, x: int, y: int)",
            contracts=[Contract(kind="pre", expression="lambda self, x, y: x > 0", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(method), RuleConfig())

        # Should have 1 violation for 'y', but NOT for 'self'
        assert len(violations) == 1
        assert "self" not in violations[0].message
        assert "'y'" in violations[0].message

    def test_method_cls_not_reported(self):
        """BUG FIX: Classmethod @pre should NOT warn about unchecked 'cls'."""
        classmethod = Symbol(
            name="test_classmethod",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(cls, x: int, y: int)",
            contracts=[Contract(kind="pre", expression="lambda cls, x, y: x > 0", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(classmethod), RuleConfig())

        # Should have 1 violation for 'y', but NOT for 'cls'
        assert len(violations) == 1
        assert "cls" not in violations[0].message
        assert "'y'" in violations[0].message

    def test_method_all_params_checked_no_violation(self):
        """Method with all params checked (except self) should have no violation."""
        method = Symbol(
            name="fully_checked",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(self, x: int, y: int)",
            contracts=[
                Contract(kind="pre", expression="lambda self, x, y: x > 0 and y > 0", line=1)
            ],
        )

        violations = check_partial_contract(self._make_file_info(method), RuleConfig())

        assert len(violations) == 0

    def test_function_still_reports_all_unused(self):
        """Function (not method) should report ALL unused params."""
        func = Symbol(
            name="test_func",
            kind=SymbolKind.FUNCTION,
            line=1,
            end_line=5,
            signature="(x: int, y: int, z: int)",
            contracts=[Contract(kind="pre", expression="lambda x, y, z: x > 0", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(func), RuleConfig())

        assert len(violations) == 1
        assert "'y'" in violations[0].message
        assert "'z'" in violations[0].message

    def test_non_core_file_skipped(self):
        """Non-core files should be skipped entirely."""
        method = Symbol(
            name="shell_method",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(self, x: int)",
            contracts=[Contract(kind="pre", expression="lambda self, x: True", line=1)],
        )
        # is_core=False
        file_info = FileInfo(path="shell.py", lines=10, symbols=[method], is_core=False)

        violations = check_partial_contract(file_info, RuleConfig())

        assert len(violations) == 0

    def test_post_contracts_not_checked(self):
        """@post contracts should not be checked for unused params."""
        method = Symbol(
            name="with_post",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(self, x: int, y: int)",
            contracts=[
                # @post only takes 'result', not function params
                Contract(kind="post", expression="lambda result: result > 0", line=1)
            ],
        )

        violations = check_partial_contract(self._make_file_info(method), RuleConfig())

        # @post is not checked, so no violations
        assert len(violations) == 0


class TestEdgeCases:
    """Edge cases for self/cls filtering."""

    def _make_file_info(self, symbol: Symbol) -> FileInfo:
        return FileInfo(path="test.py", lines=10, symbols=[symbol], is_core=True)

    def test_only_self_param_no_violation(self):
        """Method with only self param should have no violation."""
        method = Symbol(
            name="no_params",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=3,
            signature="(self)",
            contracts=[Contract(kind="pre", expression="lambda self: True", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(method), RuleConfig())

        assert len(violations) == 0

    def test_self_and_cls_both_filtered(self):
        """Both self and cls should be filtered (edge case)."""
        # This is an unusual signature but tests the filtering logic
        method = Symbol(
            name="weird_method",
            kind=SymbolKind.METHOD,
            line=1,
            end_line=5,
            signature="(self, cls, x: int)",
            contracts=[Contract(kind="pre", expression="lambda self, cls, x: x > 0", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(method), RuleConfig())

        # No violation because x is checked and self/cls are filtered
        assert len(violations) == 0

    def test_variable_named_self_in_function_is_reported(self):
        """A function param named 'self' (unusual) should still be reported."""
        # This is poor style but technically valid Python
        func = Symbol(
            name="func_with_self_param",
            kind=SymbolKind.FUNCTION,  # NOT a method!
            line=1,
            end_line=5,
            signature="(self, x: int)",
            contracts=[Contract(kind="pre", expression="lambda self, x: x > 0", line=1)],
        )

        violations = check_partial_contract(self._make_file_info(func), RuleConfig())

        # For FUNCTION (not METHOD), 'self' is just a regular param name
        # and SHOULD be reported as unused
        assert len(violations) == 1
        assert "'self'" in violations[0].message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
