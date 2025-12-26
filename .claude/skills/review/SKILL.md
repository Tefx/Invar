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

### Routing Announcement

Before any workflow action, display:

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

### Select Mode

| Condition | Mode | Reason |
|-----------|------|--------|
| `review_suggested` present | **Isolated** | Eliminates confirmation bias |
| `--isolated` flag | **Isolated** | User override |
| No trigger, `--quick` flag | **Quick** | Faster, context preserved |
| Default (no trigger) | **Quick** | Routine review |

---

## Isolated Mode (Sub-Agent)

**Spawn independent reviewer with fresh context:**

```python
Task(
    subagent_type="general-purpose",
    prompt="""
You are an ADVERSARIAL CODE REVIEWER. Your job is to FIND PROBLEMS.

## Files to Review
[list of changed files or specified files]

## Your Mindset
- The code has bugs until proven otherwise
- Contracts may be meaningless ceremony
- Escape hatches may be abused
- You are NOT here to validate or approve

## Review Focus
1. Contract QUALITY (not just presence)
   - Does @pre constrain beyond type checking?
   - Does @post verify meaningful properties?
2. Boundary conditions and edge cases
3. Logic errors and dead code
4. Error handling paths
5. Security considerations
6. Escape hatch validity (@invar:allow)

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

Your success is measured by problems found, not code approved.
"""
)
```

**Key:** Sub-agent has NO conversation history. Only sees the code.

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

## Review-Fix Loop

```
Round 1: Review
    │
    ├── Issues found?
    │   ├── NO → Exit, report clean
    │   └── YES ↓
    │
    ├── Fix CRITICAL + MAJOR issues
    │   (MINOR → backlog for later)
    │
Round 2: Re-review (if needed)
    │
    ├── Convergence check:
    │   ├── No CRITICAL/MAJOR → Exit ✓
    │   ├── No improvement → Exit (warn)
    │   └── Round >= 3 → Exit (max reached)
    │
    └── Continue if needed
```

### Convergence Criteria

Exit when ANY condition met:
1. **Quality target:** No CRITICAL or MAJOR issues
2. **Max rounds:** 3 rounds completed
3. **No improvement:** Same or more issues as previous round

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

**Fixed:**
- [list of fixed issues]

**Remaining (MINOR - backlog):**
- [list of minor issues for later]

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
