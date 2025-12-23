<!--
  ┌─────────────────────────────────────────────────────────────┐
  │ INVAR-MANAGED FILE - DO NOT EDIT DIRECTLY                   │
  │                                                             │
  │ This file is managed by Invar. Changes may be lost on       │
  │ `invar update`. Add project content to CLAUDE.md instead.   │
  └─────────────────────────────────────────────────────────────┘
-->
# The Invar Protocol v3.26

> **"Trade structure for safety."**

## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Core (pure logic) / Shell (I/O) physically separate |
| 2. Contract Complete | @pre/@post + doctests uniquely determine implementation |
| 3. Context Economy | map → sig → code (only read what's needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct; verify all paths |

## Core/Shell Architecture

| Zone | Location | Requirements |
|------|----------|--------------|
| Core | `**/core/**` | @pre/@post, pure (no I/O), doctests |
| Shell | `**/shell/**` | `Result[T, E]` return type |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`

## Core Example (Pure Logic)

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

## Shell Example (I/O Operations)

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

## Session Start (Required)

Before writing any code, execute:

1. **invar_guard** (changed=true) — Check existing violations
2. **invar_map** (top=10) — Understand code structure

Then read:
- `.invar/examples/` — Core/Shell patterns
- `.invar/context.md` — Project state, lessons learned

**Skipping these steps → Non-compliant code → Rework required.**

Use MCP tools if available (`invar_guard`, `invar_map`), otherwise use CLI commands.
For agent-specific entry format, see your configuration file (CLAUDE.md, .cursorrules, etc).

## ICIDIV Workflow (Required Order)

```
1. Intent    — What? Core or Shell? Edge cases?
2. Contract  — @pre/@post + doctests BEFORE code
3. Inspect   — invar sig <file>, invar map --top 10
4. Design    — Decompose: leaves first, then compose
5. Implement — Write code to pass your doctests
6. Verify    — invar guard. If fail: reflect → fix → verify
```

**Contract before Implement. Verify after every change. No exceptions.**

## Task Completion

A task is complete only when ALL conditions are met:
- Session Start executed (invar_guard + invar_map, context read)
- Intent explicitly stated
- Contract written before implementation
- Final **invar_guard** passed
- User requirement satisfied

**Missing any = Task incomplete.**

## Commands

```bash
invar guard              # Full: static + doctests + CrossHair + Hypothesis (default)
invar guard --static     # Static only (quick debug, ~0.5s)
invar guard --changed    # Modified files only
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
```

## Configuration

```toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
exclude_doctest_lines = true  # Don't count doctests in function size
```

---

*Protocol v3.26 | [Guide](docs/INVAR-GUIDE.md) | [Examples](.invar/examples/)*
