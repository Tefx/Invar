# The Invar Protocol v3.19

> **"Trade structure for safety."** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

**Design:** Agent-Native. Protocol optimized for AI agent consumption. See [docs/VISION.md](docs/VISION.md).

## Core/Shell Architecture

| Zone | Location | Must Have | Example |
|------|----------|-----------|---------|
| **Core** | `src/*/core/` | `@pre`/`@post` contracts, doctests | Pure calculations, transformations |
| **Shell** | `src/*/shell/` | `Result[T, E]` return type | File I/O, network, CLI |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`, `random.*`

**Core receives data, not paths** — Shell reads files, passes content to Core.

## Contracts

Every Core function must have `@pre` or `@post`:

```python
from deal import pre, post

@pre(lambda x, y: x > 0 and y > 0)  # Lambda must match ALL parameters
def calculate(x: int, y: int) -> int:
    """
    Calculate something.

    >>> calculate(2, 3)
    5
    """
    return x + y
```

Guard provides hints and suggestions for violations. Use `invar guard --explain` for details.

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

### Verification
```bash
invar guard              # Check rules (shows hints for violations)
invar guard --changed    # Modified files only (shows file context)
invar guard --explain    # Detailed explanations and limitations
invar guard --agent      # JSON output with full context
invar rules              # List all rules with severity and hints
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
- Both auto-output JSON in agent mode

## Workflow: ICIDIV

**I**ntent → **C**ontract → **I**nspect → **D**esign → **I**mplement → **V**erify

```
□ Intent    — What are we trying to achieve?
□ Contract  — What inputs are invalid? What does output guarantee?
□ Inspect   — Run: invar sig <file> to see contracts, invar map --top 10 for entry points
□ Design    — If file > 400 lines, plan extraction first
□ Implement — Write code with contracts and doctests
□ Verify    — Run: invar guard && pytest --doctest-modules
```

## Configuration

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
max_file_lines = 500
max_function_lines = 50
```

## More Information

| Topic | Location |
|-------|----------|
| Why & How (essential) | [docs/INVAR-GUIDE.md](docs/INVAR-GUIDE.md) |
| Design philosophy | [docs/VISION.md](docs/VISION.md) |
| Rule details | `invar rules` or `invar guard --explain` |

---

*Protocol v3.19 — ICIDIV workflow (6-step with Implement).*
