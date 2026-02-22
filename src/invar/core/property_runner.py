"""
Property test execution engine.

Extracted from property_gen.py (DX-08) to keep file within size limits.
Contains test execution, hint constants, exception handling, and skip detection.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import deal
from deal import post, pre

if TYPE_CHECKING:
    from collections.abc import Callable

from invar.core.property_gen import PropertyTestResult


@pre(lambda error_str: len(error_str) > 0)
@post(lambda result: result is None or isinstance(result, int))
def _extract_hypothesis_seed(error_str: str) -> int | None:
    """Extract Hypothesis seed from error message (DX-26).

    Hypothesis includes seed in output like: @seed(336048909179393285647920446708996038674)

    >>> _extract_hypothesis_seed("@seed(123456)")
    123456
    >>> _extract_hypothesis_seed("no seed here") is None
    True
    """
    match = re.search(r"@seed\((\d+)\)", error_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


@pre(lambda name, reason, hint=None: len(name) > 0 and len(reason) > 0 and (hint is None or len(hint) > 0))
@post(lambda result: isinstance(result, PropertyTestResult) and result.passed)
def _skip_result(name: str, reason: str, hint: str | None = None) -> PropertyTestResult:
    """Create a skip result (passed=True, 0 examples)."""
    return PropertyTestResult(function_name=name, passed=True, examples_run=0, error=reason, hint=hint)


# Diagnostic hints for @pre/Hypothesis relationship
_HINT_POST_FAILURE = (
    "Hypothesis generates random inputs satisfying @pre, then checks @post. "
    "If @post fails, your @pre may allow invalid inputs — consider tightening it."
)
_HINT_EXCEPTION = (
    "Function raised an exception on input that satisfied @pre. "
    "Your @pre may be too permissive — it should reject inputs the function cannot handle."
)
_HINT_SKIP = (
    "@pre may be too restrictive for Hypothesis to generate valid inputs. "
    "Consider relaxing @pre or adding type hints to help input generation."
)
_HINT_STUB = (
    "Function is a stub (NotImplementedError). "
    "Use invar guard --contracts-only (-c) during SPECIFY phase to check contract coverage without running tests."
)
_HINT_INV = (
    "Generated inputs violated @deal.inv invariant — this is a deal.cases limitation, not a function bug. "
    "deal.cases cannot filter out inputs rejected by @deal.inv during construction. "
    "Consider @skip_property_test to suppress, or add @deal.pre constraints that exclude invalid inputs."
)

# Skip patterns for untestable error detection
_SKIP_PATTERNS = (
    "Nothing",
    "NoSuchExample",
    "filter_too_much",
    "Could not resolve",
    "validation error",
    "missing",
    "positional argument",
    "Unable to satisfy",
    "has no attribute 'check'",  # invar_runtime contracts, not deal contracts
    "NotImplementedError",  # Stub functions in SPECIFY phase
)


@pre(
    lambda err_str, func_name, max_examples: len(err_str) > 0
    and len(func_name) > 0
    and max_examples > 0
)
@post(lambda result: isinstance(result, PropertyTestResult))
def _handle_test_exception(err_str: str, func_name: str, max_examples: int) -> PropertyTestResult:
    """Handle exception from property test, returning skip or failure result."""
    # Stub functions (NotImplementedError) — expected in SPECIFY phase
    if "NotImplementedError" in err_str:
        return _skip_result(func_name, "Skipped: stub function (NotImplementedError)", hint=_HINT_STUB)
    # Check for invar_runtime contracts (deal.cases requires deal contracts)
    if "has no attribute 'check'" in err_str:
        return _skip_result(
            func_name, "Skipped: uses invar_runtime (deal.cases requires deal contracts)"
        )
    if any(p in err_str for p in _SKIP_PATTERNS):
        return _skip_result(func_name, "Skipped: untestable types")
    seed = _extract_hypothesis_seed(err_str)
    return PropertyTestResult(
        func_name, passed=False, examples_run=max_examples, error=err_str, seed=seed,
        hint=_HINT_EXCEPTION,
    )


@pre(lambda exc: isinstance(exc, Exception))
@post(lambda result: result is True or result is False)
def _is_skip_worthy_multi_failure(exc: Exception) -> bool:
    """Check if Hypothesis MultipleFailures contains only skip-worthy sub-exceptions.

    Returns True only when ALL sub-exceptions are skip-worthy:
    deal.InvContractError (invariant rejection during input construction),
    hypothesis.errors.InvalidArgument (typing.Any or unresolvable strategy),
    or string patterns matching _SKIP_PATTERNS.

    Returns False for any real test failure or non-MultipleFailures exception.

    >>> _is_skip_worthy_multi_failure(ValueError("real failure"))
    False
    >>> _is_skip_worthy_multi_failure(RuntimeError("something unexpected"))
    False
    """
    try:
        from hypothesis.errors import InvalidArgument, MultipleFailures
    except ImportError:
        return False

    if not isinstance(exc, MultipleFailures):
        return False

    sub_exceptions = getattr(exc, "exceptions", [])
    if not sub_exceptions:
        return False

    for sub_exc in sub_exceptions:
        sub_str = str(sub_exc)
        is_skip_worthy = (
            isinstance(sub_exc, (deal.InvContractError, InvalidArgument))
            or any(p in sub_str for p in _SKIP_PATTERNS)
        )
        if not is_skip_worthy:
            return False
    return True


@pre(lambda func, max_examples: callable(func) and max_examples > 0)
@post(lambda result: isinstance(result, PropertyTestResult))
def run_property_test(func: Callable, max_examples: int = 100) -> PropertyTestResult:
    """
    Run a property test on a single function.

    Uses deal.cases() which respects @pre conditions and generates valid inputs.

    >>> from deal import pre, post
    >>> @pre(lambda x: x >= 0)
    ... @post(lambda result: result >= 0)
    ... def square(x: int) -> int:
    ...     return x * x
    >>> result = run_property_test(square, max_examples=10)
    >>> isinstance(result, PropertyTestResult)
    True
    """
    func_name = getattr(func, "__name__", "unknown")

    try:
        from hypothesis import HealthCheck, Verbosity, settings

        # DX-26: Suppress Hypothesis output (seed messages) for clean JSON
        test_settings = settings(
            max_examples=max_examples,
            suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
            verbosity=Verbosity.quiet,
        )
        test_case = deal.cases(func, count=max_examples, settings=test_settings)
        test_case()
        return PropertyTestResult(func_name, passed=True, examples_run=max_examples)
    except deal.PreContractError:
        return _skip_result(func_name, "Skipped: could not generate valid inputs", hint=_HINT_SKIP)
    except deal.PostContractError as e:
        err_str = str(e)
        seed = _extract_hypothesis_seed(err_str)
        return PropertyTestResult(
            func_name, passed=False, examples_run=max_examples, error=err_str, seed=seed,
            hint=_HINT_POST_FAILURE,
        )
    except deal.InvContractError:
        # Single InvContractError: @deal.inv rejected a generated input — not a function bug
        return _skip_result(
            func_name,
            "Skipped: @deal.inv invariant rejected generated inputs",
            hint=_HINT_INV,
        )
    except ImportError:
        return _skip_result(func_name, "Skipped: hypothesis not installed")
    except Exception as e:
        # Check if MultipleFailures wraps only skip-worthy sub-exceptions
        if _is_skip_worthy_multi_failure(e):
            return _skip_result(
                func_name,
                "Skipped: untestable types (could not generate valid inputs)",
            )
        return _handle_test_exception(str(e), func_name, max_examples)
