# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **PyPI:** `python-invar` v0.2.2
- **Protocol:** v3.17
- **Phase 1-11:** Complete
- **Status:** Feature complete, ready for external testing
- **Blockers:** None

## Core Principle

> **"Agent-Native Execution, Human-Directed Purpose"**

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

- Protocol and Tools are Agent-Native (Agent is primary user)
- Ultimate goal is Human success through Agent effectiveness
- See `docs/VISION.md` for full philosophy

## Implementation Summary

| Phase | Status | Key Features |
|-------|--------|--------------|
| 1-8 | Complete | Guard, Perception (map/sig), Agent-Native defaults |
| 9 | Complete | PyPI release, RULE_META, Protocol compression |
| 10 | Complete | Tautology detection (P7), Import alternatives (P17) |
| 11 | Complete | Coverage stats (P24), Extraction analysis (P25), Pattern alternatives (P27), Partial contract detection (P28) |

## Version Roadmap

| Version | Status | Scope |
|---------|--------|-------|
| 0.1.0 | Released | Phase 9 (PyPI, core features) |
| 0.2.0 | Ready | Phase 10-11 (Agent decision support) |
| 1.0.0 | Pending | After external project testing |

## Next Steps

1. Test on new external project
2. Collect real usage feedback
3. Release 0.2.0 if testing successful
4. Consider 1.0.0 after proven stable

## Proposals Status

All proposals closed. See `.invar/proposals/AGENT-IMPROVEMENTS.md` for summary.

**Rejected/Deferred:**
- P9 (Context Sync): Solves non-problem
- P10 (Liskov): Too complex for rare case
- P15 (LSP): Human-centric, not Agent-Native
- P21 (Inference): Crosses Guard/Agent boundary
- P22 (Refactor): Requires semantic judgment

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol (88 lines) |
| docs/INVAR-GUIDE.md | Why & How (130 lines) |
| docs/VISION.md | Design philosophy |
| CLAUDE.md | Development guide |

## Archived Documents

Historical documents in `docs/archive/`:
- INVAR-DETAILED-v3.16.md
- proposals-P15-P23-2025.md
- proposals-phase9-reflection-2025.md
- VISION-ORIGINAL.md, decisions-2024.md, etc.

## Lessons Learned

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Guard/Agent Boundary** - Guard does mechanical analysis, Agent does reasoning
4. **Facts Only** - Report facts, don't judge "strength" or "quality"
5. **Sufficient Context > Concise** - Agent needs info to decide

---

*Update this file when: completing phases, making design decisions, releasing versions.*
