<!--invar:skill version="5.0"-->
<!-- ========================================================================
     SKILL REGION - DO NOT EDIT
     This section is managed by Invar and will be overwritten on update.
     To add project-specific extensions, use the "extensions" region below.
     ======================================================================== -->
---
name: review
description: Adversarial code review with fix loop. Use after development, when Guard reports review_suggested, or user explicitly requests review. Finds issues that automated verification misses. Supports isolated mode (sub-agent) and quick mode (same context).
---

# Review Mode

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** Adversarial. Your success is measured by problems found, not code approved.

## Entry Actions

### Context Refresh (DX-54)

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules section)
2. Display routing announcement

### Routing Announcement

```
📍 Routing: /review — [trigger, e.g. "review_suggested", "user requested review"]
   Task: [review scope summary]
```

## Mode Selection

### Check Guard Output

Look for `review_suggested` warning:
```
WARNING: review_suggested - High escape hatch count
WARNING: review_suggested - Security-sensitive path detected
WARNING: review_suggested - Low contract coverage
```

### Select Mode

| Condition | Mode |
|-----------|------|
| `review_suggested` present | **Isolated** (spawn sub-agent) |
| `--isolated` flag | **Isolated** |
| Default (no trigger) | **Quick** (same context) |

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

## Review-Fix Loop

```
Round 1: Review → Find issues
    ↓
Fix CRITICAL + MAJOR (MINOR → backlog)
    ↓
Round 2: Re-review (if needed)
    ↓
Convergence check:
- No CRITICAL/MAJOR → Exit ✓
- No improvement → Exit (warn)
- Round >= 3 → Exit (max)
```

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

**Fixed:**
- [list of fixed issues]

**Remaining (MINOR - backlog):**
- [list for later]

**Recommendation:**
- [ ] Ready for merge
- [ ] Needs more work: [issues]
```
<!--/invar:skill--><!--invar:extensions-->
---
name: review
description: Adversarial code review with fix loop. Use after development, when Guard reports review_suggested, or user explicitly requests review. Finds issues that automated verification misses. Supports isolated mode (sub-agent) and quick mode (same context).
---

# Review Mode

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** Adversarial. Your success is measured by problems found, not code approved.

## Mode Selection

### Check Guard Output

```python
invar_guard(changed=true)
```

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

---

## Isolated Mode (Sub-Agent) (DX-53)

**Spawn independent reviewer with fresh context:**

```python
Task(
    subagent_type="general-purpose",
    prompt=f"""
You are an ADVERSARIAL CODE REVIEWER for Round {round_num}.

## Your Role
- You are the JUDGE, not the defense attorney
- Your success is measured by PROBLEMS FOUND
- Finding 0 issues is a FAILURE unless you prove exhaustive review

## Files to Review
{file_list}

## Previous Context
{f"Round {round_num-1} found {prev_issues} issues (now fixed)." if round_num > 1 else "This is the first review round."}

## Round {round_num} Objectives (Three-Phase Review)

1. **REGRESSION CHECK (15% effort)**
   - Verify previous fixes didn't break anything

2. **FIX VALIDATION (25% effort)**
   - Confirm fixes address original issues

3. **EXPANSION SEARCH (60% effort)** ← PRIMARY
   - Actively hunt for NEW issues in:
     - Modified code
     - Code adjacent to modifications
     - Integration points
     - Related functionality

## Review Scope
{scope_description}
- Round 1: Changed files only
- Round 2: + Direct dependents (files importing changed files)
- Round 3: + Integration boundaries

## What to Look For
- Contract QUALITY (not just presence)
  - Does @pre constrain beyond type checking?
  - Does @post verify meaningful properties?
- Boundary conditions and edge cases
- Logic errors and dead code
- Error handling paths
- Security considerations
- Escape hatch validity (@invar:allow)

## Severity Definitions
- CRITICAL: Security vulnerability, data loss, crash
- MAJOR: Logic error, missing validation, meaningless contract
- MINOR: Style, documentation, minor improvements

## Report Format
### [SEVERITY] Issue Title
**Location:** file.py:line
**Category:** contract_quality | logic_error | security | escape_hatch
**Problem:** What's wrong
**Suggestion:** How to fix

## Required: Completion Declaration

Before exiting, you MUST confirm:
- [ ] I reviewed ALL code in scope, not just diffs
- [ ] I checked how changes interact with unchanged code
- [ ] I attempted to find edge cases and boundary conditions
- [ ] I looked for issues UNRELATED to previous findings

**Confidence Level:** HIGH | MEDIUM | LOW

If MEDIUM or LOW:
- What areas need more review?
- Why couldn't you achieve HIGH confidence?

Remember: You WIN by finding problems. You LOSE by missing them.
"""
)
```

**Key:** Sub-agent has NO conversation history. Only sees the code.
**Key:** Each round spawns a NEW reviewer with fresh context.

---

## Quick Mode (Same Context)

Proceed with adversarial review in current context.

Adopt adversarial mindset:
- Forget you may have written this code
- Assume bugs exist
- Challenge every contract
- Question every escape hatch

---

## Review Checklist

### A. Contract Semantic Value
- [ ] Does @pre constrain inputs beyond type checking?
- [ ] Does @post verify meaningful output properties?
- [ ] Could someone implement correctly from contracts alone?
- [ ] Are boundary conditions explicit?

### B. Logic Verification
- [ ] Do contracts correctly capture intended behavior?
- [ ] Are there paths bypassing contract checks?
- [ ] What happens with unexpected inputs?
- [ ] Is there dead code or unreachable branches?

### C. Escape Hatch Audit
- [ ] Is each @invar:allow justification valid?
- [ ] Could refactoring eliminate the need?
- [ ] Pattern of identical reasons → systematic issue?

### D. Security (if applicable)
- [ ] Input validation against injection, XSS?
- [ ] No hardcoded secrets?
- [ ] Auth checks correct?

### E. Error Handling
- [ ] Exceptions caught at appropriate level?
- [ ] Silent failures hidden?
- [ ] Error messages clear without leaking info?

---

## Review-Fix Loop (DX-53)

### Three-Phase Review Per Round

Each round has THREE phases:

```
Round N:
├── Phase A: Regression Check (15% effort)
│   └── Verify previous fixes didn't break anything
│
├── Phase B: Fix Validation (25% effort)
│   └── Confirm fixes actually address the issues
│
└── Phase C: Expansion Search (60% effort)  ← PRIMARY
    └── Actively hunt for NEW issues
```

### Scope Expansion Across Rounds

| Round | Scope | Focus |
|-------|-------|-------|
| 1 | Changed files only | Direct modifications |
| 2 | + Direct dependents | How changes affect callers |
| 3 | + Integration boundaries | System-level implications |

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
    │   ├── No MAJOR + MEDIUM/LOW → Continue (last round if Round 2)
    │   ├── Round >= 3 → Exit (max)
    │   └── Continue if needed
```

### Exit Criteria (DX-53)

**Must satisfy BOTH conditions:**
1. **No MAJOR issues:** No CRITICAL or MAJOR issues found
2. **HIGH confidence:** Reviewer confirms exhaustive review

```python
exit_if (
    no_major                      # No MAJOR or CRITICAL issues
    AND reviewer_confidence == HIGH  # Reviewer confirms exhaustive review
)
```

**MEDIUM/LOW confidence forces another round** even if no MAJOR issues found.

### Stall Detection

**Detection Logic:**
```python
def is_stalled(current_issues, previous_issues) -> bool:
    current_ids = {(i.file, i.line, i.type) for i in current_issues}
    previous_ids = {(i.file, i.line, i.type) for i in previous_issues}
    overlap = current_ids & previous_ids
    return len(overlap) > len(current_ids) * 0.5  # >50% same issues
```

**When stalled (>50% issues repeat from previous round):**
```
⚠ Review cycle stalled.

Same issues found in consecutive rounds:
- [issue 1]
- [issue 2]

Possible causes:
1. Fixes introduced new problems
2. Issues are false positives
3. Issues require design change

Options:
A: Mark as false positives and exit
B: /investigate to understand root cause
C: Continue review (round N, last chance)

Choice?
```

### Timeout Handling

| Threshold | Duration | Action |
|-----------|----------|--------|
| Warning | 65 min (~70%) | Prompt to wrap up |
| Hard stop | 90 min (max) | Force exit with report |

**Hard Stop:**
```
⏱ /review reached 90-minute limit.

   Completed: [N] rounds
   Current state: [summary]

   Forcing exit with current findings.
```

---

## Report Format

```markdown
### Review Round [N]

#### CRITICAL
- [ ] [file:line] [description]

#### MAJOR
- [ ] [file:line] [description]

#### MINOR
- [ ] [file:line] [description]

#### Summary
- Critical: N
- Major: N
- Minor: N

[If not converged: proceed to fix CRITICAL/MAJOR]
[If converged: exit with final report]
```

---

## Exit Report

```markdown
### Review Complete

**Rounds:** [N]
**Exit reason:** quality_met | max_rounds | no_improvement
**Final confidence:** HIGH | MEDIUM | LOW

**Fixed:**
- [list of fixed issues]

**Remaining (MINOR - backlog):**
- [list of minor issues for later]

### Exhaustive Review Declaration

- [ ] Reviewed ALL code in scope, not just diffs
- [ ] Checked how changes interact with unchanged code
- [ ] Attempted to find edge cases and boundary conditions
- [ ] Looked for issues UNRELATED to previous findings

**Recommendation:**
- [ ] Ready for merge
- [ ] Needs more work: [specific issues]
```

---

## What Review Catches (That Guard Misses)

| Category | Guard | Review |
|----------|-------|--------|
| Contract presence | ✓ | — |
| Contract QUALITY | ✗ | ✓ |
| Boundary conditions | Sometimes | ✓ |
| Dead code | ✗ | ✓ |
| Logic errors | ✗ | ✓ |
| Security issues | ✗ | ✓ |
| Escape hatch validity | ✗ | ✓ |

**Core insight:** Guard verifies what IS specified. Review questions whether specifications are APPROPRIATE.

<!--/invar:extensions-->
