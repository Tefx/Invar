# Doctests as Specification

> **"Contracts DEFINE correctness. Doctests SHOW correctness."**

## Quick Reference

Doctests are executable examples embedded in docstrings:

```python
def add(x: int, y: int) -> int:
    """
    Add two integers.

    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    """
    return x + y
```

Run via: `invar guard` (automatic) or `pytest --doctest-modules`

## How Doctests Work

### Format

```python
>>> expression     # Input line (starts with >>>)
expected_output    # Expected result (no prefix)
```

### Multi-line Input

```python
>>> result = (
...     calculate_something()
... )
>>> result
42
```

### Expected Exceptions

```python
>>> divide(1, 0)
Traceback (most recent call last):
    ...
ZeroDivisionError: division by zero
```

### Contract Violations

```python
>>> first([])  # Empty list violates @pre
Traceback (most recent call last):
    ...
deal.PreContractError: ...
```

## Best Practices

### 1. Order: Normal, Edge, Error

```python
def average(items: list[float]) -> float:
    """
    Calculate average of a list.

    Normal case:
    >>> average([1.0, 2.0, 3.0])
    2.0

    Edge - single element:
    >>> average([5.0])
    5.0

    Edge - large numbers:
    >>> average([1e10, 2e10])
    1.5e+10

    Error - empty list:
    >>> average([])
    Traceback (most recent call last):
        ...
    deal.PreContractError: ...
    """
```

### 2. Include Boundary Cases

```python
@pre(lambda x: 0 <= x <= 100)
def process_percentage(x: float) -> str:
    """
    >>> process_percentage(0)      # Lower bound
    'none'
    >>> process_percentage(100)    # Upper bound
    'full'
    >>> process_percentage(50)     # Middle
    'half'
    """
```

### 3. Document Contract Violations

Show what happens when preconditions fail:

```python
@pre(lambda items: len(items) > 0)
def first(items: list) -> Any:
    """
    >>> first([1, 2, 3])
    1
    >>> first([])  # Contract violation
    Traceback (most recent call last):
        ...
    deal.PreContractError: ...
    """
```

## Common Issues

### 1. Dict/Set Ordering

Python dicts/sets have no guaranteed order in doctest output:

```python
# BAD: May fail due to ordering
>>> get_config()
{'port': 8080, 'host': 'localhost'}

# GOOD: Use sorted() for deterministic output
>>> sorted(get_config().items())
[('host', 'localhost'), ('port', 8080)]

# GOOD: Use equality comparison
>>> get_config() == {'port': 8080, 'host': 'localhost'}
True
```

### 2. Float Precision

Floating-point comparisons can fail due to precision:

```python
# BAD: May fail due to floating-point precision
>>> calculate_ratio()
0.3333333333333333

# GOOD: Use round() for predictable output
>>> round(calculate_ratio(), 4)
0.3333

# GOOD: Use doctest directive
>>> calculate_ratio()  # doctest: +ELLIPSIS
0.333...
```

### 3. Multi-line Output

Use `...` for continuation:

```python
>>> long_result()  # doctest: +NORMALIZE_WHITESPACE
{'key1': 'value1',
 'key2': 'value2',
 'key3': 'value3'}
```

### 4. Environment-Specific Lines

Use `exclude_doctest_lines` config for lines that vary:

```toml
# pyproject.toml
[tool.invar]
exclude_doctest_lines = [
    "platform",
    "version",
    "timestamp"
]
```

### 5. Object Representations

Object `repr()` may include memory addresses:

```python
# BAD: Address changes each run
>>> MyClass()
<MyClass object at 0x7f...>

# GOOD: Use doctest directive
>>> MyClass()  # doctest: +ELLIPSIS
<MyClass object at 0x...>

# BETTER: Define __repr__ for predictable output
>>> MyClass()
MyClass()
```

## Relationship to Contracts

### Three-Way Consistency

```
        Code
       /    \
@pre/@post ↔ Doctests
```

**All three must align.** Any conflict is a bug.

### Different Roles

| Aspect | Contracts | Doctests |
|--------|-----------|----------|
| Purpose | DEFINE correctness | SHOW correctness |
| Coverage | All valid inputs | Representative examples |
| Style | Formal (predicates) | Informal (examples) |
| Verification | CrossHair/Hypothesis | pytest |

### Complementary Strengths

**Contracts** catch violations CrossHair/Hypothesis can prove:

```python
@pre(lambda x: x > 0)
@post(lambda result: result > x)
def increment(x: int) -> int:
    return x + 1
# CrossHair PROVES: for ALL x > 0, result > x
```

**Doctests** document specific behaviors:

```python
def increment(x: int) -> int:
    """
    >>> increment(1)
    2
    >>> increment(100)
    101
    """
```

### When to Use Each

| Situation | Use |
|-----------|-----|
| Invariant property | Contract (`@pre`/`@post`) |
| Specific example | Doctest |
| Edge case behavior | Both (contract + doctest) |
| Error condition | Contract + doctest showing error |

## Doctest-First Development

Write doctests BEFORE implementation:

```python
def fibonacci(n: int) -> int:
    """
    Return nth Fibonacci number.

    >>> fibonacci(0)
    0
    >>> fibonacci(1)
    1
    >>> fibonacci(10)
    55
    >>> fibonacci(-1)
    Traceback (most recent call last):
        ...
    deal.PreContractError: ...
    """
    # Implementation follows...
```

**Why?** Doctests serve as executable specification. Writing them first:
1. Clarifies expected behavior
2. Provides immediate feedback during implementation
3. Documents edge cases before they're forgotten

## Configuration

In `pyproject.toml`:

```toml
[tool.invar]
# Doctest-related settings
missing_doctest = "warning"       # Warn if no doctests
exclude_doctest_lines = []        # Lines to skip in comparison

# Files excluded from doctest checking
exclude_paths = [
    "tests/",
    "examples/"
]
```

## Verification Pipeline

```
invar guard
    ├─ Static analysis
    ├─ Doctests ◄── pytest --doctest-modules
    ├─ CrossHair (proves contracts)
    └─ Hypothesis (property tests)
```

**Key insight:** Doctests run alongside contract verification. Both must pass.

## Example-Driven Learning (Lesson #23)

> "Abstract rules don't teach; concrete code examples do."

New agents learn fastest from working examples:

```python
# This abstract rule is hard to understand:
# "Shell functions return Result[T, E]"

# This example teaches immediately:
def read_config(path: Path) -> Result[Config, str]:
    """
    >>> read_config(Path("config.json"))  # doctest: +SKIP
    Success(Config(...))
    """
    try:
        return Success(json.loads(path.read_text()))
    except Exception as e:
        return Failure(str(e))
```

## See Also

- [Pre/Post Contracts](./pre-post.md) - Formal contract definitions
- [Contract Completeness](./contract-complete.md) - When contracts are "complete"
- [USBV Workflow](../workflow/usbv.md) - Contract-first development
- [DX-02: Doctest Best Practices](../../proposals/2025-12-21-dx-improvements.md) - Design history
