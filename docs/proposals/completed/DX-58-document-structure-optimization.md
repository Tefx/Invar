# DX-58: Document Structure Optimization

**Status:** Implemented
**Created:** 2025-12-27
**Updated:** 2025-12-28
**Dependencies:** DX-56 (Template Sync), DX-54 (Context Management)
**Related:** DX-57 (Hooks - references this proposal's critical section)

## Problem Statement

### Current Document Structure

```
Project Root:
├── CLAUDE.md (239 lines)     # Auto-loaded by Claude Code
├── INVAR.md (210 lines)      # Protocol definition, NOT auto-loaded
└── .invar/
    └── context.md (1110 lines) # Project state, NOT auto-loaded
```

### Problems Identified

#### 1. Information Priority Mismatch

Most critical information is buried in the middle of CLAUDE.md:

```
CLAUDE.md current structure:
├── Check-In (ceremonial)
├── Final (ceremonial)
├── Project Structure (important)
├── Quick Reference (CRITICAL - but buried)  ← Problem
├── Documentation Structure
├── Workflow details
└── ...
```

**Agent perspective:** The information I need MOST (tool mapping, Core/Shell rules) is not at the top where attention is highest.

#### 2. context.md Bloat

```
context.md (1110 lines):
├── Key Rules (~40 lines)        ← Useful for refresh
├── Coverage Matrix (~50 lines)  ← Reference
└── Session History (~1000 lines) ← Rarely needed, but always loaded
```

**Impact:** Check-In reads 1110 lines but only ~40 lines are immediately useful.

#### 3. Long Conversation Forgetting

```
Message 1:   CLAUDE.md content fresh in context
Message 10:  Content starting to "fade"
Message 20:  Critical rules may be forgotten
Message 30:  Agent may revert to habits (pytest instead of invar_guard)
```

**Root cause:** No mechanism to keep critical rules prominent in long conversations.

#### 4. File Ownership Complexity

| File | Claude Code | Invar | User |
|------|-------------|-------|------|
| CLAUDE.md | Expects location | Manages sections | Customizes |
| INVAR.md | — | Full control | Read-only |
| context.md | — | Template | Updates |

CLAUDE.md requires careful coordination between three parties.

## Agent Perspective Analysis

### What I Actually Need (Honest Assessment)

| Frequency | Information | Current Location | Ideal Location |
|-----------|-------------|------------------|----------------|
| **Every task** | Tool mapping (invar_guard) | CLAUDE.md middle | **Top of CLAUDE.md** |
| **Every code write** | Core/Shell decision | INVAR.md | **CLAUDE.md critical** |
| **Every task** | Workflow phase | CLAUDE.md | OK |
| **Session start** | Project state | context.md | OK (but slim it) |
| **Rarely** | Full protocol | INVAR.md | OK |
| **Rarely** | Session history | context.md | **Archive separately** |

### The Recency Bias Opportunity

```
In long conversations:
- Content at END of context → Higher attention weight
- Content at START of context → May be "pushed out"

Current: Critical rules in middle of CLAUDE.md (loaded at start)
Better: Critical rules at TOP of CLAUDE.md + Hook injection at END
```

## Proposed Solution

### 1. CLAUDE.md Restructuring

Add a new `<!--invar:critical-->` section at the very top:

```markdown
<!--invar:critical-->
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | `invar_guard` — NOT pytest, NOT crosshair |
| **Core** | `@pre/@post` + doctests, NO I/O imports |
| **Shell** | Returns `Result[T, E]` from `returns` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

<!--/invar:critical-->

<!--invar:managed version="5.0"-->
# Project Development Guide
... existing content ...
<!--/invar:managed-->
```

**Rationale:**
- Most critical info at the very top
- ~10 lines, minimal but complete
- Survives attention decay better than buried content
- Easy for hooks to reference/align with

### 2. CLAUDE.md Section Hierarchy

```markdown
<!--invar:critical-->        # 5-10 lines, MOST IMPORTANT
## ⚡ Critical Rules
...
<!--/invar:critical-->

<!--invar:managed-->         # ~150 lines, standard Invar content
# Project Development Guide
## Check-In
## Final
## Project Structure
## Workflow
...
<!--/invar:managed-->

<!--invar:project-->         # ~50 lines, project-specific
## Project Rules
## Dependencies
...
<!--/invar:project-->

<!--invar:user-->            # Variable, user customizations
## Team Conventions
...
<!--/invar:user-->
```

### 3. context.md Restructuring

**Current (1110 lines):**
```
.invar/context.md
├── Key Rules
├── Self-Reminder
├── Active Work
├── Coverage Matrix
├── Session 2025-12-26: ...
├── Session 2025-12-25: ...
├── Session 2025-12-24: ...
├── ... (many more sessions)
├── Lessons Learned
└── Version History
```

**Proposed (~150 lines + archive):**
```
.invar/
├── context.md (~150 lines)
│   ├── Key Rules (Quick Reference)
│   ├── Self-Reminder
│   ├── Active Work
│   ├── Current Blockers
│   ├── Recent Lessons (last 5)
│   └── → See archive/ for full history
│
└── archive/
    ├── sessions-2025-12.md
    └── lessons-learned.md
```

**Alternative (single file with clear sections):**
```markdown
# Context

## Key Rules (Read This)
...

## Current State
...

---
<!-- ARCHIVE BELOW - Read only if needed -->

## Session History
...
```

### 4. Information Flow Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Information Flow                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Session Start:                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  CLAUDE.md   │ +  │ context.md   │ =  │ Agent Ready  │          │
│  │  (auto-load) │    │ (Check-In)   │    │              │          │
│  │  critical ⚡  │    │ slim version │    │              │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
│  Long Conversation:                                                  │
│  ┌──────────────┐    ┌──────────────┐                               │
│  │ Hook injects │ →  │ Critical     │  (recency bias helps)        │
│  │ at context   │    │ rules fresh  │                               │
│  │ END          │    │              │                               │
│  └──────────────┘    └──────────────┘                               │
│                                                                      │
│  Reference Needed:                                                   │
│  ┌──────────────┐    ┌──────────────┐                               │
│  │  INVAR.md    │ or │ archive/     │  (on-demand read)            │
│  │  (protocol)  │    │ (history)    │                               │
│  └──────────────┘    └──────────────┘                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5. Alignment with DX-57 Hooks

DX-57's UserPromptSubmit hook should inject content aligned with critical section:

```bash
# DX-57 hook references DX-58 critical section (syntax-aware)
echo "<system-reminder>"
echo "• Verify: invar_guard — NOT pytest, NOT crosshair"
echo "• Core: @pre/@post + doctests, NO I/O imports"
echo "• Shell: Returns Result[T, E] from returns library"
echo "• Flow: USBV: Understand → Specify → Build → Validate"
echo "</system-reminder>"
```

This ensures consistency between:
- CLAUDE.md critical section (session start)
- Hook injection (long conversation refresh)

## Implementation Plan

### Phase 1: CLAUDE.md Template Update

1. Add `<!--invar:critical-->` section to template
2. Update `invar init` to generate new structure
3. Update `invar update` to preserve/merge critical section
4. Ensure backwards compatibility with existing CLAUDE.md files

### Phase 2: context.md Restructuring

1. Create archive structure in template
2. Add migration logic for existing context.md files
3. Update Check-In instructions to reference slim version
4. Document archive access pattern

### Phase 3: Template Sync Integration

1. Update manifest.toml with new regions
2. Ensure `invar dev sync` handles new structure
3. Test with existing Invar projects

## Template Changes

### CLAUDE.md.template

```markdown
<!--invar:critical-->
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | `invar_guard` — NOT pytest, NOT crosshair |
| **Core** | `@pre/@post` + doctests, NO I/O imports |
| **Shell** | Returns `Result[T, E]` from `returns` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

<!--/invar:critical-->

<!--invar:managed version="{{version}}"-->
# Project Development Guide

> **Protocol:** Follow [INVAR.md](./INVAR.md) for detailed rules.

## Check-In (DX-54)

Your first message MUST display:

```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

Actions:
1. Read `.invar/context.md` (Key Rules + Current State)
2. Show one-line status

...rest of template...
<!--/invar:managed-->
```

### context.md.template

```markdown
# Project Context

## Key Rules (Quick Reference)

<!-- DX-58: Keep this section under 50 lines -->

### Core/Shell Separation
- **Core** (`**/core/**`): @pre/@post + doctests, NO I/O imports
- **Shell** (`**/shell/**`): Result[T, E] return type

### Verification
- `invar_guard` = static + doctests + CrossHair + Hypothesis
- Final must show: `✓ Final: guard PASS | ...`

### Workflow (USBV)
1. Understand → 2. Specify (contracts first) → 3. Build → 4. Validate

---

## Current State

**Active Work:** [describe current focus]

**Blockers:** None

---

## Recent Lessons

<!-- Keep last 5 lessons here, archive older ones -->

---

<!-- ARCHIVE: Full history in .invar/archive/ if needed -->
```

### manifest.toml Update

```toml
[regions."CLAUDE.md"]
critical = { action = "overwrite", priority = 1 }
managed = { action = "overwrite", priority = 2 }
project = { action = "preserve" }
user = { action = "preserve" }

[regions.".invar/context.md"]
rules = { action = "template", preserve_content = true }
state = { action = "preserve" }
archive_note = { action = "overwrite" }
```

## Migration Strategy

### Existing CLAUDE.md Files

```bash
# invar update behavior:

1. Detect existing CLAUDE.md
2. Check for <!--invar:critical--> section
3. If missing:
   - Insert critical section at TOP
   - Preserve all existing content below
4. If present:
   - Update critical section content
   - Preserve managed/project/user sections
```

### Existing context.md Files

```bash
# invar update behavior:

1. Detect context.md size
2. If > 500 lines:
   - Offer to archive old sessions
   - Create .invar/archive/ structure
3. Update Key Rules section from template
4. Preserve user content (Current State, etc.)
```

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| CLAUDE.md critical section presence | 0% | 100% |
| context.md size | ~1100 lines | <200 lines |
| Critical rules at document top | No | Yes |
| Check-In read time (tokens) | ~3000 | <500 |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing CLAUDE.md | Careful merge logic, backwards compatible |
| Users lose history | Archive, don't delete |
| Critical section ignored | Make it visually prominent (⚡ emoji) |
| Template sync conflicts | Clear region markers, priority system |

## Appendix: Token Analysis

### Current Check-In Cost

```
Read context.md (1110 lines): ~3000 tokens
Useful content: ~100 lines (~300 tokens)
Waste: ~2700 tokens (90%)
```

### Optimized Check-In Cost

```
Read context.md (150 lines): ~400 tokens
All content useful
Savings: ~2600 tokens per session
```

### Long Conversation Refresh

```
Current (tell agent to re-read):
- Agent calls Read tool: overhead
- Reads 1110 lines: ~3000 tokens
- Total: ~3100 tokens

Optimized (hook injection):
- Hook injects 5 lines: ~60 tokens
- No tool call needed
- Total: ~60 tokens
- Savings: 98%
```

## References

- DX-54: Agent-Native Context Management
- DX-56: Template Sync Unification
- DX-57: Claude Code Hooks Integration (references this)
