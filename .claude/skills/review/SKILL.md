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
<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
<!-- Merge date: 2025-12-27 -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

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
<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
<!-- Merge date: 2025-12-27 -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

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
<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
<!-- Merge date: 2025-12-27 -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

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
<!--/invar:skill-->

<!--invar:extensions-->
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


<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->
<!--/invar:extensions-->


<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->
<!--/invar:extensions-->


<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->
<!--/invar:extensions-->
