# DX-53: Review Loop Effectiveness

> **"Separate the judge from the accused. Every round is a new trial."**

**Status:** ✅ Complete
**Created:** 2025-12-27
**Effort:** Medium
**Risk:** Low

---

## Problem Statement

Current review loop converges too quickly (1-2 rounds) due to two structural issues:

### Issue 1: Reviewer and Fixer are the Same Agent

```
Current Flow (Quick Mode - Default):
┌─────────────────────────────────────────┐
│  Same Agent                             │
│  - Writes code                          │
│  - Reviews own code                     │
│  - Fixes issues                         │
│  - Reviews own fixes                    │
└─────────────────────────────────────────┘
```

**Confirmation Bias:** Agent tends to validate its own work, even with "adversarial mindset" prompting.

**Evidence:** In Quick Mode, Round 2 typically finds 0 new issues after Round 1 fixes.

### Issue 2: Round N+1 Only Validates Fixes

```
Current Round 2 Behavior:
- "Check if previous fixes are correct" ← Primary focus
- "Find new issues" ← Secondary, often skipped

Result: Round 2 becomes fix verification, not adversarial review.
```

**Observable Pattern:**
```
Round 1: Found 5 MAJOR issues
Round 2: "All fixes verified, no new issues" → Exit
```

The agent doesn't actively seek NEW problems in Round 2.

---

## Root Cause Analysis

### Why Isolated Mode Isn't Used More

Current mode selection:
```
| Condition                  | Mode     |
|----------------------------|----------|
| review_suggested present   | Isolated |
| --isolated flag            | Isolated |
| Default (no trigger)       | Quick    |  ← Problem
```

**Problem:** Most reviews use Quick Mode because:
1. User invokes `/review` directly (no `review_suggested`)
2. Isolated Mode requires explicit flag
3. Quick Mode is faster (no sub-agent spawn)

### Why Round 2 Doesn't Find New Issues

The convergence logic rewards "no issues found":
```python
# Current implicit logic
if round_n_issues.critical + round_n_issues.major == 0:
    exit("quality_met")  # Success!
```

**Perverse Incentive:** Finding issues = more work. Not finding issues = done.

---

## Proposed Solution

### Change 1: Default to Isolated Reviewer

```
New Mode Selection:
| Condition              | Mode     | Reason                    |
|------------------------|----------|---------------------------|
| Default                | Isolated | Eliminates confirmation bias |
| --quick flag           | Quick    | User explicitly opts for speed |
| Trivial change (<10 lines) | Quick | Overhead not justified |
```

**Rationale:** The cost of false negatives (missed bugs) exceeds the cost of sub-agent spawn.

### Change 2: Separate Reviewer and Fixer Roles

```
New Flow:
┌─────────────────────────────────────────┐
│  Main Agent (Fixer)                     │
│  - Has full conversation context        │
│  - Implements fixes                     │
│  - Does NOT judge quality               │
└─────────────────────────────────────────┘
          ↕ issues / code
┌─────────────────────────────────────────┐
│  Sub-Agent (Reviewer) - Isolated        │
│  - Fresh context each round             │
│  - Only sees code, not rationale        │
│  - Pure adversarial role                │
└─────────────────────────────────────────┘
```

**Key Principle:** The reviewer NEVER sees why code was written, only WHAT was written.

### Change 3: Full Review Each Round

Each round has THREE phases, not one:

```
Round N:
├── Phase A: Regression Check (15%)
│   └── Verify previous fixes didn't break anything
│
├── Phase B: Fix Validation (25%)
│   └── Confirm fixes actually address the issues
│
└── Phase C: Expansion Search (60%)  ← NEW
    └── Actively hunt for NEW issues in:
        - Modified code
        - Code adjacent to modifications
        - Integration points
        - Related functionality
```

**Round 2+ Prompt Must Include:**
```
Your primary objective is to find NEW issues, not just verify fixes.

Scoring:
- Verifying a fix: +1 point
- Finding a NEW issue: +3 points

You are evaluated by issues FOUND, not fixes APPROVED.
```

### Change 4: Scope Expansion Across Rounds

```
Round 1: Changed files only
         └── Focus: Direct modifications

Round 2: Changed files + Direct imports
         └── Focus: How changes affect dependents

Round 3: Integration boundaries
         └── Focus: System-level implications
```

**Implementation:**
```python
def get_review_scope(round_num: int, changed_files: list[Path]) -> list[Path]:
    if round_num == 1:
        return changed_files
    elif round_num == 2:
        return changed_files + get_files_importing(changed_files)
    else:
        return changed_files + get_integration_points(changed_files)
```

### Change 5: Exhaustive Review Confirmation

Replace implicit "no issues = done" with explicit confirmation:

```markdown
### Round N Completion Declaration

Before exiting, reviewer must confirm:

- [ ] I reviewed ALL code in scope, not just diffs
- [ ] I checked how changes interact with unchanged code
- [ ] I attempted to find edge cases and boundary conditions
- [ ] I looked for issues UNRELATED to previous findings

**Confidence Level:** [HIGH / MEDIUM / LOW]

If MEDIUM or LOW:
- What areas need more review?
- Why couldn't you achieve HIGH confidence?
```

**Exit Criteria Change:**
```python
# Old
exit_if no_critical_major

# New
exit_if (
    no_major                      # No MAJOR or CRITICAL issues
    AND reviewer_confidence == HIGH  # Reviewer confirms exhaustive review
)
```

---

## Updated Review-Fix Loop

```
Round 1:
    │
    ├── Spawn Isolated Reviewer (sub-agent)
    │   └── Prompt: "Find ALL issues. Success = problems found."
    │
    ├── Reviewer returns issues + confidence level
    │
    ├── Issues found?
    │   ├── NO MAJOR + HIGH confidence → Exit ✓
    │   ├── NO MAJOR + LOW confidence → Continue (expand scope)
    │   └── MAJOR found ↓
    │
    ├── Main Agent fixes CRITICAL + MAJOR
    │
Round 2:
    │
    ├── Spawn NEW Isolated Reviewer (fresh context!)
    │   └── Prompt includes:
    │       - "Previous round found N issues (now fixed)"
    │       - "Your job: find NEW issues + verify fixes"
    │       - "Expanded scope: [files]"
    │
    ├── Reviewer returns issues + confidence
    │
    ├── Convergence check:
    │   ├── No MAJOR + HIGH confidence → Exit ✓
    │   ├── No MAJOR + LOW confidence → Continue (last round)
    │   ├── Round >= 3 → Exit (max)
    │   └── MAJOR found → Continue
    │
Round 3 (if needed):
    │
    └── Same pattern, maximum scope
```

---

## Isolated Reviewer Prompt (Updated)

```python
Task(
    subagent_type="general-purpose",
    prompt=f"""
You are an ADVERSARIAL CODE REVIEWER for Round {round_num}.

## Your Role
- You are the JUDGE, not the defense attorney
- Your success is measured by PROBLEMS FOUND
- Finding 0 issues is a FAILURE unless you can prove exhaustive review

## Files to Review
{file_list}

## Previous Context
{f"Round {round_num-1} found {prev_issues} issues (now fixed)." if round_num > 1 else "This is the first review round."}

## Round {round_num} Objectives
1. REGRESSION: Check that fixes didn't break anything (15% effort)
2. VALIDATION: Confirm fixes address original issues (25% effort)
3. EXPANSION: Find NEW issues not caught before (60% effort) ← PRIMARY

## Review Scope
{scope_description}

## What to Look For
- Contract quality (meaningful @pre/@post, not just type checks)
- Boundary conditions and edge cases
- Logic errors and dead code
- Integration issues with unchanged code
- Security considerations
- Escape hatch validity

## Severity Definitions
- CRITICAL: Security vulnerability, data loss, crash
- MAJOR: Logic error, missing validation, meaningless contract
- MINOR: Style, documentation, minor improvements

## Required Output

### Issues Found
[List each issue with severity, location, description, suggestion]

### Completion Declaration
- [ ] Reviewed ALL code in scope
- [ ] Checked integration points
- [ ] Attempted to find edge cases
- [ ] Looked for issues unrelated to previous findings

**Confidence:** HIGH / MEDIUM / LOW
**If not HIGH:** [Explain what more review is needed]

Remember: You WIN by finding problems. You LOSE by missing them.
"""
)
```

---

## Mode Comparison

| Aspect | Current (Quick Default) | Proposed (Isolated Default) |
|--------|-------------------------|------------------------------|
| Confirmation bias | Present | Eliminated |
| Round 2 behavior | Verify fixes | Find new issues + verify |
| Convergence speed | Fast (1-2 rounds) | Appropriate (2-3 rounds) |
| Issue detection | Moderate | Higher |
| Token cost | Lower | ~30% higher |
| False negative rate | Higher | Lower |

---

## Implementation Plan

### Phase 1: Update Mode Selection Default

**File:** `.claude/skills/review/SKILL.md`

```markdown
### Select Mode

| Condition                      | Mode     |
|--------------------------------|----------|
| Default                        | Isolated |
| `--quick` flag                 | Quick    |
| Trivial change (<10 lines)     | Quick    |
| `review_suggested` present     | Isolated |
```

### Phase 2: Update Isolated Reviewer Prompt

Add to prompt:
- Round-specific objectives (regression, validation, expansion)
- Scope expansion logic
- Confidence declaration requirement
- Scoring incentive ("Finding NEW issue = +3 points")

### Phase 3: Update Convergence Criteria

Change exit condition from:
```
no_critical_major → Exit
```
To:
```
no_major AND confidence == HIGH → Exit
```

MEDIUM/LOW confidence forces another round even if no MAJOR issues found.

### Phase 4: Add Scope Expansion Logic

Document how review scope expands across rounds:
- Round 1: Changed files
- Round 2: + Direct dependents
- Round 3: + Integration points

---

## Metrics

### Before (Expected)
- Average rounds: 1.3
- Issues found per review: 3-5
- False negative rate: Unknown (bugs found later)

### After (Target)
- Average rounds: 2.0-2.5
- Issues found per review: 5-8
- Confidence in review: Explicit declaration

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Increased token cost | Quick Mode available via `--quick` |
| Longer review time | Scope expansion is bounded (max 3 rounds) |
| Sub-agent spawning overhead | Only spawn when actually reviewing |
| Over-engineering | Keep core logic simple, complexity in prompts |

---

## Success Criteria

- [ ] Default mode is Isolated (sub-agent reviewer)
- [ ] Each round includes explicit expansion phase
- [ ] Reviewer must declare confidence level before exit
- [ ] Round 2+ finds new issues (not just verifies fixes)
- [ ] Quick Mode available for trivial changes
- [ ] Average review rounds increases to 2-2.5

---

## Related

- DX-41: Automatic Review Orchestration (auto-trigger)
- DX-42: Workflow Routing (routing announcements)
- `/review` skill: Current implementation

---

## Open Questions

1. **Token Budget:** Should there be a token limit per review session?
2. **Scope Expansion:** How to determine "integration points" programmatically?
3. **Confidence Calibration:** How to validate reviewer confidence is accurate?
4. **Quick Mode Threshold:** Is 10 lines the right cutoff for auto-Quick Mode?
