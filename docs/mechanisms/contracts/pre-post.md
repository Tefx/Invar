# Pre/Post Contracts

> **"Define COMPLETE, RECOVERABLE boundaries before implementation."**

## Quick Reference

Invar uses the `deal` library for runtime contracts:

| Decorator | Purpose | Checks |
|-----------|---------|--------|
| `@pre(...)` | Precondition | Before function executes |
| `@post(...)` | Postcondition | After function returns |

```python
from deal import pre, post

@pre(lambda x, y: y != 0)
@post(lambda result: isinstance(result, float))
def divide(x: float, y: float) -> float:
    return x / y
```

## How Contracts Work

### Preconditions (`@pre`)

Preconditions define **what must be true before** a function executes:

```python
@pre(lambda items: len(items) > 0)
def first(items: list) -> Any:
    """Return first element. Requires non-empty list."""
    return items[0]

# Valid call
first([1, 2, 3])  # Returns 1

# Invalid call - raises PreContractError
first([])  # Contract violation!
```

**Key insight:** `@pre` shifts responsibility to the caller. If precondition fails, the caller made a mistake.

### Postconditions (`@post`)

Postconditions define **what must be true after** a function returns:

```python
@post(lambda result: result >= 0)
def absolute(x: float) -> float:
    """Return absolute value. Result is always non-negative."""
    return abs(x)

# Always true after call
absolute(-5)  # Returns 5.0, postcondition verified
```

**Key insight:** `@post` is a promise from the function. If postcondition fails, the function has a bug.

### Lambda Parameters

The lambda must match function parameters **exactly**:

```python
# Correct: lambda has same parameters
@pre(lambda x, y: x > 0 and y > 0)
def multiply(x: float, y: float) -> float:
    return x * y

# Correct: include defaults in lambda
@pre(lambda x, y, z=None: x > 0)
def func(x: float, y: float, z: float | None = None) -> float:
    return x + y

# WRONG: lambda params don't match - causes param_mismatch ERROR
@pre(lambda x: x > 0)  # Missing y!
def multiply(x: float, y: float) -> float:  # Has 2 params
    return x * y
```

**Rule:** Lambda parameter count and names must match function signature.

## Contract Patterns

### Numeric Bounds

```python
@pre(lambda x: x > 0)              # Positive
@pre(lambda x: x >= 0)             # Non-negative
@pre(lambda x: 0 <= x <= 100)      # Range
@pre(lambda x, y: x < y)           # Ordering
```

### Collection Constraints

```python
@pre(lambda items: len(items) > 0)           # Non-empty
@pre(lambda items: len(items) <= 100)        # Max size
@pre(lambda items: all(x > 0 for x in items))  # All positive
@pre(lambda items: len(items) == len(set(items)))  # Unique
```

### Type Guards

```python
@pre(lambda x: isinstance(x, str))           # Type check
@pre(lambda x: x is not None)                # Not None
@pre(lambda data: "id" in data)              # Dict key exists
```

### Composite Conditions

```python
@pre(lambda x, y: x > 0 and y != 0)          # AND
@pre(lambda items: len(items) > 0 or items is None)  # OR
```

### Postcondition Patterns

```python
@post(lambda result: result >= 0)            # Non-negative result
@post(lambda result: len(result) > 0)        # Non-empty result
@post(lambda result: isinstance(result, str))  # Type guarantee
```

## Common Errors

### 1. `param_mismatch` ERROR

Lambda parameters don't match function:

```python
# BAD: Lambda has 1 param, function has 2
@pre(lambda x: x > 0)
def add(x: int, y: int) -> int:
    return x + y

# GOOD: Lambda matches function
@pre(lambda x, y: x > 0 and y > 0)
def add(x: int, y: int) -> int:
    return x + y
```

### 2. `empty_contract` ERROR

Contract that's always true (tautology):

```python
# BAD: Always true - provides no information
@pre(lambda: True)
def process(data):
    ...

# BAD: Redundant type check (already in signature)
@pre(lambda x: isinstance(x, int))
def square(x: int) -> int:
    return x * x

# GOOD: Meaningful constraint
@pre(lambda x: x >= 0)
def sqrt(x: float) -> float:
    return x ** 0.5
```

### 3. Boolean Trap (Lesson #24)

Python's `and`/`or` return operands, not booleans:

```python
# BAD: Returns string, deal interprets as error message!
@pre(lambda x, msg: x and msg)
def log(x: str, msg: str) -> None:
    print(f"{x}: {msg}")

# GOOD: Explicitly return boolean
@pre(lambda x, msg: bool(x) and bool(msg))
def log(x: str, msg: str) -> None:
    print(f"{x}: {msg}")
```

**Why this matters:** If `x = ""` and `msg = "hello"`, `x and msg` returns `""`, which deal interprets as an error message.

## Integration with Verification

### CrossHair (Symbolic Execution)

CrossHair proves contracts mathematically for pure Python:

```python
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    return x ** 0.5

# CrossHair PROVES: for ALL x >= 0, result >= 0
# This is mathematical certainty, not testing
```

### Hypothesis (Property Testing)

Hypothesis generates random test cases respecting `@pre`:

```python
@pre(lambda items: len(items) > 0)
@post(lambda result: result in items)
def pick_random(items: list) -> Any:
    return random.choice(items)

# Hypothesis generates: [1], [1,2,3], ["a","b"], etc.
# Never generates [] (violates @pre)
```

### deal.cases()

For functions with contracts, `deal.cases()` generates test cases:

```python
from deal import cases

for case in cases(sqrt, count=100):
    case()  # Runs with generated inputs respecting @pre
```

### Verification Pipeline

```
invar guard
    ├─ Static analysis (checks contract syntax)
    ├─ Doctests (example-based tests)
    ├─ CrossHair (symbolic proof for pure Python)
    └─ Hypothesis (property testing via deal.cases)
```

## Contract Completeness

A **complete contract** uniquely determines implementation:

```python
# INCOMPLETE: Multiple implementations satisfy this
@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def mysterious(x: float) -> float:
    ...  # Could be x, x*2, sqrt(x), etc.

# COMPLETE: Only one implementation satisfies this
@pre(lambda x: x >= 0)
@post(lambda result: result * result == x)
def sqrt(x: float) -> float:
    """
    >>> sqrt(4.0)
    2.0
    >>> sqrt(0.0)
    0.0
    """
    return x ** 0.5
```

**Self-test:** "Given only @pre/@post and doctests, could someone else write the exact same function?"

See [Contract Completeness Principle](./contract-complete.md) for details.

## Contract Composition

For reusable contracts, use the `Contract` class:

```python
from invar_runtime.contracts import Contract, pre, NonEmpty, Sorted

# Built-in contracts
@pre(NonEmpty)
def first(items: list) -> Any:
    return items[0]

# Combine with operators
SortedNonEmpty = NonEmpty & Sorted
@pre(SortedNonEmpty)
def binary_search(arr: list, target: int) -> int:
    ...

# Custom contracts
InRange = lambda lo, hi: Contract(lambda x: lo <= x <= hi, f"[{lo},{hi}]")
Age = InRange(0, 120)
```

**Standard library:** `NonEmpty`, `Sorted`, `Unique`, `Positive`, `NonNegative`, `Percentage`, `NonBlank`, `AllPositive`, `NoNone`

## Configuration

In `pyproject.toml`:

```toml
[tool.invar]
# Contract-related rules
missing_contract = "error"    # Core functions must have contracts
empty_contract = "error"      # Tautology contracts are errors
param_mismatch = "error"      # Lambda must match function
```

## See Also

- [Doctests as Specification](./doctests.md) - Examples complement contracts
- [Contract Completeness](./contract-complete.md) - How complete is enough?
- [Smart Verification Routing](../verification/smart-routing.md) - CrossHair vs Hypothesis
- [DX-12: Hypothesis Fallback](../../proposals/DX-12-hypothesis-fallback.md) - Design history
