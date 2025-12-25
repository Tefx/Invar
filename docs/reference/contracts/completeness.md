# Contract Completeness Principle

> **"A good contract uniquely determines implementation."**

## Quick Reference

A **complete contract** is one where:
- Given only `@pre`, `@post`, and doctests
- Someone could write the exact same function
- No ambiguity about expected behavior

**Self-test:** "Can this contract regenerate the function?"

## The Principle

### From Research: Clover Study

The Clover paper found that when contracts are complete:
- **80.6%** of programmers regenerated the correct function
- **87%** acceptance rate for generated code
- **0%** false positive rate

**Key insight:** Complete contracts make problems tractable. Incomplete contracts make them unsolvable.

### Mathematical Definition

A contract is **complete** when:
```
For all valid inputs (satisfying @pre):
  There exists exactly one output (satisfying @post)
```

Or equivalently:
```
@pre(P) ∧ @post(Q) → unique implementation
```

## Measuring Completeness

### Three Questions

1. **Does @pre exclude all invalid inputs?**
   - What inputs would cause the function to fail?
   - Are all edge cases covered?

2. **Does @post verify all required properties?**
   - What must be true about the result?
   - Are relationships to inputs captured?

3. **Can someone write the function from contracts alone?**
   - Without seeing the implementation
   - Without additional documentation

### Completeness Levels

| Level | Description | Example |
|-------|-------------|---------|
| **Incomplete** | Multiple implementations satisfy | `@post(lambda r: r > 0)` |
| **Partial** | Narrows possibilities | `@post(lambda r: r == x + y)` |
| **Complete** | Unique implementation | Full spec with doctests |

## Examples

### Incomplete Contract

```python
@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def mysterious(x: float) -> float:
    ...  # Could be: x, x*2, sqrt(x), x+1, etc.
```

**Problem:** Infinitely many functions satisfy these constraints.

### Partial Contract

```python
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    """
    >>> sqrt(4.0)
    2.0
    """
    ...  # Still ambiguous: could return x**0.5 or x**2
```

**Problem:** Doctests help but don't fully specify.

### Complete Contract

```python
@pre(lambda x: x >= 0)
@post(lambda result: abs(result * result - x) < 1e-10)
def sqrt(x: float) -> float:
    """
    Return the principal (non-negative) square root.

    >>> sqrt(0.0)
    0.0
    >>> sqrt(4.0)
    2.0
    >>> sqrt(2.0)  # doctest: +ELLIPSIS
    1.41421...
    """
    return x ** 0.5
```

**Complete because:**
- `@pre` specifies valid domain (non-negative)
- `@post` mathematically defines the result (r^2 = x)
- Doctests clarify edge cases and precision

## Patterns for Completeness

### 1. Relate Output to Input

```python
# INCOMPLETE: Says nothing about relationship
@post(lambda result: isinstance(result, list))

# COMPLETE: Specifies exact relationship
@post(lambda result: len(result) == len(items))
@post(lambda result: all(x * 2 == y for x, y in zip(items, result)))
def double_all(items: list[int]) -> list[int]:
    return [x * 2 for x in items]
```

### 2. Preserve Properties

```python
@pre(lambda items: len(items) == len(set(items)))  # Unique input
@post(lambda result: len(result) == len(set(result)))  # Unique output
@post(lambda result: set(result) == set(items))  # Same elements
def shuffle(items: list[int]) -> list[int]:
    ...
```

### 3. Define Edge Cases

```python
@pre(lambda items: True)  # Accept all lists
@post(lambda result: result is None if len(items) == 0 else result == items[0])
def first_or_none(items: list) -> Any | None:
    """
    >>> first_or_none([])
    >>> first_or_none([1, 2, 3])
    1
    """
```

### 4. Use Doctests for Specifics

When `@post` can't capture all details:

```python
@pre(lambda s: len(s) > 0)
@post(lambda result: len(result) == len(s))
def rot13(s: str) -> str:
    """
    Rotate each letter by 13 positions.

    >>> rot13("hello")
    'uryyb'
    >>> rot13("uryyb")
    'hello'
    >>> rot13("Hello, World!")
    'Uryyb, Jbeyq!'
    """
```

## USBV Integration

Contract completeness is central to USBV workflow:

```
U - Understand : Intent, Inspect (invar sig/map), Constraints
S - Specify    : Write COMPLETE @pre/@post + doctests
                 ↳ Self-test: Can these regenerate the function?
B - Build      : Implement leaves first, Compose
V - Validate   : invar guard confirms compliance
```

**SPECIFY phase is critical.** Incomplete contracts lead to:
- Ambiguous implementations
- Difficult debugging
- Failed verification

## Why Completeness Matters

### For Agents

Complete contracts enable:
- **Code generation** - Agent knows exactly what to write
- **Self-verification** - Agent can check own work
- **Recovery** - When wrong, contracts guide the fix

### For Verification

Complete contracts enable:
- **Symbolic proof** - CrossHair can prove correctness
- **Property testing** - Hypothesis knows valid inputs
- **Regression detection** - Changes that break contracts are caught

### For Humans

Complete contracts provide:
- **Documentation** - Contracts explain behavior
- **Review aid** - Easy to verify correctness
- **Maintenance** - Future changes have clear boundaries

## Anti-Patterns

### 1. Type-Only Contracts

```python
# BAD: Just restating the type signature
@pre(lambda x: isinstance(x, int))
@post(lambda result: isinstance(result, int))
def increment(x: int) -> int:
    return x + 1
```

### 2. Tautologies

```python
# BAD: Always true
@pre(lambda x: True)
@post(lambda result: result is not None or result is None)
```

### 3. Missing Relationships

```python
# BAD: Doesn't capture that result relates to input
@post(lambda result: result > 0)
def double(x: int) -> int:
    return x * 2  # Contract doesn't verify this!
```

### 4. Incomplete Edge Cases

```python
# BAD: What happens with empty list?
@pre(lambda items: True)
def average(items: list[float]) -> float:
    return sum(items) / len(items)  # Crashes on []!
```

## Verification

`invar guard` checks contract quality:

| Rule | Severity | Detects |
|------|----------|---------|
| `empty_contract` | ERROR | Tautology contracts |
| `missing_contract` | ERROR | Core functions without contracts |
| `partial_contract` | WARNING | Contracts that may be incomplete |

## See Also

- [Pre/Post Contracts](./pre-post.md) - Contract syntax and patterns
- [Doctests](./doctests.md) - Examples as specification
- [USBV Workflow](../workflow/usbv.md) - Contract-first development
- [Clover Paper](https://arxiv.org/abs/2310.04625) - Research on contract completeness
