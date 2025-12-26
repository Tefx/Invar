# CrossHair vs Hypothesis

> **"Proof where possible, testing where necessary."**

## Quick Comparison

| Aspect | CrossHair | Hypothesis |
|--------|-----------|------------|
| **Method** | Symbolic execution | Property-based testing |
| **Guarantee** | Mathematical proof | Statistical confidence |
| **Speed** | ~5s per function | ~2s per function |
| **C extensions** | Cannot handle | Full support |
| **Counterexamples** | Exact, minimal | Random, may vary |

## When Each Is Used

### CrossHair (Symbolic Execution)

**Used for:** Pure Python code without C extension imports.

```python
# CrossHair can PROVE this will never fail
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def square(x: int) -> int:
    return x * x
```

**How it works:**
1. Treats variables as symbolic (not concrete values)
2. Explores all possible execution paths
3. Proves precondition → postcondition for ALL inputs
4. If violation found, returns exact counterexample

**Strengths:**
- Mathematical proof of correctness
- Finds edge cases humans miss
- Counterexamples are minimal and reproducible

**Limitations:**
- Cannot execute C extensions (numpy, pandas, etc.)
- May timeout on complex code paths
- Some Python features unsupported

### Hypothesis (Property-Based Testing)

**Used for:** Code with C extension imports, or as fallback.

```python
# Hypothesis TESTS this with many random inputs
@pre(lambda arr: len(arr) > 0)
@post(lambda result: result in arr)
def find_min(arr: np.ndarray) -> float:
    return np.min(arr)
```

**How it works:**
1. Generates random inputs matching preconditions
2. Runs function with concrete values
3. Checks postcondition holds
4. Shrinks failing inputs to minimal example

**Strengths:**
- Works with any Python code
- Supports C extensions (numpy, pandas, torch)
- Fast execution (~2s per function)

**Limitations:**
- Cannot prove correctness (only test)
- May miss edge cases not randomly generated
- Counterexamples may not be minimal

## Decision Matrix

| Code Characteristic | Verification Tool | Rationale |
|---------------------|-------------------|-----------|
| Pure Python + contracts | CrossHair | Can mathematically prove |
| Uses numpy/pandas/etc. | Hypothesis | CrossHair would timeout |
| No contracts | Skip | Nothing to verify |
| CrossHair timeout | Hypothesis fallback | DX-12 fallback mechanism |

## Guarantee Levels

```
Proof (CrossHair)     ████████████████████ 100% confidence
                      Verified for ALL possible inputs

Testing (Hypothesis)  ████████████████░░░░ ~95% confidence
                      Tested with ~100 random inputs

Doctests              ████████░░░░░░░░░░░░ Examples only
                      Only specific cases tested
```

## Performance Comparison

| Scenario | CrossHair | Hypothesis |
|----------|-----------|------------|
| Simple function | ~3s | ~1s |
| Complex pure Python | ~10s | ~2s |
| C extension code | ∞ (timeout) | ~2s |

**Smart routing (DX-22)** detects C extensions upfront to avoid wasted CrossHair attempts.

## Example: Same Contract, Different Tools

```python
# Pure Python → CrossHair proves correctness
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def pure_sqrt(x: float) -> float:
    return x ** 0.5

# Uses numpy → Hypothesis tests correctness
import numpy as np

@pre(lambda arr: len(arr) > 0)
@post(lambda result: result >= np.min(arr))
def numpy_mean(arr: np.ndarray) -> float:
    return np.mean(arr)
```

## Integration in Invar

```
invar guard
    │
    ├── Static Analysis (always)
    │
    ├── Doctests (always)
    │
    └── Contract Verification
        │
        ├── Has C imports? ──Yes──→ Hypothesis
        │                           (property testing)
        │
        └── Pure Python? ──Yes──→ CrossHair
                                  (symbolic proof)
                                      │
                                      └── Timeout? → Hypothesis fallback
```

## See Also

- [Smart Verification Routing](./smart-routing.md) - Automatic tool selection
- [DX-12: Hypothesis Fallback](../../proposals/completed/DX-12-hypothesis-fallback.md) - Fallback mechanism
- [DX-22: Verification Strategy](../../proposals/completed/DX-22-verification-strategy.md) - Smart routing design
