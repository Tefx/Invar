# DX-47: Command vs Skill Naming Clarification

> **"Same name, different behavior = confusion."**

**Status:** ✅ Implemented
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Effort:** Low
**Risk:** Low

## Problem Statement

### Problem 1: `/review` Name Collision

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

### Problem 2: Missing `/guard` Command

Users have no quick way to trigger verification. They must ask the agent in natural language ("run invar guard"). A `/guard` command would provide consistency with `/audit`.

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

## Options Considered

### Option A: Rename Skill

Keep command as `/review`, rename skill to `/review-fix`.

**Rejected:** Awkward naming, skill references need updating everywhere.

### Option B: Rename Command to `/audit` ✅ Selected

Keep skill as `/review`, rename command to `/audit`.

```
User: /audit           → Command: read-only audit
Agent invokes: /review → Skill: audit + fix loop
```

**Pros:**
- "Audit" accurately describes read-only inspection
- Follows Claude Code design (commands for users, skills for agents)
- No detection logic needed - behavior is 100% predictable
- Minimal change (rename one file)

**Cons:**
- Users must learn new command name (but `/audit` is intuitive)

### Option C: Merge Into One

Remove the command, only have the skill.

**Rejected:** Users lose direct invocation capability.

### Option D: Mode Detection

Single `/review` with automatic mode detection.

**Rejected:**
- Mode detection relies on guessing user intent from context
- Skill files are static markdown - no runtime detection capability
- Boundary between "user initiated" and "agent initiated" is fuzzy
- Adds complexity without reliability

## Recommendation

**Option B: Rename Command to `/audit`**

Rationale:
1. **Follows Claude Code design** - Commands for users, Skills for agents
2. **Semantic accuracy** - "Audit" means read-only inspection in software engineering
3. **No detection logic** - Behavior is deterministic
4. **Minimal change** - Just rename one file

## Implementation Plan

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | Rename `.claude/commands/review.md` → `audit.md` | 5 min |
| 2 | Update audit.md content (title, description) | 5 min |
| 3 | Create `.claude/commands/guard.md` | 10 min |
| 4 | Update CLAUDE.md command table | 5 min |
| 5 | Update any docs referencing `/review` command | 10 min |

**Total:** ~35 minutes

### Phase 1-2: Rename Command

```bash
mv .claude/commands/review.md .claude/commands/audit.md
```

Update content:
```markdown
# Audit

Read-only code review. Reports issues without fixing them.

## Behavior

1. Analyze code for issues (style, bugs, security, architecture)
2. Report findings with file:line references
3. Do NOT make any changes - report only

## Output Format

For each issue found:
- Severity (Error/Warning/Info)
- Location (file:line)
- Description
- Suggestion (but don't implement)
```

### Phase 3: Create `/guard` Command

```markdown
# Guard

Run Invar verification on the project.

## Behavior

Execute `invar_guard()` and report:
- Pass/fail status
- Error count with details
- Warning count with details

Do NOT fix issues - just report verification results.

## When to Use

- Quick verification check
- Before committing
- After pulling changes
```

### Phase 4: Update Command Table

```markdown
# CLAUDE.md

## Commands

| Command | Purpose |
|---------|---------|
| `/audit` | Read-only code review (reports issues) |
| `/guard` | Run Invar verification (reports results) |
```

## Final State

| Type | Name | Purpose | User Invoke? |
|------|------|---------|--------------|
| Command | `/audit` | Read-only code review | ✅ Yes |
| Command | `/guard` | Run verification | ✅ Yes |
| Skill | `review` | Review + fix loop | ❌ Agent only |
| Skill | `develop` | Implementation workflow | ❌ Agent only |
| Skill | `investigate` | Exploration workflow | ❌ Agent only |
| Skill | `propose` | Design decisions | ❌ Agent only |

## Success Criteria

- [x] `/review` command renamed to `/audit`
- [x] `/guard` command created
- [x] No user confusion about command vs skill behavior
- [x] CLAUDE.md updated with command table
- [x] All docs updated to reference `/audit` instead of `/review` command

## Related

- DX-41: Automatic Review Orchestration (uses `/review` skill)
- DX-42: Workflow Auto-Routing (routing to appropriate workflow)
- `.claude/commands/audit.md`: New command (was review.md)
- `.claude/commands/guard.md`: New command
- `.claude/skills/review/SKILL.md`: Unchanged skill
