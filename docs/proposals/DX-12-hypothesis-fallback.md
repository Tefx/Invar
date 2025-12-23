# DX-12: Hypothesis as CrossHair Fallback

> Property-based testing fallback for library-dependent code

---

## Metadata

- **Date:** 2025-12-21
- **Author:** Agent (with Human direction)
- **Status:** ✅ Implemented
- **Layer:** L2 (Project)
- **Estimated Effort:** 4 days
- **Priority:** Medium (data science use cases)
- **Implemented:** 2025-12-21

---

## Trigger

CrossHair symbolic execution cannot analyze numpy/pandas operations:

```python
@pre(lambda arr: len(arr) > 0)
@post(lambda result: result > 0)  # BUG: fails when all elements are 0
def array_sum(arr: np.ndarray) -> float:
    return float(np.sum(arr ** 2))
```

**Experiment results:**
- CrossHair: Timeout after 20s, bug not detected
- Hypothesis: Found counterexample `[0.]` in <1s

For data science/ML projects, this gap is critical.

---

## Proposed Change

### Architecture

```
invar guard --prove
    │
    ├──→ CrossHair (primary)
    │       │
    │       ├── Success → Report result
    │       ├── Found bug → Report counterexample
    │       └── Skipped/Timeout → Hypothesis fallback
    │
    └──→ Hypothesis (fallback)
            │
            ├── Generate strategy from types + @pre
            └── Run property tests
```

### Three Components

#### 1. Library-Aware Timeout Inference

```python
TIMEOUT_TIERS = {
    "pure_python": 10,      # Pure logic, no external libs
    "stdlib_only": 15,      # Uses collections, itertools
    "numpy_pandas": 5,      # Quick check, likely to skip
    "complex_nested": 30,   # Deep recursion, many branches
}

def infer_timeout(func: Callable) -> int:
    """Infer CrossHair timeout from imports and complexity."""
    source = inspect.getsource(func)

    # Quick exit for known-incompatible libraries
    if any(lib in source for lib in ["numpy", "pandas", "torch"]):
        return 5  # Quick check, expect skip/fail

    # Complexity-based for pure Python
    return calculate_complexity_timeout(source)
```

#### 2. Type-Based Strategy Generation

```python
def strategy_from_type(hint: type) -> st.SearchStrategy:
    """Generate Hypothesis strategy from type annotation."""

    if hint is np.ndarray:
        return arrays(dtype=np.float64, shape=st.integers(1, 100))

    STRATEGIES = {
        int: st.integers(),
        float: st.floats(allow_nan=False, allow_infinity=False),
        str: st.text(max_size=100),
        bool: st.booleans(),
    }
    return STRATEGIES.get(hint, st.nothing())
```

#### 3. @pre Contract Enhancement (Option C)

Parse @pre lambda to extract bounds for more precise strategies:

```python
@pre(lambda x: 0 <= x <= 1)  # Extracted: min=0, max=1
def probability(x: float) -> float: ...

# Inferred strategy:
st.floats(min_value=0, max_value=1, allow_nan=False)
```

**Supported patterns:**
| Pattern | Example | Inferred |
|---------|---------|----------|
| Simple comparison | `x > 0` | `min_value=0, exclude_min=True` |
| Chained comparison | `0 <= x <= 1` | `min_value=0, max_value=1` |
| And combination | `x > 0 and y < 100` | Per-param bounds |
| Negative bounds | `x > -10` | `min_value=-10` |
| Scientific notation | `1e-10 < x` | `min_value=1e-10` |

**Unsupported (fallback to type default):**
| Pattern | Reason |
|---------|--------|
| `x % 2 == 0` | Modulo requires filter strategy |
| `len(arr) > 0` | Function calls not parseable |
| `x < 0 or x > 10` | Multiple ranges ambiguous |
| `all(v > 0 for v in arr)` | Generator expressions |

---

## Implementation Plan

### Phase 1: Type Strategy Generation (1 day)

```python
# File: src/invar/core/hypothesis_strategies.py

from hypothesis import strategies as st
from typing import get_type_hints

def strategies_from_signature(func: Callable) -> dict[str, st.SearchStrategy]:
    """Generate strategies for all parameters from type hints."""
    hints = get_type_hints(func)
    return {name: strategy_from_type(hint) for name, hint in hints.items()
            if name != 'return'}
```

### Phase 2: @pre Bound Extraction (1.5 days)

```python
# File: src/invar/core/pre_analyzer.py

@dataclass
class Bound:
    param: str
    op: str  # 'gt', 'ge', 'lt', 'le', 'eq'
    value: float | int

def infer_bounds_from_pre(pre_func: Callable) -> list[Bound]:
    """Extract numeric bounds from @pre lambda AST."""
    # Implementation: AST parsing of lambda body
    # See POC in /tmp/strategy_inference_poc.py
```

### Phase 3: Strategy Merging (0.5 day)

```python
def merged_strategy(param: str, type_hint: type, bounds: list[Bound]) -> st.SearchStrategy:
    """Combine type default with @pre bounds."""
    base = strategy_from_type(type_hint)
    param_bounds = [b for b in bounds if b.param == param]

    if not param_bounds:
        return base  # No bounds, use type default

    # Apply bounds as constraints
    kwargs = {}
    for bound in param_bounds:
        kwargs.update(bound.to_strategy_kwargs())

    return refine_strategy(base, **kwargs)
```

### Phase 4: Guard Integration (0.5 day)

```python
# In src/invar/shell/testing.py

def prove_function(func: Callable) -> ProveResult:
    # 1. Try CrossHair (primary)
    timeout = infer_timeout(func)
    crosshair_result = run_crosshair(func, timeout=timeout)

    if crosshair_result.success or crosshair_result.found_bug:
        return ProveResult(tool="crosshair", ...)

    # 2. CrossHair skipped/timed out → Hypothesis fallback
    if crosshair_result.status in ("skipped", "timeout"):
        strategies = infer_strategies(func)
        hypothesis_result = run_hypothesis(func, strategies)

        return ProveResult(
            tool="hypothesis",
            note="CrossHair skipped, used Hypothesis fallback",
            ...
        )
```

---

## Evidence

### Experiment: CrossHair vs Hypothesis on NumPy

| Test Case | CrossHair | Hypothesis |
|-----------|-----------|------------|
| `array_sum([0.])` bug | Timeout (20s) | Found (<1s) |
| Pure Python sqrt edge | Found (2s) | Found (depends on strategy) |
| Complex nested logic | May timeout | Fast but random |

### Strategy Inference POC Results

```
Simple: x > 0
  Strategy[x]: floats(min_value=0, exclude_min=True)

Chained: 0 <= x <= 1
  Strategy[x]: floats(min_value=0, max_value=1)

Two params: x > 0 and y < 100
  Strategy[x]: floats(min_value=0, exclude_min=True)
  Strategy[y]: floats(max_value=100, exclude_max=True)
```

---

## Impact Analysis

- [x] INVAR.md sections affected: Add Hypothesis fallback mention
- [ ] CLAUDE.md updates needed: None
- [ ] Template files to update: None
- [x] Code changes required:
  - `src/invar/core/hypothesis_strategies.py` (new)
  - `src/invar/core/pre_analyzer.py` (new)
  - `src/invar/shell/testing.py` (modify prove command)
  - `pyproject.toml` (add hypothesis dependency to [prove])
- [ ] Other documentation: Update docs/VISION.md if needed

---

## Alternatives Considered

### Alternative A: Hypothesis as Primary
**Rejected:** CrossHair provides complete path coverage for pure Python. Hypothesis is random-based, may miss edge cases. Use CrossHair where it works.

### Alternative B: User-Defined @strategy Decorator
```python
@strategy(x=st.floats(min_value=1e-10))
@pre(lambda x: x > 0)
def sqrt(x: float) -> float: ...
```
**Deferred:** Adds manual overhead. Auto-inference first, decorator as escape hatch later.

### Alternative C: Separate invar hypothesis Command
**Rejected:** Violates Agent-Native principle. Agents won't use separate commands. Integration into `--prove` is automatic.

---

## Agent-Native Alignment

| Principle | How DX-12 Aligns |
|-----------|------------------|
| Automatic > Opt-in | Fallback is automatic, no flags needed |
| Zero decisions | Guard decides CrossHair vs Hypothesis |
| Library-aware | Timeout adjusts based on imports |
| Type-driven | Strategies from annotations, no manual work |

---

## Approval

**For Layer 2 changes:**

- [x] Human has reviewed this proposal
- [x] Human explicitly approves: Implemented 2025-12-21

---

## Implementation Checklist

All items completed:

- [x] Create `src/invar/core/hypothesis_strategies.py`
- [x] Create `src/invar/core/strategies.py` (bounds extraction)
- [x] Modify `src/invar/shell/testing.py`
- [x] Create `src/invar/shell/prove_fallback.py`
- [x] Create `src/invar/shell/test_cmd.py` (`invar test` command)
- [x] Add `hypothesis` to dependencies
- [x] Add tests for strategy inference
- [x] Commit with clear message

**Implementation Files:**
- `src/invar/core/hypothesis_strategies.py` - Type strategies, timeout inference
- `src/invar/core/strategies.py` - @pre bounds extraction
- `src/invar/shell/prove_fallback.py` - Hypothesis fallback logic
- `src/invar/shell/test_cmd.py` - CLI commands
