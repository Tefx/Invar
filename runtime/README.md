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
- `@skip_property_test(reason)` - Skip property-based testing

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

MIT
