
<!--
  ┌─────────────────────────────────────────────────────────────┐
  │ INVAR-MANAGED FILE - DO NOT EDIT DIRECTLY                   │
  │                                                             │
  │ This file is managed by Invar. Changes may be lost on       │
  │ `invar update`. Add project content to CLAUDE.md instead.   │
  └─────────────────────────────────────────────────────────────┘

  License: CC-BY-4.0 (Creative Commons Attribution 4.0 International)
  https://creativecommons.org/licenses/by/4.0/

  You are free to share and adapt this document, provided you give
  appropriate credit to the Invar project.
-->
# The Invar Protocol v5.0

> **"Trade structure for safety."**


## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Core (pure logic) / Shell (I/O) physically separate |
| 2. Contract Complete | Preconditions + Postconditions + Examples uniquely determine implementation |
| 3. Context Economy | Overview → Signatures → Code (only read what's needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct; verify all paths |


## Core/Shell Architecture

| Zone | Location | Requirements |
|------|----------|--------------|
| Core | `**/core/**` | Contracts + Examples, pure (no I/O) |
| Shell | `**/shell/**` | Error-handling return type |

### Decision Tree: Core vs Shell

```
Does this function...
│
├─ Read or write files? ──────────────────→ Shell
├─ Make network requests? ─────────────────→ Shell
├─ Access current time? ──────────────────→ Shell OR inject as parameter
├─ Generate random values? ────────────────→ Shell OR inject as parameter
├─ Print to console? ──────────────────────→ Shell (return data, Shell logs)
├─ Access environment variables? ──────────→ Shell
│
└─ None of the above? ─────────────────────→ Core
```

### Injection Pattern (Universal)

Instead of accessing impure values directly, inject them as parameters:

```
# Core: receives 'current_time' as parameter (pure)
FUNCTION is_expired(expiry, current_time):
    RETURN current_time > expiry

# Shell: calls with actual time
expired = is_expired(token.expiry, get_current_time())
```

This keeps Core functions pure and testable.



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




## Contract Syntax (Python)

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

### Meaningful Contracts

```python
# Redundant - type hints already check this
@pre(lambda x: isinstance(x, int))
def calc(x: int): ...

# Meaningful - checks business logic
@pre(lambda x: x > 0)
def calc(x: int): ...

# Meaningful - checks relationship between params
@pre(lambda start, end: start < end)
def process_range(start: int, end: int): ...
```

### @post Scope

```python
# WRONG: @post cannot access function parameters
@post(lambda result: result > x)  # 'x' not available!
def calc(x: int) -> int: ...

# CORRECT: @post can only use 'result'
@post(lambda result: result >= 0)
def calc(x: int) -> int: ...
```

### Doctest Examples

```python
def calculate(x: int) -> int:
    """
    >>> calculate(5)
    10
    >>> calculate(0)      # Edge case
    0
    """
    return x * 2
```



## Check-In (Required)

Your first message MUST display:

```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

Actions:
1. Read `.invar/context.md` (Key Rules + Current State + Lessons Learned)
2. Show one-line status

**Do NOT execute verification at Check-In.**
Verification is for VALIDATE phase and Final only.

This is your sign-in. The user sees it immediately.
No visible check-in = Session not started.


## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Activities |
|-------|---------|------------|
| UNDERSTAND | Know what and why | Intent, Inspect existing code, Constraints |
| SPECIFY | Define boundaries | Preconditions, Postconditions, Examples |
| BUILD | Write code | Implement leaves, Compose |
| VALIDATE | Confirm correctness | Run verification, Review if needed |

**Key:** Inspect before Contract. Contracts before Code. Depth varies naturally.

**Review Gate:** When verification triggers `review_suggested` (escape hatches ≥3, security paths, low coverage), invoke `/review` before completion.


## Visible Workflow

For complex tasks (3+ functions), show 3 checkpoints in TodoList:

```
□ [UNDERSTAND] Task description, codebase context, constraints
□ [SPECIFY] Contracts and design decomposition
□ [VALIDATE] Verification results, Review Gate if triggered, integration status
```

**BUILD is internal work** — not shown in TodoList.

**Show contracts before code.** Example:

```
[SPECIFY] calculate_discount:
PRECONDITION: price > 0 AND 0 <= rate <= 1
POSTCONDITION: result >= 0
FUNCTION calculate_discount(price, rate): ...

[BUILD] Now coding...
```

**When to use:** New features (3+ functions), architectural changes, Core modifications.
**Skip for:** Single-line fixes, documentation, trivial refactoring.


## Task Completion

A task is complete only when ALL conditions are met:
- Check-In displayed: `✓ Check-In: [project] | [branch] | [clean/dirty]`
- Intent explicitly stated
- Contract written before implementation
- Final displayed: `✓ Final: verification PASS | <errors>, <warnings>`
- User requirement satisfied

**Missing any = Task incomplete.**

---

*Protocol v5.0 — USBV workflow | [Examples](.invar/examples/)*



## Markers (Python)

### Entry Points

Entry points are framework callbacks (`@app.route`, `@app.command`) at Shell boundary.
- **Exempt** from `Result[T, E]` — must match framework signature
- **Keep thin** (max 15 lines) — delegate to Shell functions that return Result

Auto-detected by decorators. For custom callbacks:

```python
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

### Architecture Escape Hatch

When rule violation has valid architectural justification:

```python
# @invar:allow shell_result: Framework callback signature fixed
def flask_handler(): ...
```

**Valid rule names for @invar:allow:**
- `shell_result` — Shell function without Result return type
- `entry_point_too_thick` — Entry point exceeds 15 lines
- `forbidden_import` — I/O import in Core (rare, justify carefully)

Run `invar rules` for complete rule catalog with hints.




## Commands (Python)

```bash
invar guard              # Check git-modified files (fast, default)
invar guard --all        # Check entire project (CI, release)
invar guard --static     # Static only (quick debug, ~0.5s)
invar guard --coverage   # Collect branch coverage
invar guard -c           # Contract coverage only (DX-63)
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules with detection/hints (JSON)
```

**Default behavior**: Checks git-modified files for fast feedback during development.
Use `--all` for comprehensive checks before release.

## Configuration (Python)

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]    # Default: ["src/core", "core"]
shell_paths = ["src/myapp/shell"]  # Default: ["src/shell", "shell"]
max_file_lines = 500               # Default: 500 (warning at 80%)
max_function_lines = 50            # Default: 50
# Doctest lines are excluded from size calculations
```




## Troubleshooting (Python)

### Size Limits (Agent Quick Reference)

| Rule | Limit | Fix |
|------|-------|-----|
| `function_too_long` | **50 lines** | Extract helper: `_impl()` + main with docstring |
| `file_too_long` | **500 lines** | Split by responsibility |
| `entry_point_too_thick` | **15 lines** | Delegate to Shell functions |

*Doctest lines excluded from counts. Limits configurable in `pyproject.toml`.*

### Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `param_mismatch` error | Lambda missing params | Include ALL params (even defaults) |
| `shell_result` error | Shell func no Result | Add Result[T,E] or @invar:allow |
| `is_failure()` not found | Wrong Result check | Use `isinstance(result, Failure)` |

### Result Type Usage

```python
from returns.result import Result, Success, Failure

# Creating results
return Success(value)
return Failure(error)

# Checking results
if isinstance(result, Failure):
    handle_error(result.failure())
else:
    use_value(result.unwrap())

# Chaining
result.map(transform).bind(next_operation)
```



---

*Protocol v5.0 — USBV workflow (DX-32) | [Examples](.invar/examples/)*
