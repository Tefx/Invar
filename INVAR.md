<!--
  ┌─────────────────────────────────────────────────────────────┐
  │ INVAR-MANAGED FILE - DO NOT EDIT DIRECTLY                   │
  │                                                             │
  │ This file is managed by Invar. Changes may be lost on       │
  │ `invar update`. Add project content to CLAUDE.md instead.   │
  └─────────────────────────────────────────────────────────────┘
-->
# The Invar Protocol v3.23

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
| **6. Integrate Fully** | Verify all feature paths connect; local correctness ≠ global correctness | DX-07: --prove post-mortem |

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

## Size Limits

| Limit | Value | Warning |
|-------|-------|---------|
| File | 500 lines | 80% (400) |
| Function | 50 lines | — |

## Commands

### Smart Guard (Primary Command)
```bash
invar guard              # Static + doctests (default)
invar guard --changed    # Modified files only
invar guard --quick      # Static only (skip doctests)
invar guard --prove      # Static + doctests + CrossHair
invar guard --explain    # Detailed explanations
```

### Three Verification Levels

| Level | Flag | Content | Use When |
|-------|------|---------|----------|
| **STATIC** | `--quick` | Rules only | Debugging static analysis |
| **STANDARD** | (default) | Rules + doctests | Normal development |
| **PROVE** | `--prove` | Rules + doctests + CrossHair | Contract changes, releases |

**Agent JSON output includes `"verification_level"` for transparency.**

**DX-14: `--prove` Now Automatic:**
- Pre-commit runs `--prove` by default (fast after DX-13)
- CI runs `--prove` for full verification
- Manual `--prove` rarely needed (already automatic)

**DX-13 Performance:**
- Incremental: Only verifies changed files
- First commit: ~5s, subsequent: ~2s (cached)

### Other Commands
```bash
invar test <file>        # Run doctests on specific file
invar verify <file>      # CrossHair verification on specific file
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

## Workflow: ICIDIV

**I**ntent → **C**ontract → **I**nspect → **D**esign → **I**mplement → **V**erify

```
□ Intent    — What are we trying to achieve? List edge cases.

□ Contract  — Write COMPLETE @pre/@post AND doctests BEFORE code.
              Include: normal case, boundaries, edge conditions.
              Self-test: Can this contract regenerate the function?

□ Inspect   — Run: invar sig <file>, invar map --top 10

□ Design    — Decompose into sub-functions:
              1. List functions (name + description)
              2. Identify dependencies
              3. Order: leaves first, then compose
              4. If file > 400 lines, plan extraction

□ Implement — For each function (in dependency order):
              Write code to pass the doctests you already wrote

□ Verify    — Run: invar guard (Smart Guard: static + doctests)
              If violations:
              1. Reflect: Why did this fail? What was misunderstood?
              2. Read: contract + doctest + error message
              3. Fix based on understanding
              4. Verify again
```

## Installation

```bash
pip install python-invar              # Basic (static + doctests)
pip install python-invar[prove]       # + CrossHair symbolic verification
```

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

# Exclude doctest lines from function size calculation (DX-03)
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

*Protocol v3.23 — Three-level verification, Agent-Native JSON output, research-validated.*
