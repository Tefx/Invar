# Agent Information Hierarchy

> **Purpose:** Document the layered structure of agent-facing documentation and expected agent reading behavior.
>
> **Created:** 2025-12-30
> **Related:** LX-04 (Multi-Agent Support), DX-54 (Context Management), DX-62 (Task Router)

---

## Overview

Invar uses a 6-layer information hierarchy to ensure agents receive critical rules reliably while providing deeper reference material on demand.

```
L0: System Prompt (CLAUDE.md)     ← 100% read, auto-loaded
L1: Critical Section              ← Highest visibility rules
L2: Session Context (context.md)  ← Check-In requirement
L3: Skill Execution (SKILL.md)    ← Skill tool mechanism
L4: Protocol Reference (INVAR.md) ← On-demand, link-following
L5: Learning Examples (examples/) ← Task Router triggered
```

---

## Information Categories

| Category | Definition | Characteristics | Examples |
|----------|------------|-----------------|----------|
| **Protocol Rules** | What is correct/incorrect | Immutable, authoritative | Six Laws, Contract Rules |
| **Architecture Guide** | How to organize code | Decision algorithms | Core/Shell decision tree |
| **Workflow** | In what order to act | Phase sequences | USBV, Check-In/Final |
| **Behavioral Triggers** | When to do what | Condition → Action | Task Router, Skill Routing |
| **Tool Usage** | What commands to use | Command syntax | invar guard, invar sig |
| **Project State** | What is current context | Dynamic, changing | Current State, Lessons |

---

## File Responsibility Matrix

| File | Protocol | Architecture | Workflow | Triggers | Tools | State |
|------|:--------:|:------------:|:--------:|:--------:|:-----:|:-----:|
| **INVAR.md** | Full | Full | Full | — | Full | — |
| **CLAUDE.md** | Key | Summary | Summary | Full | Key | — |
| **context.md** | Ref | Ref | Ref | Router | Ref | Full |
| **SKILL.md** | — | — | Phase detail | Entry | Phase | — |
| **examples/** | — | Code examples | Process examples | — | — | — |

**Legend:** Full=Complete, Key=Critical subset, Summary=Condensed, Ref=Reference only, —=Not included

---

## Layer Architecture

### L0: System Prompt (CLAUDE.md)

**Read reliability:** 100% (auto-loaded by agent runtime)

Contains:
- Critical Rules table
- Contract Rules (lambda signature, @post scope)
- Core/Shell edge cases
- Skill Routing table
- Task Router reference

### L1: Critical Section

**Location:** `<!--invar:critical-->` in CLAUDE.md

```markdown
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | `invar guard` — NOT pytest, NOT crosshair |
| **Core** | `@pre/@post` + doctests, NO I/O imports |
| **Shell** | Returns `Result[T, E]` from `returns` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

### Contract Rules (CRITICAL)
[lambda signature examples]
[post scope examples]

### Core vs Shell (Edge Cases)
- File/network/env → Shell
- datetime.now(), random → Inject OR Shell
- Pure logic → Core
```

### L2: Session Context (context.md)

**Read reliability:** 80% (requires Check-In compliance)

Contains:
- Key Rules quick reference
- Task Router table (full)
- Current State
- Lessons Learned
- Documentation ownership

### L3: Skill Execution (SKILL.md)

**Read reliability:** 95% (Skill tool mechanism)

Contains:
- Entry Actions (including Task Router reminder)
- USBV phase detailed instructions
- Error handling, timeout policies
- Incremental development patterns

### L4: Protocol Reference (INVAR.md)

**Read reliability:** 40% (link-following dependent)

Contains:
- Six Laws
- Core/Shell complete decision tree
- Contract Rules complete version
- USBV complete definition
- Command reference, configuration, troubleshooting

### L5: Learning Examples (examples/)

**Read reliability:** 60% (Task Router triggered)

Contains:
- contracts.py (Core code examples)
- core_shell.py (Architecture examples)
- functional.py (Functional patterns)
- workflow.md (Complete workflow example)

---

## Redundancy Strategy

### Design Principle

> **Critical information with high error cost must have redundancy at L1.**
> **Non-critical information can remain single-source at L4/L5.**

### Current Redundancy Map

| Information | L1 (CLAUDE.md) | L2 (context.md) | L3 (SKILL.md) | L4 (INVAR.md) |
|-------------|----------------|-----------------|---------------|---------------|
| **Contract Rules** | Full example | — | — | Full |
| **Core/Shell Decision** | Edge cases | Brief | — | Full tree |
| **Task Router** | Reference | Full table | Reminder | — |
| **USBV Workflow** | Brief | Brief | Phase detail | Full |
| **Tool Commands** | Key | Reference | Phase-specific | Full |

### Redundancy Justification

| Information | Error Cost | Usage Frequency | Recommended Redundancy |
|-------------|------------|-----------------|------------------------|
| Contract Rules | High | High | L1 full + L4 authoritative |
| Core/Shell Decision | Medium | Medium | L1 summary + L4 full |
| Task Router | Low-Medium | High | L1 ref + L2 full + L3 reminder |
| USBV Workflow | Low-Medium | Medium | L1 brief + L3 detail |
| Six Laws | Low | Low | L4 only |

---

## Agent Reading Behavior

### Trigger Points

| Trigger | File Read | Reliability | Reason |
|---------|-----------|-------------|--------|
| **Session start** | CLAUDE.md | 100% | Auto-loaded |
| **Check-In** | context.md | 80% | Instruction compliance |
| **Skill call** | SKILL.md | 95% | Tool mechanism |
| **Link following** | INVAR.md | 40% | Agent often skips |
| **Task Router** | examples/ | 60% | Requires active checking |

### Reading Path Diagram

```
Agent Start
    │
    ▼
┌──────────────────┐
│ CLAUDE.md        │◄─────── 100% must-read
│ (L0 + L1)        │
└────────┬─────────┘
         │
         ▼ Check-In instruction
┌──────────────────┐
│ context.md       │◄─────── 80% read rate
│ (L2)             │
└────────┬─────────┘
         │
         ▼ User request "implement X"
┌──────────────────┐
│ Skill("develop") │◄─────── 95% tool call
│ (L3)             │
└────────┬─────────┘
         │
         ├──▶ Entry Actions: "Check Task Router"
         │         │
         │         ▼
         │    ┌──────────────────┐
         │    │ examples/*.py    │◄─── 60% actual read
         │    │ (L5)             │
         │    └──────────────────┘
         │
         └──▶ Core/Shell decision needed
                   │
                   ▼ "Full tree: INVAR.md"
              ┌──────────────────┐
              │ INVAR.md         │◄─── 40% link-following
              │ (L4)             │
              └──────────────────┘
```

---

## Design Rationale

### Why 6 Layers?

1. **L0/L1 separation:** Critical rules must be visible even if agent only reads CLAUDE.md
2. **L2 for session state:** Project-specific context that changes per session
3. **L3 for execution detail:** Skill-specific instructions loaded on-demand
4. **L4 for protocol authority:** Complete reference that doesn't bloat primary files
5. **L5 for learning:** Concrete examples that teach by demonstration

### Why Redundancy at L1?

Agents unreliably follow markdown links. Testing shows:
- 100% read CLAUDE.md
- 40% follow [INVAR.md] links
- 60% check Task Router before coding

Therefore, critical rules (Contract Rules, Core/Shell edge cases) must be at L1.

### Why Task Router at L2?

Task Router is a behavioral trigger (condition → action). It needs:
- High visibility (L1 reference)
- Complete definition (L2 table)
- Execution reminder (L3 Entry Actions)

This 3-layer approach ensures the trigger fires even if one layer is missed.

---

## Validation Criteria

A well-designed information hierarchy should satisfy:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **Critical info at L1** | ✅ | Contract Rules, Core/Shell in CLAUDE.md |
| **Protocol vs Operation separated** | ✅ | INVAR.md (protocol) vs CLAUDE.md (operation) |
| **Single authoritative source** | ✅ | Each info type has one complete location |
| **Minimal necessary redundancy** | ✅ | Only critical info duplicated |
| **Trigger over dependency** | ✅ | Task Router actively triggers vs passive links |

---

## Related Documents

- [LX-04: Multi-Agent Support](../proposals/LX-04-pi-agent-support.md)
- [DX-54: Agent Native Context Management](../proposals/completed/DX-54-agent-context.md)
- [DX-62: Proactive Reference Reading](../proposals/DX-62-proactive-reference.md)

---

*Document created during LX-04 Phase 1.5 implementation.*
