# DX-72: Mandatory Self-Review Detection

**Status:** Implemented
**Priority:** Medium
**Category:** Developer eXperience
**Created:** 2026-01-02
**Evolved from:** [DX-70](DX-70-review-isolation.md) (optional --deep)
**Depends on:** LX-07 (Context Isolation Architecture)

## Problem

DX-70 proposed "Smart Suggestion" — detecting self-review and prompting the user to use `--deep` mode. However, empirical evidence showed this is insufficient:

### Evidence: DX-71 Review Session

During the DX-71 skill command simplification review:

| Review Mode | Issues Found |
|-------------|--------------|
| Same-context review (Round 1) | 2 MAJOR |
| Isolated agent (`--deep`) | 2 CRITICAL + 4 MAJOR |

**The isolated agent found issues that same-context review completely missed:**
- CRITICAL-1: Silent data loss in `_merge_md_file()` exception handler
- CRITICAL-2: Path traversal vulnerability in skill_name validation
- MAJOR-3: `_has_user_extensions()` incorrectly filtered markdown lists
- MAJOR-5: Documentation mentioned `--all` flag that wasn't implemented
- MAJOR-6: Race condition in directory copy

### Why Same-Context Fails for Self-Review

| Cognitive Bias | Effect |
|----------------|--------|
| **Intent over code** | Agent "knows" what it intended, so doesn't see what code actually does |
| **Context memory** | Agent "remembers" reading code, so skips re-reading carefully |
| **Confirmation bias** | Agent looks for "code works" evidence, not "code fails" evidence |
| **Completion pressure** | Subconscious goal becomes "finish review" not "find bugs" |

**Claim "fresh eyes mindset" does not work.** Even with explicit instructions to adopt fresh perspective, the same agent reviewing its own code cannot overcome these biases.

## Solution

Change from "optional prompt" (DX-70) to "mandatory detection with safe default" (DX-72).

### Behavior

```
Before starting /review:

1. Detect if ANY file in review scope was edited by agent this session

2. If self-review detected:
   ┌──────────────────────────────────────────────────────────────┐
   │ SELF-REVIEW DETECTED — Isolation Required                    │
   │                                                              │
   │ You modified files in the review scope this session.         │
   │ Same-context review has proven cognitive blind spots.        │
   │                                                              │
   │ Options:                                                     │
   │ [1] Use --deep (RECOMMENDED) — Spawn isolated agent          │
   │ [2] Acknowledge risk — User explicitly accepts limitations   │
   │                                                              │
   │ If user says "continue" or "quick review":                   │
   │ → Proceed but add WARNING to final report                    │
   │ → Report MUST state: "Self-review without isolation"         │
   └──────────────────────────────────────────────────────────────┘

3. Default action: If user doesn't specify, use --deep for self-review
```

### Key Differences from DX-70

| Aspect | DX-70 (Smart Suggestion) | DX-72 (Mandatory Detection) |
|--------|--------------------------|------------------------------|
| Detection | Optional check | Mandatory check |
| Prompt | Neutral ("consider using") | Strong ("Isolation Required") |
| Default | Continue normal review | Use --deep |
| Report | No warning | Warning section if user bypassed |
| Rationale | User preference | Empirical evidence of failure |

### Exit Report Warning

When user bypasses isolation:

```markdown
## Self-Review Warning (if applicable)

This was a same-context self-review. Cognitive biases may have caused
issues to be missed. For higher confidence, run `--deep` review before merge.

Known blind spots in self-review:
- Exception handlers that silently lose data
- Path traversal / security issues in user input
- Edge cases in validation logic
- Documentation-implementation mismatches
```

## Implementation

### Changes to review SKILL.md (v5.2 → v5.3)

1. **Depth Levels section** — Clarified that default is only for others' code
2. **Added "Same-Context Review Limitations (CRITICAL)"** — Documents cognitive biases
3. **Renamed "Smart Suggestion" to "Mandatory Self-Review Detection"**
4. **Updated Mode Selection** — Self-review check is Step 1 (mandatory)
5. **Updated Exit Report** — Added Review Mode line and Self-Review Warning section

### Files Modified

- `.claude/skills/review/SKILL.md` — Installed version
- `src/invar/templates/skills/review/SKILL.md.jinja` — Template

## Success Criteria

- [x] Self-review detection is mandatory (not optional)
- [x] Default behavior is `--deep` for self-review
- [x] User can bypass with explicit acknowledgment
- [x] Bypass adds warning to exit report
- [x] Cognitive bias documentation included
- [x] Template and installed version synchronized

## Trade-offs

| Pro | Con |
|-----|-----|
| Catches more issues | Slower for self-review |
| Evidence-based design | More aggressive prompting |
| Educates about cognitive bias | May feel paternalistic |

**Mitigation:** User can always bypass by saying "continue" or "quick review", but they do so with full awareness of the limitations.

## References

- DX-70: Original --deep proposal
- LX-07: Context Isolation Architecture
- DX-71: Skill command simplification (where evidence was gathered)

---

*Evolved from DX-70 based on empirical evidence from DX-71 review session*
