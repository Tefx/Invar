# The Invar Protocol v3.23

> **"Trade structure for safety."** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

**Design:** Agent-Native. Protocol optimized for AI agent consumption. See [docs/VISION.md](docs/VISION.md).

**Smart Guard:** `invar guard` runs static + doctests automatically. Zero decisions needed.

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
      /      \
@pre/@post ↔ Doctests
```

All three must align. Any conflict is a bug.

## Why Contracts Matter

Contracts serve **dual purpose**:

1. **Verification** — Catch violations before they become bugs
2. **Recovery** — When violations occur, contracts guide the fix

Research shows:
- Underspecified problems are unsolvable (SWE-bench: 1.96% solve rate)
- Clear contracts make problems tractable (Clover: 87% acceptance)
- Good contracts enable auto-recovery (Pel: self-healing agents)

## Size Limits

| Limit | Value | Warning |
|-------|-------|---------|
| File | 500 lines | 80% (400) |
| Function | 50 lines | — |

## Guard Commands

```bash
invar guard              # Static + doctests (default)
invar guard --changed    # Modified files only
invar guard --quick      # Static only (skip doctests)
invar guard --prove      # Static + doctests + CrossHair
invar guard --explain    # Detailed explanations
invar rules              # List all rules
```

**Three levels:** STATIC (`--quick`) → STANDARD (default) → PROVE (`--prove`)

**When to use `--prove`:** Contract changes, releases, debugging contract failures.

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

□ Verify    — Run: invar guard && pytest --doctest-modules
              If violations:
              1. Reflect: Why did this fail? What was misunderstood?
              2. Read: contract + doctest + error message
              3. Fix based on understanding
              4. Verify again
```

## Doctest Best Practices

**Dict/Set comparison:** Use deterministic comparison to avoid ordering issues:

```python
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
```

## More Information

| Topic | Location |
|-------|----------|
| Why & How (essential) | [docs/INVAR-GUIDE.md](docs/INVAR-GUIDE.md) |
| Design philosophy | [docs/VISION.md](docs/VISION.md) |
| Rule details | `invar rules` or `invar guard --explain` |

---

*Protocol v3.23 — Three-level verification, Agent-Native JSON output, research-validated.*
