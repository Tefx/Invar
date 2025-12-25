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

> **"Trade structure for safety."** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

**Design:** Agent-Native. Protocol optimized for AI agent consumption.

**Smart Guard:** `invar guard` runs static analysis + doctests + property tests automatically.

## The Six Laws

| Law | Principle |
|-----|-----------|
| **1. Separation** | Pure logic (Core) and I/O (Shell) must be physically separate |
| **2. Contract Complete** | Define COMPLETE boundaries before implementation |
| **3. Context Economy** | Read map → signatures → implementation (only if needed) |
| **4. Decompose First** | Break complex tasks into sub-functions before implementing |
| **5. Verify Reflectively** | If fail: Reflect (why?) → Fix → Verify again |
| **6. Integrate Fully** | Verify all feature paths connect; local ≠ global correctness |

## Core/Shell Architecture

| Zone | Location | Must Have | Example |
|------|----------|-----------|---------|
| **Core** | `src/*/core/` | `@pre`/`@post` contracts | Pure calculations |
| **Shell** | `src/*/shell/` | `Result[T, E]` return type | File I/O, network |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`

## Commands

```bash
invar guard              # Full verification (default)
invar guard --changed    # Modified files only
invar sig <file>         # Function signatures + contracts
invar map --top 10       # Entry points by reference count
```

## Check-In / Final

**First message:**
```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

**Last message (implementation tasks):**
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

## Size Limits

| Limit | Value |
|-------|-------|
| File | 500 lines |
| Function | 50 lines |

## Workflow Sections

Detailed instructions for each phase:

| Section | Purpose |
|---------|---------|
| [sections/investigate.md](sections/investigate.md) | Exploration, no code changes |
| [sections/propose.md](sections/propose.md) | Decision facilitation |
| [sections/develop.md](sections/develop.md) | USBV implementation workflow |
| [sections/review.md](sections/review.md) | Adversarial review, fix loop |
| [sections/reference.md](sections/reference.md) | Contracts, markers, config |

## Installation

```bash
pip install invar-tools     # Dev tools (guard, sig, map)
pip install invar-runtime   # Runtime contracts (@pre, @post)
```

---

*Protocol v5.0 — Modular sections for workflow-based phase separation (DX-35/36).*
