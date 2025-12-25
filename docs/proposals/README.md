# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- Archived proposals in `archive/` subdirectory

## Active Proposals (14)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-11 | documentation-restructure | Draft | Documentation restructure for multi-agent support |
| DX-23 | entry-point-detection | Draft | Entry point 检测与 Monad Runner 模式 |
| DX-24 | mechanism-documentation | Draft | Mechanism documentation |
| DX-25 | functional-patterns | Draft | Functional patterns enhancement |
| DX-27 | system-prompt-protocol | Proposed | System prompt protocol entry |
| DX-29 | pure-content-detection | Proposed | Pure content detection |
| DX-32 | workflow-iteration | Proposed | USBV workflow (ICIDIV iteration) |
| DX-37 | coverage-integration | Draft | Coverage integration for Guard |
| DX-38 | contract-quality-rules | Draft | Contract quality rules (Tier 1-4) |
| DX-39 | workflow-efficiency | Draft | Workflow efficiency improvements |
| DX-40 | smart-tool-redirect-hook | Draft | Smart tool redirect hook (from DX-16) |
| DX-41 | automatic-review-orchestration | Draft | Automatic review orchestration (from DX-31+35) |
| DX-42 | workflow-auto-routing | Draft | Workflow auto-routing (from DX-35) |
| DX-43 | cross-platform-distribution | Draft | Cross-platform distribution (from DX-35+36) |

## Archived Proposals (18)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-12 | hypothesis-fallback | ✅ Implemented | Hypothesis as CrossHair fallback |
| DX-13 | incremental-prove | ✅ Implemented | Incremental CrossHair verification |
| DX-14 | expanded-prove-usage | ✅ Implemented | Expanded --prove usage |
| DX-16 | agent-tool-enforcement | ✅ Complete | MCP server (Phase 2 → DX-40) |
| DX-17 | workflow-enforcement | ✅ Evolved | Check-In format |
| DX-20 | property-testing-enhancements | Draft | Property testing UX |
| DX-21 | package-and-init | ✅ Implemented | Two-package architecture |
| DX-22 | verification-strategy | ✅ Implemented | Smart routing, Shell rules |
| DX-26 | guard-simplification | ✅ Implemented | Guard CLI simplification |
| DX-28 | semantic-verification | ✅ Complete | @relates, format specs (P2 → DX-38) |
| DX-30 | visible-workflow | ✅ Complete | TodoList convention |
| DX-31 | adversarial-reviewer | ✅ Complete | /review skill (Phase 2 → DX-41) |
| DX-33 | verification-blind-spots | ✅ Complete | Analysis (→ DX-37, DX-38) |
| DX-34 | review-cycle | Superseded | → DX-35 |
| DX-35 | workflow-phase-separation | ✅ Complete | Workflow skills (Phase 3-5 → DX-41/42/43) |
| DX-36 | documentation-restructuring | ✅ Complete | Sections (Phase 5-6 → DX-43) |

## Priority Recommendations

| Priority | Proposal | Rationale |
|----------|----------|-----------|
| **High** | DX-41 | Automatic review orchestration — core workflow enhancement |
| **High** | DX-43 | Cross-platform distribution — expand Invar reach |
| **Medium** | DX-42 | Workflow auto-routing — UX improvement |
| **Medium** | DX-37 | Coverage integration — verification enhancement |
| **Low** | DX-38 | Contract quality rules — high risk, needs careful design |
| **Low** | DX-40 | Smart tool redirect — incremental optimization |
