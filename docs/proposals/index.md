# Invar Proposals Index

> **Last Updated:** 2026-03-13
> **Current Direction:** [DX-91: Simplification](./DX-91-simplification.md) — Python-only, guard-first architecture

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- `LX-XX-name.md` — Language eXtension (historically TypeScript/multi-language; now deferred)
- Completed/archived proposals in `completed/` subdirectory

---

## Strategic Direction: DX-91 Simplification

**[DX-91: Invar Simplification](./DX-91-simplification.md)** defines the current architectural direction:

| Aspect | Pre-DX-91 | Post-DX-91 |
|--------|-----------|------------|
| **Scope** | Python + TypeScript + Multi-agent | Python-only |
| **Workflow** | USBV four-phase with ceremony | Guard-enforced, minimal ceremony |
| **Agent Support** | Claude Code-specific (skills, hooks) | Agent-agnostic (MCP + contracts) |
| **Instruction Surface** | ~200 lines in CLAUDE.md + skills + hooks | ~50 lines in CLAUDE.md + INVAR.md |
| **Core Value** | guard, sig, map, refs, Core/Shell, @pre/@post | Same core, less baggage |

### Related DX-91 Documents

| Document | Purpose |
|----------|---------|
| [DX-91-simplification.md](./DX-91-simplification.md) | Main proposal — what to keep/remove |
| [DX-91-invar-md-draft.md](./DX-91-invar-md-draft.md) | Draft INVAR.md structure |
| [DX-91-claude-md-draft.md](./DX-91-claude-md-draft.md) | Draft CLAUDE.md content |
| [DX-91-migration-semantics.md](./DX-91-migration-semantics.md) | v1 → v2 migration behavior |
| [DX-91-generated-file-contracts.md](./DX-91-generated-file-contracts.md) | Contract for init-generated files |
| [DX-91-freeze-spec-baseline.md](./DX-91-freeze-spec-baseline.md) | Pre-implementation spec freeze |

---

## Open Proposals (13)

### Active Implementation

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-91 | [invar-simplification](DX-91-simplification.md) | **Active** | Python-only, guard-first architecture with minimal agent instruction surface |
| DX-94 | [mcp-full-guard-support-model](DX-94-mcp-full-guard-support-model.md) | Draft | Deferred full-scan model for MCP timeout-safe `invar_guard(changed=false)` |
| DX-84 | [security-review-backlog](DX-84-security-review-backlog.md) | Active | Security review backlog for Python Guard |
| DX-80 | [guard-cli-mcp-alignment](DX-80-guard-cli-mcp-alignment.md) | Draft | Align Guard CLI default behavior with MCP |

### Deferred / Future

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-83 | [multi-agent-subagent-support](DX-83-multi-agent-subagent-support.md) | Draft | Subagent support (superseded by DX-91 simplification) |
| DX-68 | [agent-behavior-optimization](DX-68-agent-behavior-optimization.md) | Draft | Agent reading reliability improvements |
| DX-62 | [proactive-reference-reading](DX-62-proactive-reference-reading.md) | Partial | Task Router (Layer 1) done, Layers 2-4 pending |
| DX-61 | [functional-pattern-guidance](DX-61-functional-pattern-guidance.md) | Draft | Teach agents functional patterns |
| DX-60 | [structured-rules-ssot](DX-60-structured-rules-ssot.md) | Draft | Optimize rule token usage |
| DX-38 | [contract-quality-rules](DX-38-contract-quality-rules.md) | Partial | Tier 1-2 done, Tier 3-4 deferred |
| DX-29 | [pure-content-detection](DX-29-pure-content-detection.md) | Defer | Pure content detection marker |
| DX-25 | [functional-patterns](DX-25-functional-patterns.md) | Defer | Functional patterns enhancement |

### Legacy / Pre-DX-91 (Archived Concepts)

> These proposals describe features removed or superseded by DX-91.
> They remain in the index for historical reference but do not describe current behavior.

| ID | Name | Status | Notes |
|----|------|--------|-------|
| DX-85 | [opencode-support](DX-85-opencode-support.md) | Superseded | Native OpenCode init — see DX-91 for simplified approach |
| DX-79 | [invar-usage-feedback](DX-79-invar-usage-feedback.md) | Removed | Feedback collection removed per DX-91 |
| LX-13 | [typescript-runtime-optimization](LX-13-typescript-runtime-optimization.md) | **Removed** | TypeScript support removed per DX-91 |
| LX-09 | [legacy-onboarding](LX-09-legacy-onboarding.md) | **Removed** | Onboarding system removed per DX-91 |
| LX-08 | extension-skills-future | **Removed** | Skills system removed per DX-91 |
| LX-17 | [haskell-elm-feasibility](LX-17-haskell-elm-feasibility.md) | Deferred | Multi-language exploration on hold |
| LX-17 | [implementation-matrix](LX-17-implementation-matrix.md) | Deferred | Implementation matrix |
| LX-17 | [summary](LX-17-summary.md) | Deferred | Go & Rust feasibility summary |
| LX-16 | [typescript-guard-remaining-gap](LX-16-typescript-guard-remaining-gap.md) | **Removed** | TypeScript Guard removed per DX-91 |
| LX-11 | [cursor-support](LX-11-cursor-support.md) | Deferred | IDE expansion on hold |
| LX-01 | [multi-language-feasibility](LX-01-multi-language-feasibility.md) | Deferred | Multi-language exploration on hold |

---

## Archived Proposals (completed/)

> All completed proposals have been moved to `completed/` directory.

See `completed/` directory for detailed implementation notes. Key archived milestones:

- **v1.15.0**: Multi-agent init support (DX-81) — _superseded by DX-91_
- **v1.12.0**: MCP protocol sync (DX-78)
- **v1.11.0**: TypeScript Guard parity (LX-15) — _removed per DX-91_
- **v1.9.0**: Extension skills architecture (LX-07) — _removed per DX-91_
- **v1.7.0**: Pi agent support (LX-04) — _simplified per DX-91_

---

## Statistics

| Category | Count |
|----------|-------|
| **Active** | 4 |
| **Deferred** | 8 |
| **Legacy/Removed** | 11 |
| **Archived** | 78 |
| **Total** | 101 |

---

## Priority Recommendations

### High Priority (Actionable Now)

1. **[DX-91](./DX-91-simplification.md)** — Strategic simplification and product reset
2. **[DX-84](./DX-84-security-review-backlog.md)** — Security review for production readiness
3. **[DX-80](./DX-80-guard-cli-mcp-alignment.md)** — CLI/MCP alignment bug fix

### Medium Priority (Strategic)

1. **[DX-62](./DX-62-proactive-reference-reading.md)** — Continue Layers 2-4
2. **[DX-61](./DX-61-functional-pattern-guidance.md)** — Pattern guidance for agents

### Low Priority / Deferred

- DX-68, DX-60, DX-38, DX-29, DX-25, LX-17 series, LX-11, LX-01

---

## Historical Reference

See `completed/` directory for detailed implementation notes and execution history of archived proposals.

**Pre-DX-91 Concepts (for historical context):**

- **USBV Workflow**: Four-phase protocol (Understand → Specify → Build → Validate) — _ceremony removed per DX-91, core intent preserved as "contracts before code"_
- **Skills System**: `.claude/skills/` with 8 skills — _removed per DX-91_
- **Hooks**: PreToolUse, PostToolUse, Stop, UserPromptSubmit — _removed per DX-91_
- **TypeScript Support**: Full TS/JS guard and verification — _removed per DX-91_

---

## Cross-Reference: Active Navigation

| Document | Relevance Post-DX-91 |
|----------|----------------------|
| `CLAUDE.md` (project root) | **Active** — DX-91 managed block (~50 lines) |
| `INVAR.md` (project root) | **Active** — Agent semantic spec |
| [DX-91-simplification.md](./DX-91-simplification.md) | **Active** — Authoritative direction |
| `docs/reference/workflow/usbv.md` | **Archive** — Historical USBV documentation |
| `docs/AGENTS.md` | **Archive** — Pre-DX-91 agent roles (skills/hooks era) |
| `docs/reference/index.md` | **Update needed** — Contains USBV references |
| `README.md` | **Update needed** — Contains legacy workflow descriptions |
