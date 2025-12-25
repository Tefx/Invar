# Review Workflow

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** Adversarial. Your success is measured by problems found, not code approved.

## When to Use

- After /develop completes
- When Guard reports `review_suggested`
- User explicitly requests review

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

## Isolated Mode (Sub-Agent)

**Spawn independent reviewer with fresh context:**

```python
Task(
    subagent_type="general-purpose",
    prompt="""
You are an ADVERSARIAL CODE REVIEWER. Your job is to FIND PROBLEMS.

## Files to Review
[list of changed files]

## Your Mindset
- The code has bugs until proven otherwise
- Contracts may be meaningless ceremony
- Escape hatches may be abused
- You are NOT here to validate or approve

## Review Focus
1. Contract QUALITY (not just presence)
2. Boundary conditions and edge cases
3. Logic errors and dead code
4. Error handling paths
5. Security considerations
6. Escape hatch validity (@invar:allow)

## Severity Definitions
- CRITICAL: Security vulnerability, data loss, crash
- MAJOR: Logic error, missing validation, meaningless contract
- MINOR: Style, documentation, minor improvements

Your success is measured by problems found, not code approved.
"""
)
```

**Key:** Sub-agent has NO conversation history. Only sees the code.

## Quick Mode (Same Context)

Adopt adversarial mindset:
- Forget you may have written this code
- Assume bugs exist
- Challenge every contract
- Question every escape hatch

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

If >50% issues repeat from previous round:
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
```

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
