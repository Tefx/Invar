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
# The Invar Protocol v4.0

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

## Check-In (Required)

Your first message MUST display:

```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

Execute `invar_guard(changed=true)` and `invar_map(top=10)`, then show this one-line summary.

This is your sign-in. The user sees it immediately.
No visible check-in = Session not started.

Then read `.invar/context.md` for project state and lessons learned.

## USBV Workflow (DX-32)

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Activities |
|-------|---------|------------|
| UNDERSTAND | Know what and why | Intent, Inspect (invar sig/map), Constraints |
| SPECIFY | Define boundaries | @pre/@post, Design decomposition, Doctests |
| BUILD | Write code | Implement leaves, Compose |
| VALIDATE | Confirm correctness | invar guard, Review Gate, Reflect |

**Key:** Inspect before Contract. Depth varies naturally. Iterate when needed.

**Review Gate:** When Guard triggers `review_suggested` (escape hatches ≥3, security paths, low coverage), invoke `/review` before completion.

## Visible Workflow (DX-30)

For complex tasks (3+ functions), show 3 checkpoints in TodoList:

```
□ [UNDERSTAND] Task description, codebase context, constraints
□ [SPECIFY] Contracts (@pre/@post) and design decomposition
□ [VALIDATE] Guard results, Review Gate if triggered, integration status
```

**BUILD is internal work** — not shown in TodoList.

**Show contracts before code.** Example:

```python
[SPECIFY] calculate_discount:
@pre(lambda price, rate: price > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_discount(price: float, rate: float) -> float: ...

[BUILD] Now coding...
```

**When to use:** New features (3+ functions), architectural changes, Core modifications.
**Skip for:** Single-line fixes, documentation, trivial refactoring.

## Task Completion

A task is complete only when ALL conditions are met:
- Check-In displayed: `✓ Check-In: guard PASS | top: <entry1>, <entry2>`
- Intent explicitly stated
- Contract written before implementation
- Final displayed: `✓ Final: guard PASS | <errors>, <warnings>`
- User requirement satisfied

**Missing any = Task incomplete.**

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
# DX-22: Doctest lines are always excluded from size calculations by default
```

---

*Protocol v4.0 — USBV workflow (DX-32) | [Guide](docs/INVAR-GUIDE.md) | [Examples](.invar/examples/)*
