# DX-51: Workflow Phase Visibility

> **"You can't follow what you can't see."**

**Status:** Draft
**Created:** 2025-12-27
**Origin:** Observation during DX-38 implementation
**Effort:** Low (2 hours)
**Risk:** Low

## Problem Statement

USBV workflow phases (UNDERSTAND → SPECIFY → BUILD → VALIDATE) are documented but not consistently visible during execution:

1. **Scroll-away problem**: Phase markers in conversation text disappear as work progresses
2. **TodoWrite mismatch**: TodoWrite is designed for tasks, not workflow stages
3. **No persistent state**: User cannot see "current phase" at a glance
4. **Low follow rate**: Without visibility, workflow discipline degrades

### Current Behavior

```
User: "Add input validation to parse_source"

Agent: [Long response with inline UNDERSTAND section...]
       [More text...]
       [SPECIFY section buried in scroll...]
       [Even more text...]

       # User scrolls up: "Wait, did they do SPECIFY?"
```

### Desired Behavior

```
User: "Add input validation to parse_source"

Agent:
📍 /develop → UNDERSTAND (1/4)
   Task: Add input validation to parse_source

[Analysis content...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Contract definitions...]
```

## Key Insight: Three-Layer Visibility

```
┌─────────────────────────────────────────┐
│ Layer 1: Skill    📍 /develop           │ ← DX-42 (Routing)
├─────────────────────────────────────────┤
│ Layer 2: Phase    → SPECIFY (2/4)       │ ← DX-51 (This proposal)
├─────────────────────────────────────────┤
│ Layer 3: Tasks    □ Add @pre contract   │ ← TodoWrite
│                   □ Add doctests        │
└─────────────────────────────────────────┘
```

**Each layer serves a different purpose:**

| Layer | Question Answered | Tool | Persistence |
|-------|------------------|------|-------------|
| Skill | Which workflow? | Routing announcement | Start of skill |
| Phase | Where in workflow? | Phase banner | Each transition |
| Tasks | What specific work? | TodoWrite | Continuous |

## Proposed Solution

### 1. Phase Header (Required)

On each phase transition, display a prominent header:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Format:** `📍 {skill} → {phase} ({current}/{total})`

### 2. Compact Inline Format (For Brief Updates)

When phase content is short, use inline format:

```
📍 VALIDATE — Running guard...
✓ guard PASS | 0 errors, 1 warning
```

### 3. Phase-Task Separation

**Phase announcements** (this proposal):
- Shown in conversation output
- Visual separators for easy scanning
- Progress indicator (2/4)

**TodoWrite** (existing):
- Tracks concrete tasks within phases
- Provides checkable items
- Survives in status panel

### 4. BUILD Phase Handling

BUILD is intentionally de-emphasized (internal work):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → BUILD (3/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Implementation happens here - no detailed breakdown needed]
```

Unlike UNDERSTAND/SPECIFY/VALIDATE, BUILD does not require visible sub-steps.

## Implementation

### Template Changes

Update `.claude/skills/develop/SKILL.md.jinja`:

```markdown
## Phase Visibility (REQUIRED)

On entering each USBV phase, display phase header:

### Full Header (phase transitions)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → {PHASE} ({N}/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Compact Header (brief updates)
```
📍 {PHASE} — {one-line description}
```

Phase headers are SEPARATE from TodoWrite items.
- Phase = where you are in workflow
- TodoWrite = what tasks need doing
```

### CLAUDE.md Addition

Add to Visible Workflow section:

```markdown
## Phase Visibility (DX-51)

Each USBV phase transition requires a visible header:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This is separate from TodoWrite:
- Phase headers = workflow progress (visible in output)
- TodoWrite = task tracking (visible in status panel)
```

## Example: Complete Flow

```
User: "Add input validation to parse_source"

Agent:
📍 Routing: /develop — "add" trigger detected
   Task: Add input validation to parse_source

✓ Check-In: guard PASS | top: parse_file, check_rules

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → UNDERSTAND (1/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current state:
- `parse_source` accepts any string
- No validation for empty/whitespace input
- Located in src/invar/core/parser.py:45

Constraints:
- Must maintain backward compatibility
- Core file → requires @pre/@post

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

□ [TodoWrite: Define contracts]
  - Add @pre for non-empty source
  - Add doctest for edge cases

Proposed contract:
@pre(lambda source, path: len(source.strip()) > 0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → BUILD (3/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Implementation...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → VALIDATE (4/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ guard PASS | 0 errors, 0 warnings
✓ All TodoWrite items complete

✓ Final: guard PASS | 0 errors, 0 warnings
```

## Success Criteria

- [ ] Phase transitions visually distinct (separator lines)
- [ ] Progress indicator shows current/total (2/4)
- [ ] Phase headers appear in /develop skill execution
- [ ] TodoWrite used for tasks, not phases
- [ ] User can scan conversation and identify current phase

## Non-Goals

- No enforcement hooks (respects Lesson #19)
- No Claude Code modifications (documentation only)
- No status line integration (out of scope)

## Relationship to Other Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-42 (Routing) | Skill-level visibility; DX-51 adds phase-level |
| DX-30 (Visible Workflow) | Original USBV visibility; DX-51 refines format |
| DX-39 (Efficiency) | Error Pattern Guide; orthogonal |

## Effort Estimate

| Task | Time |
|------|------|
| Write proposal | 30 min |
| Update develop template | 30 min |
| Update CLAUDE.md | 15 min |
| Test and verify | 15 min |
| **Total** | ~1.5 hours |
