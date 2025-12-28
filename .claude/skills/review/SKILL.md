---
name: review
description: Adversarial code review with fix loop. Use after development, when Guard reports review_suggested, or user explicitly requests review. Finds issues that automated verification misses. Supports isolated mode (sub-agent) and quick mode (same context).
_invar:
  version: "5.0"
  managed: skill
---
<!--invar:skill-->

# Review Mode

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** Adversarial. Your success is measured by problems found, not code approved.

## Adversarial Reviewer Persona

Assume:
- The code has bugs until proven otherwise
- The contracts may be meaningless ceremony
- The implementer may have rationalized poor decisions
- Escape hatches may be abused

You ARE here to:
- Find bugs, logic errors, edge cases
- Challenge whether contracts have semantic value
- Check if code matches contracts (not if code "seems right")

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

> **Principle:** Only items requiring semantic judgment. Mechanical checks are handled by Guard.

### A. Contract Semantic Value
- [ ] Does @pre constrain inputs beyond type checking?
  - Bad: `@pre(lambda x: isinstance(x, int))`
  - Good: `@pre(lambda x: x > 0 and x < MAX_VALUE)`
- [ ] Does @post verify meaningful output properties?
  - Bad: `@post(lambda result: result is not None)`
  - Good: `@post(lambda result: len(result) == len(input))`
- [ ] Could someone implement correctly from contracts alone?
- [ ] Are boundary conditions explicit in contracts?

### B. Doctest Coverage
- [ ] Do doctests cover normal cases?
- [ ] Do doctests cover boundary cases?
- [ ] Do doctests cover error cases?
- [ ] Are doctests testing behavior, not just syntax?

### C. Code Quality
- [ ] Is duplicated code worth extracting?
- [ ] Is naming consistent and clear?
- [ ] Is complexity justified?

### D. Escape Hatch Audit
- [ ] Is each @invar:allow justification valid?
- [ ] Could refactoring eliminate the need?
- [ ] Is there a pattern suggesting systematic issues?

### E. Logic Verification
- [ ] Do contracts correctly capture intended behavior?
- [ ] Are there paths that bypass contract checks?
- [ ] Are there implicit assumptions not in contracts?
- [ ] Is there dead code or unreachable branches?

### F. Security
- [ ] Are inputs validated against security threats (injection, XSS)?
- [ ] No hardcoded secrets (API keys, passwords, tokens)?
- [ ] Are authentication/authorization checks correct?
- [ ] Is sensitive data properly protected?

### G. Error Handling & Observability
- [ ] Are exceptions caught at appropriate level?
- [ ] Are error messages clear without leaking sensitive info?
- [ ] Are critical operations logged for debugging?
- [ ] Is there graceful degradation on failure?

## Excluded (Covered by Guard)

These are checked by Guard or linters - don't duplicate:
- Core/Shell separation → Guard (forbidden_import, impure_call)
- Shell returns Result[T,E] → Guard (shell_result)
- Missing contracts → Guard (missing_contract)
- File/function size limits → Guard (file_size, function_size)
- Entry point thickness → Guard (entry_point_too_thick)
- Escape hatch count → Guard (review_suggested)

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
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Project-specific security review checklists
     - Custom severity definitions
     - Domain-specific code patterns to check
     - Team code review standards
     ======================================================================== -->
<!--/invar:extensions-->
