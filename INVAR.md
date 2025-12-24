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
# The Invar Protocol v3.28

> **"Trade structure for safety."** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

**Design:** Agent-Native. Protocol optimized for AI agent consumption. See [docs/VISION.md](docs/VISION.md).

**Smart Guard:** `invar guard` runs static analysis + doctests automatically. Zero decisions needed.

## The Six Laws

| Law | Principle | Research Basis |
|-----|-----------|----------------|
| **1. Separation** | Pure logic (Core) and I/O (Shell) must be physically separate | Determinism enables testing |
| **2. Contract Complete** | Define COMPLETE, RECOVERABLE boundaries before implementation | Clover: 87% accept, 0% false positive |
| **3. Context Economy** | Read map → signatures → implementation (only if needed) | Token efficiency |
| **4. Decompose First** | Break complex tasks into sub-functions before implementing | Parsel: +75% pass rate |
| **5. Verify Reflectively** | If fail: Reflect (why?) → Fix → Verify again | Reflexion: +11% success |
| **6. Integrate Fully** | Verify all feature paths connect; local correctness ≠ global correctness | Post-mortem driven |

## Core/Shell Architecture

| Zone | Location | Must Have | Example |
|------|----------|-----------|---------|
| **Core** | `src/*/core/` | `@pre`/`@post` contracts, doctests | Pure calculations, transformations |
| **Shell** | `src/*/shell/` | `Result[T, E]` return type | File I/O, network, CLI |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`, `random.*`

**Core receives data, not paths** — Shell reads files, passes content to Core.

## Contracts (Test-First)

Before implementation, define COMPLETE contracts:

```python
from deal import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    Apply discount to price.

    >>> discounted_price(100, 0.2)    # Normal case
    80.0
    >>> discounted_price(100, 0)      # Edge: no discount
    100.0
    >>> discounted_price(100, 1)      # Edge: full discount
    0.0
    """
    return price * (1 - discount)
```

**Complete Contract = uniquely determines implementation.**

Self-test: "Given only @pre/@post and doctests, could someone else write the exact same function?"

**Three-Way Consistency:**

```
        Code
       /    \
@pre/@post ↔ Doctests
```

All three must align. Any conflict is a bug.

## Must-Use Return Values

Mark functions whose return values should not be ignored:

```python
from invar import must_use

@must_use("Error must be handled")
def validate(data: dict) -> Result[Valid, Error]:
    ...

validate(user_input)  # Guard warns: return value ignored!
```

## Loop Invariants

Document what must remain true throughout loop execution:

```python
from invar import invariant

def binary_search(arr: list[int], target: int) -> int:
    lo, hi = 0, len(arr)
    while lo < hi:
        invariant(0 <= lo <= hi <= len(arr))  # Bounds check
        invariant(target not in arr[:lo])      # Already searched left
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(arr) and arr[lo] == target else -1
```

- **Checked at runtime** when `INVAR_CHECK=1` (default ON)
- **Disabled in production** with `INVAR_CHECK=0`
- **Raises `InvariantViolation`** when condition fails

## Contract Composition

Compose reusable contracts with `&`, `|`, `~` operators:

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

**Standard library:** `NonEmpty`, `Sorted`, `Unique`, `Positive`, `NonNegative`, `Percentage`, `NonBlank`, `AllPositive`, `NoNone`

## Resource Management

Mark classes that require explicit cleanup:

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
# File automatically closed
```

- **Adds context manager protocol** automatically
- **Use `is_must_close(obj)`** to check if resource requires cleanup

## Why Contracts Matter

Contracts serve **dual purpose**:

1. **Verification** — Catch violations before they become bugs
2. **Recovery** — When violations occur, contracts guide the fix

Research shows:
- Underspecified problems are unsolvable (SWE-bench: 1.96% solve rate)
- Clear contracts make problems tractable (Clover: 87% acceptance)
- Good contracts enable auto-recovery (Pel: self-healing agents)

## Rule Severity

| Level | Blocks Commit | Examples |
|-------|---------------|----------|
| **ERROR** | Yes | missing_contract, impure_call, empty_contract, forbidden_import |
| **WARNING** | No | function_size, internal_import, shell_result, missing_doctest |

Guard shows **Code Health** percentage based on warnings. Fix warnings in files you modify.

## Markers

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

See `invar rules` for all rule names.

## Size Limits

| Limit | Value | Warning |
|-------|-------|---------|
| File | 500 lines | 80% (400) |
| Function | 50 lines | — |

## Commands

### Smart Guard (Primary Command)
```bash
invar guard              # Full verification (default)
invar guard --changed    # Modified files only
invar guard --static     # Static only (~0.5s, for debugging)
invar guard --explain    # Detailed explanations
```

### Two Verification Levels (DX-19)

| Level | Flag | Content | Use When |
|-------|------|---------|----------|
| **STATIC** | `--static` | Rules only (~0.5s) | Debugging static analysis |
| **STANDARD** | (default) | Rules + doctests + CrossHair + Hypothesis (~5s) | Everything else |

**DX-19: Zero decisions.** Default = full verification. No need to choose modes.

**Agent JSON output includes `"verification_level"` for transparency.**

**Incremental verification makes STANDARD fast:**
- Only verifies changed files with `--changed`
- First run: ~5s, subsequent: ~2s (CrossHair cache)

### Other Commands
```bash
invar rules              # List all rules with severity
```

### Perception (use BEFORE reading/modifying code)
```bash
invar sig <file>           # Function signatures + contracts (no body)
invar sig <file>::<symbol> # Specific function with contracts
invar map                  # Symbol locations + reference counts
invar map --top 20         # Most-referenced symbols (entry points)
```

**Why use Invar perception tools?**
- `invar sig` shows **@pre/@post contracts** (generic tools don't)
- `invar map --top` finds **entry points by reference count** (unique feature)
- **Auto JSON**: All commands auto-detect agent mode (pipe/redirect → JSON, terminal → human-readable)

## Check-In (Required)

Your first message MUST display:

```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

Execute `invar_guard(changed=true)` and `invar_map(top=10)`, then show this one-line summary.

This is your sign-in. The user sees it immediately.
No visible check-in = Session not started.

Then read `.invar/context.md` for project state and lessons learned.

## Workflow: ICIDIV (Required Order)

**I**ntent → **C**ontract → **I**nspect → **D**esign → **I**mplement → **V**erify

```
1. Intent    — What? Core or Shell? Edge cases?
2. Contract  — @pre/@post + doctests BEFORE code
3. Inspect   — invar sig <file>, invar map --top 10
4. Design    — Decompose: leaves first, then compose
5. Implement — Write code to pass your doctests
6. Verify    — invar guard. If fail: reflect → fix → verify
```

**Contract before Implement. Verify after every change. No exceptions.**

## Visible Workflow (DX-30)

For complex tasks (3+ functions, architectural changes), show ICIDIV phases in your TodoList:

```
□ [Intent] Task description, Core/Shell classification
□ [Contract] Function signatures with @pre/@post
□ [Inspect] Files and symbols to review
□ [Design] Decomposition plan
□ [Implement] Write code
□ [Verify] Guard results
```

**Contract before Implement:** Show contracts in your message before writing code.

```python
[Contract] calculate_discount:
@pre(lambda price, rate: price > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_discount(price: float, rate: float) -> float:
    ...

Edge cases:
- price = 0 → Invalid (rejected by @pre)
- rate = 0 → Full price
- rate = 1 → Zero (free)

[Implement] Now coding...
```

**When to use Phase TodoList:**
- New features (3+ functions)
- Architectural changes
- Core module modifications

**Skip for:** Single-line fixes, documentation changes, trivial refactoring.

This makes compliance visible and catches mistakes early.

## Task Completion

A task is complete only when ALL conditions are met:
- Check-In displayed: `✓ Check-In: guard PASS | top: <entry1>, <entry2>`
- Intent explicitly stated
- Contract written before implementation
- Final displayed: `✓ Final: guard PASS | <errors>, <warnings>`
- User requirement satisfied

**Missing any = Task incomplete.**

## Installation

```bash
# Development tools (guard, map, sig, MCP)
pip install invar-tools

# Or use without installing
uvx invar-tools guard

# Runtime contracts for your project
pip install invar-runtime
```

| Package | Size | Purpose |
|---------|------|---------|
| `invar-runtime` | ~3MB | Runtime contracts (`@pre`, `@post`, etc.) |
| `invar-tools` | ~100MB | Dev tools (static analysis, doctests, Hypothesis, CrossHair, MCP) |

## Doctest Best Practices

**Dict/Set comparison:** Use deterministic comparison to avoid ordering issues:

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

## Configuration

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
max_file_lines = 500
max_function_lines = 50

# Exclude doctest lines from function size calculation
# Useful when comprehensive doctests cause size violations
exclude_doctest_lines = true

# Override purity detection for specific functions
purity_pure = ["pandas.DataFrame.groupby", "numpy.sum"]
purity_impure = ["mylib.cached_compute"]  # Has side effects
```

## More Information

| Topic | Location |
|-------|----------|
| Why & How (essential) | [docs/INVAR-GUIDE.md](docs/INVAR-GUIDE.md) |
| Design philosophy | [docs/VISION.md](docs/VISION.md) |
| Rule details | `invar rules` or `invar guard --explain` |

---

*Protocol v3.28 — Added Visible Workflow (DX-30): Phase TodoList and Contract Declaration conventions.*
