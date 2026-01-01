# DX-41: Automatic Review Orchestration

> **"Guard says review → Agent reviews. No questions asked."**

**Status:** ✅ Complete
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Origin:** Merged from DX-31 Phase 2 + DX-35 Phase 3
**Effort:** Low (reduced from Medium)
**Risk:** Low (reduced from Medium)

---

## Problem Statement

Current state:
- Guard outputs `review_suggested` when conditions are met
- `/review` skill exists but requires manual invocation

**Gap:** User must manually invoke `/review` after seeing `review_suggested`.

**Desired:** Review automatically executes when `review_suggested` is triggered.

## Current Flow (Manual)

```
Agent: ✓ Final: guard PASS | 0 errors, 2 warnings
       ⚠ review_suggested: escape_hatches >= 3

User: "review"  ← Extra step required

Agent: 📍 Routing: /review...
```

## Proposed Flow (Automatic)

```
Agent: ✓ Final: guard PASS | 0 errors, 2 warnings
       ⚠ review_suggested: escape_hatches >= 3

       📍 Routing: /review — review_suggested triggered
       [Enters review cycle automatically]

       [Round 1/3] Reviewing...
       Found 2 MAJOR issues.
       Fixing...
```

---

## Design Rationale

### Why Auto-Execute (Not Ask)?

| Scenario | Signal Source | Reliability | Default Behavior |
|----------|---------------|-------------|------------------|
| DX-42 Simple task | Agent judgment | May be wrong | **Ask Y/N** |
| DX-41 review_suggested | Guard rules | Deterministic | **Auto-execute** |

**Key insight:** Guard's `review_suggested` is triggered by definitive rules:

```
Trigger conditions (all are concrete, measurable):
- escape_hatch_count >= 3      # Too many @invar:allow
- contract_ratio < 70%         # Low coverage
- is_new_core_file             # New Core file needs review
- security-sensitive path      # Security files must be reviewed
```

**If Guard says review is needed, it IS needed.**

### Analogy

| Scenario | Default |
|----------|---------|
| Compiler warning | Show (not hide) |
| Security scan finds issue | Block (not ignore) |
| Guard says review needed | **Execute (not skip)** |

---

## User Control

| Control | Mechanism |
|---------|-----------|
| Skip current review | Say "skip" or "stop" during execution |
| Disable globally | `auto_review = false` in pyproject.toml |
| Manual trigger | User says "review" → /review skill |

**Note:** Unlike DX-42 simple task (which asks Y/N), auto-review proceeds by default. User can interrupt but doesn't need to confirm.

---

## Integration with DX-42

Auto-review uses DX-42's routing announcement format:

```
Agent: ✓ Final: guard PASS | 0 errors, 2 warnings
       ⚠ review_suggested: escape_hatches >= 3

       📍 Routing: /review — review_suggested triggered
          Task: Review recent changes (3 files)

       [Proceeds to review...]
```

---

## Review-Fix Cycle

```
review_suggested triggered
    │
    ├── 📍 Routing: /review — review_suggested
    │
    ├── Round 1: Review (isolated or quick mode)
    │   └── Find issues, categorize by severity
    │
    ├── CRITICAL/MAJOR? ──No──→ Done (report MINOR for backlog)
    │       │
    │      Yes
    │       ↓
    ├── Fix CRITICAL + MAJOR issues
    │
    ├── Round 2: Re-review
    │
    ├── Convergence check:
    │   ├── No CRITICAL/MAJOR → Exit ✓
    │   ├── Round >= 3 → Exit (max)
    │   └── No improvement → Exit (stalled)
    │
    └── Report remaining MINOR issues for backlog
```

---

## Implementation Plan

| Phase | Content | Files Changed |
|-------|---------|---------------|
| **1** | Update /develop Final section | develop/SKILL.md.jinja |
| **2** | Document auto-review in CLAUDE.md | CLAUDE.md.jinja |

### Phase 1: Update /develop Final

Add after Final display in develop/SKILL.md.jinja:

```markdown
### Auto-Review (DX-41)

If Guard outputs `review_suggested`:

```
⚠ review_suggested: [reason]

📍 Routing: /review — review_suggested triggered
   Task: Review [scope]
```

Proceed directly to /review skill. User can say "skip" to bypass.
```

### Phase 2: Update CLAUDE.md

Add to Routing Control section:

```markdown
**Auto-review:** When Guard outputs `review_suggested`, agent automatically
enters /review. Say "skip" to bypass.
```

---

## What Was Simplified (vs Original)

| Removed | Reason |
|---------|--------|
| 5-second timeout | Unnecessary complexity |
| Y/N confirmation | Guard rules are reliable, no need to ask |
| Python code examples | This is Agent behavior, not code |
| Configuration options | Can add later if needed |

---

## Success Criteria

- [ ] `review_suggested` → automatic /review entry
- [ ] Routing announcement shows trigger reason
- [ ] User can say "skip" to bypass
- [ ] Review-fix cycle converges (max 3 rounds)
- [ ] MINOR issues reported for backlog

---

## Comparison: DX-42 vs DX-41

| Aspect | DX-42 Simple Task | DX-41 Auto-Review |
|--------|-------------------|-------------------|
| Trigger | Agent judges "looks simple" | Guard outputs `review_suggested` |
| Reliability | Subjective | Objective (rules) |
| Default | **Ask Y/N** | **Execute** |
| Skip method | Say "N" | Say "skip" |
| Rationale | Agent might misjudge | Guard is reliable |

---

## Related

- DX-42: Visible Workflow Routing (routing announcement format)
- DX-31: Independent Adversarial Reviewer (review design)
- `/review` skill: `.claude/skills/review/SKILL.md`
