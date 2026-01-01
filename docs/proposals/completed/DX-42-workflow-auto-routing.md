# DX-42: Visible Workflow Routing

> **"Make routing decisions visible, not automatic."**

**Status:** ✅ Complete
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Origin:** Extracted from DX-35 Phase 4, simplified after DX-49/DX-50
**Effort:** Low-Medium (reduced from Medium-High)
**Risk:** Low (reduced from Medium)

---

## Problem Statement (Revised)

### Original Problem (Partially Solved)

> "Users cannot invoke skills directly"

This is a Claude Code platform constraint, not solvable by Invar.

### Actual Problem

**Agent skips workflow routing despite having rules.**

| What Exists | What's Missing |
|-------------|----------------|
| CLAUDE.md has trigger word → skill mapping | Agent doesn't announce routing decision |
| Skills have entry/exit actions | User can't see WHY a skill was chosen |
| Violation check exists | No confirmation before proceeding |

### Root Cause Analysis (from DX-50)

1. Agent treats routing as "optional best practice" not "mandatory protocol"
2. Efficiency bias: skipping skill invocation feels "faster"
3. No visible checkpoint between user request and workflow entry

---

## What's Already Implemented

| Component | Status | Location |
|-----------|--------|----------|
| Trigger words table | ✅ Done | CLAUDE.md L108-121 |
| Violation check prompt | ✅ Done | CLAUDE.md L119-121 |
| Skill entry actions | ✅ Done | .claude/skills/*/SKILL.md |

**Key Insight:** We don't need Python routing code — CLAUDE.md already has the rules.

---

## Revised Solution: Routing Announcement Protocol

### Core Principle

> **"Show the decision, not just the action."**

Before entering any workflow, Agent MUST display:

```
📍 Routing: /[skill] — [trigger detected]
   Task: [user's request summary]

   [Proceeds to skill entry...]
```

### Examples

**Clear action task:**
```
User: "Add validation to parse_source"

Agent: 📍 Routing: /develop — trigger "add" detected
       Task: Add input validation to parse_source

       ✓ Check-In: guard PASS | top: pre, post, Violation
       ...
```

**Vague task:**
```
User: "Make the parser faster"

Agent: 📍 Routing: /investigate — task is vague, needs analysis first
       Task: Improve parser performance

       Entering /investigate for: parser performance
       ...
```

**Decision task:**
```
User: "Should we use Redis or in-memory cache?"

Agent: 📍 Routing: /propose — trigger "should we" detected
       Task: Cache implementation decision

       Entering /propose for: Redis vs in-memory cache
       ...
```

---

## Simple Task Auto-Orchestration (Opt-in)

### Problem with Original Approach

| Approach | Problem |
|----------|---------|
| Auto-execute (original Part 4) | User loses control, opt-out model |
| User says "just do it" | User must know this option exists |

### Solution: Agent Suggests, User Confirms

For simple tasks, Agent **proactively offers** auto-orchestration:

```
User: "Add validation to parse_source"

Agent: 📍 Routing: /develop — trigger "add" detected
       Task: Add validation to parse_source

       📊 Simple task (1 file, ~10 lines).
          Auto-orchestrate: investigate → develop → validate?
          [Y/N]
```

### Response Handling

| User Says | Action |
|-----------|--------|
| Y / yes / go / proceed | Auto-orchestrate full cycle |
| N / no / step by step | Proceed with normal checkpoints |
| (no response) | Default to step-by-step (safe) |

### Why Opt-in, Not Opt-out?

| Opt-out (original) | Opt-in (revised) |
|--------------------|------------------|
| Auto-execute, user says "stop" | Ask first, user says "yes" |
| Fast but risky | Slightly slower but safe |
| User may not notice | User explicitly agrees |

**Key insight:** First-time users need safety; experienced users will quickly say "Y".

### Simple Task Signals

Agent judges "simple" by (no code needed):

| Signal | Indicates Simple |
|--------|------------------|
| Single file mentioned | ✓ |
| Clear function target | ✓ |
| Additive change (add, not refactor) | ✓ |
| No architectural decision | ✓ |
| Estimated < 50 lines | ✓ |

**If 4+ signals → suggest auto-orchestration.**

### Auto-Orchestration Flow

When user says "Y":

```
📍 Auto-orchestrating...

[1/3 Quick Investigation]
✓ Found parse_source at src/invar/core/parser.py:45
✓ Current: accepts any string
✓ Need: reject empty/whitespace

[2/3 Development]
✓ Check-In: guard PASS
✓ Added @pre constraint
✓ Added doctest

[3/3 Validation]
✓ Final: guard PASS | 0 errors, 0 warnings

📋 Complete. Ready for commit.
```

---

## User Control Mechanisms

### Routing Override (Natural Language)

| User Says | Effect |
|-----------|--------|
| "just implement it" | Skip to /develop |
| "I want to discuss options first" | Route to /propose |
| "explain first" | Route to /investigate |
| "stop" / "wait" | Pause, ask for direction |

### Explicit Correction

```
User: "Add validation"
Agent: 📍 Routing: /develop — trigger "add" detected

User: "Wait, let's investigate first"
Agent: 📍 Re-routing: /investigate — user requested
       Entering /investigate...
```

**No special syntax needed.** Natural language is the override mechanism.

---

## Implementation Plan

| Phase | Feature | Effort | Files Changed |
|-------|---------|--------|---------------|
| **1** | Routing announcement format | Low | 4 SKILL.md files |
| **2** | User control documentation | Low | CLAUDE.md |
| **3** | Simple task suggestion | Low | develop/SKILL.md |

### Phase 1: Update Skill Entry Points

Add to each skill's Entry section:

```markdown
## Entry Actions (REQUIRED)

### Routing Announcement

Before any workflow action, display:

```
📍 Routing: /[skill] — [reason]
   Task: [summary]
```

Then proceed with Check-In (if applicable).
```

### Phase 2: Document User Controls

Add to CLAUDE.md:

```markdown
## Routing Control

Agent announces routing decision before entering workflow.
User can redirect with natural language:
- "wait" / "stop" — pause and ask
- "just do it" — proceed with /develop
- "let's discuss" — switch to /propose
- "explain first" — switch to /investigate
```

### Phase 3: Simple Task Suggestion

Add to develop/SKILL.md after Routing Announcement:

```markdown
### Simple Task Detection

If task appears simple (4+ signals: single file, clear target, additive, <50 lines):

```
📊 Simple task (1 file, ~N lines).
   Auto-orchestrate: investigate → develop → validate?
   [Y/N]
```

- Y → Execute full cycle without intermediate confirmations
- N → Proceed with normal USBV checkpoints
- No response → Default to step-by-step
```

---

## What Was Removed (vs Original Proposal)

| Removed | Reason |
|---------|--------|
| Python routing heuristics | CLAUDE.md already has rules |
| Complexity assessment | Over-engineering; Agent judges naturally |
| Auto-orchestration | Moved to DX-41 (review-specific) |
| `!develop` syntax | Natural language is cleaner |
| Configuration options | Premature; see if needed later |

---

## Success Criteria

- [ ] Every workflow entry shows `📍 Routing: /[skill] — [reason]`
- [ ] User can redirect with natural language
- [ ] Agent never skips routing announcement
- [ ] Simple tasks trigger auto-orchestration suggestion
- [ ] User Y/N response correctly handled
- [ ] 0 "workflow skip" incidents after implementation

---

## Relationship to Other Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-50 | Solves Option B (visible routing) |
| DX-41 | Handles auto-review orchestration separately |
| DX-39 | Complements with efficiency improvements |

---

## Open Questions (Reduced)

1. Should routing announcement be a separate line or merged with skill entry?
2. How verbose should the "[reason]" be?

---

## Appendix: Original vs Revised

| Aspect | Original | Revised |
|--------|----------|---------|
| Scope | 6 parts, Python code | 3 phases, documentation only |
| Effort | Medium-High (3 days) | Low-Medium (1 day) |
| Risk | Medium (misrouting) | Low (just visibility + opt-in) |
| Core change | Automated routing | Visible routing + suggested orchestration |
| User control | `!develop` syntax | Natural language |
| Auto-orchestration | Opt-out (auto, say "stop") | **Opt-in (ask, say "Y")** |
| Simple task handling | Auto-execute | **Agent suggests, user confirms** |
