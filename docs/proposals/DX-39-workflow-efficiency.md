# DX-39: Workflow Efficiency Improvements

> **"The best process is the one you don't notice."**

**Status:** ✅ Complete
**Created:** 2025-12-25
**Updated:** 2025-12-27
**Origin:** Meta-review of DX-33/35/36 development process, merged DX-27
**Effort:** Low (revised from Medium)
**Risk:** Low

## Revision Summary (2025-12-27)

After DX-41, DX-42, DX-46, DX-49 completion, this proposal was revised:

| Solution | Original | Revised | Rationale |
|----------|----------|---------|-----------|
| Skill Caching | Medium priority | **Defer** | Claude Code lacks session state |
| USBV Enforcement | High priority | **Downgrade to guidance** | Enforcement complex, guidance sufficient |
| Auto-Transition | Low priority | **Complete** | DX-42 Simple Task Detection covers this |
| Error Pattern Guide | High priority | **Keep** | Still needed |
| Workflow Metrics | Low priority | **Defer** | Unclear ROI, depends on deferred features |
| Output Style | Medium priority | **Drop** | Risk > benefit (loses efficient output instructions) |

**New items added:**
- SKILL.md extensions bug fix
- Guard suggestion integration

## Problem Statement

The workflow skill system provides structure but has remaining friction:

1. ~~**Skill content re-injection**~~ — Defer (Claude Code lacks session state)
2. ~~**USBV steps invisible**~~ — Current ~70% compliance acceptable
3. ~~**Manual workflow transitions**~~ — Solved by DX-42 Simple Task Detection
4. **Error recovery unclear** — Common Guard errors lack quick-fix guidance (**Active**)

## Current State (Post DX-41/42/49)

### Already Implemented

| Feature | By | Status |
|---------|-------|--------|
| Routing announcements | DX-42 | ✅ In SKILL.md |
| Simple task detection | DX-42 | ✅ In SKILL.md |
| Auto-review on review_suggested | DX-41 | ✅ In SKILL.md |
| Check-In/Final protocol | DX-49 | ✅ In CLAUDE.md + MCP |

### Still Needed

| Feature | Priority | Status |
|---------|----------|--------|
| Error Pattern Guide | High | Not implemented |
| SKILL.md extensions bug | High | Bug discovered |
| Guard suggestion integration | Medium | Not linked |

## Active Solutions

### 1. SKILL.md Extensions Bug Fix (NEW)

**Problem:** `develop/SKILL.md` extensions region contains duplicate content (~200 lines).

```markdown
<!--invar:skill version="5.0"-->
[... skill content ...]
<!--/invar:skill-->

<!--invar:extensions-->
---
name: develop              ← BUG: Duplicate frontmatter
description: ...           ← BUG: Entire skill duplicated
---
# Development Mode
[... ~200 lines duplicate ...]
<!--/invar:extensions-->
```

**Root cause:** Unknown (manual edit or early sync-self bug).

**Fix:** Clear extensions region, verify sync-self logic.

**Effort:** 5 minutes

### 2. Error Pattern Guide

**Current:** Raw Guard errors without guidance
```
ERROR: forbidden_import - Imports 'io' (forbidden in Core)
[user must figure out the fix]
```

**Proposed:** Quick-fix table in develop/SKILL.md

```markdown
## Common Guard Errors

| Error | Cause | Quick Fix |
|-------|-------|-----------|
| `forbidden_import: io` | I/O in Core | Use `iter(s.splitlines())` |
| `forbidden_import: os` | os.path in Core | Accept `Path` as parameter |
| `internal_import` | Import inside function | Move to module top |
| `missing_contract` | Core function without contract | Add `@pre`/`@post` before impl |
| `file_size` | File > 500 lines | Extract to new module |
| `shell_no_result` | Shell function missing Result | Return `Result[T, E]` |
```

**Implementation:**
- Add to develop/SKILL.md template
- Run sync-self to propagate

**Effort:** Low

### 3. Guard Suggestion Integration (NEW)

**Current state:** `suggestions.py` generates smart contract suggestions:

```python
generate_contract_suggestion("(x: int, y: int) -> int")
# → '@pre(lambda x, y: x >= 0 and y >= 0)'

generate_pattern_options("(x: int, y: str) -> int")
# → 'Patterns: x >= 0 | x > 0 | x != 0, len(y) > 0 | y | y.strip()'
```

But these aren't linked from the Error Pattern Guide.

**Proposed:** Add reference in Error Pattern Guide:

```markdown
| `missing_contract` | Core function without contract | See Guard "Suggested:" output |
```

Guard already outputs:
```
ERROR: missing_contract at src/core/parser.py:25 (parse_source)
  Suggested: @pre(lambda source, path: len(source.strip()) > 0)
  Patterns: len(source) > 0 | source | source.strip()
```

**Effort:** Minimal (documentation link)

## Deferred Solutions

### Skill Caching — Defer

**Original proposal:**
```yaml
---
name: develop
cache: session      # Only inject once per session
refresh: on_error   # Re-inject if workflow fails
---
```

**Why defer:**

| Issue | Detail |
|-------|--------|
| **No session state** | Claude Code has no native session persistence mechanism |
| **Custom frontmatter not parsed** | Claude Code ignores unknown frontmatter fields |
| **Implementation complexity** | Would require MCP server extension or external state |
| **Limited benefit** | ~2K tokens/call, but 200K context makes 1% savings low priority |

**Alternative:** Agent can self-manage via `<!--invar:skill-->` markers.

### USBV Enforcement — Downgrade to Guidance

**Original proposal:**
```toml
[tool.invar.workflow]
require_specify = "core"  # Enforce SPECIFY before BUILD
```

**Why downgrade:**

| Issue | Detail |
|-------|--------|
| **Enforcement difficult** | Requires Agent execution flow interception |
| **False positive risk** | Simple one-line fixes would trigger unnecessary SPECIFY |
| **Current compliance acceptable** | ~70% SPECIFY compliance observed |
| **ROI questionable** | High implementation cost for ~20% improvement |

**Current state:** SKILL.md guidance is sufficient. SPECIFY section clearly documented.

### Workflow Metrics — Defer

**Original proposal:**
```markdown
## Session Summary
| Metric | Value |
|--------|-------|
| USBV compliance | 3/4 functions specified first |
| Guard iterations | 2.5 avg per function |
```

**Why defer:**

| Issue | Detail |
|-------|--------|
| **Data collection difficult** | Requires session-wide state tracking |
| **No clear action** | Metrics are informational, no improvement action defined |
| **Dependencies deferred** | "Context efficiency" depends on Skill Caching |

### Output Style Protocol Entry — Drop

**Original proposal:**
```markdown
# .claude/output-styles/invar-protocol.md
---
name: Invar Protocol
keep-coding-instructions: true
---
```

**Why drop:**

| Issue | Detail |
|-------|--------|
| **Loses default behaviors** | Even with `keep-coding-instructions: true`, loses "efficient output" instructions |
| **Risk > benefit** | 50%→85% compliance improvement not worth losing Anthropic optimizations |
| **Current enforcement sufficient** | MCP Server instructions already enforce Check-In at system level |

**Documentation reference:**
> "All output styles exclude instructions for efficient output (like responding concisely)"
> — Claude Code Output Styles documentation

## Implementation Plan

| Phase | Feature | Effort | Priority |
|-------|---------|--------|----------|
| **0** | SKILL.md extensions bug fix | 5 min | Critical |
| **1** | Error Pattern Guide | Low | High |
| **2** | Guard suggestion integration | Minimal | Medium |
| ∞ | Skill Caching | — | Defer |
| ∞ | USBV Enforcement | — | Downgrade |
| ∞ | Workflow Metrics | — | Defer |
| ✗ | Output Style | — | Drop |

**Total effort:** ~0.5 day (revised from 1-2 days)

### Phase 0: Bug Fix

```bash
# Option A: Manual fix
# Edit .claude/skills/develop/SKILL.md, clear extensions region

# Option B: Regenerate
invar sync-self
```

### Phase 1: Error Pattern Guide

Add to `src/invar/templates/skills/develop/SKILL.md.jinja`:

```markdown
## Common Guard Errors

| Error | Cause | Quick Fix |
|-------|-------|-----------|
| `forbidden_import: io` | I/O library in Core | Use `iter(s.splitlines())` not `io.StringIO` |
| `forbidden_import: os` | os module in Core | Accept `Path` as parameter |
| `internal_import` | Import inside function | Move to module top |
| `missing_contract` | Core function without @pre/@post | See Guard "Suggested:" output |
| `file_size` | File > 500 lines | Extract to new module |
| `shell_no_result` | Shell function missing Result | Return `Result[T, E]` |

**Tip:** Guard automatically suggests contracts for `missing_contract` errors.
```

Then run `invar sync-self` to propagate.

## Success Criteria

- [x] ~~Skill re-injection reduced by 80%~~ — Defer
- [x] ~~SPECIFY phase visible for Core functions~~ — Current ~70% acceptable
- [ ] Common errors resolved in 1 iteration (not 2-3)
- [ ] SKILL.md extensions bug fixed
- [ ] Error Pattern Guide in develop/SKILL.md

## Open Questions

~~1. Should auto-transition be per-workflow or global?~~ — Solved by DX-42
~~2. How strict should USBV enforcement be?~~ — Downgraded to guidance
~~3. Should metrics be opt-in or always-on?~~ — Deferred

No open questions remain.

## Related

- DX-27: System Prompt Protocol Entry (merged, then dropped)
- DX-35: Workflow-based Phase Separation (origin of skill system)
- DX-41: Auto-review orchestration (implemented)
- DX-42: Workflow auto-routing (implemented)
- DX-49: Protocol distribution unification (implemented)
