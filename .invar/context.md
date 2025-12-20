# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **PyPI:** `python-invar` v0.1.0
- **Protocol:** v3.17
- **Phase 1-10:** Complete
- **Blockers:** None

## Core Principle

> **"Agent-Native Execution, Human-Directed Purpose"**

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

- Protocol and Tools are Agent-Native (Agent is primary user)
- Ultimate goal is Human success through Agent effectiveness
- See `docs/VISION.md` for full philosophy

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1-8 | Complete | Core Guard, Perception, Agent-Native features |
| 9 | Complete | PyPI release, CI/CD, documentation |
| 10 | Complete | P7 (tautology detection), P17, P18, P19 |

## Phase 11 Plan

Based on Phase 10 development experience and detailed design discussions.

### Approved for Implementation

**P24: Contract Coverage Statistics** (Priority: Low)
```
Design: Simplified from "strength scoring" to pure statistics
Original idea: Score contracts as STRONG/MODERATE/WEAK
Problem: "Strength" requires semantic understanding (Guard can't do)
Simplified: Just report distribution, no judgment

Output in Guard summary:
  Contract coverage: 90% (45/50 functions)
  Issues: 3 tautology, 5 type-check only

Principle: Facts only, no subjective "strength" rating
```

**P25: Automatic Extraction Analysis** (Priority: High)
```
Design: Guard enhancement, NOT a separate command
Trigger: file_size >= warning_threshold
Output:
  - Default: one-line summary of extractable groups
  - --agent: full JSON with dependency analysis
Principle: Automatic > Opt-in (no new command to remember)
```

**P27: Enhanced Context for Agent Decision** (Priority: Medium)
```
Design: Improve suggestion quality, NOT auto-fix
Changes:
  1. Suggestion wording: "Add X" → "Patterns: X | Y | Z"
  2. Include docstring/param info in --agent output
  3. Mark confidence level (HIGH/MEDIUM/LOW)
Principle: Guard provides options, Agent decides
```

### Under Consideration

- **P26:** `invar check-contract <file>:<line>` for deep analysis

### Key Design Decisions (Phase 11)

1. **Guard vs Agent boundary**: Guard does mechanical analysis, Agent does semantic reasoning
2. **No auto-fix**: Guard doesn't know correct answers, only patterns
3. **Automatic embedding**: New info appears in existing output, not new commands

See `.invar/proposals/` for historical details.

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol (90 lines) |
| docs/INVAR-GUIDE.md | Why & How (130 lines) |
| docs/VISION.md | Design philosophy |
| CLAUDE.md | Development guide |

## Archived Documents

Historical documents moved to `docs/archive/`:
- INVAR-DETAILED-v3.16.md (superseded by compressed protocol + Guard hints)
- VISION-ORIGINAL.md (pre-revision)
- PHASE3_REVIEW.md
- FIRST_PRINCIPLES_REVIEW.md
- PROTOCOL_EVOLUTION.md
- decisions-2024.md

## Lessons Learned (Key Insights)

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Documentation ≠ Behavior** - Only automatic mechanisms change behavior
4. **Don't Force, Show** - Auto-embed info in output agents will see
5. **Formal compliance ≠ verification** - `@pre(lambda: True)` is worthless
6. **Mechanical vs Reasoning** - Tool time for mechanics, Agent time for reasoning
7. **Protocol compression** - Info in commands/hints doesn't need to be in protocol
8. **Meta-detection works** - P7 caught tautologies in its own implementation
9. **Guard provides options, not answers** - Guard can't understand business semantics
10. **New commands = cognitive load** - Enhance existing commands instead

Full list in `.invar/proposals/AGENT-IMPROVEMENTS.md` Discussion Log.

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
