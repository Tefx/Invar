#!/bin/bash
# Invar UserPromptSubmit Hook
# Protocol: v5.0 | Generated: 2025-12-30
# DX-57: Protocol refresh with full INVAR.md injection

USER_MESSAGE="$1"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Use session-specific state
STATE_DIR="${CLAUDE_STATE_DIR:-/tmp/invar_hooks_$(id -u)}"
mkdir -p "$STATE_DIR" 2>/dev/null

# Session detection: Reset if state is stale (>4 hours)
SESSION_MARKER="$STATE_DIR/session_start"
MAX_AGE_SECONDS=14400  # 4 hours

reset_session() {
  rm -f "$STATE_DIR/msg_count" "$STATE_DIR/changes" 2>/dev/null
  date +%s > "$SESSION_MARKER"
}

if [[ -f "$SESSION_MARKER" ]]; then
  MARKER_TIME=$(cat "$SESSION_MARKER" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  AGE=$((NOW - MARKER_TIME))
  if [[ $AGE -gt $MAX_AGE_SECONDS ]]; then
    reset_session
  fi
else
  reset_session
fi

COUNT_FILE="$STATE_DIR/msg_count"
COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNT_FILE"

# ============================================
# Keyword triggers (independent of count)
# ============================================

# pytest intent → immediate correction
if echo "$USER_MESSAGE" | grep -qiE "run.*pytest|pytest.*test|用.*pytest"; then
  echo "<system-reminder>Use invar_guard, not pytest.</system-reminder>"
fi

# Implementation intent → workflow reminder (after warmup)
if [[ $COUNT -gt 3 ]]; then
  if echo "$USER_MESSAGE" | grep -qiE "^implement|^fix|^add|^实现|^修复|^添加"; then
    echo "<system-reminder>USBV: Specify contracts → Build → Validate</system-reminder>"
  fi
fi

# ============================================
# Progressive refresh based on message count
# ============================================

# Message 15: Lightweight checkpoint
if [[ $COUNT -eq 15 ]]; then
  echo "<system-reminder>"
  echo "Checkpoint: guard=verify, sig=contracts, USBV workflow."
  echo "</system-reminder>"
fi

# Message 25+: Full INVAR.md injection every 10 messages
# SSOT: Inject entire protocol to ensure no content drift
if [[ $COUNT -ge 25 && $((COUNT % 10)) -eq 0 ]]; then
  echo "<system-reminder>"
  echo "=== Protocol Refresh (message $COUNT) ==="
  echo ""
  cat << 'INVAR_EOF'
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

### Decision Tree: Core vs Shell

```
Does this function...
│
├─ Read or write files? ──────────────────→ Shell
├─ Make network requests? ─────────────────→ Shell
├─ Access current time (datetime.now)? ────→ Shell OR inject as parameter
├─ Generate random values? ────────────────→ Shell OR inject as parameter
├─ Print to console? ──────────────────────→ Shell (return data, Shell logs)
├─ Access environment variables? ──────────→ Shell
│
└─ None of the above? ─────────────────────→ Core
```

**Pattern:** Inject impure values as parameters:
```python
# Core: receives 'now' as parameter (pure)
def is_expired(expiry: datetime, now: datetime) -> bool:
    return now > expiry

# Shell calls with actual time
expired = is_expired(token.expiry, datetime.now())
```

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

## Contract Rules

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

## Check-In (Required)

Your first message MUST display:

```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

Actions:
1. Read `.invar/context.md` (Key Rules + Current State + Lessons Learned)
2. Show one-line status

**Do NOT execute guard or map at Check-In.**
Guard is for VALIDATE phase and Final only.

This is your sign-in. The user sees it immediately.
No visible check-in = Session not started.

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
- Check-In displayed: `✓ Check-In: [project] | [branch] | [clean/dirty]`
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

**Valid rule names for @invar:allow:**
- `shell_result` — Shell function without Result return type
- `entry_point_too_thick` — Entry point exceeds 15 lines
- `forbidden_import` — I/O import in Core (rare, justify carefully)

Run `invar rules` for complete rule catalog with hints.

## Commands

```bash
invar guard              # Full: static + doctests + CrossHair + Hypothesis
invar guard --static     # Static only (quick debug, ~0.5s)
invar guard --changed    # Modified files only
invar guard --coverage   # Collect branch coverage
invar guard -c           # Contract coverage only (DX-63)
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules with detection/hints (JSON)
```

## Configuration

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]    # Default: ["src/core", "core"]
shell_paths = ["src/myapp/shell"]  # Default: ["src/shell", "shell"]
max_file_lines = 500               # Default: 500 (warning at 80%)
max_function_lines = 50            # Default: 50
# Doctest lines are excluded from size calculations
```

## Troubleshooting

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

---

*Protocol v5.0 — USBV workflow (DX-32) | [Examples](.invar/examples/)*

INVAR_EOF
  echo "</system-reminder>"
fi
