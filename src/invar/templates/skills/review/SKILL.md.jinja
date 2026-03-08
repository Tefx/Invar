---
name: review
description: Adversarial code review. Code is GUILTY until proven INNOCENT. Every round spawns isolated subagent reviewing FULL scope.
_invar:
  version: "7.0"
  managed: skill
---
<!--invar:skill-->

# Review Skill (Adversarial)

**REJECTION-FIRST mindset:** Assume defects exist until proven otherwise.

## Mandatory Rules (MUST follow, NO exceptions)

1. **EVERY round MUST spawn isolated subagent** (Task tool with model=opus)
2. **EVERY round reviews FULL scope** (all files, not just changes)
3. **Code is GUILTY until proven INNOCENT**
4. **NO user confirmation between rounds** — just do it
5. **MAX_ROUNDS = 5**

**Violation = Review Invalid.** If you skip subagent or review only changes, the review is worthless.

---

## Scope Classification (DX-75)

**Before starting, classify the scope:**

| Classification | Criteria | Strategy |
|----------------|----------|----------|
| **SMALL** | <5 files AND <1500 lines | THOROUGH (no enumeration) |
| **MEDIUM** | 5-10 files OR 1500-5000 lines | HYBRID (enum + open) |
| **LARGE** | >10 files OR >5000 lines | CHUNKED (parallel subagents) |

**Why different strategies?**
- SMALL: Pre-enumeration causes "checklist mentality" — you only verify listed items, miss variants
- LARGE: Without enumeration, attention drifts — later files get less scrutiny

---

## Strategy: THOROUGH (SMALL scope)

```
┌─────────────────────────────────────────────────────────────┐
│  THOROUGH STRATEGY (for SMALL scope)                        │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  ⚠️ DO NOT pre-enumerate issues or patterns                 │
│  ⚠️ DO NOT use grep/sig to "find issues first"              │
│                                                             │
│  Instead:                                                   │
│  1. Read each file COMPLETELY, line by line                 │
│  2. Apply checklist A-G as you read                         │
│  3. Trust your judgment to find issues                      │
│  4. Look for VARIANTS and EDGE CASES                        │
│                                                             │
│  Why: Pre-enumeration narrows focus to known patterns.      │
│  Small scope = you CAN read everything thoroughly.          │
│  This finds issues that pattern matching misses.            │
└─────────────────────────────────────────────────────────────┘
```

## Strategy: HYBRID (MEDIUM scope)

```
┌─────────────────────────────────────────────────────────────┐
│  HYBRID STRATEGY (for MEDIUM scope)                         │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Phase 0: ENUMERATE (Main Agent)                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Use grep/invar_sig to find:                        │   │
│  │  - All @pre/@post contracts                         │   │
│  │  - All @invar:allow escape hatches                  │   │
│  │  - Hardcoded strings (secrets?)                     │   │
│  │  - subprocess/exec/eval calls                       │   │
│  │  - bare except clauses                              │   │
│  │  Create issue_map with file:line for each           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Phase 1: GUIDED REVIEW (Isolated Subagent)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Pass issue_map to subagent                         │   │
│  │  Subagent verifies each item                        │   │
│  │  Reports: "Checked N/M items from issue_map"        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Phase 2: OPEN DISCOVERY (Same Subagent)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  "Now forget the issue_map.                         │   │
│  │   Look for issues NOT in the map:                   │   │
│  │   - Variants of listed patterns                     │   │
│  │   - Logic errors                                    │   │
│  │   - Edge cases"                                     │   │
│  │  Reports: "Found N additional issues"               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Strategy: CHUNKED (LARGE scope)

```
┌─────────────────────────────────────────────────────────────┐
│  CHUNKED STRATEGY (for LARGE scope)                         │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  1. Split files into chunks of ~3-5 files each              │
│                                                             │
│  2. For each chunk (can be parallel):                       │
│     - Spawn isolated subagent                               │
│     - Use HYBRID strategy within chunk                      │
│                                                             │
│  3. Cross-chunk analysis:                                   │
│     - Check cross-file dependencies                         │
│     - Check API consistency                                 │
│                                                             │
│  4. Merge all findings, deduplicate                         │
│                                                             │
│  Why: Prevents "attention fatigue" on file 8+ of 15.        │
│  Each chunk gets fresh attention.                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2-Step Loop (MANDATORY workflow)

```
┌─────────────────────────────────────────────────────────────┐
│  Round N:                                                   │
│                                                             │
│  1. REVIEWER [Subagent] ─────────────────────────────────── │
│     • Spawn NEW isolated agent (Task tool)                  │
│     • Use strategy based on scope classification            │
│     • Review ALL files in scope (full checklist A-G)        │
│     • Return: issues[] or APPROVED                          │
│                                                             │
│  2. FIXER [Main Agent] ──────────────────────────────────── │
│     • Fix CRITICAL/MAJOR issues with CODE                   │
│     • Run invar_guard()                                     │
│     • Cannot declare quality_met                            │
│                                                             │
│  → Loop until: APPROVED OR max_rounds OR no_progress        │
└─────────────────────────────────────────────────────────────┘
```

**Why new subagent each round?**
- Main agent has context contamination from fixing
- "Fresh eyes" impossible in same context
- Round 2+ drifts to "verify my fixes" not "find problems"

---

## Review Checklist (apply to ALL files)

> **Principle:** Only items requiring semantic judgment. Mechanical checks handled by Guard.

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

- [ ] Do doctests cover normal, boundary, and error cases?
- [ ] Are doctests testing behavior, not just syntax?

### C. Code Quality

- [ ] Is duplicated code worth extracting?
- [ ] Is naming consistent and clear?
- [ ] Is complexity justified?

### D. Escape Hatch Audit

- [ ] Is each @invar:allow justification valid?
- [ ] Could refactoring eliminate the need?

### E. Logic Verification

- [ ] Do contracts correctly capture intended behavior?
- [ ] Are there paths that bypass contract checks?
- [ ] Are there implicit assumptions not in contracts?

### F. Security

- [ ] Are inputs validated against security threats (injection, XSS)?
- [ ] No hardcoded secrets (API keys, passwords, tokens)?
- [ ] Are authentication/authorization checks correct?

### G. Error Handling

- [ ] Are exceptions caught at appropriate level?
- [ ] Are error messages clear without leaking sensitive info?
- [ ] Is there graceful degradation on failure?

---

## Subagent Prompt Templates

### THOROUGH (SMALL scope)

```
You are an independent Adversarial Code Reviewer.

RULES:
1. Code is GUILTY until proven INNOCENT
2. You did NOT write this code — no emotional attachment
3. Find reasons to REJECT, not accept
4. Be specific: file:line + concrete fix

STRATEGY: THOROUGH READING
- Read each file COMPLETELY, line by line
- DO NOT pre-scan for patterns — just READ
- Look for VARIANTS and EDGE CASES
- Trust your judgment

SCOPE: [list all files]

Apply checklist A-G to each file.

OUTPUT FORMAT:
## Verdict: APPROVED | NEEDS WORK | REJECTED
## Critical Issues (must fix)
| ID | File:Line | Issue | Fix |
## Major Issues (should fix)
| ID | File:Line | Issue | Fix |
## Minor Issues (backlog)
| ID | File:Line | Issue | Fix |
```

### HYBRID (MEDIUM scope)

```
You are an independent Adversarial Code Reviewer.

RULES:
1. Code is GUILTY until proven INNOCENT
2. You did NOT write this code — no emotional attachment
3. Find reasons to REJECT, not accept
4. Be specific: file:line + concrete fix

STRATEGY: HYBRID (two passes)

PASS 1 - GUIDED:
Using this issue_map, verify each potential issue:
[issue_map from Phase 0]

Report: "Verified X/Y items from issue_map"

PASS 2 - OPEN DISCOVERY:
Now FORGET the issue_map. Read the code fresh.
Look for issues NOT in the map:
- Variants of listed patterns
- Logic errors
- Edge cases

Report: "Found N additional issues not in issue_map"

SCOPE: [list all files]

OUTPUT FORMAT:
## Verdict: APPROVED | NEEDS WORK | REJECTED
## From Issue Map (Pass 1)
| ID | File:Line | Issue | Fix |
## Additional Findings (Pass 2)
| ID | File:Line | Issue | Fix |
```

---

## Exit Conditions

| Condition | Exit Reason | Result |
|-----------|-------------|--------|
| Subagent returns APPROVED | `quality_met` | Ready for merge |
| round >= 5 | `max_rounds` | Manual review needed |
| Same issues 2 rounds | `no_improvement` | Architectural issue |

---

## Exit Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Scope:** SMALL | MEDIUM | LARGE
**Strategy:** THOROUGH | HYBRID | CHUNKED
**Exit:** quality_met | max_rounds | no_improvement
**Rounds:** N / 5
**Guard:** PASS | FAIL

## Issues Table
| Issue | Severity | Round | Status | Evidence |

## Round Summary
| Round | Found | Fixed |

✓ Final: guard PASS | X errors, Y warnings
```

---

## Scope Boundaries

**IS for:** Finding bugs, verifying contracts, security review
**NOT for:** New features → /develop | Understanding → /investigate

## Excluded (Covered by Guard)

Don't duplicate mechanical checks:
- Core/Shell separation → Guard
- Missing contracts → Guard
- File/function size → Guard

<!--/invar:skill--><!--invar:extensions-->
<!-- User extensions preserved on update -->
<!--/invar:extensions-->
