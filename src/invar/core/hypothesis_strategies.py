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

# Note: inspect and re are still used by _extract_pre_sources

if TYPE_CHECKING:
    from collections.abc import Callable

# Lazy import to avoid dependency issues
_hypothesis_available = False
_numpy_available = False


# @invar:allow missing_contract: Boolean availability check, no meaningful contract
def _ensure_hypothesis() -> bool:
    """Check if hypothesis is available."""
    global _hypothesis_available
    try:
        import hypothesis  # noqa: F401

        _hypothesis_available = True
        return True
    except ImportError:
        return False


# @invar:allow missing_contract: Boolean availability check, no meaningful contract
def _ensure_numpy() -> bool:
    """Check if numpy is available."""
    global _numpy_available
    try:
        import numpy  # noqa: F401

        _numpy_available = True
        return True
    except ImportError:
        return False


# Re-export timeout inference for backwards compatibility
from invar.core.timeout_inference import (  # noqa: F401
    LIBRARY_BLACKLIST,
    TIMEOUT_TIERS,
    TimeoutTier,
    infer_timeout,
)

# ============================================================
# Type-Based Strategy Generation
# ============================================================


@dataclass
class StrategySpec:
    """Specification for a Hypothesis strategy.

    DX-12-B: Added raw_code field for user-defined strategies.
    """

    strategy_name: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    raw_code: str | None = None  # DX-12-B: For custom @strategy decorator

    @post(lambda result: isinstance(result, str) and result.startswith("st."))
    def to_code(self) -> str:
        """
        Generate Hypothesis strategy code.

        >>> spec = StrategySpec("integers", {"min_value": 0, "max_value": 100})
        >>> spec.to_code()
        'st.integers(min_value=0, max_value=100)'

        >>> custom = StrategySpec("custom", raw_code="st.floats(min_value=0)")
        >>> custom.to_code()
        'st.floats(min_value=0)'
        """
        # DX-12-B: Return raw code if provided and valid (user-defined strategy)
        if self.raw_code and self.raw_code.startswith("st."):
            return self.raw_code
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
    1. User-defined @strategy decorator (DX-12-B) - highest priority
    2. Type-based strategy generation
    3. @pre contract bound extraction (via strategies.infer_from_lambda)

    >>> def constrained(x: float) -> float:
    ...     '''Requires x > 0.'''
    ...     return x ** 0.5
    >>> specs = infer_strategies_for_function(constrained)
    >>> specs['x'].strategy_name
    'floats'
    """
    type_specs = strategies_from_signature(func)
    user_strategies = _get_user_strategies(func)
    pre_sources = _extract_pre_sources(func)

    if not pre_sources and not user_strategies:
        return type_specs

    # Refine each parameter strategy
    result = _refine_all_strategies(func, type_specs, user_strategies, pre_sources)

    # Add any user strategies for params not in type_specs
    for param_name, spec in user_strategies.items():
        if param_name not in result:
            result[param_name] = spec

    return result


@pre(lambda func, type_specs, user_strategies, pre_sources: callable(func))
@post(lambda result: isinstance(result, dict))
def _refine_all_strategies(
    func: Callable,
    type_specs: dict[str, StrategySpec],
    user_strategies: dict[str, StrategySpec],
    pre_sources: list[str],
) -> dict[str, StrategySpec]:
    """Refine type-based strategies with @pre bounds and user overrides."""
    from invar.core.strategies import infer_from_lambda

    result: dict[str, StrategySpec] = {}
    for param_name, spec in type_specs.items():
        # DX-12-B: User-defined strategy takes highest priority
        if param_name in user_strategies:
            result[param_name] = user_strategies[param_name]
            continue

        # Infer bounds from @pre sources
        param_type = _get_param_type(func, param_name)
        all_bounds: dict[str, Any] = {}
        for source in pre_sources:
            hint = infer_from_lambda(source, param_name, param_type)
            all_bounds.update(hint.constraints)

        if all_bounds:
            strategy_kwargs = _bounds_to_strategy_kwargs(all_bounds, spec.strategy_name)
            result[param_name] = refine_strategy(spec, **strategy_kwargs)
        else:
            result[param_name] = spec

    return result


@pre(lambda func, param_name: callable(func) and isinstance(param_name, str))
@post(lambda result: result is None or isinstance(result, type))
def _get_param_type(func: Callable, param_name: str) -> type | None:
    """Get parameter type from function type hints."""
    try:
        hints = get_type_hints(func)
        return hints.get(param_name)
    except Exception:
        return None


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, dict))
def _get_user_strategies(func: Callable) -> dict[str, StrategySpec]:
    """
    Extract user-defined strategies from @strategy decorator.

    DX-12-B: Supports both strategy objects and string representations.

    >>> from invar_runtime import strategy
    >>> @strategy(x="floats(min_value=0)")
    ... def sqrt(x: float) -> float:
    ...     return x ** 0.5
    >>> specs = _get_user_strategies(sqrt)
    >>> 'x' in specs
    True
    >>> specs['x'].to_code()
    'st.floats(min_value=0)'
    """
    if not hasattr(func, "__invar_strategies__"):
        return {}

    user_specs: dict[str, StrategySpec] = {}
    raw_strategies = func.__invar_strategies__  # type: ignore[attr-defined]

    for param_name, strat in raw_strategies.items():
        if isinstance(strat, str):
            # String representation: "floats(min_value=0)"
            raw_code = f"st.{strat}" if not strat.startswith("st.") else strat
            user_specs[param_name] = StrategySpec(
                strategy_name="custom",
                description=f"User-defined: {strat}",
                raw_code=raw_code,
            )
        else:
            # Actual strategy object - convert to code representation
            strat_repr = repr(strat)
            # Ensure it starts with st. for the postcondition
            raw_code = strat_repr if strat_repr.startswith("st.") else f"st.{strat_repr}"
            user_specs[param_name] = StrategySpec(
                strategy_name="custom",
                description="User-defined strategy object",
                raw_code=raw_code,
            )

    return user_specs


@post(lambda result: all("lambda" in s for s in result))  # Only lambda expressions
def _extract_pre_lambdas_from_source(source: str) -> list[str]:
    """
    Extract lambda expressions from @pre decorators with balanced parenthesis.

    >>> _extract_pre_lambdas_from_source("@pre(lambda x: x > 0)")
    ['lambda x: x > 0']
    >>> _extract_pre_lambdas_from_source("@pre(lambda x: len(x) > 0)")
    ['lambda x: len(x) > 0']
    >>> _extract_pre_lambdas_from_source("@pre(lambda x, y: isinstance(x, str))")
    ['lambda x, y: isinstance(x, str)']
    >>> _extract_pre_lambdas_from_source("")
    []
    """
    results = []
    i = 0
    while i < len(source):
        # Find @pre(
        pre_match = re.search(r"@pre\s*\(", source[i:])
        if not pre_match:
            break
        start = i + pre_match.end()

        # Find matching closing paren with balance counting
        paren_depth = 1
        j = start
        while j < len(source) and paren_depth > 0:
            if source[j] == "(":
                paren_depth += 1
            elif source[j] == ")":
                paren_depth -= 1
            j += 1

        if paren_depth == 0:
            # Extract content between @pre( and matching )
            content = source[start : j - 1].strip()
            if content.startswith("lambda"):
                results.append(content)

        i = j

    return results


@pre(lambda func: callable(func))
@post(lambda result: isinstance(result, list))
def _extract_pre_sources(func: Callable) -> list[str]:
    """Extract @pre contract source strings from a function."""
    pre_sources: list[str] = []

    # Check for deal contracts
    if hasattr(func, "__wrapped__"):
        # deal stores contracts in _deal attribute
        pass

    # Try to extract from source using balanced parenthesis matching
    try:
        source = inspect.getsource(func)
        pre_sources.extend(_extract_pre_lambdas_from_source(source))
    except (OSError, TypeError):
        pass

    return pre_sources


@post(lambda result: all(k in ("min_value", "max_value", "min_size", "max_size", "exclude_min", "exclude_max") for k in result))
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
