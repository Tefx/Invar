# DX-36: Documentation Restructuring for Workflow Support

> **"Right information at right time."**

**Status:** ✅ Complete (Phase 1-4 implemented, Phase 5-6 extracted to DX-43)
**Created:** 2025-12-25
**Depends On:** DX-35 (Workflow-based Phase Separation)
**Related:** DX-33 (Verification Blind Spots), DX-34 (Review Cycle)

## Resolution

| Phase | Description | Resolution |
|-------|-------------|------------|
| Phase 1 | Section files (sections/) | ✅ Implemented |
| Phase 2 | Skill files (.claude/skills/) | ✅ Implemented |
| Phase 3 | Update templates (src/invar/templates/) | ✅ Implemented |
| Phase 4 | Simplify CLAUDE.md | ✅ Implemented |
| Phase 5 | CLI updates (`invar init --claude`) | → Extracted to **DX-43** |
| Phase 6 | Documentation & Migration guide | → Extracted to **DX-43** |

### ✅ Implemented (Phase 1-4)

- `sections/` directory with investigate.md, propose.md, develop.md, review.md
- 4 workflow skill files in `.claude/skills/`
- Template files updated in `src/invar/templates/`
- Simplified CLAUDE.md (~30 lines)

---

## Problem Statement

### Current State

| Document | Lines | Issues |
|----------|-------|--------|
| INVAR.md | 464 | Monolithic, all loaded at once, dilutes in long context |
| CLAUDE.md | 260 | Too detailed, mixes project config with workflow instructions |
| Templates | 3 files | No skill templates, no platform-specific rules |

### Issues with Current Structure

1. **Context Pollution** — All 464 lines of INVAR.md loaded upfront, most irrelevant to current phase
2. **Instruction Dilution** — By turn 50+, agent forgets Check-In and workflow rules
3. **No Phase Awareness** — Same instructions whether investigating, developing, or reviewing
4. **Platform Coupling** — No support for Cursor/Windsurf (Tier 2 platforms)
5. **Template Gap** — `invar init` doesn't create skill files

### Goal

Restructure documentation to support DX-35's workflow-based phase separation:
- Load only relevant instructions for current workflow
- Re-inject instructions at workflow transitions
- Support multiple platforms with appropriate depth

---

## Two Contexts: Invar vs Other Projects

**Critical distinction:** This proposal affects TWO different contexts:

### Context 1: Invar Project Itself

| File | Current | After DX-36 |
|------|---------|-------------|
| `/INVAR.md` | 464 lines (SOURCE) | Modular: core + sections/ |
| `/CLAUDE.md` | 260 lines | Simplified ~30 lines |
| `/.claude/skills/` | None | 4 workflow skills |

**Note:** `/INVAR.md` at root is the **authoritative source**. It's NOT from templates.

### Context 2: Other Projects (via `invar init`)

| File | Current | After DX-36 |
|------|---------|-------------|
| `templates/INVAR.md` | 207 lines (compact) | Self-contained, no sections/ |
| `templates/skills/` | Only review.md | 4 workflow skill templates |
| `templates/cursorrules.template` | None | Tier 2 baseline |

**Note:** Templates are **self-contained**. No external sections/ dependency.

### Why Different?

| Aspect | Invar Project | Other Projects |
|--------|---------------|----------------|
| Complexity | Full protocol, all details | Compact, essentials only |
| Maintenance | Actively developed | Stable templates |
| Sections | Separate files (modular) | Inline (simpler) |
| Skills | Project-specific | Generic templates |

---

## Proposed Structure

### Overview

```
Before (Monolithic)                 After (Modular)
┌─────────────────────┐            ┌─────────────────────┐
│     INVAR.md        │            │   INVAR.md (Core)   │ ← Always loaded (~80 lines)
│     (464 lines)     │            ├─────────────────────┤
│                     │            │   sections/         │ ← Loaded by workflows
│  - Six Laws         │            │   ├── investigate.md│
│  - Architecture     │            │   ├── propose.md    │
│  - Contracts        │            │   ├── develop.md    │
│  - Commands         │            │   ├── review.md     │
│  - USBV             │            │   └── reference.md  │
│  - Review Gate      │            └─────────────────────┘
│  - ...              │
└─────────────────────┘            ┌─────────────────────┐
                                   │   CLAUDE.md         │ ← Project config (~30 lines)
┌─────────────────────┐            └─────────────────────┘
│    CLAUDE.md        │
│    (260 lines)      │            ┌─────────────────────┐
│                     │            │   .claude/skills/   │ ← Workflow triggers
│  - Check-In         │            │   ├── investigate/  │
│  - Project Rules    │            │   ├── propose/      │
│  - Dependencies     │            │   ├── develop/      │
│  - USBV details     │            │   └── review/       │
│  - ...              │            └─────────────────────┘
└─────────────────────┘
```

---

## INVAR.md Modularization

### New Structure

```markdown
# INVAR.md (Core) — ~80 lines

## Header
- Version, license, managed-file notice

## Philosophy (10 lines)
- "Trade structure for safety"
- Agent-Native design principle

## Six Laws (15 lines)
- Table format, always relevant

## Core/Shell Architecture (15 lines)
- Zone definitions, forbidden imports

## Quick Reference (20 lines)
- Commands: guard, sig, map
- Check-In/Final format
- Size limits table

## Workflow Sections (links only)
- See sections/investigate.md
- See sections/develop.md
- See sections/review.md
- See sections/reference.md

## Installation (10 lines)
- pip install commands
```

### Section Files

#### sections/investigate.md (~40 lines)

```markdown
# Investigation Workflow

## Purpose
Understand before acting. No code changes in this phase.

## Tools
| Tool | Usage |
|------|-------|
| invar map --top 10 | Find entry points |
| invar sig <file> | See contracts without reading code |
| Read | Understand implementation when needed |

## Constraints
- NO editing (Edit, Write forbidden)
- NO commits (nothing to commit)
- Focus on understanding, not solving

## Exit Format
Report findings, recommend next workflow.
```

#### sections/propose.md (~40 lines)

```markdown
# Proposal Workflow

## Purpose
Facilitate decisions with clear options.

## Output Formats

### Quick Decision (2-3 options)
| Option | Pros | Cons |
|--------|------|------|
| A | ... | ... |
| B | ... | ... |

Recommendation: [choice] because [reason]

### Formal Proposal (complex decision)
Create docs/proposals/DX-XX-[topic].md with:
- Problem Statement
- Options with trade-offs
- Recommendation
- Open Questions

## Exit
Human makes choice → proceed to /develop
```

#### sections/develop.md (~100 lines)

```markdown
# Development Workflow

## Entry: Check-In (REQUIRED)
```
invar_guard(changed=true)
invar_map(top=10)
```
Display: `✓ Check-In: guard PASS | top: <entry1>, <entry2>`

## USBV Flow

### UNDERSTAND
- Read .invar/context.md
- Use invar sig to see contracts
- Identify affected areas

### SPECIFY
- Write @pre/@post BEFORE implementation
- Add doctests for edge cases
- Design decomposition if complex

### BUILD
- Complex task? → Enter Plan Mode first
- Implement following contracts
- Commit after each logical unit
- Run invar_guard(changed=true) frequently

### VALIDATE
- Run invar_guard() (full verification)
- All todos complete
- Review Gate check

## Task Batching
- Max 5 tasks per batch
- Guard between each task
- Commit after each task
- Stop on Guard failure

## Exit: Final (REQUIRED)
```
invar_guard()
```
Display: `✓ Final: guard PASS | <summary>`

If `review_suggested` → recommend /review
```

#### sections/review.md (~80 lines)

```markdown
# Review Workflow

## Mode Selection
- `review_suggested` OR `--isolated` → Isolated Mode (sub-agent)
- Otherwise → Quick Mode (same context)

## Isolated Mode

Spawn adversarial reviewer with fresh context:
- NO development history
- Focus: Find what Guard missed
- Mindset: Adversarial, not collaborative

## Review Focus
1. Contract QUALITY (not just presence)
2. Boundary conditions
3. Error handling paths
4. Security considerations
5. Dead code / logic errors

## Severity Definitions
| Level | Meaning | Examples |
|-------|---------|----------|
| CRITICAL | Security, data loss, crash | SQL injection, unhandled null |
| MAJOR | Logic error, missing validation | Wrong calculation, no bounds check |
| MINOR | Style, documentation | Naming, missing docstring |

## Review-Fix Loop

Round 1: Review → Find issues
    ↓
Fix CRITICAL + MAJOR (MINOR → backlog)
    ↓
Round 2: Re-review (if needed)
    ↓
Convergence check:
- No CRITICAL/MAJOR → Exit ✓
- No improvement → Exit (warn)
- Round >= 3 → Exit (max)

## Stall Detection
If >50% issues repeat from previous round:
- Report stall to user
- Options: false positive, investigate, continue

## Exit Report
- Rounds completed
- Exit reason
- Fixed issues
- Remaining MINOR (backlog)
```

#### sections/reference.md (~150 lines)

```markdown
# Reference

## Contracts

### Syntax
@pre(lambda args: condition)
@post(lambda result: condition)

### Composition
NonEmpty & Sorted  # AND
NonEmpty | Sorted  # OR
~NonEmpty          # NOT

### Standard Library
NonEmpty, Sorted, Unique, Positive, NonNegative,
Percentage, NonBlank, AllPositive, NoNone

## Must-Use Return Values
@must_use("Reason")
def func() -> Result: ...

## Loop Invariants
invariant(condition)  # Checked at runtime

## Resource Management
@must_close
class Resource: ...

## Markers

### Entry Points
# @shell:entry
def framework_callback(): ...

### Shell Complexity
# @shell_complexity: Reason
# @shell_orchestration: Reason

### Escape Hatch
# @invar:allow rule_name: Reason

## Configuration (pyproject.toml)
[tool.invar.guard]
core_paths = ["src/*/core"]
shell_paths = ["src/*/shell"]
max_file_lines = 500
max_function_lines = 50
exclude_doctest_lines = true
```

---

## CLAUDE.md Simplification

### Current (260 lines) → Proposed (~30 lines)

```markdown
# Project: [Name]

## Check-In
First message must display:
`✓ Check-In: guard PASS | top: <entry1>, <entry2>`

## Structure
```
src/
├── core/    # Pure logic, @pre/@post required
└── shell/   # I/O, Result[T, E] required
```

## Project Rules
- [Any project-specific rules]
- [Custom paths or exceptions]

## Dependencies
```bash
pip install -e ".[dev]"
```

## Context
See .invar/context.md for current state.
```

### Rationale

| Removed Content | Moved To |
|-----------------|----------|
| USBV details | sections/develop.md |
| Review protocol | sections/review.md |
| Tool selection | sections/investigate.md |
| Command reference | INVAR.md Core |
| Contract examples | sections/reference.md |

---

## Skill Files Implementation

### Directory Structure

```
.claude/skills/
├── investigate/
│   └── SKILL.md
├── propose/
│   └── SKILL.md
├── develop/
│   └── SKILL.md
└── review/
    └── SKILL.md
```

### Skill File Template

Each skill file follows this structure:

```markdown
---
name: [workflow-name]
description: [one-line description]
---

# [Workflow Name] Mode

## Re-injected Instructions
[Content from sections/[workflow].md]

## Entry Actions
[What to do when entering this workflow]

## Constraints
[What is allowed/forbidden]

## Exit Conditions
[When this workflow ends]

## Output Format
[Expected output structure]
```

### Skill Loading Mechanism

```
User input → Routing analysis
                  ↓
         ┌───────────────────┐
         │ Load SKILL.md     │
         │ (re-inject rules) │
         └───────────────────┘
                  ↓
         Execute workflow with
         fresh instructions
```

---

## Template System Updates

### New Template Structure

```
src/invar/templates/
├── INVAR.md              # Core only (~80 lines)
├── sections/
│   ├── investigate.md
│   ├── propose.md
│   ├── develop.md
│   ├── review.md
│   └── reference.md
├── skills/
│   ├── investigate/SKILL.md
│   ├── propose/SKILL.md
│   ├── develop/SKILL.md
│   └── review/SKILL.md
├── CLAUDE.md.template    # Simplified (~30 lines)
├── cursorrules.template  # Tier 2 baseline
└── context.md.template   # Project state
```

### `invar init` Behavior

#### Default: `invar init`

```bash
invar init
```

**Creates:**
```
project/
├── INVAR.md              # Self-contained protocol (~200 lines)
├── .invar/
│   ├── context.md        # Project state (user fills in)
│   └── examples/
│       ├── README.md
│       ├── core_example.py
│       └── shell_example.py
└── [Does NOT touch CLAUDE.md - user content]
```

**Note:** Template INVAR.md is SELF-CONTAINED. No sections/ directory needed.

#### Claude Code: `invar init --claude`

```bash
invar init --claude
```

**Creates (in addition to default):**
```
project/
├── .claude/
│   └── skills/
│       ├── investigate/
│       │   └── SKILL.md    # Investigation workflow
│       ├── propose/
│       │   └── SKILL.md    # Proposal workflow
│       ├── develop/
│       │   └── SKILL.md    # Development workflow (USBV)
│       └── review/
│           └── SKILL.md    # Review workflow
└── [Suggests CLAUDE.md template if not exists]
```

**Skill files include workflow instructions INLINE** (no external sections/ dependency).

#### Cursor/Windsurf: `invar init --cursor`

```bash
invar init --cursor
```

**Creates (in addition to default):**
```
project/
└── .cursorrules            # Baseline protocol (~50 lines)
```

#### Combined Flags

```bash
# Full setup for Claude Code user who also uses Cursor
invar init --claude --cursor
```

### Template File Details

| Template | Lines | Content |
|----------|-------|---------|
| `INVAR.md` | ~200 | Self-contained protocol |
| `skills/investigate/SKILL.md` | ~50 | Investigation instructions |
| `skills/propose/SKILL.md` | ~40 | Proposal format |
| `skills/develop/SKILL.md` | ~100 | USBV + Check-In/Final |
| `skills/review/SKILL.md` | ~80 | Review-fix loop |
| `.cursorrules` | ~50 | Tier 2 baseline |

**Total for Claude Code setup:** ~470 lines across 6 files (vs current 207 lines in 1 file)

**But:** Each workflow only loads ~100-150 lines relevant to current phase.

---

## Platform Tiering

### Tier 1: Claude Code (Full)

**Files:**
- INVAR.md (core)
- sections/* (workflow docs)
- .claude/skills/* (workflow triggers)
- CLAUDE.md (simplified)

**Features:**
- Automatic workflow routing
- Instruction re-injection via skills
- Isolated review via sub-agent
- MCP tools integration

### Tier 2: Cursor/Windsurf (Baseline)

**Files:**
- INVAR.md (core + sections inline)
- .cursorrules (combined instructions)

**Features:**
- Manual workflow awareness
- CLI tools (invar guard/sig/map)
- No skill automation
- No isolated sub-agents

**.cursorrules Template:**

```markdown
# Invar Protocol (Baseline)

## Check-In
First response: run `invar guard --changed` and `invar map --top 10`

## Workflow Awareness
- Vague task? → Investigate first (no code changes)
- Clear task? → Follow USBV (Understand → Specify → Build → Validate)
- After development → Consider review if complex

## Commands
- `invar guard` — Verify code (static + tests)
- `invar sig <file>` — See contracts
- `invar map --top 10` — Find entry points

## Architecture
- Core (src/*/core/): @pre/@post required, no I/O
- Shell (src/*/shell/): Result[T, E] required

## Contracts Before Code
Write @pre/@post and doctests before implementation.

## Size Limits
- File: 500 lines
- Function: 50 lines

[Condensed from INVAR.md — see full protocol for details]
```

### Tier 3: Others (Protocol Only)

**Files:**
- INVAR.md (full, not modularized)

**Features:**
- Protocol reference only
- Manual compliance
- CLI if installed

---

## Migration Plan

### For Invar Project Itself

```
Phase 1: Create section files
├── Split INVAR.md content into sections/
├── Keep original INVAR.md as reference
└── Validate section coverage

Phase 2: Create skill files
├── Implement 4 skill files in .claude/skills/
├── Test workflow transitions
└── Verify instruction re-injection

Phase 3: Update templates
├── Update src/invar/templates/
├── Add skill templates
├── Add .cursorrules template

Phase 4: Simplify CLAUDE.md
├── Reduce to ~30 lines
├── Move content to sections/skills
└── Test with fresh conversation

Phase 5: Update invar init
├── Add --claude flag
├── Add --cursor flag
└── Update default behavior
```

### For Existing Projects Using Invar

```bash
# Check current version
invar version

# Update to new structure
invar update --restructure

# This will:
# 1. Backup existing INVAR.md
# 2. Install new modular structure
# 3. Optionally create skill files (--claude)
# 4. Preserve .invar/context.md (user content)
```

### Backward Compatibility

| Scenario | Handling |
|----------|----------|
| Old INVAR.md | Still works, `invar update` migrates |
| No sections/ | Falls back to inline INVAR.md |
| No skills/ | Works without workflow automation |
| Custom CLAUDE.md | Preserved, user updates manually |

---

## File Size Comparison

### Before

| File | Lines | Loaded |
|------|-------|--------|
| INVAR.md | 464 | Always (full) |
| CLAUDE.md | 260 | Always (full) |
| **Total per session** | **724** | — |

### After

| Context | Files Loaded | Lines |
|---------|--------------|-------|
| Session start | INVAR.md (core) + CLAUDE.md | ~110 |
| /investigate | + sections/investigate.md | +40 |
| /develop | + sections/develop.md | +100 |
| /review | + sections/review.md | +80 |
| Reference needed | + sections/reference.md | +150 |

**Typical session:** ~150-250 lines loaded vs 724 previously.
**Reduction:** 65-80% less irrelevant content.

---

## Implementation Checklist

### Phase 1: Invar Project — Section Files

**For Invar itself (not templates):**
- [ ] Create `/sections/investigate.md`
- [ ] Create `/sections/propose.md`
- [ ] Create `/sections/develop.md`
- [ ] Create `/sections/review.md`
- [ ] Create `/sections/reference.md`
- [ ] Refactor `/INVAR.md` to core (~80 lines) + links to sections
- [ ] Validate all content preserved

### Phase 2: Invar Project — Skill Files

**For Invar itself:**
- [ ] Create `/.claude/skills/investigate/SKILL.md`
- [ ] Create `/.claude/skills/propose/SKILL.md`
- [ ] Create `/.claude/skills/develop/SKILL.md`
- [ ] Create `/.claude/skills/review/SKILL.md`
- [ ] Skills reference `/sections/` content
- [ ] Test workflow triggers
- [ ] Verify instruction re-injection

### Phase 3: Invar Project — CLAUDE.md

- [ ] Reduce `/CLAUDE.md` to ~30 lines
- [ ] Move detailed content to sections/skills
- [ ] Test with fresh conversation
- [ ] Validate Check-In still works

### Phase 4: Templates for Distribution

**For `invar init` on other projects:**
- [ ] Update `src/invar/templates/INVAR.md` (self-contained, no sections/)
- [ ] Create `src/invar/templates/skills/investigate/SKILL.md` (inline instructions)
- [ ] Create `src/invar/templates/skills/propose/SKILL.md`
- [ ] Create `src/invar/templates/skills/develop/SKILL.md`
- [ ] Create `src/invar/templates/skills/review/SKILL.md`
- [ ] Create `src/invar/templates/cursorrules.template`
- [ ] Create `src/invar/templates/CLAUDE.md.template`

### Phase 5: CLI Updates

- [ ] Add `invar init --claude` flag
- [ ] Add `invar init --cursor` flag
- [ ] Update default `invar init` behavior
- [ ] Implement `invar update --restructure` for existing projects
- [ ] Test all flag combinations

### Phase 6: Documentation & Migration

- [ ] Update README.md with new init options
- [ ] Document migration path for existing projects
- [ ] Test migration on sample projects
- [ ] Update docs/INVAR-GUIDE.md if needed

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Context size reduction | >60% | Lines loaded per workflow |
| Check-In compliance | >95% | Visible in first message |
| Workflow recognition | >90% | Agent announces correct workflow |
| Tier 2 usability | Functional | Cursor users can follow protocol |
| Migration success | 100% | Existing projects update cleanly |

---

## Open Questions

### Q1: Section File Location

**Options:**
- A: `sections/` directory alongside INVAR.md
- B: Inside `.invar/sections/`
- C: Embedded in skill files only

**Recommendation:** A — visible, version-controlled, easy to reference.

### Q2: Skill File Maintenance

**Question:** How to keep skill files in sync with sections?

**Recommendation:** Skill files include sections via reference or copy. `invar update` syncs them.

### Q3: INVAR.md Versioning

**Question:** Should modular INVAR.md have different version?

**Recommendation:** Yes, bump to v5.0 to indicate structural change.

---

## Summary

DX-36 restructures Invar documentation to support DX-35's workflow-based phase separation:

| Change | Before | After |
|--------|--------|-------|
| INVAR.md | 464 lines, monolithic | ~80 lines core + sections |
| CLAUDE.md | 260 lines, detailed | ~30 lines, essentials |
| Skills | None | 4 workflow triggers |
| Templates | Basic | Full workflow support |
| Platforms | Claude Code only | Tier 1/2/3 support |

**Key benefits:**
1. **Context efficiency** — Load only relevant instructions
2. **Instruction persistence** — Re-inject at workflow transitions
3. **Platform flexibility** — Tier 2 support via .cursorrules
4. **Cleaner separation** — Protocol (INVAR) vs Project (CLAUDE) vs Workflow (Skills)

---

*Implements documentation layer for DX-35 (Workflow-based Phase Separation).*
