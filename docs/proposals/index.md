# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` — Developer Experience improvements
- `LX-XX-name.md` — Language eXtension (multi-language evolution)
- Completed/archived proposals in `completed/` subdirectory

## Active Proposals (9)

### DX Series (Developer Experience)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-70 | init-simplification | ✅ Complete | Simplified init with interactive menus and safe merge |
| DX-69 | project-uninstall | ✅ Complete | `invar uninstall` command with marker-based detection |
| DX-68 | agent-behavior-optimization | Draft | Agent reading reliability improvements (P3-P5) |
| DX-67 | explicit-skill-invocation | ✅ Complete | Require Skill tool call for workflow routing |
| DX-62 | proactive-reference-reading | Partial | Task Router (Layer 1) done, Layers 2-4 pending |
| DX-61 | functional-pattern-guidance | Draft | Teach agents functional patterns (NewType, Validation, etc.) |
| DX-60 | structured-rules-ssot | Draft | Optimize DX-57 token usage (1,800t → 600t) |
| DX-25 | functional-patterns | Defer | Functional patterns enhancement |
| DX-29 | pure-content-detection | Defer | Pure content detection (`@invar:module` marker) |
| DX-38 | contract-quality-rules | Partial | Tier 1-2 done, Tier 3-4 deferred |

### LX Series (Language/Platform eXtension)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| LX-04 | multi-agent-framework | **Phase 2 Ready** | Pi hooks with `pi.send()` protocol injection (4.5 days) |
| LX-02 | agent-portability-analysis | ✅ Complete | Research: 6 agents (Claude, Pi, Codex, Cursor, Cline, Aider) |
| LX-01 | multi-language-feasibility | Draft | Feasibility assessment for multi-language Invar |

**LX Series Vision:** Evolve Invar from Python-specific tool to universal AI-assisted development protocol.

**LX-02 Key Findings + Testing:**
- SKILL.md is de facto standard (Claude, Pi, Codex) — 50% CLI agents
- CLI is universal interface — 100% agents can call `invar guard`
- MCP widely supported but Pi rejects it (design decision)
- AGENTS.md emerging standard (Pi, Codex)
- Hooks divergent: Claude (Bash), Pi (TypeScript), Cursor (JSON)
- **Pi reads CLAUDE.md** — No separate SYSTEM.md needed (verified)
- **Pi reads .claude/skills/** — Skill sharing works!

## Archived Proposals (47)

| ID | Name | Status | Description |
|----|------|--------|-------------|
| LX-03 | multi-agent-support | ✅ Complete | docs/guides/ created, implementation → LX-04 |
| DX-66 | escape-hatch-visibility | ✅ Complete | Guard shows escape hatch summary in output |
| DX-65 | single-file-guard | ✅ Complete | `invar guard file.py` support |
| DX-64 | version-display-unification | ✅ Complete | Use importlib.metadata for accurate version |
| DX-63 | contracts-first-enforcement | ✅ Complete | Guard -c flag + function-level gates + trivial detection |
| DX-58 | document-structure-optimization | ✅ Complete | Critical section in CLAUDE.md, context.md slimming |
| DX-57 | claude-code-hooks | ✅ Complete | Claude Code hooks for protocol enforcement (4 hooks) |
| DX-56 | template-sync-unification | ✅ Complete | Unify init/dev sync, manifest-driven, shared engine |
| DX-55 | claude-init-conflict-resolution | ✅ Complete | Unified idempotent init with smart CLAUDE.md merge |
| DX-54 | agent-native-context-management | ✅ Complete | Long conversation resilience + workflow refresh |
| DX-53 | review-loop-effectiveness | ✅ Complete | Isolated reviewer + scope expansion per round |
| DX-52 | venv-dependency-injection | ✅ Complete | PYTHONPATH injection for uvx compatibility |
| DX-51 | workflow-phase-visibility | ✅ Complete | USBV phase headers separate from TodoWrite |
| DX-48 | code-structure-reorganization | ✅ Complete | Dead code + shell/ restructure done |
| DX-49 | protocol-distribution-unification | ✅ Complete | SSOT for INVAR.md, CLAUDE.md, skills/ |
| DX-47 | command-skill-naming | ✅ Complete | /audit, /guard commands; /review skill |
| DX-46 | documentation-audit | ✅ Complete | docs/ directory audit |
| DX-43 | cross-platform-distribution | ✅ Complete | Absorbed by DX-49 |
| DX-42 | workflow-auto-routing | ✅ Complete | Visible Workflow Routing |
| DX-41 | automatic-review-orchestration | ✅ Complete | Automatic review orchestration (from DX-31+35) |
| DX-40 | smart-tool-redirect-hook | ✗ Dropped | Contradicts Lesson #19 (PreToolUse ineffective) |
| DX-39 | workflow-efficiency | ✅ Complete | Error Pattern Guide + bug fixes |
| DX-37 | coverage-integration | ✅ Complete | Coverage integration for Guard (`--coverage` flag) |
| DX-36 | documentation-restructuring | ✅ Complete | Sections (Phase 5-6 → DX-43) |
| DX-35 | workflow-phase-separation | ✅ Complete | Workflow skills (Phase 3-5 → DX-41/42/43) |
| DX-34 | review-cycle | Superseded | → DX-35 |
| DX-33 | verification-blind-spots | ✅ Complete | Analysis (→ DX-37, DX-38) |
| DX-32 | workflow-iteration | ✅ Complete | USBV is now standard workflow |
| DX-31 | adversarial-reviewer | ✅ Complete | /review skill (Phase 2 → DX-41) |
| DX-30 | visible-workflow | ✅ Complete | TodoList convention |
| DX-28 | semantic-verification | ✅ Complete | @relates, format specs (P2 → DX-38) |
| DX-27 | system-prompt-protocol | ✅ Merged | → DX-39 (Output Style feature) |
| DX-26 | guard-simplification | ✅ Complete | Guard CLI simplification |
| DX-24 | mechanism-documentation | ✅ Complete | 13/13 mechanism docs created |
| DX-23 | entry-point-detection | ✅ Complete | Entry point detection & Monad Runner pattern |
| DX-22 | verification-strategy | ✅ Complete | Smart routing, Shell rules |
| DX-21 | package-and-init | ✅ Complete | Two-package architecture |
| DX-20 | property-testing-enhancements | Draft | Property testing UX |
| DX-17 | workflow-enforcement | ✅ Evolved | Check-In format (→ DX-54) |
| DX-16 | agent-tool-enforcement | ✅ Complete | MCP server (Phase 2 → DX-40) |
| DX-14 | expanded-prove-usage | ✅ Complete | Expanded --prove usage |
| DX-13 | incremental-prove | ✅ Complete | Incremental CrossHair verification |
| DX-12 | hypothesis-fallback | ✅ Complete | Hypothesis as CrossHair fallback |
| DX-11 | documentation-restructure | ✅ Complete | Multi-agent support (remnants → DX-43) |
| DX-45 | template-consistency | Superseded | → DX-49 (SSOT) |

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
      Extends DX-42 concepts          ✅ DX-53 (Review Effectiveness)

      ✅ DX-54 (Agent Native Context)
              │
              ▼
      Simplifies Check-In, adds Workflow Refresh

      ✅ DX-57 (Claude Code Hooks)    ✅ DX-58 (Document Structure)
              │                               │
              ▼                               ▼
      Protocol enforcement via hooks    Critical section + slimmed context

Completed: DX-47, DX-48, DX-49, DX-41, DX-42, DX-43, DX-39, DX-46, DX-23, DX-37, DX-51, DX-52, DX-53, DX-54, DX-57, DX-58
Partial: DX-38 (Tier 1-2 done)
Dropped: DX-40 (contradicts Lesson #19)
Deferred: DX-38 Tier 3-4, DX-25, DX-29
Draft: DX-60 (optimizes DX-57), DX-61, DX-62, LX-01 (multi-language)
Complete: DX-63 (contracts-first)

      Draft: DX-61 ↔ DX-62 (Synergy)
              │
      DX-61 (Functional Pattern Guidance)
              │
              └── Suggestions include file references
                        │
      DX-62 (Proactive Reference Reading)
              │
              ├── Extends DX-54 (Check-In as anchor point)
              └── Ensures agents read referenced files
                        │
                        ▼
              Learning feedback loop
```

## Remaining Work

| Status | Proposal | Description | Notes |
|--------|----------|-------------|-------|
| **New** | DX-67 | Explicit Skill tool invocation | Verified in benchmark, templates updated |
| **Partial** | DX-62 | Proactive reference reading | Layer 1 (Task Router) ✅, Layers 2-4 pending |
| **Draft** | DX-61 | Functional pattern guidance | Teach agents functional patterns |
| **Draft** | DX-60 | Structured rules SSOT | Optimize DX-57 token usage (1,800t → 600t) |
| **Draft** | LX-01 | Multi-language feasibility | Strategic exploration for language extension |
| **Partial** | DX-38 | Contract quality rules | Tier 1-2 ✅, Tier 3-4 deferred (high false-positive risk) |
| **Defer** | DX-25 | Functional patterns | Non-essential major change |
| **Defer** | DX-29 | Pure content detection | DX-22 sufficient |

**All core proposals complete (47/52).** LX-04 active, DX-67 new, 2 draft + 2 partial + 2 deferred items remain.

## Execution History

| Wave | Proposals | Status |
|------|-----------|--------|
| 0 | DX-47, DX-48, DX-49 | ✅ Complete |
| 1 | DX-42 | ✅ Complete |
| 2 | DX-43, DX-41 | ✅ Complete |
| 3 | DX-39 | ✅ Complete |
| 4 | DX-46, DX-37 | ✅ Complete |
| 5 | DX-40 | ✗ Dropped |
| 6 | DX-51 | ✅ Complete |
| 7 | DX-52 | ✅ Complete |
| 8 | DX-53 | ✅ Complete |
| 9 | DX-54 | ✅ Complete |
| 10 | DX-57, DX-58 | ✅ Complete |

## Recent Changes (2025-12-30)

### LX-04 Phase 2 Revised
- **LX-04** — Multi-Agent Framework **Phase 2 Ready** (15 days → 4.5 days)
  - **Phase 1 ✅:** Contract Rules added to CLAUDE.md critical section, Check-In simplified
  - **Phase 1.5 ✅:** Core/Shell edge cases, Task Router reference, SKILL.md Entry Actions
  - **Phase 2 Revised:** Pi hooks with `pi.send()` for protocol injection (full feature parity!)
  - **Key Discovery:** Pi's `pi.send()` API supports message injection → same capability as Claude Code
  - **CLI Aligned:** Interactive menu instead of `--agent pi` flag (DX-70 consistent)
  - Phase 2 (Pi: 1.5 days) and Phase 3 (Cursor: 1 day) ready to implement

### DX-68 Created
- **DX-68** — Agent Behavior Optimization (Draft)
  - Future optimizations identified during LX-04 analysis
  - Phase A: Context enforcement (P3)
  - Phase B: Example inlining (P4)
  - Phase C: Agent behavior monitoring (P5)

## Recent Changes (2025-12-29)

### Proposed Earlier
- **DX-67** — Explicit Skill Tool Invocation **New**
  - Problem: Claude followed USBV workflow but never called Skill tool
  - SKILL.md content (DX-63, timeout, error recovery) was never read
  - Solution: Explicit `Skill(skill="...")` syntax in routing table
  - Verified: Skill Calls 0 → 1 in benchmark
  - Templates updated: CLAUDE.md, CLAUDE.md.template, CLAUDE.md.jinja

### Updated Today (LX Series Research)
- **LX-02** — Agent Portability Analysis ✅ (Deep Research Update)
  - Removed Continue, added Pi and Codex CLI
  - 6 agents analyzed: Claude Code, Pi, Codex CLI, Cursor, Cline, Aider
  - Key findings: SKILL.md standard, CLI universal, MCP non-universal, AGENTS.md emerging
  - Portability matrix: Concepts (100%) > Tools (90%) > Integration (50%)

- **LX-03** — Multi-Agent Support Implementation ✅ **Archived**
  - Simplified to Phase 1 summary only (docs/guides/ output)
  - Moved to completed/ directory
  - Implementation work continues in LX-04

- **LX-04** — Multi-Agent Support Framework (Major Simplification)
  - **Key Discovery:** Pi reads CLAUDE.md directly → No SYSTEM.md needed!
  - **Key Discovery:** Pi reads .claude/skills/ → Skill sharing works!
  - Phase 3 reduced: 3 days → 2 days (no SYSTEM.md template)
  - Total reduced: 16 days → 15 days
  - Updated Pi manifest: shared_with: ["claude"]
  - Updated migration guide for Pi users

### Completed Earlier Today
- **DX-66** — Escape Hatch Visibility ✅
  - Guard output now includes `escape_hatches` summary
  - Shows count, files, rules, and reasons
- **DX-65** — Single File Guard ✅
  - `invar guard src/core/file.py` now works
- **DX-64** — Version Display Unification ✅
  - Uses `importlib.metadata` for accurate PyPI version
- **DX-62** — Proactive Reference Reading (Layer 1) ✅
  - Added Task Router to context.md template
  - Benchmark treatment config updated

### Proposed Earlier Today
- **LX-04** — Multi-Agent Support Framework (expanded scope)
  - Originally Pi-only support, now comprehensive 6-agent framework
  - **Agents:** Claude Code, Pi, Codex CLI, Cursor, Cline, Aider
  - **Integration patterns:**
    - Native Skill (Claude, Pi, Codex) — SKILL.md + hooks
    - Lint Hook (Aider) — CONVENTIONS.md + lint-cmd
    - MCP First (Claude, Cline, Codex, Cursor) — MCP tools + CLI fallback
    - Rules File (Cline, Cursor) — .clinerules / .mdc
  - **Key Design Change:** Copy-Sync instead of Symlink
    - Claude Code doesn't follow symlinks (security)
    - Skills copied from `.invar/skills/` to `.{agent}/skills/`
    - Generation markers for drift detection
  - Manifest-driven architecture with JSON agent definitions
  - Hook logic SSOT in Python, generated to Bash/TypeScript/JSON
  - System prompt templates with Jinja2
  - **Platform:** macOS/Linux only (Windows not supported)
  - **Implementation order:** Claude → Pi → Cursor → Codex → Aider/Cline
  - **Estimated:** 15 days implementation (reduced due to Pi/Claude sharing)

## Recent Changes (2025-12-28)

### Implemented
- **DX-58** — Document Structure Optimization ✅
  - Critical section at top of CLAUDE.md (~50 tokens)
  - Slimmed context.md (~150 lines vs 1110 lines)
  - Key Rules + Self-Reminder for long conversation resilience

- **DX-57** — Claude Code Hooks Integration ✅
  - 4 hooks: PreToolUse, PostToolUse, UserPromptSubmit, Stop
  - pytest/crosshair blocking with smart auto-escape
  - Protocol refresh in long conversations (~1,800 tokens)
  - `invar hooks --install/--sync/--remove/--disable/--enable`

## Recent Changes (2025-12-27)

### Implemented
- **DX-54** — Agent Native Context Management ✅
  - Simplified Check-In (no guard/map execution, just read context.md)
  - Workflow Refresh: All skills read context.md before Entry Actions
  - Key Rules + Self-Reminder in context.md for long conversation resilience
  - Context Management section in CLAUDE.md (re-read triggers)
  - Lesson #29 fix: Agent workflow compliance through document-based refresh

- **DX-53** — Review Loop Effectiveness ✅
  - Isolated reviewer (sub-agent) as default mode
  - Three-phase review: Regression (15%) + Validation (25%) + Expansion (60%)
  - Scope expansion across rounds (changed → dependents → integration)
  - Exit criteria: `no_major AND confidence == HIGH/MEDIUM`
  - Exhaustive Review Declaration requirement

- **DX-52** — Virtual Environment Dependency Injection ✅
  - Phase 1: PYTHONPATH injection for uvx compatibility
  - Phase 2: Smart re-spawn with project Python
  - Phase 3: Version mismatch detection and upgrade prompts
  - Enables `uvx invar-tools guard` to access project dependencies

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
  - dev sync with project-additions.md injection
  - Phase 8: Template system testing (init, dev sync, syntax switching)
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

---

## LX Series Roadmap (Updated 2025-12-29)

### Strategic Direction

Invar's core value (USBV workflow, agent protocol, adversarial review) is language-agnostic.
The LX series explores evolving Invar into a universal development protocol.

### Current Focus: Multi-Agent Support

```
LX-01: Multi-Language Feasibility    ← Draft (strategic exploration)
LX-02: Agent Portability Analysis    ← ✅ Complete (research)
LX-03: Multi-Agent Support (Docs)    ← ✅ Archived (output: docs/guides/)
LX-04: Multi-Agent Framework         ← Active (canonical implementation)
```

### LX-02 Research Summary (6 Agents)

| Agent | Skills | MCP | Hooks | System Prompt | Tier |
|-------|--------|-----|-------|---------------|------|
| Claude Code | SKILL.md ✅ | ✅ | Bash (4) | CLAUDE.md | 1 |
| Pi | SKILL.md ✅ | ❌ | TypeScript | **CLAUDE.md** ✅ | 1 |
| Codex CLI | SKILL.md ✅ | ✅ | ❌ | AGENTS.md | 2 |
| Cursor | ❌ | ✅ | JSON (6) | .cursor/rules/ | 2 |
| Cline | ❌ | ✅ | ❌ | .clinerules | 3 |
| Aider | ❌ | ⚠️ | lint-cmd | CONVENTIONS.md | 4 |

> **Key:** Pi reads CLAUDE.md → Claude/Pi share same system prompt!

### LX-04 Implementation Order (Revised 2025-12-30)

```
Phase 1: Content Optimization ✅ Complete
├── Contract Rules inlined in CLAUDE.md critical section
├── Task Router reference added
└── Core/Shell edge cases documented

Phase 2: Pi Support (1.5 days) ← NEXT
├── Create Pi TypeScript hook template
├── Implement pi.send() protocol injection (NEW!)
├── Implement pytest/crosshair blocking
└── Extend interactive menu for Pi selection

Phase 3: Cursor Support (1 day)
├── Create Cursor .mdc template
├── Extend interactive menu for Cursor selection
└── Test MCP integration
```

> **Key Discovery:** Pi's `pi.send()` enables full feature parity with Claude Code hooks.
> **CLI Alignment:** No new flags. Interactive menu only (DX-70 consistent).

### Future Phases

```
Phase 2: Python Refactor (LX-10+)
├── Modularize current Python implementation
└── Use plugin interface from Phase 1

Phase 3: Second Language (LX-20+)
├── TypeScript adapter (highest demand)
└── Validates multi-language architecture

Phase 4: Community (LX-30+)
├── Rust, Go, Java adapters
└── Community-driven contributions
```

### Decision Points

| After | Decision |
|-------|----------|
| LX-04 | Validate Pi/Codex integration |
| LX-01 | Proceed with multi-language? |
| Phase 2 | Continue to Phase 3? |

Each phase has a natural exit point if approach proves unviable.
