# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- Completed/archived proposals in `completed/` subdirectory

## Active Proposals (11)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-23 | entry-point-detection | Defer | Entry point detection & Monad Runner pattern |
| DX-25 | functional-patterns | Defer | Functional patterns enhancement |
| DX-29 | pure-content-detection | Defer | Pure content detection (`@invar:module` marker) |
| DX-37 | coverage-integration | Draft | Coverage integration for Guard |
| DX-38 | contract-quality-rules | Defer | Contract quality rules (Tier 1-4) |
| DX-39 | workflow-efficiency | Draft | Workflow efficiency (merged DX-27) |
| DX-40 | smart-tool-redirect-hook | Draft | Smart tool redirect hook (from DX-16) |
| DX-41 | automatic-review-orchestration | Draft | Automatic review orchestration (from DX-31+35) |
| DX-42 | workflow-auto-routing | Draft | Auto-routing + autonomous orchestration |
| DX-43 | cross-platform-distribution | Draft | Cross-platform distribution (from DX-35+36+11) |
| DX-46 | documentation-audit | Draft | docs/ directory audit + `invar check-docs` |

## Archived Proposals (26)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-48 | code-structure-reorganization | ✅ Complete | Dead code + shell/ restructure done |
| DX-49 | protocol-distribution-unification | ✅ Complete | SSOT for INVAR.md, CLAUDE.md, skills/ |
| DX-11 | documentation-restructure | ✅ Mostly Implemented | Multi-agent support (remnants → DX-43) |
| DX-45 | template-consistency | Superseded | → DX-49 (SSOT) |
| DX-47 | command-skill-naming | ✅ Implemented | /audit, /guard commands; /review skill |
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

## Dependency Graph

```
      ✅ DX-49 (SSOT)                 DX-42 (Auto-routing)
              │                               │
              ▼                       ┌───────┴───────┐
      DX-43 (Cross-platform)          ▼               ▼
                              DX-41 (Auto-review)  DX-39 (Efficiency)
                                      │
                                      ▼
                              DX-40 (Tool redirect)

Completed: DX-47, DX-48, DX-49
Independent: DX-37 (Coverage), DX-46 (docs/ audit)
Deferred: DX-38, DX-23, DX-25, DX-29
```

## Priority Recommendations

| Priority | Proposal | Description | Rationale | Deps |
|----------|----------|-------------|-----------|------|
| **High** | DX-42 | Agent auto-identifies task intent and routes to correct workflow | Users cannot invoke skills directly | — |
| **High** | DX-41 | Auto-trigger /review skill when Guard outputs `review_suggested` | Close VALIDATE phase loop | DX-42 |
| **High** | DX-39 | Skill session cache, USBV SPECIFY enforcement, workflow transition | Reduce token waste | DX-42 |
| **Medium** | DX-43 | `invar init --cursor` generates .cursorrules | Cross-platform expansion | ✅ DX-49 |
| **Medium** | DX-37 | `invar guard --coverage` reports uncovered branches | Verification visibility | — |
| **Low** | DX-46 | docs/ directory audit + `invar check-docs` command | Documentation maintenance | — |
| **Low** | DX-40 | Hook intercepts incorrect tool calls | Tool enforcement | DX-42 |
| **Defer** | DX-38 | Tier 1-4 contract quality detection | High false-positive risk | — |
| **Defer** | DX-23 | Framework callback auto-exempt from Result requirement | DX-22 already covers | — |
| **Defer** | DX-25 | Validation error accumulation, Monoid, etc. | Non-essential major change | — |
| **Defer** | DX-29 | `@invar:module` explicit marker | DX-22 sufficient | — |

## Recommended Execution Order

| Wave | Proposals | Parallel? | Effort | Goal |
|------|-----------|-----------|--------|------|
| ~~0~~ | ~~DX-47, DX-48, DX-49~~ | — | — | ✅ Complete |
| **1** | DX-42 | — | 3 days | Core auto-routing |
| **2** | DX-43 ∥ DX-41 | ✅ Both parallel | 1-2 days | Feature completion |
| **3** | DX-39 | — | 1-2 days | Efficiency optimization |
| **4** | DX-46 ∥ DX-37 | ✅ Both parallel | 1 day | Quality enhancement |
| **5** | DX-40 | — | 0.5 day | Tool enforcement (optional) |
| **∞** | DX-38, DX-23, DX-25, DX-29 | — | — | Deferred |

**Time estimate:** Serial ~7 days, optimized parallel ~4-5 days

**Critical path:** DX-42 → DX-41 → DX-39 → DX-40

## Recent Changes (2025-12-26)

### Completed
- **DX-48** — Complete (Phase 1 + DX-48b-lite)
  - Phase 1: Deleted 664 lines dead code
  - DX-48b-lite: Created `shell/commands/` and `shell/prove/` subdirectories
  - Moved 10 files, updated ~40 imports
  - Full core/ restructuring deferred (high risk, low value)

- **DX-49** — Complete (Phase 1-10)
  - templates/ = single source, all project files generated
  - Deleted sections/, merged into skills/
  - Jinja2 templates with MCP/CLI syntax switching
  - Three-region architecture (managed/project/user for CLAUDE.md, skill/extensions for skills)
  - sync-self with project-additions.md injection
  - Phase 8: Template system testing (init, sync-self, syntax switching)
  - Phase 9: Documentation deep review (INVAR.md, CLAUDE.md, Skills)
  - Phase 10: Final validation (guard pass, link check)
  - **Fixes applied:**
    - Added workflow.md to examples (was missing)
    - Fixed INVAR.md Check-In to use CLI syntax
    - Skills now always created by `invar init` (not just --claude)

### Archived
- **DX-45** → Superseded by DX-49

### Scope Changes
- **DX-46** — Scope reduced to docs/ directory audit (INVAR/CLAUDE/sections → DX-49)

### Priority Re-evaluation
- **DX-47** ↑↑ → **Critical** (blocks DX-49 and DX-42)
- **DX-49** → **High** (eliminate version divergence)
- **DX-42** → **High** (users cannot invoke skills directly)
- **DX-39** ↑ → **High** (efficiency optimization)
- **DX-38, DX-23, DX-25, DX-29** → **Defer**

### Execution Order Optimization
- Wave 2: DX-49 ∥ DX-42 can parallel (both only depend on DX-47)
- Wave 3: DX-43 ∥ DX-41 can parallel
- Time optimization: serial 10 days → parallel 6-8 days

## Changes (2025-12-25)

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
