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

## Future Work (Phase 11 Ideas)

Potential improvements from Phase 10 development:
- **P24:** Contract strength scoring (meaningful > type-check > tautology)
- **P25:** Auto-extraction hints when files approach size limits
- **P26:** `invar check-contract <file>:<line>` for deep analysis
- **P27:** `invar guard --fix` for auto-fixing simple issues

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

Full list of 29 lessons in `.invar/proposals/AGENT-IMPROVEMENTS.md` Discussion Log.

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
