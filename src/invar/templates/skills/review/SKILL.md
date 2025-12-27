---
name: review
description: Adversarial code review with fix loop. Use after development, when Guard reports review_suggested, or user explicitly requests review. Finds issues that automated verification misses.
---

# Review Mode

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** Adversarial. Your success is measured by problems found, not code approved.

## Mode Selection

### Check Guard Output

Look for `review_suggested` warning:
```
WARNING: review_suggested - High escape hatch count
WARNING: review_suggested - Security-sensitive path detected
WARNING: review_suggested - Low contract coverage
```

### Select Mode (DX-53)

| Condition | Mode | Reason |
|-----------|------|--------|
| Default | **Isolated** | Eliminates confirmation bias |
| `--quick` flag | **Quick** | User opts for speed |
| Trivial change (<10 lines) | **Quick** | Overhead not justified |

**Why Isolated is Default:** The cost of false negatives (missed bugs) exceeds the cost of sub-agent spawn.

## Review Checklist

### A. Contract Semantic Value
- [ ] Does @pre constrain inputs beyond type checking?
- [ ] Does @post verify meaningful output properties?
- [ ] Could someone implement correctly from contracts alone?

### B. Logic Verification
- [ ] Do contracts correctly capture intended behavior?
- [ ] Are there paths bypassing contract checks?
- [ ] Is there dead code or unreachable branches?

### C. Escape Hatch Audit
- [ ] Is each @invar:allow justification valid?
- [ ] Could refactoring eliminate the need?

### D. Security (if applicable)
- [ ] Input validation against injection, XSS?
- [ ] No hardcoded secrets?

## Review-Fix Loop (DX-53)

### Three-Phase Review Per Round

Each round has THREE phases, not one:

```
Round N:
├── Phase A: Regression Check (15% effort)
│   └── Verify previous fixes didn't break anything
│
├── Phase B: Fix Validation (25% effort)
│   └── Confirm fixes actually address the issues
│
└── Phase C: Expansion Search (60% effort)  ← PRIMARY
    └── Actively hunt for NEW issues in:
        - Modified code
        - Code adjacent to modifications
        - Integration points
```

### Scope Expansion Across Rounds

```
Round 1: Changed files only
         └── Focus: Direct modifications

Round 2: Changed files + Direct dependents
         └── Focus: How changes affect callers

Round 3: Integration boundaries
         └── Focus: System-level implications
```

### Convergence Logic

```
Round 1:
    │
    ├── Spawn Isolated Reviewer (sub-agent)
    │   └── Prompt: "Find ALL issues. Success = problems found."
    │
    ├── Reviewer returns issues + confidence level
    │
    ├── Exit check:
    │   ├── NO MAJOR + HIGH confidence → Exit ✓
    │   ├── NO MAJOR + MEDIUM/LOW confidence → Continue (expand scope)
    │   └── MAJOR found → Fix, continue
    │
Round 2+:
    │
    ├── Spawn NEW Isolated Reviewer (fresh context!)
    │
    ├── Convergence check:
    │   ├── No MAJOR + HIGH confidence → Exit ✓
    │   ├── Round >= 3 → Exit (max)
    │   └── Continue if needed
```

**Exit Criteria:** `no_major AND confidence == HIGH`

## Severity Definitions

| Level | Meaning | Examples |
|-------|---------|----------|
| CRITICAL | Security, data loss, crash | SQL injection, unhandled null |
| MAJOR | Logic error, missing validation | Wrong calculation, no bounds |
| MINOR | Style, documentation | Naming, missing docstring |

## Exit Report

```markdown
### Review Complete

**Rounds:** [N]
**Exit reason:** quality_met | max_rounds | no_improvement
**Final confidence:** HIGH | MEDIUM | LOW

**Fixed:**
- [list of fixed issues]

**Remaining (MINOR - backlog):**
- [list for later]

### Exhaustive Review Declaration

- [ ] Reviewed ALL code in scope, not just diffs
- [ ] Checked how changes interact with unchanged code
- [ ] Attempted to find edge cases and boundary conditions
- [ ] Looked for issues UNRELATED to previous findings

**Recommendation:**
- [ ] Ready for merge
- [ ] Needs more work: [issues]
```
