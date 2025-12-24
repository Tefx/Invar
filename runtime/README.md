# invar-runtime

Lightweight runtime contracts for Python projects using Invar.

## Installation

```bash
pip install invar-runtime
```

## Usage

```python
from invar_runtime import pre, post, Contract, NonEmpty, Positive

# Use built-in contracts
@pre(NonEmpty)
def first(xs: list) -> int:
    return xs[0]

# Create custom contracts
Even = Contract(lambda x: x % 2 == 0, "even")

@pre(Positive & Even)
def half(n: int) -> int:
    return n // 2

# Compose contracts
@post(NonEmpty)
def get_items() -> list:
    return [1, 2, 3]
```

## Available Contracts

### Collections
- `NonEmpty` - Collection has at least one element
- `Sorted` - Elements are in sorted order
- `Unique` - No duplicate elements
- `SortedNonEmpty` - Both sorted and non-empty

### Numbers
- `Positive` - Greater than zero
- `NonNegative` - Greater than or equal to zero
- `Negative` - Less than zero
- `InRange(lo, hi)` - Value in [lo, hi]
- `Percentage` - Value in [0, 100]

### Strings
- `NonBlank` - Non-empty and not just whitespace

### List Elements
- `AllPositive` - All elements > 0
- `AllNonNegative` - All elements >= 0
- `NoNone` - No None values

## Decorators

- `@must_use(reason)` - Mark return value as must-use
- `@must_close` - Mark class as requiring explicit cleanup
- `@strategy(**params)` - Specify Hypothesis strategies
- `@skip_property_test(reason)` - Skip property-based testing (**reason required**)

### Skip Property Test Usage

The `@skip_property_test` decorator requires a reason explaining why the function cannot be property-tested. Guard warns if used without justification.

```python
# ✅ Good - with reason
@skip_property_test("no_params: Zero-parameter function, no inputs to vary")
def get_version() -> str:
    return "1.0.0"

# ❌ Bad - Guard warns about missing reason
@skip_property_test
def my_func(): ...
```

**Valid reason categories:**
- `no_params:` - Function has no parameters to test
- `strategy_factory:` - Returns Hypothesis strategy, not testable data
- `external_io:` - Requires database/network/filesystem
- `non_deterministic:` - Output depends on time/random state

## Loop Invariants

```python
from invar_runtime import invariant

while lo < hi:
    invariant(0 <= lo <= hi <= len(arr), "bounds check")
    mid = (lo + hi) // 2
    ...
```

## Development Tools

For static analysis and verification tools, install `invar-tools`:

```bash
pip install invar-tools
# or use without installing:
uvx invar-tools guard
```

## License

Apache-2.0
