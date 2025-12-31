---
name: review
description: Fault-finding code review with REJECTION-FIRST mindset. Code is GUILTY until proven INNOCENT. Two-step loop (Review→Fix) with full-scope review each round. Use after development, when Guard reports review_suggested, or user explicitly requests review.
_invar:
  version: "5.2"
  managed: skill
---
<!--invar:skill-->

# Review Mode (Fault-Finding with Auto-Loop)

> **Purpose:** Find problems that Guard, doctests, and property tests missed.
> **Mindset:** REJECTION-FIRST. Code is GUILTY until proven INNOCENT.
> **Success Metric:** Issues FOUND, not code approved. Zero issues = you failed to look hard enough.
> **Workflow:** Two-step loop: Review → Fix → Review → Fix → ... (full scope each round, no separate "verify" step).

## Scope Boundaries

**This skill IS for:**
- Finding bugs and logic errors in existing code
- Verifying contract semantic value
- Auditing escape hatches
- Security review

**This skill is NOT for:**
- Implementing new features → switch to `/develop`
- Understanding how code works → switch to `/investigate`
- Deciding on architecture → switch to `/propose`

**Drift detection:** If you're writing significant new code (not fixes) → STOP, you're in wrong skill.

## Auto-Loop Configuration

```
MAX_ROUNDS = 5          # Maximum review-fix cycles
AUTO_TRANSITION = true  # No human confirmation between roles
```

## Prime Directive: Reject Until Proven Correct

**You are the PROSECUTOR, not the defense attorney.**

| Trap | Reality Check |
|------|---------------|
| "Seems fine" | You failed to find the bug |
| "Makes sense" | You're rationalizing, not reviewing |
| "Edge case is unlikely" | Edge cases ARE bugs |
| "Comment explains it" | Comments don't fix code |
| "Assessed as acceptable" | "Assessed" ≠ "Fixed" |

## Role Separation (CRITICAL)

**You play TWO distinct roles that cycle AUTOMATICALLY:**

| Role | Allowed Actions | Forbidden |
|------|-----------------|-----------|
| **REVIEWER** | Find issues (full scope), declare quality_met | Write code, rationalize issues |
| **FIXER** | Implement fixes only | Declare quality_met, dismiss issues |

**Role Transition Markers (REQUIRED):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 REVIEWER [Round N] — Full scope review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 FIXER [Round N] — Implementing fixes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**NO separate "Verify" step.** After Fix, go directly to next round's Review.

## Quality Gate Authority

**ONLY the Reviewer role can declare `quality_met`.**

Before declaring exit:
1. Re-read EVERY issue found
2. For each issue, verify: "Is this ACTUALLY fixed, or did I rationalize it?"
3. Ask: "Would I accept this excuse from someone else's code?"

**Self-Check Questions:**
- Did I write code AND declare quality_met? → Role confusion detected
- Did I say "assessed" instead of "fixed"? → Rationalization detected
- Did any MAJOR become a comment instead of code? → Fix failed

## Fault-Finding Persona

Assume:
- The code has bugs until proven otherwise
- The contracts may be meaningless ceremony
- The implementer may have rationalized poor decisions
- Escape hatches may be abused
- **Your own fixes may introduce new bugs**

You ARE here to:
- Find bugs, logic errors, edge cases
- Challenge whether contracts have semantic value
- Check if code matches contracts (not if code "seems right")

## Fresh Eyes Mandate (Round 2+)

**For rounds after the first, you MUST adopt "fresh eyes" mindset:**

> "I am a different reviewer who has never seen this code or the previous fixes."

| Trap | Correction |
|------|------------|
| "I just fixed this" | Irrelevant. Review it like new code. |
| "This was fine last round" | Maybe you missed something. Check again. |
| "The fix looks correct" | That's FIXER thinking. Find what's WRONG. |

**Full scope means:**
1. Re-run the ENTIRE checklist (A through G)
2. Review ALL changed files, not just recent fixes
3. Check if fixes introduced NEW issues
4. Look for issues you missed in previous rounds

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

## Auto-Loop Workflow (NO HUMAN CONFIRMATION)

**The loop runs AUTOMATICALLY until exit condition is met.**

**Two-step cycle: Review → Fix → Review → Fix → ...**

```
┌─────────────────────────────────────────────────────────────────┐
│  START: round = 1, issues = []                                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🔍 REVIEWER [Round N] — Full Scope Review              │    │
│  │    1. Apply FULL checklist (A-G) to ENTIRE scope       │    │
│  │    2. Find ALL issues (don't stop at first)            │    │
│  │    3. Classify: CRITICAL / MAJOR / MINOR               │    │
│  │    4. Check previous fixes: CODE or just COMMENT?      │    │
│  │    5. Check if fixes introduced NEW issues             │    │
│  │    6. Update issues table                              │    │
│  │                                                         │    │
│  │    EXIT CHECK:                                          │    │
│  │    - IF no CRITICAL/MAJOR found → quality_met, EXIT    │    │
│  │    - IF round >= MAX_ROUNDS → max_rounds, EXIT         │    │
│  │    - IF no progress (same issues 2 rounds) → EXIT      │    │
│  │    - ELSE → AUTO-TRANSITION to FIXER                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         ↓ (automatic)                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🔧 FIXER [Round N]                                     │    │
│  │    1. Fix EACH CRITICAL/MAJOR issue with CODE          │    │
│  │    2. Run invar_guard() after fixes                    │    │
│  │    3. NO declaring quality_met (forbidden)             │    │
│  │    4. round++                                           │    │
│  │    5. AUTO-TRANSITION to REVIEWER [Round N+1]          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         ↓ (automatic, fresh eyes)               │
│                    [LOOP BACK TO REVIEWER]                      │
│                                                                 │
│  EXIT: Generate final report                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key change from v5.1:** No separate "Verify" step. Each round's Review is a
full-scope audit with the same rigor as Round 1. This prevents the "verification
mindset" trap where standards unconsciously lower after fixing.

## Loop State Tracking

**Maintain this state throughout the loop:**

```markdown
## Review State
- **Round:** N / MAX_ROUNDS
- **Role:** REVIEWER | FIXER
- **Issues Found:** [count]
- **Issues Fixed:** [count]
- **Guard Status:** PASS | FAIL
```

## Issues Table (Updated Each Round)

| Issue ID | Severity | Round Found | Round Fixed | Status | Evidence |
|----------|----------|-------------|-------------|--------|----------|
| MAJOR-1 | MAJOR | 1 | 1 | ✅ Fixed | Code change at file.py:123 |
| MAJOR-2 | MAJOR | 1 | - | ❌ Unfixed | Fix was comment, not code |
| MAJOR-3 | MAJOR | 2 | - | 🆕 New | Found in Round 2 review |
| MINOR-1 | MINOR | 1 | - | ⏭️ Backlog | Deferred (non-blocking) |

**Status Legend:**
- ✅ Fixed — Actually fixed with CODE (not comments)
- ❌ Unfixed — Fix failed, was just a comment, or not addressed
- 🆕 New — Found in a later round (fix may have introduced it, or missed earlier)
- ⏭️ Backlog — MINOR, deferred to later (non-blocking)

**Round 2+ Review MUST check:**
1. Are previous ✅ Fixed items ACTUALLY fixed? (Re-verify with fresh eyes)
2. Did fixes introduce NEW issues?
3. Did we miss anything in earlier rounds?

If ANY ❌ exists for CRITICAL/MAJOR after MAX_ROUNDS → quality_not_met

## Severity Definitions

| Level | Meaning | Examples | Exit Blocker? |
|-------|---------|----------|---------------|
| CRITICAL | Security, data loss, crash | SQL injection, unhandled null | **YES** |
| MAJOR | Logic error, missing validation | Wrong calculation, no bounds | **YES** |
| MINOR | Style, documentation | Naming, missing docstring | No (backlog) |

## Exit Conditions (Auto-Loop)

**Exit is checked at the START of each REVIEWER phase (before finding issues):**

| Condition | Exit Reason | Result |
|-----------|-------------|--------|
| Round N Review finds 0 CRITICAL/MAJOR | `quality_met` | ✅ Ready for merge |
| Round >= MAX_ROUNDS | `max_rounds` | ⚠️ Manual review needed |
| No progress (same issues 2 rounds) | `no_improvement` | ❌ Architectural issue |

**quality_met requires ALL of:**
1. Current round's FULL SCOPE review found zero CRITICAL/MAJOR
2. All previous issues verified as fixed (with code, not comments)
3. Guard passes
4. Issues table complete with evidence

**Automatic quality_not_met:**
- Any MAJOR "fixed" with comment instead of code
- Any issue marked "assessed" or "acceptable"
- Fixer role declared quality_met (role violation)
- Same CRITICAL/MAJOR persists for 2+ rounds

**Important:** quality_met is declared when a Review round finds NO new issues,
not when fixes are applied. This ensures the final state is actually reviewed.

## Exit Report (Generated Automatically)

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Exit Reason:** quality_met | max_rounds | no_improvement
**Total Rounds:** N / MAX_ROUNDS
**Final Round Result:** 0 CRITICAL/MAJOR found (quality_met) | X issues remain
**Guard Status:** PASS | FAIL

## Issues Table

| Issue | Severity | Found | Fixed | Status | Evidence |
|-------|----------|-------|-------|--------|----------|
| MAJOR-1 | MAJOR | R1 | R1 | ✅ Fixed | Code at file.py:123 |
| MAJOR-2 | MAJOR | R2 | R2 | ✅ Fixed | Added validation |
| ... | ... | ... | ... | ... | ... |

## Round Summary

| Round | Issues Found | Issues Fixed | New from Fixes |
|-------|--------------|--------------|----------------|
| 1 | 3 | 3 | 0 |
| 2 | 1 | 1 | 0 |
| 3 | 0 | - | - | ← quality_met

## Self-Check (Final Review Round)

- [x] Applied FULL checklist (A-G) with fresh eyes
- [x] All fixes are CODE, not comments
- [x] No "assessed as acceptable" rationalizations
- [x] Guard passes after all changes
- [x] Role separation maintained throughout

## Recommendation

- [x] Ready for merge (quality_met)
- [ ] Needs manual review (max_rounds)
- [ ] Architectural refactor needed (no_improvement)

**MINOR (Backlog):**
- [list deferred items]
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
