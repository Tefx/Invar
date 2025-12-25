# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- Completed/archived proposals in `completed/` subdirectory

## Active Proposals (13)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-23 | entry-point-detection | Draft | Entry point detection & Monad Runner pattern |
| DX-25 | functional-patterns | Draft | Functional patterns enhancement |
| DX-29 | pure-content-detection | Proposed | Pure content detection (`@invar:module` marker) |
| DX-37 | coverage-integration | Draft | Coverage integration for Guard |
| DX-38 | contract-quality-rules | Draft | Contract quality rules (Tier 1-4) |
| DX-39 | workflow-efficiency | Draft | Workflow efficiency (merged DX-27) |
| DX-40 | smart-tool-redirect-hook | Draft | Smart tool redirect hook (from DX-16) |
| DX-41 | automatic-review-orchestration | Draft | Automatic review orchestration (from DX-31+35) |
| DX-42 | workflow-auto-routing | Draft | Auto-routing + autonomous orchestration |
| DX-43 | cross-platform-distribution | Draft | Cross-platform distribution (from DX-35+36+11) |
| DX-45 | template-consistency | Draft | **NEW** Template sync checking |
| DX-46 | documentation-audit | Draft | **NEW** Documentation freshness audit |
| DX-47 | command-skill-naming | Draft | **NEW** Review command vs skill naming |

## Archived Proposals (22)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-11 | documentation-restructure | ✅ Mostly Implemented | Multi-agent support (remnants → DX-43) |
| DX-12 | hypothesis-fallback | ✅ Implemented | Hypothesis as CrossHair fallback |
| DX-13 | incremental-prove | ✅ Implemented | Incremental CrossHair verification |
| DX-14 | expanded-prove-usage | ✅ Implemented | Expanded --prove usage |
| DX-16 | agent-tool-enforcement | ✅ Complete | MCP server (Phase 2 → DX-40) |
| DX-17 | workflow-enforcement | ✅ Evolved | Check-In format |
| DX-20 | property-testing-enhancements | Draft | Property testing UX |
| DX-21 | package-and-init | ✅ Implemented | Two-package architecture |
| DX-22 | verification-strategy | ✅ Implemented | Smart routing, Shell rules |
| DX-24 | mechanism-documentation | ✅ Complete | 13/13 mechanism docs created |
| DX-26 | guard-simplification | ✅ Implemented | Guard CLI simplification |
| DX-27 | system-prompt-protocol | ✅ Merged | → DX-39 (Output Style feature) |
| DX-28 | semantic-verification | ✅ Complete | @relates, format specs (P2 → DX-38) |
| DX-30 | visible-workflow | ✅ Complete | TodoList convention |
| DX-31 | adversarial-reviewer | ✅ Complete | /review skill (Phase 2 → DX-41) |
| DX-32 | workflow-iteration | ✅ Implemented | USBV is now standard workflow |
| DX-33 | verification-blind-spots | ✅ Complete | Analysis (→ DX-37, DX-38) |
| DX-34 | review-cycle | Superseded | → DX-35 |
| DX-35 | workflow-phase-separation | ✅ Complete | Workflow skills (Phase 3-5 → DX-41/42/43) |
| DX-36 | documentation-restructuring | ✅ Complete | Sections (Phase 5-6 → DX-43) |

## Priority Recommendations

| Priority | Proposal | Rationale |
|----------|----------|-----------|
| **High** | DX-42 | Auto-routing + orchestration — users can't invoke skills |
| **High** | DX-41 | Automatic review orchestration — closes VALIDATE loop |
| **High** | DX-45 | Template consistency — prevents drift |
| **Medium** | DX-39 | Workflow efficiency — direct UX improvement |
| **Medium** | DX-43 | Cross-platform distribution — expand reach |
| **Medium** | DX-37 | Coverage integration — verification enhancement |
| **Medium** | DX-47 | Command/skill naming — reduce confusion |
| **Low** | DX-46 | Documentation audit — maintenance task |
| **Low** | DX-38 | Contract quality rules — high risk |
| **Low** | DX-40 | Smart tool redirect — incremental |
| **Low** | DX-23, DX-25, DX-29 | Architecture enhancements |

## Recent Changes (2025-12-25)

### New Proposals
- **DX-45** — Template consistency (pre-commit hook, sync commands)
- **DX-46** — Documentation audit (stale content detection)
- **DX-47** — Command vs skill naming clarification

### Updated
- **DX-42** — Expanded with autonomous orchestration, skill invocation issue

### Archived
- **DX-11** — Mostly implemented, `invar migrate` → DX-43
- **DX-24** — Self-reported 100% complete
- **DX-27** — Merged into DX-39 as Output Style feature
- **DX-32** — USBV implemented as standard workflow

### Merged
- **DX-27 → DX-39** — System prompt protocol entry
- **DX-11 remnants → DX-43** — `invar migrate` command

## Key Discoveries

1. **Skills cannot be user-invoked** — Users get "Ask Claude to run /develop for you"
2. **Command vs Skill confusion** — `/review` exists as both with different behavior
3. **Template drift risk** — Project files and templates can diverge
