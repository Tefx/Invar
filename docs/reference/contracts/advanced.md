# Advanced Contract Features

> Runtime features for complex validation scenarios.

## Must-Use Return Values

Mark return values that must be handled:

```python
from invar_runtime import must_use

@must_use("Error must be handled")
def validate(data: dict) -> Result[Valid, Error]:
    ...

validate(user_input)  # Guard warns: return value ignored!
```

**Use case:** Functions returning `Result`, `Option`, or error states that callers must handle.

## Loop Invariants

Assert conditions that must hold on every loop iteration:

```python
from invar_runtime import invariant

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

**Runtime behavior:**
- **Checked** when `INVAR_CHECK=1` (default ON in development)
- **Disabled** with `INVAR_CHECK=0` (production)

## Resource Management

Ensure resources are properly closed:

```python
from invar_runtime import must_close

@must_close
class TempFile:
    def __init__(self, path: str): ...
    def write(self, data: bytes): ...
    def close(self) -> None: ...

# Preferred: context manager (auto-close)
with TempFile("data.tmp") as f:
    f.write(data)

# Manual: Guard warns if close() not called
f = TempFile("data.tmp")
f.write(data)
# Missing f.close() → Guard warning
```

**Use case:** File handles, database connections, network sockets.

## Standard Library Contracts

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

```python
from invar_runtime.contracts import NonEmpty, Sorted, Positive

@pre(NonEmpty & Sorted)
def binary_search(arr: list[int], target: int) -> int:
    ...

@pre(Positive)
def sqrt(x: float) -> float:
    ...
```

## See Also

- [Pre/Post Contracts](./pre-post.md) - Basic contract usage
- [Contract Completeness](./completeness.md) - Contract quality
- [Doctests](./doctests.md) - Testing contracts
