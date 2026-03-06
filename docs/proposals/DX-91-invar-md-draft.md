# DX-91: INVAR.md Reference Draft (v2.1)

Target: ~150 lines. Complete reference. Agent reads on-demand (linked from CLAUDE.md and guard error hints).
Location: Top-level `INVAR.md` (architectural guidance, discoverable, short guard references).

---

```markdown
# Invar Reference

## Core/Shell Architecture

| Zone | Path | Requirements |
|------|------|-------------|
| Core | `**/core/**` | @pre/@post contracts + doctests, pure (no I/O) |
| Shell | `**/shell/**` | Returns Result[T, E], handles all I/O |

### Decision Tree

```
Does this function...
├─ Read/write files?              → Shell
├─ Make network requests?         → Shell
├─ Access environment variables?  → Shell
├─ Access current time?           → Shell (or inject as parameter)
├─ Generate random values?        → Shell (or inject as parameter)
└─ None of the above?             → Core
```

### Injection Pattern

Keep Core pure by injecting impure values as parameters:

```python
# Core: receives current_time as parameter (pure, testable)
@pre(lambda expiry, current_time: isinstance(expiry, datetime))
def is_expired(expiry: datetime, current_time: datetime) -> bool:
    """
    >>> from datetime import datetime
    >>> is_expired(datetime(2025, 1, 1), datetime(2025, 6, 1))
    True
    """
    return current_time > expiry

# Shell: calls with actual time
expired = is_expired(token.expiry, datetime.now())
```

## Core Example

```python
from deal import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    >>> discounted_price(100, 0)
    100.0
    """
    return price * (1 - discount)
```

**Forbidden imports in Core:** os, sys, subprocess, pathlib, open, requests, datetime.now

## Shell Example

```python
from pathlib import Path
from returns.result import Result, Success, Failure

def read_config(path: Path) -> Result[dict, str]:
    """Shell: handles I/O, returns Result."""
    try:
        import json
        return Success(json.loads(path.read_text()))
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON: {e}")
```

### Result Type Patterns

```python
from returns.result import Result, Success, Failure

# Creating
return Success(value)
return Failure(error)

# Checking
if isinstance(result, Failure):
    handle_error(result.failure())
else:
    use_value(result.unwrap())

# Chaining
result.map(transform).bind(next_operation)
```

## Contract Syntax

### Lambda Signature (Critical)

```python
# WRONG: Lambda only takes first parameter
@pre(lambda x: x >= 0)
def calculate(x: int, y: int = 0): ...

# CORRECT: Lambda must include ALL parameters (even defaults)
@pre(lambda x, y=0: x >= 0)
def calculate(x: int, y: int = 0): ...
```

Guard's `param_mismatch` rule catches this as ERROR.

### @post Scope

```python
# WRONG: @post cannot access function parameters
@post(lambda result: result > x)  # 'x' not available!

# CORRECT: @post can only use 'result'
@post(lambda result: result >= 0)
```

### Meaningful Contracts

```python
# Redundant — type hints already check this
@pre(lambda x: isinstance(x, int))  # DON'T

# Meaningful — checks business logic
@pre(lambda x: x > 0)               # DO

# Meaningful — checks relationship between params
@pre(lambda start, end: start < end) # DO
```

## Configuration

```toml
# pyproject.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]     # Default: ["src/core", "core"]
shell_paths = ["src/myapp/shell"]   # Default: ["src/shell", "shell"]
max_file_lines = 500                # Default: 500 (warning at 80%)
max_function_lines = 50             # Default: 50
timeout_doctest = 60                # Default: 60s
timeout_crosshair = 300             # Default: 300s
timeout_hypothesis = 300            # Default: 300s
```

Alternative: `invar.toml` with `[guard]` section (same keys, no `tool.invar` prefix).

## Markers

### Entry Points

Functions called by frameworks (Click, Typer, Flask, pytest) don't need cross-file callers:

```python
@app.command()           # Typer/Click: auto-detected as entry point
def deploy(): ...

app.command()(deploy)    # Dynamic registration: also detected
```

### Escape Hatches

```python
# Suppress a specific rule
# @invar:allow dead_export: CLI entry point called by framework
def main(): ...

# Mark shell complexity as acknowledged
# @invar:allow shell_complexity: orchestration requires many steps
def deploy_pipeline(): ...
```

## Size Limits

| Rule | Limit | Fix |
|------|-------|-----|
| `function_too_long` | 50 lines | Extract helper `_impl()` |
| `file_too_long` | 500 lines | Split by responsibility |
| `entry_point_too_thick` | 15 lines | Delegate to Shell functions |

Doctest lines excluded from counts. Limits configurable in pyproject.toml.

## Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `param_mismatch` error | Lambda missing params | Include ALL params (even defaults) |
| `shell_result` error | Shell func missing Result | Add `Result[T, E]` return or `@invar:allow` |
| `is_failure()` not found | Wrong Result check | Use `isinstance(result, Failure)` |
```

**Line count: ~150 lines**

---

This replaces:
- Old INVAR.md (434 lines) → INVAR.md (150 lines)
- .invar/examples/ (12 files) → inline code examples in INVAR.md
- Six Laws, USBV, Check-In/Final, Visible Workflow → deleted
