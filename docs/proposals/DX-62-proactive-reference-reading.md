# DX-62: Proactive Reference Reading

**Status:** Partial (Layer 1 Complete)
**Created:** 2024-12-28
**Updated:** 2025-12-31
**Category:** Agent Behavior / Documentation

## Implementation Status

| Layer | Status | Evidence |
|-------|--------|----------|
| Layer 1: Task Router | ✅ Complete | `.invar/context.md` lines 22-32 |
| Layer 2: Pre-Flight | ❌ Not started | No Pre-Flight block in SKILL.md |
| Layer 3: Guard Suggestions | ❌ Not started | No pattern → file mapping in Guard |
| Layer 4: Language Transform | ⚡ Partial | CLAUDE.md uses imperative language |

## Problem Statement

Invar's documentation system references critical files (examples, context, protocol docs), but agents consistently fail to read them proactively. This creates a knowledge gap where agents have access to patterns and guidance but don't utilize them.

### Observed Failure Modes

| Symptom | Root Cause |
|---------|------------|
| Agent writes non-idiomatic code | Didn't read `examples/core.py` |
| Agent asks questions answered in docs | Didn't read `context.md` thoroughly |
| Agent violates project conventions | Didn't read `project-additions.md` references |
| Agent reinvents existing patterns | Didn't read `examples/workflow.md` |

### Why Current Approach Fails

```
Current: Passive References
┌─────────────────────────────────────┐
│ CLAUDE.md                           │
│ ┌─────────────────────────────────┐ │
│ │ Documentation Table             │ │
│ │ | File | Purpose |              │ │  ← Agent sees table
│ │ | examples/ | Must read |       │ │  ← "Must read" is ignored
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
         ↓
    Agent continues without reading
```

**Key Insight:** Tables are informative, not imperative. "Must read" is a suggestion, not a command. Agents optimize for speed, not thoroughness.

---

## Solution: Active Reference Chain

### Core Principle

Transform passive references into **gated checkpoints** that agents must pass through. Use the existing Check-In mechanism as the anchor point.

```
Proposed: Active Reference Chain
┌─────────────────────────────────────┐
│ Check-In (MANDATORY)                │
│ └── Read context.md                 │ ← Already enforced
│     └── Task Router Table           │ ← NEW: Routes to specific files
│         └── "Before X, read Y"      │ ← Imperative, not informative
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Skill Pre-Flight (MANDATORY)        │
│ └── Show confirmation line          │ ← NEW: Visible verification
│     "✓ Pre-Flight: [files] read"    │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Guard Suggestions (REACTIVE)        │
│ └── Pattern detected → suggest file │ ← DX-61 integration
└─────────────────────────────────────┘
```

---

## Implementation

### Layer 1: Context.md Task Router

Add a **Task Router** section to `.invar/context.md` template:

```markdown
## Task Router (Read Before Acting)

| If you are about to... | STOP and read first |
|------------------------|---------------------|
| Write code in `core/` | `.invar/examples/core.py` |
| Write code in `shell/` | `.invar/examples/shell.py` |
| Implement a feature | `.invar/examples/workflow.md` |
| Add `@pre`/`@post` | `.invar/examples/contracts.py` |
| Use functional patterns | `.invar/examples/functional.py` |

**Rule:** If your task matches a row above, read the file BEFORE writing any code.
```

**Why this works:**
- Check-In already forces reading `context.md`
- Task Router is encountered during that read
- Imperative language ("STOP and read") triggers action
- Specific routing prevents "I'll read it later" procrastination

### Layer 2: Skill Pre-Flight Confirmation

Add Pre-Flight block to each SKILL.md:

```markdown
## Pre-Flight (MANDATORY)

Before proceeding past UNDERSTAND phase, confirm:

| Required Reading | Status |
|------------------|--------|
| `.invar/context.md` | ✓ Read at Check-In |
| Task-specific file from Router | ◻ Pending |

**Show confirmation in your response:**
```
✓ Pre-Flight: context.md ✓ | examples/workflow.md ✓
```
```

**Integration with existing workflow:**

```
┌────────────────────────────────────────────────┐
│ Current Check-In                               │
│ ✓ Check-In: MyProject | main | clean           │
├────────────────────────────────────────────────┤
│ NEW Pre-Flight (after UNDERSTAND)              │
│ ✓ Pre-Flight: context.md ✓ | workflow.md ✓    │
├────────────────────────────────────────────────┤
│ Existing Phase Header                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 📍 /develop → SPECIFY (2/4)                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
└────────────────────────────────────────────────┘
```

### Layer 3: Guard Pattern Suggestions (DX-61 Integration)

When Guard detects improvable patterns, include file references:

```
⚠ SUGGEST: Multiple string parameters without type distinction
  Pattern: Use NewType for semantic clarity
  Reference: .invar/examples/functional.py:15-30

⚠ SUGGEST: Validation fails fast instead of accumulating
  Pattern: Use Validation applicative for error collection
  Reference: .invar/examples/functional.py:45-60
```

**This creates a feedback loop:**
1. Agent skips examples → writes suboptimal code
2. Guard catches pattern → suggests specific file + line range
3. Agent reads example → learns pattern
4. Next time: Agent remembers to check examples first

### Layer 4: Language Transformation

Transform all passive references to active imperatives:

| Before (Passive) | After (Active) |
|------------------|----------------|
| "Must read: patterns" | "STOP: Read `examples/core.py` before writing core/ code" |
| "See examples/" | "You MUST read `examples/workflow.md` before implementing" |
| "Refer to INVAR.md" | "Protocol violation? Read INVAR.md section X" |

**Linguistic principle:** Commands > Suggestions > Information

---

## File Changes Required

### 1. Template: context.md.jinja

Add Task Router section after Current State:

```jinja
## Task Router (Read Before Acting)

| If you are about to... | STOP and read first |
|------------------------|---------------------|
| Write code in `core/` | `.invar/examples/core.py` |
| Write code in `shell/` | `.invar/examples/shell.py` |
| Implement a feature | `.invar/examples/workflow.md` |
| Add `@pre`/`@post` | `.invar/examples/contracts.py` |
{%- if functional_examples %}
| Use functional patterns | `.invar/examples/functional.py` |
{%- endif %}

**Rule:** Match found above? Read the file BEFORE writing code.
```

### 2. Template: SKILL.md (all skills)

Add Pre-Flight block after routing announcement:

```markdown
## Pre-Flight

After UNDERSTAND phase, before SPECIFY:

1. Identify which Task Router row matches your task
2. Read the referenced file(s)
3. Show confirmation: `✓ Pre-Flight: [files] ✓`

Skipping Pre-Flight → suboptimal code → Guard warnings → rework
```

### 3. CLAUDE.md Documentation Table

Transform to active language:

```markdown
## Documentation (Action Required)

| File | When to Read | Action |
|------|--------------|--------|
| `.invar/context.md` | Every Check-In | **MANDATORY** |
| `.invar/examples/` | Before writing code | **READ matching example** |
| `INVAR.md` | Protocol questions | Reference as needed |
```

### 4. Guard Output Enhancement (DX-61)

Ensure SUGGEST messages include file references:

```python
class PatternSuggestion:
    pattern_name: str
    description: str
    reference_file: str
    line_range: tuple[int, int] | None
```

---

## Success Metrics

### Measurable Outcomes

| Metric | Before | Target |
|--------|--------|--------|
| Examples read per session | ~0.2 | >1.5 |
| Guard pattern suggestions | High | Decreasing over time |
| "Didn't know about X" incidents | Frequent | Rare |
| Code matching example patterns | ~30% | >80% |

### Verification Method

1. **Session Logs:** Track Pre-Flight confirmations
2. **Guard Stats:** Monitor SUGGEST frequency per pattern
3. **Code Review:** Sample check for example pattern adherence

---

## Rollout Plan

### Phase 1: Context.md Task Router (Low Risk)
- Add Task Router section to context.md template
- Update existing projects via `invar dev sync`
- No behavior change required, just improved guidance

### Phase 2: Pre-Flight Confirmation (Medium Risk)
- Add Pre-Flight blocks to SKILL.md templates
- Agents start showing confirmation lines
- Monitor for workflow friction

### Phase 3: Guard Integration (DX-61 Dependency)
- Implement pattern → file reference mapping
- Add line ranges to SUGGEST messages
- Creates feedback loop for learning

### Phase 4: Language Audit (Low Risk)
- Review all documentation for passive language
- Transform to active imperatives
- Update templates

---

## Design Decisions

### Why Not Make Reading Mandatory via Hooks?

Could implement a PreToolUse hook that blocks code writing until examples are read. Rejected because:

1. **Friction:** Would slow down simple tasks
2. **Gaming:** Agents would "read" files superficially to pass check
3. **Trust:** Protocol should guide, not police

The goal is to create **habits**, not **gates**.

### Why Chain Through context.md?

Context.md is already a mandatory read (Check-In). Using it as the routing hub means:

1. No new mandatory reads to add
2. Single source of truth for "what to read when"
3. Project-specific customization (each project's context.md can have different routing)

### Why Show Pre-Flight Confirmation?

Visibility creates accountability:

1. User sees what agent read (or didn't)
2. Agent commits publicly to having read files
3. Missing confirmation = obvious red flag

---

## Alternatives Considered

### Alternative A: Inline All Examples in CLAUDE.md

**Rejected:** Would bloat CLAUDE.md massively. Agents need full files for context, not snippets.

### Alternative B: Memory-Based Tracking

**Deferred:** Could use claude-mem to track what's been read and prompt for unread files. Good enhancement but adds complexity. Consider for future iteration.

### Alternative C: Quiz-Based Verification

**Rejected:** Could require agents to answer questions about file contents before proceeding. Too gameable and adds friction without value.

---

## Appendix: Example Session Flow

```
User: Add a new validation function to the user module

Agent:
✓ Check-In: MyProject | feature/validation | clean

[Reads context.md, sees Task Router]
[Task: "Write code in core/" → Read examples/core.py]
[Task: "Add @pre/@post" → Read examples/contracts.py]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → UNDERSTAND (1/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Analyzes requirements]

✓ Pre-Flight: context.md ✓ | core.py ✓ | contracts.py ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Writes contracts following examples/contracts.py patterns]
[Code matches examples/core.py style]

... continues with high-quality implementation ...

✓ Final: guard PASS | 0 errors, 0 warnings
```

---

## References

- DX-54: Agent-Native Context Management (Check-In protocol)
- DX-51: Workflow Phase Visibility (Phase headers)
- DX-61: Functional Pattern Guidance (Guard suggestions)
- DX-30: Visible Workflow (TodoList checkpoints)
