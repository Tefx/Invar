# Invar Reference

> Quick reference for contracts, markers, configuration, and patterns.

## Contracts

### Basic Syntax

```python
from deal import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)
```

### Contract Composition

```python
from invar import Contract, pre, NonEmpty, Sorted

# Built-in contracts
SortedNonEmpty = NonEmpty & Sorted  # AND
FlexibleInput = NonEmpty | Sorted   # OR
AcceptsEmpty = ~NonEmpty            # NOT

# Custom contracts
InRange = lambda lo, hi: Contract(lambda x: lo <= x <= hi, f"[{lo},{hi}]")
Age = InRange(0, 120)

# Use with decorators
@pre(SortedNonEmpty)
def binary_search(arr, target): ...
```

### Standard Library

| Contract | Description |
|----------|-------------|
| `NonEmpty` | Collection has at least one element |
| `Sorted` | Collection is sorted |
| `Unique` | No duplicate elements |
| `Positive` | Number > 0 |
| `NonNegative` | Number >= 0 |
| `Percentage` | Number in [0, 1] |
| `NonBlank` | String with non-whitespace |
| `AllPositive` | All elements > 0 |
| `NoNone` | No None values |

## Must-Use Return Values

```python
from invar import must_use

@must_use("Error must be handled")
def validate(data: dict) -> Result[Valid, Error]:
    ...

validate(user_input)  # Guard warns: return value ignored!
```

## Loop Invariants

```python
from invar import invariant

def binary_search(arr: list[int], target: int) -> int:
    lo, hi = 0, len(arr)
    while lo < hi:
        invariant(0 <= lo <= hi <= len(arr))  # Bounds check
        invariant(target not in arr[:lo])      # Already searched
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(arr) and arr[lo] == target else -1
```

- **Checked at runtime** when `INVAR_CHECK=1` (default ON)
- **Disabled in production** with `INVAR_CHECK=0`

## Resource Management

```python
from invar import must_close

@must_close
class TempFile:
    def __init__(self, path: str): ...
    def write(self, data: bytes): ...
    def close(self) -> None: ...

# Preferred: context manager (auto-close)
with TempFile("data.tmp") as f:
    f.write(data)
```

## Markers

### Entry Points

Framework callbacks exempt from `Result[T, E]`:

```python
# Auto-detected by decorators (@app.route, @app.command)

# Manual marker for custom callbacks:
# @shell:entry
def on_custom_event(data: dict) -> dict:
    result = handle_event(data)
    return result.unwrap_or({"error": "failed"})
```

### Shell Complexity

When shell function complexity is justified:

```python
# @shell_complexity: Subprocess with error classification
def run_external_tool(...): ...

# @shell_orchestration: Multi-step pipeline coordination
def process_batch(...): ...
```

### Escape Hatch

When rule violation has valid justification:

```python
# @invar:allow shell_result: Framework callback signature fixed
def flask_handler(): ...

# @invar:allow impure_call: Third-party lib requires init
def setup_client(): ...
```

See `invar rules` for all rule names.

## Configuration

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
max_file_lines = 500
max_function_lines = 50

# Exclude doctest lines from function size calculation
exclude_doctest_lines = true

# Override purity detection for specific functions
purity_pure = ["pandas.DataFrame.groupby", "numpy.sum"]
purity_impure = ["mylib.cached_compute"]  # Has side effects
```

## Size Limits

| Limit | Value | Warning At |
|-------|-------|------------|
| File | 500 lines | 80% (400) |
| Function | 50 lines | — |

## Rule Severity

| Level | Blocks Commit | Examples |
|-------|---------------|----------|
| **ERROR** | Yes | missing_contract, impure_call, empty_contract, forbidden_import |
| **WARNING** | No | function_size, internal_import, shell_result, missing_doctest |

## Commands

### Smart Guard

```bash
invar guard              # Full verification (default)
invar guard --changed    # Modified files only
invar guard --static     # Static only (~0.5s)
invar guard --explain    # Detailed explanations
```

### Perception

```bash
invar sig <file>           # Function signatures + contracts
invar sig <file>::<symbol> # Specific function
invar map                  # Symbol locations + reference counts
invar map --top 20         # Most-referenced symbols
```

### Other

```bash
invar rules              # List all rules with severity
invar version            # Show version
```

## Doctest Best Practices

**Dict/Set comparison:** Use deterministic comparison:

```python
# BAD: Dict ordering may vary
>>> result.constraints
{'min_value': 1, 'max_value': 99}  # May fail!

# GOOD: Use sorted() for deterministic output
>>> sorted(result.items())
[('max_value', 99), ('min_value', 1)]

# GOOD: Use equality comparison
>>> result == {'min_value': 1, 'max_value': 99}
True
```

## Three-Way Consistency

```
        Code
       /    \
@pre/@post ↔ Doctests
```

All three must align. Any conflict is a bug.

**Complete Contract = uniquely determines implementation.**

Self-test: "Given only @pre/@post and doctests, could someone else write the exact same function?"
