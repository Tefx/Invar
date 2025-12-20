# Agent-Native Improvements Summary

*Created: 2025-12-19*
*Updated: 2025-12-20*
*Status: Phase 9-11 Complete, Proposals Closed*

---

## Completion Summary

### v0.1.0 (Phase 9)

| ID | Proposal | Status |
|----|----------|--------|
| P1 | Relaxed limits (500L) + config-level exclusions | Complete |
| P2 | Severity configuration + `--pedantic` | Complete |
| P3 | RULE_META system + `invar rules` | Complete |
| P4 | Lambda skeleton templates | Complete |
| P5 | Always-on hints + `--explain` | Complete |
| P6 | Protocol compression (88 lines) | Complete |
| P8 | File size warnings at 80% | Complete |
| P11 | INVAR_MODE env auto-detection | Complete |
| P12 | `strict_pure` default ON | Complete |
| P14 | Automatic inspection in `--changed` | Complete |

### v0.2.0 (Phase 10-11)

| ID | Proposal | Status |
|----|----------|--------|
| P7 | Semantic tautology detection | Complete |
| P17 | Forbidden import alternatives | Complete |
| P18 | Function groups in size warnings | Complete |
| P19 | Doctest/code line breakdown | Complete |
| P24 | Contract coverage statistics | Complete |
| P25 | Automatic extraction analysis | Complete |
| P27 | Pattern alternatives in suggestions | Complete |
| P28 | Partial contract detection | Complete |

---

## Closed Proposals

### P9: Context Sync Command
**Decision:** Rejected
**Reason:** Solves non-problem. Manual context.md update works fine. Violates "Automatic > Opt-in" - adding commands increases cognitive load.

### P10: Contract Inheritance (Liskov)
**Decision:** Deferred indefinitely
**Reason:** High implementation cost (cross-file analysis, multiple inheritance), low frequency issue. Invar codebase has minimal inheritance.

### P13: Mechanical vs Reasoning Audit
**Decision:** Closed as done
**Reason:** The spirit of this audit is already embedded in development practice. P4, P25, P27, P28 are all products of this thinking.

### P15: IDE/LSP Integration
**Decision:** Out of scope
**Reason:** Human-centric feature, not Agent-Native. Agents batch changes and run Guard once; don't benefit from "as you type" feedback. High effort, low value for primary user (Agent).

### P16: API Usage Examples
**Decision:** Duplicate
**Reason:** Doctests already serve as usage examples AND verification. No additional value.

### P20: Proactive Plan Command
**Decision:** Out of scope
**Reason:** Invar is verification (Guard) + perception (map/sig). Planning is Agent reasoning work, not tool work.

### P21: Contract Inference
**Decision:** Rejected
**Reason:** Crosses Guard/Agent boundary. Guard can suggest patterns (P27), but choosing correct constraints requires semantic understanding - that's Agent's job.

### P22: Automated Refactoring
**Decision:** Rejected
**Reason:** Refactoring requires semantic judgment (naming, API design). Guard can identify WHEN (P8) and suggest WHAT (P25), but HOW is Agent's job.

### P23: Cross-Session Memory
**Decision:** Out of scope
**Reason:** Memory is LLM infrastructure responsibility, not verification tool's job. context.md already works.

---

## Key Principles Established

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Guard/Agent Boundary** - Guard does mechanical analysis, Agent does semantic reasoning
4. **Facts Only** - Report distribution, don't judge "strength"
5. **Sufficient Context > Concise** - Agent needs info to decide, not minimal output
6. **Single Source of Truth** - RULE_META for all rule information

---

## Historical Details

Detailed proposal discussions archived in `docs/archive/proposals-detailed-2025.md`
