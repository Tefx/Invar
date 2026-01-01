# DX-70: /review --deep Isolation Option

**Status:** Implemented (evolved into DX-72)
**Priority:** Low
**Category:** Developer eXperience
**Created:** 2026-01-01
**Updated:** 2026-01-02
**Depends on:** LX-07 (Context Isolation Architecture)
**See also:** [DX-72](completed/DX-72-mandatory-self-review-detection.md) (mandatory self-review detection)

## Summary

Add optional context isolation (`--deep` flag) to the core `/review` skill, enabling maximum objectivity when reviewing code that the agent previously wrote.

## Problem

When the same agent writes and reviews code, cognitive bias reduces review effectiveness:

```
Agent writes login function
    ↓
Agent reviews login function
    ↓
"I know I handled the edge case at line 45"
    ↓
Skips verification → Bug slips through
```

## Solution

Add `--deep` flag to `/review` that spawns an isolated agent:

```
/review           → Same context (default, fast)
/review --deep    → Isolated agent (slower, objective)
```

## Design

### When to Use

| Scenario | Recommendation |
|----------|----------------|
| Quick feedback during development | Default (same context) |
| After completing a feature | `--deep` |
| Before merge/PR | `--deep` |
| Reviewing others' code | Default (already fresh perspective) |

### Smart Suggestion (Self-Review Detection)

Instead of always defaulting to `--deep` (too slow) or never (misses critical cases), detect self-review and prompt:

```
┌─────────────────────────────────────────────────────────────┐
│ SELF-REVIEW DETECTION                                        │
│                                                              │
│ Before /review, check:                                       │
│ • Did agent write/edit any files being reviewed?            │
│ • In this session?                                          │
│                                                              │
│ If YES:                                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚠️ Self-review detected                                  │ │
│ │                                                          │ │
│ │ You are about to review code you wrote in this session. │ │
│ │ For maximum objectivity, consider using --deep mode.    │ │
│ │                                                          │ │
│ │ [Use --deep] [Continue normal review]                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ If NO:                                                      │
│ └─ Proceed normally (no prompt)                             │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Fast by default (doesn't slow development)
- Prompts at critical moments (high bias risk)
- User retains choice
- Educates about isolation value

### Isolation Mechanism

Reuse LX-07's Context Isolation Architecture:

```
/review --deep
    ↓
Collect inputs:
├── Code files to review
├── Contracts (if available)
├── Test files (if available)
└── NO conversation history
    ↓
Spawn Task agent with:
└── Adversarial Code Reviewer persona (from LX-07 Appendix)
    ↓
Return structured review report
```

### Persona

Use the "Adversarial Code Reviewer" persona from LX-07 Appendix:

```markdown
# Adversarial Code Reviewer

## CRITICAL RULES
1. Code is GUILTY until proven INNOCENT
2. You did NOT write this code
3. Find reasons to REJECT, not accept
4. Be specific and actionable
```

## Implementation

### Changes Required

1. **Update `/review` SKILL.md.jinja**
   - Add `--deep` flag documentation
   - Add isolation check at entry
   - Add self-review detection logic
   - Reference persona template

2. **Self-Review Detection Logic**
   ```python
   # Pseudocode for detection
   def detect_self_review(review_scope: list[str], session_edits: list[str]) -> bool:
       """Check if any file in review scope was edited by agent this session."""
       return bool(set(review_scope) & set(session_edits))
   
   # In SKILL.md workflow:
   # 1. Get files to review
   # 2. Check against session edit history (from hooks or state)
   # 3. If overlap → show prompt
   ```

3. **Session Edit Tracking**
   - Leverage existing PostToolUse hook's `$CHANGES_FILE`
   - Or track via conversation context (files agent wrote to)

4. **Prompt via AskUserQuestion**
   ```markdown
   If self-review detected:
     Use AskUserQuestion tool:
       question: "Self-review detected. Use --deep for maximum objectivity?"
       options: ["Use --deep (recommended)", "Continue normal review"]
   ```

### Estimated Effort

| Task | Time |
|------|------|
| Update SKILL.md.jinja | 30 min |
| Add self-review detection | 30 min |
| Test isolation flow | 30 min |
| Documentation | 15 min |
| **Total** | ~2 hours |

## Success Criteria

- [ ] `/review --deep` spawns isolated agent
- [ ] Isolated agent has no access to conversation history
- [ ] Review report follows standard format
- [ ] Default `/review` unchanged (no performance impact)
- [ ] Self-review detection works (prompts when agent reviews own code)
- [ ] User can dismiss prompt and continue normal review

## Trade-offs

| Aspect | Default | --deep |
|--------|---------|--------|
| Speed | Fast (~30s) | Slower (~2-3 min) |
| Context | Full history | Isolated |
| Objectivity | Medium | High |
| Use frequency | High | Low (critical reviews) |

## References

- LX-07: Extension Skills Architecture (Context Isolation section)
- LX-07 Appendix: Adversarial Code Reviewer persona

---

*Small enhancement to core skill, leveraging LX-07 infrastructure*
