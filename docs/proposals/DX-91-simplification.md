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

**Remove entirely.** Focus on Python. node_tools/ (5,981 LOC), ts_compiler.py, TS protocol/example/CLAUDE.md templates, TS routing in guard/perception/sig/map/refs.

### 2.5 Examples Directory

**Remove.** Guard error messages replace examples as teaching mechanism (requires investment in error message quality — see Section 4.3).

### 2.6 Feedback Collection (DX-79)

**Remove.** No actionable data, adds consent prompt complexity.

### 2.7 Onboarding System

**Remove.** Goes with skills.

### 2.8 CLI Commands to Remove

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
| `invar dev sync` | Internal only |

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

No interactive prompts. No agent selection. No file selection.

Default target is **CLAUDE.md** (most users use Claude Code, and it auto-loads CLAUDE.md).
`--file` flag for other targets (AGENTS.md, .cursorrules, etc.)

### 3.2 Generated Files

| File | Content | Lines |
|------|---------|-------|
| **CLAUDE.md** | Invar section appended in `<!--invar:begin/end-->` markers | ~50 |
| **INVAR.md** | Complete reference (core/shell, contracts, config, examples) | ~150 |
| **.pre-commit-config.yaml** | Single hook: `invar guard` | ~8 |

Optional:
| **.mcp.json** | MCP server config (if `--mcp` flag) |

**NOT generated:** directory skeleton, .invar/ directory, examples, skills, hooks, context.md.

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

When `invar init` detects a v1 layout (old skills/hooks/protocol):

1. **Back up** `.invar/context.md` and `.invar/project-additions.md` (if exist)
2. **Delete** `.claude/skills/`, `.claude/hooks/` (dead files confuse agents)
3. **Replace** managed sections in CLAUDE.md with new minimal content
4. **Create** INVAR.md (replaces old 434-line version with 150-line version)
5. **Print** summary of what was deleted and where backups are

Stale files MUST be actively cleaned up — not left "inert." Agents read files on disk and will follow old instructions.

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

Full reference: see `INVAR.md`
<!--invar:end-->
```

**~50 lines.** Key content:
1. **Contracts before code** — emphasized as CRITICAL, mandatory
2. Architecture table — Core/Shell zones and rules
3. Tools table — what to use
4. Contract syntax — the 3 most common mistakes
5. Escape hatch — how to suppress rules
6. Configuration — minimal, just paths
7. Pointer to INVAR.md for full reference

---

## 5. INVAR.md Reference (~150 lines)

**Location:** Top-level (architectural guidance, not tooling internals).

**Content:** See `docs/proposals/DX-91-invar-md-draft.md` for full draft.

Sections:
1. Core/Shell decision tree
2. Injection pattern (how to keep Core pure)
3. Core example (@pre/@post + doctest)
4. Shell example (Result[T, E])
5. Result type patterns (Success/Failure/chaining)
6. Full contract syntax (lambda signature, @post scope, meaningful contracts)
7. Full configuration reference (all pyproject.toml keys with defaults)
8. Markers and escape hatches (entry points, shell complexity, @invar:allow)
9. Size limits table
10. Common errors table

**Replaces:** Old INVAR.md (434 lines) + .invar/examples/ (12 files)

---

## 6. Guard Changes

### 6.1 Remove TS Routing

All TypeScript paths removed. Guard becomes Python-only.

### 6.2 Keep All Python Rules

Static analysis, doctests, CrossHair, Hypothesis, and all wiring integrity rules (DX-89).

### 6.3 Invest in Error Message Quality

Guard errors must teach (replacing examples/ and protocol docs). Each violation includes:
- **What's wrong** (clear description)
- **Where** (file:line)
- **How to fix** (corrected code example)
- **Why** (one sentence of rationale)
- **Reference** (`see INVAR.md#section`)

Example:
```
E: missing_contract — function `calculate_total` in core/ has no @post contract

  @post(lambda result: result >= 0)
  def calculate_total(items: list[Item]) -> float:

  Core functions require @pre/@post + doctest. See INVAR.md#contracts
```

**Audit before deleting examples/:** For each example file, verify guard errors fully communicate what the example taught. Any gap → add to INVAR.md.

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

### 7.3 Update .invar/context.md

Remove references to USBV, skills, hooks, TypeScript, protocol templates.

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

**Remove (12):** update, uninstall, test, verify, mutate, rules, version, feedback *, hooks *, skill *, dev sync

---

## 9. Migration Path

### 9.1 Runtime: No Breaking Changes

@pre, @post, guard, sig, map, refs — all unchanged.

### 9.2 `invar init` v2 on v1 Project

Active cleanup (not "leave old files inert"):
1. Back up user data (.invar/context.md, project-additions.md)
2. Delete stale agent config (.claude/skills/, .claude/hooks/)
3. Replace CLAUDE.md managed sections with new 50-line content
4. Create/overwrite INVAR.md (150 lines)
5. Print migration summary

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

## 12. Open Questions

1. **Guard `--contracts-only` and `--coverage` flags** — keep or remove?
2. **MCP config generation** — should `invar init --mcp` create .mcp.json, or leave it fully manual?
3. **Invar's own development** — without `invar dev sync`, how to manage templates during development?

---

## Appendix: Related Proposals

- DX-89 (Wiring Integrity): Continues in parallel, unaffected by simplification
- DX-87 (Remove Multi-Agent): Superseded — absorbed into DX-91
- DX-88 (dead_export Precision): Complete
