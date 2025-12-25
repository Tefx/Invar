# DX-39: Workflow Efficiency Improvements

> **"The best process is the one you don't notice."**

**Status:** Draft
**Created:** 2025-12-25
**Origin:** Meta-review of DX-33/35/36 development process
**Effort:** Medium
**Risk:** Low

## Problem Statement

The new workflow skill system (DX-35) provides structure but introduces friction:

1. **Skill content re-injection** - Full SKILL.md loaded on every `/develop` call (~90 lines)
2. **USBV steps invisible** - SPECIFY phase often skipped in practice
3. **Manual workflow transitions** - User must explicitly request next phase
4. **Error recovery unclear** - Common Guard errors lack quick-fix guidance

## Observations from DX-33/35/36 Development

### What Worked Well

| Feature | Benefit |
|---------|---------|
| `/propose` decision tables | Clear options with trade-offs |
| Check-In / Final markers | Visible session boundaries |
| TodoWrite integration | Progress tracking across tasks |
| Severity-based exit | Know when to stop |

### What Needs Improvement

| Issue | Impact | Frequency |
|-------|--------|-----------|
| Skill re-injection | ~2K tokens wasted per call | Every workflow switch |
| Missing SPECIFY | Contracts added reactively | ~50% of functions |
| Extra user input for transitions | Breaks flow | Every phase change |
| Guard error confusion | 2-3 fix iterations | Common errors |

## Proposed Solutions

### 1. Skill Caching (Context Efficiency)

**Current:** Full SKILL.md injected every time
```
User: /develop
System: [91 lines of develop/SKILL.md]
```

**Proposed:** Session-level caching via frontmatter
```yaml
---
name: develop
cache: session  # Only inject once per session
refresh: on_error  # Re-inject if workflow fails
---
```

**Implementation:**
- Track injected skills in session state
- Skip re-injection if already loaded
- Force refresh on explicit `/develop!` or after errors

**Estimated savings:** ~2K tokens per workflow switch

### 2. USBV Enforcement (Quality)

**Current:** SPECIFY often skipped
```
□ [UNDERSTAND] Add validation
[jumps directly to code]
```

**Proposed:** Require SPECIFY checkpoint for Core functions
```
□ [UNDERSTAND] Add validation to parse_source
□ [SPECIFY] Contract design
  @pre(lambda source: len(source.strip()) > 0)
  Doctest: >>> parse_source("   ") → PreContractError
□ [BUILD] Implementation
□ [VALIDATE] Guard pass
```

**Implementation:**
- Detect Core file modifications
- Require explicit SPECIFY block before BUILD
- Skip for Shell files (less strict)

**Configuration:**
```toml
[tool.invar.workflow]
require_specify = "core"  # "core" | "all" | "none"
```

### 3. Auto-Transition (Flow)

**Current:** Manual phase transitions
```
Claude: **Recommendation:** /develop
        **Next step?**
User: run /develop  ← extra input
```

**Proposed:** Optional auto-transition
```
Claude: **Recommendation:** /develop
        [Auto-transitioning in 3s... type 'stop' to cancel]

        Entering /develop for: ...
```

**Implementation:**
- Add `auto_transition` config option
- Default: off (preserve current behavior)
- When on: auto-proceed after recommendation
- Always show transition, allow interrupt

**Configuration:**
```toml
[tool.invar.workflow]
auto_transition = false  # true to enable
transition_delay = 3     # seconds to wait
```

### 4. Error Pattern Guide (Recovery)

**Current:** Raw Guard errors
```
ERROR: forbidden_import - Imports 'io' (forbidden in Core)
[user must figure out the fix]
```

**Proposed:** Quick-fix suggestions in SKILL.md
```markdown
## Common Errors & Fixes

| Error | Pattern | Quick Fix |
|-------|---------|-----------|
| `forbidden_import: io` | `io.StringIO` in Core | Use `iter(s.splitlines())` |
| `forbidden_import: os` | `os.path` in Core | Accept `Path` as parameter |
| `internal_import` | Import inside function | Move to module top |
| `missing_contract` | New Core function | Add `@pre`/`@post` before impl |
| `file_size` | File > 500 lines | Extract to new module |
```

**Implementation:**
- Add error patterns section to develop/SKILL.md
- Guard could emit fix hints in JSON output
- Agent matches error → pattern → fix

### 5. Workflow Metrics (Visibility)

Track workflow effectiveness:

```markdown
## Session Summary

| Metric | Value |
|--------|-------|
| Workflows used | /propose → /develop |
| USBV compliance | 3/4 functions specified first |
| Guard iterations | 2.5 avg per function |
| Context efficiency | 85% (skill cached) |
```

**Implementation:**
- Track in session state
- Display in Final output
- Optional: persist for trend analysis

## Implementation Plan

| Phase | Feature | Effort | Priority |
|-------|---------|--------|----------|
| 1 | Error Pattern Guide | Low | High |
| 2 | USBV Enforcement | Medium | High |
| 3 | Skill Caching | Medium | Medium |
| 4 | Auto-Transition | Low | Low |
| 5 | Workflow Metrics | Medium | Low |

### Phase 1: Error Pattern Guide (Quick Win)

Add to `.claude/skills/develop/SKILL.md`:

```markdown
## Common Guard Errors

### forbidden_import
**Cause:** I/O library used in Core module
**Fix:**
- Accept data as parameter instead of reading
- Use iterator patterns: `iter(s.splitlines())` not `io.StringIO(s)`

### internal_import
**Cause:** Import statement inside function body
**Fix:** Move import to top of file

### missing_contract
**Cause:** Core function without @pre/@post
**Fix:** Add contract BEFORE implementation (SPECIFY phase)
```

## Success Criteria

- [ ] Skill re-injection reduced by 80%
- [ ] SPECIFY phase visible for Core functions
- [ ] Common errors resolved in 1 iteration (not 2-3)
- [ ] User reports smoother workflow experience

## Open Questions

1. Should auto-transition be per-workflow or global?
2. How strict should USBV enforcement be?
3. Should metrics be opt-in or always-on?

## Related

- DX-35: Workflow-based Phase Separation (origin of skill system)
- DX-36: Documentation Restructuring (SKILL.md structure)
- DX-33: Verification Blind Spots (the development session reviewed)
