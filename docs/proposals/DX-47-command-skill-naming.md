# DX-47: Command vs Skill Naming Clarification

> **"Same name, different behavior = confusion."**

**Status:** Draft
**Created:** 2025-12-25
**Effort:** Low
**Risk:** Low

## Problem Statement

Currently, `/review` exists in two forms with different behaviors:

| Type | Location | User Invoke? | Behavior |
|------|----------|--------------|----------|
| **Command** | `.claude/commands/review.md` | ✅ Yes | Read-only audit, reports issues |
| **Skill** | `.claude/skills/review/SKILL.md` | ❌ No | Audit + fix loop, convergence |

**Problem:** Same name `/review` but different capabilities.

When user types `/review`:
- They get the **command** version (read-only)
- They might expect the **skill** version (with fixes)

When agent runs `/review`:
- Agent uses the **skill** version (with fix loop)
- User may not realize the difference

## Current Distinction

### Command (User-Invokable)

```markdown
# .claude/commands/review.md
- READ-ONLY: Report issues, don't fix
- Quick adversarial review
- User can invoke directly
```

### Skill (Agent-Only)

```markdown
# .claude/skills/review/SKILL.md
- Review + Fix Loop
- Multi-round convergence
- Stall detection
- Timeout handling
- Only agent can invoke
```

## Proposed Solutions

### Option A: Rename Skill

Keep command as `/review`, rename skill:

| Old | New |
|-----|-----|
| skill: `/review` | skill: `/review-fix` |

```
User: /review          → Command: read-only audit
Agent invokes: /review-fix → Skill: audit + fix loop
```

**Pros:**
- User-invokable command keeps intuitive name
- Skill name indicates additional behavior

**Cons:**
- Skill descriptions in other proposals need updating

### Option B: Rename Command

Keep skill as `/review`, rename command:

| Old | New |
|-----|-----|
| command: `/review` | command: `/audit` |

```
User: /audit           → Command: read-only audit
Agent invokes: /review → Skill: audit + fix loop
```

**Pros:**
- Skill keeps established name
- "Audit" is accurate for read-only inspection

**Cons:**
- Users already know `/review`

### Option C: Merge Into One

Remove the command, only have the skill:

```
User: "Please review my code"
Agent: [invokes /review skill with fix loop]
```

**Pros:**
- No naming confusion
- Single behavior

**Cons:**
- Users lose direct invocation capability
- May not always want fix loop

### Option D: Add Mode Parameter (Recommended)

Keep single `/review` skill, add mode detection:

```markdown
# Skill can detect if user explicitly invoked vs agent chose

If user said "/review" or "review my code":
  → Quick mode (read-only)

If agent determines review needed:
  → Isolated mode with fix loop
```

**Implementation:**

```markdown
# .claude/skills/review/SKILL.md (updated)

## Mode Selection

### User-Initiated Review
If user explicitly requested review ("review this", "/review"):
- Use Quick mode
- Read-only, no fixes
- Report and stop

### Agent-Initiated Review
If agent invoked (after /develop, review_suggested):
- Use Isolated mode
- Include fix loop
- Multi-round convergence
```

**Pros:**
- Single name, context-aware behavior
- No renaming needed

**Cons:**
- Mode detection may be imperfect

## Recommendation

**Option D (Mode Parameter)** is cleanest because:
1. No breaking changes
2. Context-appropriate behavior
3. User gets what they expect

Fallback: **Option B (Rename Command to /audit)** if mode detection proves unreliable.

## Implementation Plan

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | Update skill with mode detection | Low |
| 2 | Remove command (superseded by skill) | Low |
| 3 | Update skill descriptions | Low |

## Success Criteria

- [ ] No user confusion about `/review` behavior
- [ ] User-initiated reviews are read-only
- [ ] Agent-initiated reviews have fix loop
- [ ] Clear documentation of modes

## Related

- DX-41: Automatic Review Orchestration (uses /review skill)
- DX-42: Workflow Auto-Routing (routing to appropriate workflow)
- `.claude/commands/review.md`: Current command
- `.claude/skills/review/SKILL.md`: Current skill
