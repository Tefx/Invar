# DX-63: Contracts-First Enforcement

**Status:** Draft
**Created:** 2024-12-28
**Category:** Workflow / Agent Behavior
**Related:** DX-51 (Phase Visibility), DX-54 (Context Management)

## Problem Statement

Agents consistently violate the USBV workflow by skipping the SPECIFY phase, writing implementations first and retrofitting contracts afterwards. This causes:

1. **Contracts become ceremony** — Added as afterthought, not design tool
2. **Missing contracts at scale** — 81 `missing_contract` errors in DX-61 implementation
3. **Lost design value** — Contracts don't constrain implementation, they document it

### Observed Failure Pattern (DX-61 Case Study)

```
Expected USBV:
  UNDERSTAND → SPECIFY → BUILD → VALIDATE
                  ↑
            Write contracts FIRST
            (they are the spec)

Actual behavior:
  UNDERSTAND → BUILD → (retrofit) SPECIFY → VALIDATE
                  ↑
            Write code FIRST
            (contracts become documentation)
```

### Evidence

| Metric | Expected | Actual |
|--------|----------|--------|
| Contract coverage at BUILD end | 80%+ | 0% |
| Files created without contracts | 0 | 8 |
| Missing contract errors | 0 | 81 |

### Root Causes

| Cause | Why It Happens |
|-------|----------------|
| **Prototype mindset** | "Get it working first, polish later" |
| **Batch creation** | Creating 8 files at once skips per-file SPECIFY |
| **AST complexity rationalization** | "I need to figure out the implementation first" |
| **Doctest as substitute** | Treating doctests as "good enough" specification |
| **Context loss on continuation** | Session continuation loses workflow anchor |

---

## Solution: SPECIFY Phase Gate

### Core Principle

Make SPECIFY phase **visible and gated** — agent cannot proceed to BUILD until contracts are written and shown.

### Proposed Mechanism

```
Current USBV (no enforcement):
┌─────────────────────────────────────┐
│ SPECIFY phase                       │
│ ├── "Design the contracts"          │  ← Implicit, easily skipped
│ └── No visible checkpoint           │
└─────────────────────────────────────┘
         ↓
    Agent jumps to BUILD

Proposed USBV (gated):
┌─────────────────────────────────────┐
│ SPECIFY phase                       │
│ ├── Write @pre/@post in code        │
│ ├── Show contracts in response      │  ← VISIBLE
│ └── Mark TODO complete              │  ← GATED
└─────────────────────────────────────┘
         ↓
    Only then proceed to BUILD
```

---

## Implementation

### Layer 1: SKILL.md Enforcement

Add to `/develop` skill SPECIFY section:

```markdown
## SPECIFY Phase Requirements

Before proceeding to BUILD, you MUST:

1. **Write contracts first** — Add @pre/@post decorators to function signatures
2. **Show contracts visibly** — Display contract code block in response
3. **Mark SPECIFY complete** — TodoWrite status update

### Contract-First Template

For each function to implement:

```python
# Write THIS first (SPECIFY):
@pre(lambda x, y: len(x) > 0 and y >= 0)
@post(lambda result: result is not None)
def function_name(x: str, y: int) -> Result:
    """
    Brief description.

    @pre: x non-empty, y non-negative
    @post: always returns valid Result
    """
    ...  # Implementation in BUILD phase
```

### Violation Check

Before writing any implementation code, ask:
- "Have I written the contracts for this function?"
- "Have I shown the contracts in my response?"

If NO → You are in BUILD without completing SPECIFY.
```

### Layer 2: TodoWrite Enforcement

Require explicit SPECIFY task in TodoList:

```python
# Current (allows skipping):
todos = [
    {"content": "Implement feature X", "status": "in_progress", ...}
]

# Proposed (explicit phase):
todos = [
    {"content": "SPECIFY: Write contracts for feature X", "status": "pending", ...},
    {"content": "BUILD: Implement feature X", "status": "pending", ...}
]
```

### Layer 3: Guard Pre-Check (Optional)

Add `--contracts-only` mode to guard:

```bash
# Before BUILD phase, run contracts check
invar guard --contracts-only src/new_module.py

# Output:
# ✓ 5 functions have contracts
# ✗ 0 functions missing contracts
# Ready for BUILD phase
```

---

## Visible Workflow Change

### Current Phase Header

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Proposed Phase Header (with gate)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
   Gate: Show contracts before BUILD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Contracts for this phase:

```python
@pre(lambda self, tree, file_path: len(file_path) > 0)
@post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
    ...
```

✓ Contracts shown. Proceeding to BUILD.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Contract coverage at BUILD end | 0% | 80%+ |
| SPECIFY phase skipped | Frequent | Never |
| Retrofit contracts needed | 81 | 0 |
| Contract quality (semantic value) | Low | High |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Overhead for simple tasks | Skip gate for single-function changes |
| Contracts hard to write upfront | Allow `@post(lambda result: True)` placeholder with TODO |
| Agent ignores gate anyway | Add hook check (DX-57 extension) |

---

## Dependencies

- **DX-51** — Phase visibility (provides header format)
- **DX-54** — Context management (provides workflow refresh)
- **DX-57** — Hooks (optional enforcement layer)

---

## Open Questions

1. Should we require contracts before EVERY function, or only public interfaces?
2. Should placeholder contracts (`@post(lambda: True)`) be allowed as "TODO"?
3. How to handle Protocol classes (abstract methods with no implementation)?

---

## Implementation Priority

**Priority:** High
**Effort:** Medium
**Value:** High (prevents systemic workflow violations)

This proposal addresses a fundamental workflow compliance issue observed during DX-61 implementation. Without enforcement, agents consistently optimize for speed over specification quality.
