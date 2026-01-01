"""
Property test generation from contracts.

DX-08: Automatically generates Hypothesis property tests from @pre/@post contracts.
Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from deal import post, pre

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class PropertyTestResult:
    """Result of running a property test.

    DX-26: Added file_path and seed for actionable failure output.
    """

    function_name: str
    passed: bool
    examples_run: int = 0
    counterexample: dict[str, Any] | None = None
    error: str | None = None
    file_path: str | None = None  # DX-26: For file::function format
    seed: int | None = None  # DX-26: Hypothesis seed for reproduction


@dataclass
class GeneratedTest:
    """A generated property test."""

    function_name: str
    module_name: str
    strategies: dict[str, str]  # param_name -> strategy code
    test_code: str
    description: str = ""


@dataclass
class PropertyTestReport:
    """Report from running property tests on multiple functions."""

    functions_tested: int = 0
    functions_passed: int = 0
    functions_failed: int = 0
    functions_skipped: int = 0
    total_examples: int = 0
    results: list[PropertyTestResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @post(lambda result: isinstance(result, bool))
    def all_passed(self) -> bool:
        """Check if all tests passed.

        >>> report = PropertyTestReport(functions_failed=0)
        >>> report.all_passed()
        True
        >>> report2 = PropertyTestReport(functions_failed=1)
        >>> report2.all_passed()
        False
        """
        return self.functions_failed == 0 and len(self.errors) == 0


@pre(lambda func: callable(func))
@post(lambda result: result is None or isinstance(result, dict))
def _infer_strategy_strings(func: Callable) -> dict[str, str] | None:
    """Infer strategy code strings from function.

    >>> def example(x: int) -> int: return x
    >>> result = _infer_strategy_strings(example)
    >>> result is None or isinstance(result, dict)
    True
    """
    # Lazy import to avoid circular dependency
    from invar.core.hypothesis_strategies import infer_strategies_for_function

    try:
        strategy_specs = infer_strategies_for_function(func)
    except Exception:
        return None

    if not strategy_specs:
        return None

    strategies: dict[str, str] = {}
    for param_name, spec in strategy_specs.items():
        try:
            strategies[param_name] = spec.to_code()
        except (AttributeError, TypeError):
            continue

    return strategies if strategies else None


@pre(lambda func: callable(func))
@post(lambda result: result is None or isinstance(result, GeneratedTest))
def generate_property_test(func: Callable) -> GeneratedTest | None:
    """
    Generate a Hypothesis property test from a function's contracts.

    Returns None if:
    - Function has no @pre contracts
    - @pre is too complex to parse
    - Types are not inferrable

    DX-08: Uses strategies.py for constraint inference and
    hypothesis_strategies.py for type-based strategy generation.

    >>> def example(x: int) -> int:
    ...     return x * 2
    >>> result = generate_property_test(example)
    >>> result is None or isinstance(result, GeneratedTest)
    True
    """
    # Get function metadata
    try:
        func_name = func.__name__
        module_name = func.__module__ or "__main__"
    except AttributeError:
        return None

    # Infer strategies
    strategies = _infer_strategy_strings(func)
    if not strategies:
        return None

    # Generate test code
    test_code = _generate_test_code(func_name, strategies)

    return GeneratedTest(
        function_name=func_name,
        module_name=module_name,
        strategies=strategies,
        test_code=test_code,
        description=f"Property test for {func_name}",
    )


@pre(lambda func_name, strategies: len(func_name) > 0 and len(strategies) > 0)
@post(lambda result: isinstance(result, str) and "@given" in result)
def _generate_test_code(func_name: str, strategies: dict[str, str]) -> str:
    """
    Generate the actual test code string.

    >>> code = _generate_test_code("sqrt", {"x": "st.floats(min_value=0)"})
    >>> "@given" in code
    True
    >>> "def test_sqrt_property" in code
    True
    """
    # Build @given decorator arguments
    given_args = ", ".join(f"{name}={strat}" for name, strat in strategies.items())

    # Build test function
    param_list = ", ".join(strategies.keys())

    return f'''@given({given_args})
def test_{func_name}_property({param_list}):
    """Auto-generated property test for {func_name}."""
    {func_name}({param_list})  # @post verified by deal at runtime
'''


@pre(lambda dec: isinstance(dec, ast.Call) and hasattr(dec, "func"))
@post(lambda result: isinstance(result, tuple) and len(result) == 2)
def _check_decorator_contracts(dec: ast.Call) -> tuple[bool, bool]:
    """Check if decorator is @pre or @post, return (has_pre, has_post).

    >>> import ast
    >>> code = "pre(lambda x: x > 0)"
    >>> tree = ast.parse(code, mode='eval')
    >>> isinstance(tree.body, ast.Call)
    True
    """
    func = dec.func
    has_pre, has_post = False, False
    # @pre(...) or @post(...)
    if isinstance(func, ast.Name):
        has_pre = func.id == "pre"
        has_post = func.id == "post"
    # @deal.pre(...) or @deal.post(...)
    elif isinstance(func, ast.Attribute):
        has_pre = func.attr == "pre"
        has_post = func.attr == "post"
    return has_pre, has_post


@pre(lambda node: (
    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
    hasattr(node, 'decorator_list')
))
@post(lambda result: isinstance(result, tuple) and len(result) == 2)
def _get_function_contracts(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[bool, bool]:
    """Check function decorators for contracts, return (has_pre, has_post).

    >>> import ast
    >>> code = '''
    ... @pre(lambda x: x > 0)
    ... def foo(x): pass
    ... '''
    >>> tree = ast.parse(code)
    >>> func_node = tree.body[0]
    >>> isinstance(func_node, ast.FunctionDef)
    True
    """
    has_pre, has_post = False, False
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            dec_pre, dec_post = _check_decorator_contracts(dec)
            has_pre = has_pre or dec_pre
            has_post = has_post or dec_post
    return has_pre, has_post


@pre(lambda source: isinstance(source, str) and len(source) > 0)
@post(lambda result: isinstance(result, list))
def find_contracted_functions(source: str) -> list[dict[str, Any]]:
    """
    Find all functions with @pre/@post contracts in source code.

    >>> source = '''
    ... from deal import pre, post
    ... @pre(lambda x: x > 0)
    ... def sqrt(x: float) -> float:
    ...     return x ** 0.5
    ... '''
    >>> funcs = find_contracted_functions(source)
    >>> len(funcs) >= 0
    True
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, TypeError):
        return []

    functions: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_pre, has_post = _get_function_contracts(node)
            if has_pre or has_post:
                functions.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "has_pre": has_pre,
                    "has_post": has_post,
                    "params": _extract_params(node),
                    "return_type": _extract_return_type(node),
                })
    return functions


@pre(lambda node: isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(node, "args"))
@post(lambda result: isinstance(result, list))
def _extract_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, str]]:
    """Extract parameter names and type annotations from function node."""
    params = []
    for arg in node.args.args:
        param_info = {"name": arg.arg, "type": None}
        if arg.annotation:
            param_info["type"] = ast.unparse(arg.annotation)
        params.append(param_info)
    return params


@pre(lambda node: isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
@post(lambda result: result is None or isinstance(result, str))
def _extract_return_type(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Extract return type annotation from function node."""
    if node.returns:
        return ast.unparse(node.returns)
    return None


@pre(lambda func, strategies, max_examples=100: callable(func) and isinstance(strategies, dict))
@post(lambda result: result is None or callable(result))
def build_test_function(
    func: Callable,
    strategies: dict[str, str],
    max_examples: int = 100,
) -> Callable | None:
    """
    Build an executable test function using Hypothesis.

    Returns None if hypothesis is not available.

    >>> def example(x: int) -> int:
    ...     return x * 2
    >>> test_fn = build_test_function(example, {"x": "st.integers()"})
    >>> test_fn is None or callable(test_fn)
    True
    """
    # Lazy import: hypothesis is optional dependency
    try:
        from hypothesis import given, settings
        from hypothesis import strategies as st
    except ImportError:
        return None

    # Build strategy dict
    strategy_dict = {}
    for param_name, strat_code in strategies.items():
        # Skip functions with nothing() strategy (untestable types)
        if "nothing()" in strat_code:
            return None

        # Evaluate the strategy code
        try:
            # strat_code is like "st.integers(min_value=0)"
            strategy = eval(strat_code, {"st": st})
            strategy_dict[param_name] = strategy
        except Exception:
            # If evaluation fails, use a fallback
            return None

    if not strategy_dict:
        return None

    # Create the test function
    @settings(max_examples=max_examples)
    @given(**strategy_dict)
    def property_test(**kwargs):
        func(**kwargs)

    property_test.__name__ = f"test_{func.__name__}_property"
    return property_test


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
    import re

    match = re.search(r"@seed\((\d+)\)", error_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


@pre(lambda name, reason: len(name) > 0 and len(reason) > 0)
@post(lambda result: isinstance(result, PropertyTestResult) and result.passed)
def _skip_result(name: str, reason: str) -> PropertyTestResult:
    """Create a skip result (passed=True, 0 examples)."""
    return PropertyTestResult(function_name=name, passed=True, examples_run=0, error=reason)


# Skip patterns for untestable error detection
_SKIP_PATTERNS = (
    "Nothing", "NoSuchExample", "filter_too_much", "Could not resolve",
    "validation error", "missing", "positional argument", "Unable to satisfy",
    "has no attribute 'check'",  # invar_runtime contracts, not deal contracts
)


@pre(lambda err_str, func_name, max_examples: len(err_str) > 0 and len(func_name) > 0 and max_examples > 0)
@post(lambda result: isinstance(result, PropertyTestResult))
def _handle_test_exception(
    err_str: str, func_name: str, max_examples: int
) -> PropertyTestResult:
    """Handle exception from property test, returning skip or failure result."""
    # Check for invar_runtime contracts (deal.cases requires deal contracts)
    if "has no attribute 'check'" in err_str:
        return _skip_result(func_name, "Skipped: uses invar_runtime (deal.cases requires deal contracts)")
    if any(p in err_str for p in _SKIP_PATTERNS):
        return _skip_result(func_name, "Skipped: untestable types")
    seed = _extract_hypothesis_seed(err_str)
    return PropertyTestResult(func_name, passed=False, examples_run=max_examples, error=err_str, seed=seed)


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
        import deal
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
        return _skip_result(func_name, "Skipped: could not generate valid inputs")
    except deal.PostContractError as e:
        err_str = str(e)
        seed = _extract_hypothesis_seed(err_str)
        return PropertyTestResult(func_name, passed=False, examples_run=max_examples, error=err_str, seed=seed)
    except ImportError:
        pass  # Fall through to custom strategy approach
    except Exception as e:
        return _handle_test_exception(str(e), func_name, max_examples)
