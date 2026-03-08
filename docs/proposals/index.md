# Invar Proposals Index

> **Last Updated:** 2026-03-09

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- `LX-XX-name.md` — Language eXtension (multi-language evolution)
- Completed/archived proposals in `completed/` subdirectory

---

## Active Proposals (15)

### DX Series (Developer Experience)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-94 | [mcp-full-guard-support-model](DX-94-mcp-full-guard-support-model.md) | Draft | Deferred full-scan model for MCP timeout-safe `invar_guard(changed=false)` |
| DX-87 | [remove-multi-agent-init](DX-87-remove-multi-agent-init.md) | Draft | Remove combined/multi-select init; enforce single-agent init only |
| DX-84 | [security-review-backlog](DX-84-security-review-backlog.md) | Active | Security review backlog for TypeScript & Python Guard |
| DX-83 | [multi-agent-subagent-support](DX-83-multi-agent-subagent-support.md) | Draft | Subagent support and fallback strategy for multi-agent environments |
| DX-80 | [guard-cli-mcp-alignment](DX-80-guard-cli-mcp-alignment.md) | Draft | Align Guard CLI default behavior with MCP (bug fix) |
| DX-79 | [invar-usage-feedback](DX-79-invar-usage-feedback.md) | Draft | Invar usage feedback collection |
| DX-68 | [agent-behavior-optimization](DX-68-agent-behavior-optimization.md) | Draft | Agent reading reliability improvements (P3-P5) |
| DX-62 | [proactive-reference-reading](DX-62-proactive-reference-reading.md) | Partial | Task Router (Layer 1) done, Layers 2-4 pending |
| DX-61 | [functional-pattern-guidance](DX-61-functional-pattern-guidance.md) | Draft | Teach agents functional patterns (NewType, Validation, etc.) |
| DX-60 | [structured-rules-ssot](DX-60-structured-rules-ssot.md) | Draft | Optimize DX-57 token usage (1,800t → 600t) |

### Agent Ecosystem

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-85 | [opencode-support](DX-85-opencode-support.md) | Draft | Native OpenCode init (`AGENTS.md` + `opencode.json`) |

### LX Series (TypeScript Focus)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| LX-13 | [typescript-runtime-optimization](LX-13-typescript-runtime-optimization.md) | Draft | Reduce Zod validation overhead by 80-90% |
| LX-09 | [legacy-onboarding](LX-09-legacy-onboarding.md) | Draft | Update `/invar-onboard` skill for --mcp-only path |
| LX-08 | extension-skills-future | Deferred | Future extension skills (split from LX-07) |

### Deferred (Low Priority)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-38 | [contract-quality-rules](DX-38-contract-quality-rules.md) | Partial | Tier 1-2 done, Tier 3-4 deferred |
| DX-29 | [pure-content-detection](DX-29-pure-content-detection.md) | Defer | Pure content detection (`@invar:module` marker) |
| DX-25 | [functional-patterns](DX-25-functional-patterns.md) | Defer | Functional patterns enhancement |
| LX-17 | [haskell-elm-feasibility](LX-17-haskell-elm-feasibility.md) | Deferred | Haskell & Elm feasibility assessment |
| LX-17 | [implementation-matrix](LX-17-implementation-matrix.md) | Deferred | Implementation matrix for language feasibility |
| LX-17 | [summary](LX-17-summary.md) | Deferred | Summary of Go & Rust feasibility |
| LX-16 | [typescript-guard-remaining-gap](LX-16-typescript-guard-remaining-gap.md) | Deferred | TypeScript Guard remaining gap analysis |
| LX-11 | [cursor-support](LX-11-cursor-support.md) | Deferred | Cursor IDE native support |
| LX-01 | [multi-language-feasibility](LX-01-multi-language-feasibility.md) | Deferred | Strategic exploration for multi-language Invar |

---

## Archived Proposals (77)

> All completed proposals have been moved to `completed/` directory.

### Recently Archived (2026-02-18)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-23 | entry-point-detection | ✅ Complete | Entry point detection & Monad Runner pattern |
| DX-78 | mcp-protocol-sync | ✅ Implemented | MCP protocol synced to v5.0 + TypeScript support |
| DX-85 | mcp-typescript-descriptions | ✅ Fixed | MCP tool descriptions fixed for TypeScript |
| DX-81 | multi-agent-init | ✅ Implemented | Multi-agent init support (v1.15.0) |
| DX-74 | tiered-attention-defense | ✅ Validation Complete | Multi-tier defense experiment validated |
| DX-75 | attention-aware-framework | ✅ Phase B Complete | Attention-aware framework architecture |
| LX-04 | pi-agent-support | ✅ Complete | Pi native support (--pi flag, init/uninstall, docs) |
| LX-07 | extension-skills | ✅ T0 Complete | T0 skills implemented, CLI implemented |
| LX-15 | typescript-guard-parity | ✅ Complete | TS Guard achieved parity with Python |

### Earlier Archive (by category)

**Core Framework (DX):**

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-67 | explicit-skill-invocation | ✅ Complete | Require Skill tool call for workflow routing |
| DX-66 | escape-hatch-visibility | ✅ Complete | Guard shows escape hatch summary |
| DX-65 | single-file-guard | ✅ Complete | `invar guard file.py` support |
| DX-64 | version-display-unification | ✅ Complete | Use importlib.metadata for accurate version |
| DX-63 | contracts-first-enforcement | ✅ Complete | Guard -c flag + function-level gates |
| DX-58 | document-structure-optimization | ✅ Complete | Critical section in CLAUDE.md |
| DX-57 | claude-code-hooks | ✅ Complete | Claude Code hooks (4 hooks) |
| DX-56 | template-sync-unification | ✅ Complete | Unified init/dev sync |
| DX-55 | claude-init-conflict-resolution | ✅ Complete | Unified idempotent init |
| DX-54 | agent-native-context-management | ✅ Complete | Long conversation resilience |
| DX-53 | review-loop-effectiveness | ✅ Complete | Isolated reviewer + scope expansion |
| DX-52 | venv-dependency-injection | ✅ Complete | PYTHONPATH injection for uvx |
| DX-51 | workflow-phase-visibility | ✅ Complete | USBV phase headers |
| DX-49 | protocol-distribution-unification | ✅ Complete | SSOT for INVAR.md, CLAUDE.md, skills/ |
| DX-48 | code-structure-reorganization | ✅ Complete | Dead code + shell/ restructure |
| DX-47 | command-skill-naming | ✅ Complete | /audit, /guard commands; /review skill |
| DX-46 | documentation-audit | ✅ Complete | docs/ directory audit |
| DX-43 | cross-platform-distribution | ✅ Complete | Absorbed by DX-49 |
| DX-42 | workflow-auto-routing | ✅ Complete | Visible Workflow Routing |
| DX-41 | automatic-review-orchestration | ✅ Complete | Automatic review orchestration |
| DX-40 | smart-tool-redirect-hook | ✗ Dropped | Contradicts Lesson #19 |
| DX-39 | workflow-efficiency | ✅ Complete | Error Pattern Guide + bug fixes |
| DX-37 | coverage-integration | ✅ Complete | Coverage integration for Guard |
| DX-36 | documentation-restructuring | ✅ Complete | Sections (Phase 5-6 → DX-43) |
| DX-35 | workflow-phase-separation | ✅ Complete | Workflow skills (Phase 3-5) |
| DX-33 | verification-blind-spots | ✅ Complete | Analysis (→ DX-37, DX-38) |
| DX-32 | workflow-iteration | ✅ Complete | USBV is now standard workflow |
| DX-31 | adversarial-reviewer | ✅ Complete | /review skill |
| DX-30 | visible-workflow | ✅ Complete | TodoList convention |
| DX-28 | semantic-verification | ✅ Complete | @relates, format specs |
| DX-27 | system-prompt-protocol | ✅ Merged | → DX-39 |
| DX-26 | guard-simplification | ✅ Complete | Guard CLI simplification |
| DX-24 | mechanism-documentation | ✅ Complete | 13/13 mechanism docs |
| DX-22 | verification-strategy | ✅ Complete | Smart routing, Shell rules |
| DX-21 | package-and-init | ✅ Complete | Two-package architecture |
| DX-17 | workflow-enforcement | ✅ Evolved | Check-In format |
| DX-16 | agent-tool-enforcement | ✅ Complete | MCP server |
| DX-14 | expanded-prove-usage | ✅ Complete | Expanded --prove usage |
| DX-13 | incremental-prove | ✅ Complete | Incremental CrossHair verification |
| DX-12 | hypothesis-fallback | ✅ Complete | Hypothesis as CrossHair fallback |
| DX-11 | documentation-restructure | ✅ Complete | Multi-agent support |
| DX-45 | template-consistency | Superseded | → DX-49 |
| DX-34 | review-cycle | Superseded | → DX-35 |
| DX-70 | init-simplification | ✅ Complete | Simplified init with interactive menus |
| DX-69 | project-uninstall | ✅ Complete | `invar uninstall` command |

**Language Extension (LX):**

| ID | Name | Status | Description |
|----|------|--------|-------------|
| LX-14 | typescript-doctest-execution | Merged → LX-15 | Doctest execution merged |
| LX-12 | typescript-contract-enforcement | Merged → LX-15 | Contract enforcement merged |
| LX-06 | typescript-tooling | ✅ Phase 1-3 Complete | TypeScript verification |
| LX-05 | language-agnostic-protocol | ✅ Protocol Complete | Universal protocol extracted |
| LX-03 | multi-agent-support | ✅ Complete | docs/guides/ created |
| LX-02 | agent-portability-analysis | ✅ Complete | Research: 6 agents |
| LX-09 | legacy-onboarding | ✅ Implemented | Legacy onboarding skill |

---

## Statistics

| Category | Count |
|----------|-------|
| **Active** | 15 |
| **Deferred** | 12 |
| **Archived** | 77 |
| **Total** | 104 |

### Active Breakdown

| Status | Count |
|--------|-------|
| Draft | 11 |
| Active | 1 |
| Partial | 2 |
| Deferred | 12 |

---

## Priority Recommendations

### High Priority (Actionable Now)

1. **DX-84** (Security Review) — Active, blocking for production readiness
2. **DX-80** (Guard CLI/MCP Alignment) — Bug fix, user impact
3. **DX-87** (Remove Multi-Agent Init) — Cleanup, reduces maintenance

### Medium Priority (Strategic)

1. **LX-09** (Legacy Onboarding) — Improves adoption
2. **DX-85** (OpenCode Support) — Ecosystem expansion
3. **LX-13** (TypeScript Runtime Optimization) — TypeScript performance
4. **DX-62** (Proactive Reference Reading) — Layer 1 done, continue

### Low Priority (Future) — All Deferred

1. **LX-11** (Cursor Support) — IDE expansion (Deferred)
2. **DX-68** (Agent Behavior Optimization) — Reliability improvements
3. **LX-17** (Haskell/Elm/Go/Rust Feasibility) — Multi-language exploration
4. **LX-01** (Multi-Language Feasibility) — Strategic exploration

---

## Historical Reference

See `completed/` directory for detailed implementation notes and execution history of archived proposals.

Key milestones:
- **v1.15.0**: Multi-agent init support (DX-81)
- **v1.12.0**: MCP protocol sync (DX-78)
- **v1.11.0**: TypeScript Guard parity (LX-15)
- **v1.9.0**: Extension skills architecture (LX-07)
- **v1.7.0**: Pi agent support (LX-04)
