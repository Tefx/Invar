"""Regression tests proving property-target owner-loss bug (expected-red).

These tests document the current broken behavior before any src/ fix.
Each test case demonstrates a specific scenario where @skip_property_test
markers are lost or mis-resolved due to wrong target resolution.

Bug: find_contracted_functions() returns function names from class methods,
but run_property_tests_on_file() uses module-level getattr which cannot
correctly resolve classmethod/staticmethod descriptors, causing the
skip marker (attached to the underlying function) to be invisible.

Expected-red means: these tests FAIL today, and will PASS once the fix is applied.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from returns.result import Success

if TYPE_CHECKING:
    from invar.shell.property_tests import PropertyTestReport


# =============================================================================
# Test Fixtures — Minimal source snippets per scenario
# =============================================================================


class TestClassDunderOwnerLoss:
    """Scenario 1: class dunder method with @skip_property_test fails today.

    Expected error pattern: "expected 1 argument, got 0" — because the
    module-level getattr sees the descriptor wrapper, not the bound method,
    so when called without self it gets the wrong signature.
    """

    def test_class_dunder_skip_still_fails(self, tmp_path: Path) -> None:
        """Class __eq__ with @skip_property_test still fails today.

        This is the PRIMARY expected-red test. The error 'expected 1 argument, got 0'
        occurs because module-level getattr on __eq__ returns the descriptor wrapper
        that requires self, but deal.cases calls it without the self argument.
        """
        # Create a minimal module with a class containing a dunder method
        # decorated with @skip_property_test
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        mod_file = src_dir / "example_class.py"
        mod_file.write_text(
            """
from deal import pre, post
from invar_runtime import skip_property_test


class MyClass:
    @skip_property_test("equality_op: identity only, no testable property")
    @pre(lambda self, other: self.value == other.value)
    @post(lambda result: result is True or result is False)
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MyClass):
            return False
        return self.value == other.value

    def __init__(self, value: int) -> None:
        self.value = value


def make_instance(v: int) -> MyClass:
    return MyClass(v)
""".lstrip()
        )

        # Create __init__.py to make it a package
        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        # The bug manifests as: the function is NOT skipped properly,
        # and either an error occurs or it's treated as untestable.
        # After fix: it should be recognized as skipped (functions_skipped > 0)
        assert isinstance(result, Success), f"Expected Success, got {type(result)}: {result}"
        report: PropertyTestReport = result.unwrap()

        # BUG: Today, this reports functions_failed=1 with error "expected 1 argument, got 0"
        # because module-level getattr on __eq__ returns the wrapper,
        # not the bound method with the skip marker.
        # After fix: functions_skipped should be 1.
        assert report.functions_skipped >= 1, (
            f"Expected __eq__ to be skipped, but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )


class TestNonDunderClassMethodOwnership:
    """Scenario 2: non-dunder class method ownership is currently lost.

    Regular class methods (not dunders) decorated with @skip_property_test
    lose their markers when accessed via module-level getattr.
    """

    def test_non_dunder_class_method_skips_lost(self, tmp_path: Path) -> None:
        """Non-dunder class method @skip_property_test marker is lost today."""
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        mod_file = src_dir / "class_method_example.py"
        mod_file.write_text(
            """
from deal import pre, post
from invar_runtime import skip_property_test


class Calculator:
    @skip_property_test("no_params: Returns fixed result, not variable")
    @post(lambda result: result == 42)
    def fixed_result(self) -> int:
        return 42
""".lstrip()
        )

        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        assert isinstance(result, Success), f"Expected Success, got {type(result)}: {result}"
        report = result.unwrap()

        # BUG: fixed_result is NOT being skipped because the marker is on the
        # underlying function, but getattr(module, "fixed_result") gets a bound
        # method that doesn't carry the __invar_skip_property_test__ attribute.
        # After fix: functions_skipped should be 1.
        assert report.functions_skipped >= 1, (
            f"Expected fixed_result to be skipped, but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )


class TestModuleLevelEqCollision:
    """Scenario 3: module-level __eq__ collision/shadowing case.

    CONTROL CASE: This test PASSES because module-level functions work correctly.
    This proves the bug is SPECIFICALLY about class-owned methods losing their
    skip markers via module-level getattr resolution.
    """

    def test_module_eq_not_masked_by_class_eq(self, tmp_path: Path) -> None:
        """Module-level __eq__ is NOT masked by class __eq__ (control case)."""
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        mod_file = src_dir / "eq_collision.py"
        mod_file.write_text(
            """
from deal import pre, post
from invar_runtime import skip_property_test


# Module-level __eq__ (different from class)
@skip_property_test("module_level: module identity comparison")
@post(lambda result: result is True or result is False)
def __eq__(a: object, b: object) -> bool:  # shadowing built-in
    return a is b


class SomeClass:
    @pre(lambda self, other: True)
    @post(lambda result: result is True or result is False)
    def __eq__(self, other: object) -> bool:
        return self is other
""".lstrip()
        )

        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        assert isinstance(result, Success), f"Expected Success, got {type(result)}: {result}"
        report = result.unwrap()

        # CONTROL CASE: Module-level __eq__ IS correctly skipped.
        # This proves the bug is class-specific, not universal.
        assert report.functions_skipped >= 1, (
            f"Expected module __eq__ to be skipped (control passes), but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )


class TestStaticmethodClassmethodVariants:
    """Scenario 4: staticmethod/classmethod decorator-order variants.

    The order of @staticmethod/@classmethod vs @skip_property_test affects
    whether the skip marker is visible. Different decorator orders create
    different descriptor chains.
    """

    @pytest.mark.parametrize(
        "decorator_order",
        [
            "skip_then_static",  # @skip -> @staticmethod (inner to outer)
            "static_then_skip",  # @staticmethod -> @skip (outer to inner)
        ],
        ids=["skip_then_static", "static_then_skip"],
    )
    def test_staticmethod_skip_marker_variants(self, tmp_path: Path, decorator_order: str) -> None:
        """staticmethod decorator order affects skip marker visibility."""
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        if decorator_order == "skip_then_static":
            deco_code = """
    @skip_property_test("static_helper: no instance dependence")
    @staticmethod
    @pre(lambda x: x >= 0)
    @post(lambda result: result >= 1)
    def helper(x: int) -> int:
        return x + 1
"""
        else:
            deco_code = """
    @staticmethod
    @skip_property_test("static_helper: no instance dependence")
    @pre(lambda x: x >= 0)
    @post(lambda result: result >= 1)
    def helper(x: int) -> int:
        return x + 1
"""

        mod_file = src_dir / "static_method_variants.py"
        mod_file.write_text(
            f"""
from deal import pre, post
from invar_runtime import skip_property_test


class MathLib:
{deco_code}
""".lstrip()
        )

        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        assert isinstance(result, Success), f"Expected Success, got {type(result)}: {result}"
        report = result.unwrap()

        # BUG: At least one order fails to skip because the decorator chain
        # doesn't preserve the __invar_skip_property_test__ marker correctly.
        # After fix: both orders should result in skip.
        assert report.functions_skipped >= 1, (
            f"Expected staticmethod helper to be skipped in {decorator_order}, but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )

    @pytest.mark.parametrize(
        "decorator_order",
        [
            "skip_then_class",  # @skip -> @classmethod
            "class_then_skip",  # @classmethod -> @skip
        ],
        ids=["skip_then_class", "class_then_skip"],
    )
    def test_classmethod_skip_marker_variants(self, tmp_path: Path, decorator_order: str) -> None:
        """classmethod decorator order affects skip marker visibility."""
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        if decorator_order == "skip_then_class":
            deco_code = """
    @skip_property_test("class_config: returns class-level config")
    @classmethod
    @post(lambda result: isinstance(result, dict))
    def get_config(cls) -> dict:
        return {{}}
"""
        else:
            deco_code = """
    @classmethod
    @skip_property_test("class_config: returns class-level config")
    @post(lambda result: isinstance(result, dict))
    def get_config(cls) -> dict:
        return {{}}
"""

        mod_file = src_dir / "class_method_variants.py"
        mod_file.write_text(
            f"""
from deal import pre, post
from invar_runtime import skip_property_test


class Config:
{deco_code}
""".lstrip()
        )

        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        assert isinstance(result, Success), f"Expected Success, got {type(result)}: {result}"
        report = result.unwrap()

        # BUG: At least one order fails to skip properly.
        # After fix: both orders should result in skip.
        assert report.functions_skipped >= 1, (
            f"Expected classmethod get_config to be skipped in {decorator_order}, but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )


class TestPlainInstanceMethodsNotMisResolved:
    """Scenario 5: plain instance methods are not silently mis-resolved.

    Plain instance methods (no @skip_property_test) cannot be tested by
    deal.cases() which cannot construct the ``self`` argument. After the fix,
    they receive an EXPLICIT skip with a clear hint, rather than being
    silently swallowed or mis-resolved to a wrong callable.
    """

    def test_plain_instance_method_explicitly_skipped(self, tmp_path: Path) -> None:
        """Plain instance method without skip decorator is explicitly skipped.

        After fix: instance methods are skipped with a clear diagnostic hint,
        not silently dropped or mis-resolved to the wrong callable.
        """
        from invar.shell.property_tests import run_property_tests_on_file

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        mod_file = src_dir / "plain_methods.py"
        mod_file.write_text(
            """
from deal import pre, post


class Counter:
    @pre(lambda self, n: n >= 0)
    @post(lambda result: result >= 0)
    def increment(self, n: int) -> int:
        return n + 1
""".lstrip()
        )

        (src_dir / "__init__.py").write_text("")

        result = run_property_tests_on_file(mod_file, max_examples=10, project_root=tmp_path)

        assert isinstance(result, Success), f"Expected SUCCESS, got {result}"
        report = result.unwrap()

        # After fix: instance methods are explicitly skipped with a clear hint,
        # not silently dropped.  functions_skipped should be 1.
        assert report.functions_skipped >= 1, (
            f"Expected increment to be explicitly skipped, but got "
            f"tested={report.functions_tested} "
            f"failed={report.functions_failed} "
            f"skipped={report.functions_skipped}"
        )
        # The skip result must contain a hint mentioning that self cannot be constructed
        skip_results = [r for r in report.results if r.passed and r.examples_run == 0]
        assert any("self" in (r.hint or "") for r in skip_results), (
            f"Expected skip hint to mention 'self', got hints: {[r.hint for r in skip_results]}"
        )
