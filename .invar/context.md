# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **PyPI:** `python-invar` v0.1.0
- **Protocol:** v3.17
- **Phase 1-9:** Complete
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
| 10 | Future | Advanced verification (P7, P9, P10, P13) |

## Future Work

See `.invar/proposals/` for detailed proposals:
- **P7:** Semantic contract validation
- **P9:** Context sync command
- **P10:** Contract inheritance
- **P13:** Mechanical vs Reasoning audit
- **P15-P23:** IDE integration, refactoring, etc. (see NEW-PROPOSALS-P15-P23.md)

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol (88 lines) |
| docs/VISION.md | Design philosophy |
| docs/DESIGN.md | Technical architecture |
| CLAUDE.md | Development guide |
| docs/INVAR-DETAILED.md | Full protocol details |

## Archived Documents

Historical documents moved to `docs/archive/`:
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

Full list of 29 lessons in `.invar/proposals/AGENT-IMPROVEMENTS.md` Discussion Log.

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
