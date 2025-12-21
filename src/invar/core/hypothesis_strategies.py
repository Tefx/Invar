"""
Hypothesis strategy generation from type annotations and @pre contracts.

Core module: converts Python types and @pre bounds to Hypothesis strategies.
Part of DX-12: Hypothesis as CrossHair fallback.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

from deal import post, pre

if TYPE_CHECKING:
    from collections.abc import Callable

# Lazy import to avoid dependency issues
_hypothesis_available = False
_numpy_available = False


@post(lambda result: isinstance(result, bool))
def _ensure_hypothesis() -> bool:
    """Check if hypothesis is available."""
    global _hypothesis_available
    try:
        import hypothesis  # noqa: F401

        _hypothesis_available = True
        return True
    except ImportError:
        return False


@post(lambda result: isinstance(result, bool))
def _ensure_numpy() -> bool:
    """Check if numpy is available."""
    global _numpy_available
    try:
        import numpy  # noqa: F401

        _numpy_available = True
        return True
    except ImportError:
        return False


# ============================================================
# Timeout Inference
# ============================================================


@dataclass
class TimeoutTier:
    """Timeout tier for CrossHair based on code characteristics."""

    name: str
    timeout: int
    description: str


TIMEOUT_TIERS = {
    "pure_python": TimeoutTier("pure_python", 10, "Pure Python, no external libs"),
    "stdlib_only": TimeoutTier("stdlib_only", 15, "Uses collections, itertools"),
    "numpy_pandas": TimeoutTier("numpy_pandas", 5, "Quick check, likely to skip"),
    "complex_nested": TimeoutTier("complex_nested", 30, "Deep recursion, many branches"),
}

# Libraries that CrossHair cannot handle well
LIBRARY_BLACKLIST = frozenset([
    "numpy", "pandas", "torch", "tensorflow", "scipy",
    "sklearn", "cv2", "PIL", "requests", "aiohttp",
])


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, int) and result > 0)
def infer_timeout(func: Callable) -> int:
    """
    Infer appropriate CrossHair timeout from function source.

    Args:
        func: The function to analyze

    Returns:
        Timeout in seconds

    >>> def pure_func(x: int) -> int: return x * 2
    >>> infer_timeout(pure_func)
    10
    """
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return TIMEOUT_TIERS["pure_python"].timeout

    # Check for blacklisted libraries
    for lib in LIBRARY_BLACKLIST:
        if re.search(rf"\b{lib}\b", source):
            return TIMEOUT_TIERS["numpy_pandas"].timeout

    # Count complexity indicators
    nesting_depth = _estimate_nesting_depth(source)
    branch_count = _count_branches(source)

    if nesting_depth > 4 or branch_count > 10:
        return TIMEOUT_TIERS["complex_nested"].timeout

    if _uses_only_stdlib(source):
        return TIMEOUT_TIERS["stdlib_only"].timeout

    return TIMEOUT_TIERS["pure_python"].timeout


@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, int) and result >= 0)
def _estimate_nesting_depth(source: str) -> int:
    """Estimate maximum nesting depth from indentation."""
    max_indent = 0
    for line in source.split("\n"):
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(stripped)
            spaces = indent // 4  # Assuming 4-space indent
            max_indent = max(max_indent, spaces)
    return max_indent


@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, int) and result >= 0)
def _count_branches(source: str) -> int:
    """Count branching statements (if, for, while, try)."""
    return len(re.findall(r"\b(if|for|while|try|elif|except)\b", source))


@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, bool))
def _uses_only_stdlib(source: str) -> bool:
    """Check if source only uses standard library."""
    stdlib_patterns = ["collections", "itertools", "functools", "typing", "dataclasses"]
    third_party_patterns = ["pandas", "numpy", "requests", "flask", "django"]

    has_stdlib = any(pat in source for pat in stdlib_patterns)
    has_third_party = any(pat in source for pat in third_party_patterns)

    return has_stdlib and not has_third_party


# ============================================================
# Type-Based Strategy Generation
# ============================================================


@dataclass
class StrategySpec:
    """Specification for a Hypothesis strategy."""

    strategy_name: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    @post(lambda result: isinstance(result, str) and result.startswith("st."))
    def to_code(self) -> str:
        """
        Generate Hypothesis strategy code.

        >>> spec = StrategySpec("integers", {"min_value": 0, "max_value": 100})
        >>> spec.to_code()
        'st.integers(min_value=0, max_value=100)'
        """
        if not self.kwargs:
            return f"st.{self.strategy_name}()"
        args = ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items())
        return f"st.{self.strategy_name}({args})"


# Type to strategy mapping
TYPE_STRATEGIES: dict[type, StrategySpec] = {
    int: StrategySpec("integers", {}, "Any integer"),
    float: StrategySpec(
        "floats",
        {"allow_nan": False, "allow_infinity": False},
        "Finite floats",
    ),
    str: StrategySpec("text", {"max_size": 100}, "Text up to 100 chars"),
    bool: StrategySpec("booleans", {}, "True or False"),
    bytes: StrategySpec("binary", {"max_size": 100}, "Bytes up to 100"),
}


@post(lambda result: isinstance(result, StrategySpec))
def _strategy_for_list(args: tuple, strategy_fn: Callable) -> StrategySpec:
    """Generate strategy for list type."""
    element_type = args[0] if args else int
    element_strategy = strategy_fn(element_type)
    type_name = element_type.__name__ if hasattr(element_type, "__name__") else element_type
    return StrategySpec("lists", {"elements": element_strategy.to_code()}, f"Lists of {type_name}")


@post(lambda result: isinstance(result, StrategySpec))
def _strategy_for_dict(args: tuple, strategy_fn: Callable) -> StrategySpec:
    """Generate strategy for dict type."""
    key_type = args[0] if len(args) > 0 else str
    val_type = args[1] if len(args) > 1 else int
    return StrategySpec(
        "dictionaries",
        {"keys": strategy_fn(key_type).to_code(), "values": strategy_fn(val_type).to_code()},
        f"Dict[{key_type}, {val_type}]",
    )


@post(lambda result: isinstance(result, StrategySpec))
def _strategy_for_set(args: tuple, strategy_fn: Callable) -> StrategySpec:
    """Generate strategy for set type."""
    element_type = args[0] if args else int
    return StrategySpec("frozensets", {"elements": strategy_fn(element_type).to_code()}, f"Sets of {element_type}")


@post(lambda result: result is None or isinstance(result, StrategySpec))
def _strategy_for_numpy(hint: type) -> StrategySpec | None:
    """Generate strategy for numpy array type, or None if not numpy."""
    if not _ensure_numpy():
        return None
    import numpy as np

    if hint is np.ndarray or (hasattr(hint, "__name__") and "ndarray" in str(hint)):
        return StrategySpec(
            "arrays",
            {"dtype": "np.float64", "shape": "st.integers(1, 100)", "elements": "st.floats(-1e6, 1e6, allow_nan=False)"},
            "NumPy float64 array",
        )
    return None


@pre(lambda hint: hint is not None)
@post(lambda result: isinstance(result, StrategySpec))
def strategy_from_type(hint: type) -> StrategySpec:
    """
    Generate Hypothesis strategy specification from type annotation.

    >>> strategy_from_type(int).strategy_name
    'integers'

    >>> strategy_from_type(float).kwargs['allow_nan']
    False

    >>> strategy_from_type(list).strategy_name
    'lists'
    """
    # Direct type match
    if hint in TYPE_STRATEGIES:
        return TYPE_STRATEGIES[hint]

    # Handle generic types
    origin = get_origin(hint)
    args = get_args(hint)

    # Handle bare container types (without type args)
    if hint is list:
        return StrategySpec("lists", {"elements": "st.integers()"}, "Lists of int")
    if hint is dict:
        return StrategySpec("dictionaries", {"keys": "st.text()", "values": "st.integers()"}, "Dict")
    if hint is tuple:
        return StrategySpec("tuples", {}, "Tuple")
    if hint is set:
        return StrategySpec("frozensets", {"elements": "st.integers()"}, "Set of int")

    # Handle generic container types
    if origin is list:
        return _strategy_for_list(args, strategy_from_type)
    if origin is dict:
        return _strategy_for_dict(args, strategy_from_type)
    if origin is set:
        return _strategy_for_set(args, strategy_from_type)
    if origin is tuple:
        if args:
            element_specs = [strategy_from_type(a).to_code() for a in args]
            return StrategySpec("tuples", {"*args": element_specs}, f"Tuple{args}")
        return StrategySpec("tuples", {}, "Empty tuple")

    # Check for numpy array
    if (numpy_spec := _strategy_for_numpy(hint)) is not None:
        return numpy_spec

    # Fallback to nothing for unknown types
    return StrategySpec("nothing", {}, f"Unknown type: {hint}")


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, dict))
def strategies_from_signature(func: Callable) -> dict[str, StrategySpec]:
    """
    Generate strategies for all parameters from function signature.

    >>> def example(x: int, y: float) -> bool: return x > y
    >>> specs = strategies_from_signature(example)
    >>> specs['x'].strategy_name
    'integers'
    >>> specs['y'].strategy_name
    'floats'
    """
    try:
        hints = get_type_hints(func)
    except Exception:
        return {}

    result = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        result[name] = strategy_from_type(hint)

    return result


# ============================================================
# Bound Refinement
# ============================================================


@post(lambda result: isinstance(result, StrategySpec))
def refine_strategy(base: StrategySpec, **kwargs: Any) -> StrategySpec:
    """
    Refine a base strategy with additional constraints.

    >>> base = StrategySpec("floats", {"allow_nan": False})
    >>> refined = refine_strategy(base, min_value=0, max_value=1)
    >>> refined.kwargs['min_value']
    0
    >>> refined.kwargs['max_value']
    1
    """
    merged_kwargs = {**base.kwargs, **kwargs}

    # Handle exclude_min/exclude_max for integers (not supported)
    if base.strategy_name == "integers":
        if merged_kwargs.pop("exclude_min", False) and "min_value" in merged_kwargs:
            merged_kwargs["min_value"] += 1
        if merged_kwargs.pop("exclude_max", False) and "max_value" in merged_kwargs:
            merged_kwargs["max_value"] -= 1

    return StrategySpec(
        strategy_name=base.strategy_name,
        kwargs=merged_kwargs,
        description=f"{base.description} (refined)",
    )


# ============================================================
# Integration with existing strategies.py
# ============================================================


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, dict))
def infer_strategies_for_function(func: Callable) -> dict[str, StrategySpec]:
    """
    Infer complete strategies for a function from types and @pre contracts.

    This combines:
    1. Type-based strategy generation
    2. @pre contract bound extraction (via strategies.infer_from_lambda)

    >>> def constrained(x: float) -> float:
    ...     '''Requires x > 0.'''
    ...     return x ** 0.5
    >>> specs = infer_strategies_for_function(constrained)
    >>> specs['x'].strategy_name
    'floats'
    """
    from invar.core.strategies import infer_from_lambda

    # Start with type-based strategies
    type_specs = strategies_from_signature(func)

    # Try to extract @pre contracts
    pre_sources = _extract_pre_sources(func)

    if not pre_sources:
        return type_specs

    # Refine strategies with @pre bounds
    result = {}
    for param_name, spec in type_specs.items():
        # Get type for this param
        try:
            hints = get_type_hints(func)
            param_type = hints.get(param_name)
        except Exception:
            param_type = None

        # Infer bounds from @pre sources
        all_bounds: dict[str, Any] = {}
        for source in pre_sources:
            hint = infer_from_lambda(source, param_name, param_type)
            all_bounds.update(hint.constraints)

        if all_bounds:
            # Convert to strategy kwargs
            strategy_kwargs = _bounds_to_strategy_kwargs(all_bounds, spec.strategy_name)
            result[param_name] = refine_strategy(spec, **strategy_kwargs)
        else:
            result[param_name] = spec

    return result


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, list))
def _extract_pre_sources(func: Callable) -> list[str]:
    """Extract @pre contract source strings from a function."""
    pre_sources: list[str] = []

    # Check for deal contracts
    if hasattr(func, "__wrapped__"):
        # deal stores contracts in _deal attribute
        pass

    # Try to extract from source
    try:
        source = inspect.getsource(func)
        # Find @pre decorators
        pre_pattern = r"@pre\s*\(\s*(lambda[^)]+)\s*\)"
        matches = re.findall(pre_pattern, source)
        pre_sources.extend(matches)
    except (OSError, TypeError):
        pass

    return pre_sources


@pre(lambda bounds, strategy_name: isinstance(bounds, dict) and isinstance(strategy_name, str))
@post(lambda result: isinstance(result, dict))
def _bounds_to_strategy_kwargs(bounds: dict[str, Any], strategy_name: str) -> dict[str, Any]:
    """Convert bound constraints to Hypothesis strategy kwargs."""
    kwargs = {}

    # Numeric bounds
    if "min_value" in bounds:
        kwargs["min_value"] = bounds["min_value"]
    if "max_value" in bounds:
        kwargs["max_value"] = bounds["max_value"]

    # Size bounds (for collections)
    if "min_size" in bounds:
        kwargs["min_size"] = bounds["min_size"]
    if "max_size" in bounds:
        kwargs["max_size"] = bounds["max_size"]

    # Exclusion flags for floats
    if strategy_name == "floats":
        if bounds.get("exclude_min"):
            kwargs["exclude_min"] = True
        if bounds.get("exclude_max"):
            kwargs["exclude_max"] = True

    return kwargs
