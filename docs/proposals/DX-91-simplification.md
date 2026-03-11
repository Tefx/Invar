# DX-91: Invar Simplification

**Status:** Draft v3 (incorporates expert review + user corrections)
**Date:** 2026-03-06
**Supersedes:** DX-87 (multi-agent removal — absorbed into this proposal)

## Motivation

Real-world usage across multiple projects shows:
- **High value:** guard, sig, map, refs, Core/Shell separation, @pre/@post contracts
- **Low value:** USBV workflow enforcement, skills, hooks, protocol ceremony
- **Negative value:** Installation/configuration complexity that discourages adoption

## Guiding Principles

1. **Guard is the compiler.** It enforces outcomes, not process.
2. **Contracts before code is the ONE mandatory workflow rule.** This is the single behavioral instruction that survives from USBV. Everything else is enforced by guard or optional.
3. **Core/Shell separation is mandatory.** Proven across projects. Not opt-in — this is core value.
4. **Agent-agnostic.** No Claude Code-specific features. Tools work with any agent.

---

## 1. What to Keep

### 1.1 Core Tools

| Tool | Purpose |
|------|---------|
| `invar guard` | Smart verification (static + doctest + CrossHair + Hypothesis + wiring rules) |
| `invar sig` | Show function signatures + contracts |
| `invar map` | Entry points with reference counts |
| `invar refs` | Cross-file symbol references |
| `invar init` | Project setup (rewritten) |
| `invar doc *` | Document tools (toc/read/find/replace/insert/delete) |

### 1.2 Runtime Package (`invar-runtime`)

Unchanged. `@pre`, `@post`, `icontract` re-exports.

### 1.3 Architectural Principles (Mandatory, Not Opt-in)

- **Core/Shell separation**: guard enforces (no I/O imports in core/)
- **Contracts before code**: the ONE required workflow rule
- **Contracts required in core**: guard enforces (@pre/@post + doctests)
- **Shell returns Result[T, E]**: guard checks

### 1.4 MCP Server

Keep all MCP tools: invar_guard, invar_sig, invar_map, invar_refs, invar_doc_*.

### 1.5 Pre-commit Hook

Keep as **backstop enforcement**. Single hook: `invar guard`.

### 1.6 Wiring Integrity Rules (DX-89, in progress)

All planned rules continue: dead_export, dead_param, stub_body, wiring_gap, mock_leak, dead_assign.

---

## 2. What to Remove

### 2.1 USBV Workflow Enforcement

**Remove the ceremony. Keep the ONE rule.** The four-phase protocol (Understand → Specify → Build → Validate), phase visibility headers (DX-51), TodoWrite checkpoints — all removed. The essential intent survives as a single emphasized instruction in CLAUDE.md: "Write @pre/@post contracts BEFORE implementation."

### 2.2 Skills System

**Remove entirely.** Claude Code-specific, routing unreliable. All 8 skills, 17 files, `.claude/skills/` generation.

### 2.3 Hooks (Agent-Specific)

**Remove entirely.** PreToolUse, PostToolUse, Stop, UserPromptSubmit hooks. Only Claude Code, adds config burden. `.claude/hooks/` and Pi hooks.

### 2.4 TypeScript/JS Support

**Remove entirely as a strategic product decision.** Invar v2 is explicitly Python-only. This is not a temporary scope reduction or package split; it is a deliberate narrowing of product boundary. Remove node_tools/ (5,981 LOC), ts_compiler.py, TS protocol/example/CLAUDE.md templates, and TS routing in guard/perception/sig/map/refs.

### 2.5 Examples Directory

**Remove as an agent-facing instruction source.** Keeping `.invar/examples/` creates a second semantic source alongside `INVAR.md`, increases staleness risk, and leaves agents vulnerable to copying obsolete patterns. Before deletion, run a full reference audit and inline only the mistake-prone normative patterns into `INVAR.md` (contract lambda signature, `@post` scope, Core/Shell boundary, shell `Result[T, E]`). Guard diagnostics must then carry the remaining teaching load for instance-level fixes (see Section 6.3).

### 2.6 Feedback Collection (DX-79)

**Remove.** No actionable data, adds consent prompt complexity.

### 2.7 Onboarding System

**Remove.** Goes with skills.

### 2.8 CLI Command Surface Changes

| Command | Why |
|---------|-----|
| `invar update` | Nothing to sync |
| `invar uninstall` | Nothing complex to remove |
| `invar test` | Redundant with guard |
| `invar verify` | Redundant with guard |
| `invar mutate` | Niche, revisit later |
| `invar rules` | Low usage |
| `invar version` | Use `invar --version` |
| `invar feedback *` (3) | Feature removed |
| `invar hooks *` (2) | Feature removed |
| `invar skill *` (2) | Feature removed |
| `invar dev sync` | Keep, but reduce to internal maintenance of generated semantic artifacts |

### 2.9 Check-In/Final Protocol

**Remove as protocol.** Guard instruction in CLAUDE.md replaces Final. No Check-In ceremony.

### 2.10 Complex Managed Section Merge Logic

**Simplify.** Replace multi-region versioned merge (`<!--invar:critical-->`, `<!--invar:managed-->`, `<!--invar:project-->`, `<!--invar:user-->`) with single `<!--invar:begin/end-->` marker pair.

---

## 3. Simplified `invar init`

### 3.1 Behavior

```bash
# Install (recommended: dev dependency)
uv add --dev invar-tools invar-runtime

# Initialize (default: writes to CLAUDE.md)
invar init

# Alternative: if project uses a different agent file
invar init --file AGENTS.md
```

No agent selection. No file selection.

Default target is **CLAUDE.md** (most users use Claude Code, and it auto-loads CLAUDE.md).
`--file` flag for other targets (AGENTS.md, .cursorrules, etc.)

Fresh init should be non-interactive. Migration prompts are allowed only when destructive cleanup is detected.

### 3.2 Generated Files

| File | Content | Lines |
|------|---------|-------|
| **CLAUDE.md** | Invar section appended in `<!--invar:begin/end-->` markers | ~50 |
| **INVAR.md** | Agent semantic specification (core/shell, contracts, config, repair guidance) | ~70-120 |
| **.pre-commit-config.yaml** | Single hook: `invar guard` | ~8 |

Optional:
| **.mcp.json** | MCP server config (if `--mcp` flag) |

**NOT generated:** directory skeleton, `.invar/` user workspace, examples, skills, hooks, context.md.

### 3.3 Idempotent Merge

| Scenario | Action |
|----------|--------|
| CLAUDE.md doesn't exist | Create with invar section |
| CLAUDE.md exists, no invar markers | Append invar section |
| CLAUDE.md exists, has invar markers | Replace content between markers |
| User content outside markers | Preserved |
| INVAR.md doesn't exist | Create |
| INVAR.md exists | Overwrite (it's fully managed) |
| .pre-commit-config.yaml exists | Merge invar hook (preserve other hooks) |

### 3.4 v1 → v2 Migration

When `invar init` detects a v1 layout (old skills/hooks/protocol), it MAY perform destructive migration - but only after an explicit preview and confirmation.

Required flow:

1. **Detect** legacy layout and collect impacted files/directories
2. **Preview** exactly what will be deleted, overwritten, or preserved
3. **Back up** preserved user data (`.invar/context.md`, `.invar/project-additions.md`) and any user-customized legacy instruction files before deletion
4. **Ask for confirmation** before any destructive action
5. **Delete** stale agent config and stale semantic sources, including `.claude/skills/`, `.claude/hooks/`, and `.invar/examples/`
6. **Replace** managed sections in CLAUDE.md with new minimal content
7. **Create/overwrite** `INVAR.md` with the new agent semantic spec
8. **Print** a migration summary with deleted paths, overwritten files, and backup locations

Stale files MUST be actively cleaned up - not left "inert." Agents read files on disk and will follow old instructions.

If backup fails, destructive migration must abort.

### 3.5 Installation Recommendation

```bash
# Recommended (reliable, version-locked)
uv add --dev invar-tools invar-runtime

# NOT recommended (known issues)
# uvx invar-tools guard
```

Known uvx issues:
- Python version mismatch causes respawn to wrong version
- Can't find project venv deps for CrossHair/Hypothesis
- Different behavior from `uv run invar`

---

## 4. CLAUDE.md Injected Content (~50 lines)

```markdown
<!--invar:begin-->
## Invar

**CRITICAL: Write @pre/@post contracts BEFORE implementation. Guard rejects uncontracted core functions. This is not optional.**

### Architecture (Mandatory)

| Zone | Path | Rules |
|------|------|-------|
| Core | `**/core/**` | @pre/@post + doctests, NO I/O imports |
| Shell | `**/shell/**` | Returns `Result[T, E]` from `returns` |

Core receives data, Shell handles I/O. When unsure → Shell.

### Verification

Run `invar guard` after every change. Fix all errors before committing.

### Tools

| Tool | Use |
|------|-----|
| `invar guard` | Verify code (static + doctest + CrossHair + wiring rules) |
| `invar sig <file>` | Show function signatures and contracts |
| `invar map [path]` | Entry points with reference counts |
| `invar refs <file>::<symbol>` | Cross-file symbol references |

### Contract Syntax

```python
# @pre: lambda must include ALL parameters (even defaults)
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# @post: only receives 'result', NOT function parameters
@post(lambda result: result >= 0)

# Every core function needs @pre/@post + at least one doctest
```

### Escape Hatches

```python
# Suppress a specific rule with reason
# @invar:allow dead_export: CLI entry point called by framework
```

### Configuration

```toml
# pyproject.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
```

More repair rules and exact syntax: see `INVAR.md`
<!--invar:end-->
```

**~50 lines.** Key content:
1. **Contracts before code** — emphasized as CRITICAL, mandatory
2. Architecture table — Core/Shell zones and rules
3. Tools table — what to use
4. Contract syntax — the 3 most common mistakes
5. Escape hatch — how to suppress rules
6. Configuration — minimal, just paths
7. Pointer to `INVAR.md` for durable agent semantics

---

## 5. INVAR.md as Agent Semantic Spec

**Location:** Top-level. This is not a human reference manual; it is part of the active instruction surface agents consume.

**Role:** `CLAUDE.md` gives the short entry contract. `INVAR.md` carries the durable semantic rules agents need when guard fails or when they need exact syntax.

**Content:** See `docs/proposals/DX-91-invar-md-draft.md` for the draft to be revised in this direction.

Required characteristics:
- Imperative, compact, and optimized for agent consumption rather than narrative reading
- Stable section anchors so guard diagnostics can point to exact fixes
- Contains only normative patterns or repair guidance, not optional tutorials
- Must not reference deleted files such as `.invar/examples/`

Required sections:
1. Before writing code (contracts first, when to choose Core vs Shell)
2. Core/Shell decision rule
3. Contract syntax traps (`@pre` lambda parameters, `@post(result)` scope)
4. Minimal canonical examples for Core and Shell
5. Escape hatches and markers
6. Minimal configuration
7. Common guard failures and repair patterns

**Replaces:** Old INVAR.md (434 lines) and the agent-facing role of `.invar/examples/`.

---

## 6. Guard Changes

### 6.1 Remove TS Routing

All TypeScript paths removed. Guard becomes Python-only.

### 6.2 Keep All Python Rules

Static analysis, doctests, CrossHair, Hypothesis, and all wiring integrity rules (DX-89).

### 6.3 Invest in Error Message Quality

Guard errors must teach enough to replace deleted examples for instance-level fixes. They do not replace the semantic role of `INVAR.md`; they complement it. This section defines a new requirement for DX-91 implementation. Each violation includes:
- **What's wrong** (clear description)
- **Where** (file:line)
- **How to fix** (corrected code example)
- **Why** (one sentence of rationale)
- **Pattern hint** (the general rule the agent should apply elsewhere)
- **Semantic spec link** (`see INVAR.md#section`)

Example:
```
E: missing_contract — function `calculate_total` in core/ has no @post contract

  @post(lambda result: result >= 0)
  def calculate_total(items: list[Item]) -> float:

  Core functions require @pre/@post + doctest. See INVAR.md#contract-syntax-traps
```

**Audit before deleting examples/:**
1. Remove or rewrite every reference to `.invar/examples/`
2. Verify each deleted example's normative lesson appears either in `INVAR.md` or guard diagnostics
3. Delete `workflow.md` entirely because it preserves removed USBV ceremony
4. Do not preserve examples as a second agent-facing instruction source

This audit is required before implementing Section 2.5.

### 6.4 Enforcement Layers

| Layer | Mechanism | When |
|-------|-----------|------|
| **Primary** | MCP tool (`invar_guard`) + CLAUDE.md instruction | During development |
| **Backstop** | Pre-commit hook | At commit time |
| **CI** | `invar guard --all` in CI pipeline | At PR time |

Document CI integration in README (one-line example, not a built feature).

---

## 7. Documentation Changes

### 7.1 Archive Old Proposals

Move to `docs/proposals/archive/`:
- DX-22 through DX-81, DX-87 (completed or superseded)
- LX-05, LX-06, LX-07 (TS-related, obsolete)
- DX-79 (feedback, removed)

Keep active: DX-88, DX-89, DX-91.

### 7.2 README.md Rewrite

1. What Invar is (one paragraph)
2. Install (`uv add --dev invar-tools invar-runtime`)
3. Init (`invar init`)
4. Use (`invar guard`)
5. Tools reference table
6. Core/Shell in 5 lines
7. CI integration example (one line)

### 7.3 Update `.invar/context.md`

Remove references to USBV, skills, hooks, TypeScript, protocol templates, and `.invar/examples/` as required reading.

### 7.4 Archive or Replace `docs/AGENTS.md`

`docs/AGENTS.md` currently documents the skill/hook-era model and conflicts with DX-91. On implementation:
- either archive it as a v1 historical artifact
- or replace it with a minimal note pointing agents to `CLAUDE.md` and `INVAR.md`

It must not remain as an active source of skills/hooks instructions after DX-91 lands.

---

## 8. Code Impact

### 8.1 Current Codebase

| Component | Files | LOC |
|-----------|-------|-----|
| CLI Commands | 15 | 4,598 |
| MCP Server | 2 | 1,056 |
| TypeScript Tools | 35 | 5,981 |
| Templates | 79 | 12,817 |
| **Total** | **131** | **24,452** |

### 8.2 Deletions (~107 files, ~18,300 lines, 75%)

| Area | Files | Lines |
|------|-------|-------|
| node_tools/ | 35 | 5,981 |
| Templates (skills, hooks, protocol, examples, onboard, TS) | ~62 | ~10,000 |
| ts_compiler.py | 1 | ~300 |
| CLI commands (uninstall, template_sync, feedback, skill, hooks, update, sync_self, test, mutate) | 9 | ~2,000 |

### 8.3 Rewrites

| File | Before | After |
|------|--------|-------|
| init.py | ~700 lines | ~80 lines |
| guard.py | ~800 lines | ~600 lines |
| perception.py | ~600 lines | ~400 lines |
| handlers.py | ~500 lines | ~400 lines |
| server.py | ~550 lines | ~450 lines |

### 8.4 CLI: Before → After

**Keep (6):** guard, sig, map, refs, init, doc *

**Remove (11):** update, uninstall, test, verify, mutate, rules, version, feedback *, hooks *, skill *

**Keep internal-only:** `dev sync` for maintaining generated semantic artifacts during Invar development

Minimum retained scope for `dev sync`:
- regenerate Invar's own `CLAUDE.md` managed block
- regenerate `INVAR.md`
- keep any other managed artifacts required by `invar init` in sync

Out of scope for retained `dev sync`: skills, hooks, examples, onboarding assets, or multi-agent template families.

---

## 9. Migration Path

### 9.1 Runtime: No Breaking Changes

@pre, @post, guard, sig, map, refs — all unchanged.

### 9.2 `invar init` v2 on v1 Project

Active cleanup (not "leave old files inert") with explicit user confirmation:
1. Detect v1 layout and preview impacted paths
2. Back up preserved user data (`.invar/context.md`, `project-additions.md`) and any user-customized legacy instruction files that will be deleted
3. Ask for confirmation before deletion/overwrite
4. Delete stale agent config and stale semantic files (`.claude/skills/`, `.claude/hooks/`, `.invar/examples/`)
5. Replace CLAUDE.md managed sections with new 50-line content
6. Create/overwrite `INVAR.md` as agent semantic spec
7. Print migration summary and backup locations
8. Run a post-migration validation step: `invar guard --all`, then verify no surviving references to deleted instruction sources remain

### 9.3 Version: v2.0.0

Breaking changes:
- Removed CLI commands
- Removed TypeScript support
- Changed init behavior
- New CLAUDE.md/INVAR.md format

---

## 10. Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `invar init` generated files | 30+ | 3-4 |
| Template files in repo | 79 | ~5 |
| CLAUDE.md (invar section) | ~200 lines | ~50 lines |
| Time: install → first guard | ~10 min | ~2 min |
| CLI commands | 18 | 6 |
| Agent compatibility | Claude Code only | Any agent |
| Codebase | 24,452 LOC | ~6,100 LOC |

---

## 11. Non-Goals

- Not changing guard verification logic
- Not changing runtime package
- Not removing MCP support
- Not removing doc tools (DX-76)
- Not making Core/Shell opt-in (it's mandatory, proven value)

---

## 12. Resolved Decisions

1. **Guard flags**
   - Keep `--contracts-only` as a useful fast-path for contract coverage and CI checks.
   - Remove `--coverage` from the DX-91 surface; revisit only if a clear post-v2 need appears.
2. **MCP config generation**
   - Remove automatic MCP config generation from `invar init`.
   - `.mcp.json` setup becomes manual documentation, not generated state.
3. **`invar dev sync` scope**
   - Keep only the minimum internal sync surface needed to regenerate `CLAUDE.md`, `INVAR.md`, and any other artifacts directly emitted by `invar init`.

---

## Appendix: Related Proposals

- DX-89 (Wiring Integrity): Continues in parallel, unaffected by simplification
- DX-87 (Remove Multi-Agent): Superseded — absorbed into DX-91
- DX-88 (dead_export Precision): Complete
