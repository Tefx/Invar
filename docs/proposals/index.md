# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- Completed/archived proposals in `completed/` subdirectory

## Active Proposals (11)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-23 | entry-point-detection | ✅ Complete | Entry point detection & Monad Runner pattern |
| DX-25 | functional-patterns | Defer | Functional patterns enhancement |
| DX-29 | pure-content-detection | Defer | Pure content detection (`@invar:module` marker) |
| DX-37 | coverage-integration | ✅ Complete | Coverage integration for Guard (`--coverage` flag) |
| DX-38 | contract-quality-rules | Partial | Tier 1-2 done, Tier 3-4 deferred |
| DX-39 | workflow-efficiency | ✅ Complete | Error Pattern Guide + bug fixes |
| DX-40 | smart-tool-redirect-hook | ✗ Dropped | Contradicts Lesson #19 (PreToolUse ineffective) |
| DX-41 | automatic-review-orchestration | ✅ Complete | Automatic review orchestration (from DX-31+35) |
| DX-42 | workflow-auto-routing | ✅ Complete | Visible Workflow Routing |
| DX-43 | cross-platform-distribution | ✅ Complete | Absorbed by DX-49 |
| DX-46 | documentation-audit | ✅ Complete | docs/ directory audit |
| DX-51 | workflow-phase-visibility | ✅ Complete | USBV phase headers separate from TodoWrite |
| DX-52 | venv-dependency-injection | ✅ Complete | PYTHONPATH injection for uvx compatibility |
| DX-53 | review-loop-effectiveness | Draft | Isolated reviewer + scope expansion per round |

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
      ✅ DX-49 (SSOT)                 ✅ DX-42 (Auto-routing)
              │                               │
              ▼                       ┌───────┴───────┐
      ✅ DX-43 (Cross-platform)       ▼               ▼
                              ✅ DX-41 (Auto-review)  ✅ DX-39 (Efficiency)
                                      │
                                      ▼
                              ✗ DX-40 (Dropped)

      ✅ DX-51 (Phase Visibility)     ✅ DX-52 (uvx Compatibility)
              │                               │
              ▼                               ▼
      Extends DX-42 concepts          DX-53 (Review Effectiveness)

Completed: DX-47, DX-48, DX-49, DX-41, DX-42, DX-43, DX-39, DX-46, DX-23, DX-37, DX-51, DX-52
Partial: DX-38 (Tier 1-2 done)
Dropped: DX-40 (contradicts Lesson #19)
Active: DX-53 (Review Effectiveness)
Deferred: DX-38 Tier 3-4, DX-25, DX-29
```

## Priority Recommendations

| Priority | Proposal | Description | Rationale | Status |
|----------|----------|-------------|-----------|--------|
| ~~High~~ | ~~DX-42~~ | ~~Visible Workflow Routing~~ | ~~Route announcements~~ | ✅ Complete |
| ~~High~~ | ~~DX-41~~ | ~~Auto-review on review_suggested~~ | ~~Close VALIDATE loop~~ | ✅ Complete |
| ~~Medium~~ | ~~DX-43~~ | ~~Cross-platform distribution~~ | ~~Absorbed by DX-49~~ | ✅ Complete |
| ~~High~~ | ~~DX-39~~ | ~~Error Pattern Guide + bug fix~~ | ~~Faster error recovery~~ | ✅ Complete |
| ~~High~~ | ~~DX-51~~ | ~~USBV phase headers visible in output~~ | ~~Workflow follow rate~~ | ✅ Complete |
| ~~Medium~~ | ~~DX-37~~ | ~~`invar guard --coverage` reports uncovered branches~~ | ~~Verification visibility~~ | ✅ Complete |
| ~~High~~ | ~~DX-52~~ | ~~uvx dependency injection~~ | ~~uvx can access project deps~~ | ✅ Complete |
| **Medium** | DX-53 | Isolated reviewer + scope expansion | Review effectiveness | Draft |
| ~~Low~~ | ~~DX-46~~ | ~~docs/ directory audit~~ | ~~Documentation maintenance~~ | ✅ Complete |
| ~~Low~~ | ~~DX-40~~ | ~~Hook intercepts incorrect tool calls~~ | ~~Contradicts Lesson #19~~ | ✗ Dropped |
| **Partial** | DX-38 | Tier 1-2 done; Tier 3-4 deferred | High false-positive risk | Tier 1-2 ✅ |
| ~~Defer~~ | ~~DX-23~~ | ~~Framework callback auto-exempt from Result requirement~~ | ~~Already implemented~~ | ✅ Complete |
| **Defer** | DX-25 | Validation error accumulation, Monoid, etc. | Non-essential major change | — |
| **Defer** | DX-29 | `@invar:module` explicit marker | DX-22 sufficient | — |

## Recommended Execution Order

| Wave | Proposals | Parallel? | Effort | Goal |
|------|-----------|-----------|--------|------|
| ~~0~~ | ~~DX-47, DX-48, DX-49~~ | — | — | ✅ Complete |
| ~~1~~ | ~~DX-42~~ | — | — | ✅ Complete |
| ~~2~~ | ~~DX-43, DX-41~~ | — | — | ✅ Complete |
| ~~3~~ | ~~DX-39~~ | — | — | ✅ Complete |
| ~~4~~ | ~~DX-46, DX-37~~ | — | — | ✅ Complete |
| ~~5~~ | ~~DX-40~~ | — | — | ✗ Dropped (Lesson #19) |
| ~~6~~ | ~~DX-51~~ | — | — | ✅ Complete |
| ~~7~~ | ~~DX-52~~ | — | — | ✅ Complete |
| **8** | DX-53 | — | 0.5 day | Review Effectiveness |
| **∞** | DX-38 Tier 3-4, DX-25, DX-29 | — | — | Deferred |

**Time estimate:** ~0.5 day remaining (DX-53)

**Next:** DX-53 (Review Loop Effectiveness)

## Recent Changes (2025-12-27)

### Implemented Today
- **DX-52** — Virtual Environment Dependency Injection ✅
  - Phase 1: PYTHONPATH injection for uvx compatibility
  - Phase 2: Smart re-spawn with project Python
  - Phase 3: Version mismatch detection and upgrade prompts
  - Enables `uvx invar-tools guard` to access project dependencies

- **DX-53** — Review Loop Effectiveness (Draft)
  - Proposes isolated reviewer (sub-agent) as default
  - Each round includes expansion phase (60% effort on NEW issues)
  - Exit criteria: `no_major AND confidence == HIGH`

- **DX-51** — Workflow Phase Visibility ✅
  - Separates USBV phase tracking from TodoWrite task tracking
  - Phase headers: `📍 /develop → SPECIFY (2/4)`

- **DX-37** — Coverage Integration ✅
  - `invar guard --coverage` reports branch coverage
  - Tracks doctest + hypothesis phases (CrossHair excluded)

### Earlier (2025-12-27)
- **DX-38 Tier 1-2** — Contract quality rules partially implemented
  - ✅ Tier 1: Literal True/False, no-parameter lambda detection
  - ✅ Tier 2: `redundant_type_contract` enabled by default
  - Tier 3-4 deferred (high false-positive risk)

### Completed Earlier
- **DX-23** — Already fully implemented (discovered during review)
- **DX-39** — Error Pattern Guide + bug fixes

### Dropped
- **DX-40** — Contradicts Lesson #19
  - PreToolUse hooks are ineffective (decision already made when hook fires)
  - Original attempt with Read/.py was removed after reflection
  - "Pre-commit blocks are effective; PreToolUse hooks are noise"

### Revised (earlier)
- **DX-39** — Scope reduced after analysis
  - **Keep:** Error Pattern Guide, SKILL.md extensions bug fix
  - **Defer:** Skill Caching (Claude Code lacks session state)
  - **Downgrade:** USBV Enforcement → guidance only
  - **Defer:** Workflow Metrics (unclear ROI)
  - **Drop:** Output Style (loses Anthropic default behaviors)

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
