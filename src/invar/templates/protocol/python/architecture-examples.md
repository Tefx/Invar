## Core Example (Python)

```python
from deal import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    >>> discounted_price(100, 0)      # Edge: no discount
    100.0
    """
    return price * (1 - discount)
```

**Self-test:** Can someone else write the exact same function from just @pre/@post + doctests?

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`

## Shell Example (Python)

```python
from pathlib import Path
from returns.result import Result, Success, Failure

def read_config(path: Path) -> Result[dict, str]:
    """Shell: handles I/O, returns Result for error handling."""
    try:
        import json
        return Success(json.loads(path.read_text()))
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON: {e}")
```

**Pattern:** Shell reads file → passes content to Core → returns Result.

More examples: `.invar/examples/`
