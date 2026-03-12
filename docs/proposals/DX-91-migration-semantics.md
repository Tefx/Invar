# DX-91: Migration Semantics Specification

**Status:** Final
**Date:** 2026-03-12
**Derived from:** DX-91-simplification.md, DX-91-claude-md-draft.md, DX-91-invar-md-draft.md

---

## 1. Scope

This document defines the **canonical execution contract** for DX-91. Downstream implementation and test phases must reference this document without reinterpretation.

---

## 2. Keep/Remove Boundary (Canonical)

### 2.1 What Stays

| Category | Items | Lines Affected |
|----------|-------|----------------|
| **CLI Commands** | `guard`, `sig`, `map`, `refs`, `init`, `doc *` | ~3,600 |
| **MCP Server** | All tools unchanged | ~1,056 |
| **Runtime** | `invar-runtime` package unchanged | — |
| **Core Rules** | Core/Shell, @pre/@post, doctests | — |
| **Wiring Rules** | DX-89 rules continue | — |
| **Pre-commit** | Single hook: `invar guard` | — |

### 2.2 What Gets Removed

**Canonical delete list (implementation reference):**

| Category | Files | Lines | Delete Action |
|----------|-------|-------|---------------|
| `node_tools/` | 35 files | ~5,981 | Delete entire directory (must exist) |
| TS routing in guard/perception/sig/map/refs | — | ~500 | Remove TS branches |
| Skills templates | `templates/skills/**` | ~2,000 | Delete if present (non-fatal if absent) |
| Hooks templates | `templates/hooks/**` | ~200 | Delete if present (non-fatal if absent) |
| Onboard templates | `templates/onboard/**` | ~200 | Delete if present (non-fatal if absent) |
| Examples (agent-facing) | `.invar/examples/` | — | Delete if present (non-fatal if absent) |
| CLI commands removed | 9 files | ~2,000 | Delete command modules (must exist) |
| Feedback collection | DX-79 code | ~300 | Remove all feedback code (must exist) |

**Optional-file semantics:** Directories marked "if present" proceed silently when absent. No error for missing optional deletions.

### 2.3 CLI Surface Change

| Before (18) | After (6) |
|-------------|-----------|
| `guard` | ✅ KEEP |
| `sig` | ✅ KEEP |
| `map` | ✅ KEEP |
| `refs` | ✅ KEEP |
| `init` | ✅ KEEP (rewrite) |
| `doc *` | ✅ KEEP |
| `update` | ❌ REMOVE |
| `uninstall` | ❌ REMOVE |
| `test` | ❌ REMOVE |
| `verify` | ❌ REMOVE |
| `mutate` | ❌ REMOVE |
| `rules` | ❌ REMOVE |
| `version` | ❌ REMOVE (use `--version`) |
| `feedback *` (3) | ❌ REMOVE |
| `hooks *` (2) | ❌ REMOVE |
| `skill *` (2) | ❌ REMOVE |
| `dev sync` | ⚠️ KEEP (internal-only, reduced scope) |

---

## 3. init v2 Behavior

### 3.1 Command Surface

```bash
# Install (recommended)
uv add --dev invar-tools invar-runtime

# Initialize (non-interactive for fresh projects)
invar init                    # Default: writes to CLAUDE.md
invar init --file AGENTS.md   # Alternative target
invar init --preview          # Dry-run mode
```

**Removed flags:**
- `--claude`, `--pi`, `--mcp-only`, `--language` — multi-agent selection removed
- Interactive agent/file selection UI removed

**New behavior:**
- Non-interactive for fresh projects (no v1 markers)
- Interactive confirmation required **only for migration** (v1 layout detected)

### 3.2 Generated Files

| File | Content | Lines |
|------|---------|-------|
| `CLAUDE.md` | Injected section in `<!--invar:begin/end-->` markers | ~50 |
| `INVAR.md` | Agent semantic spec (fully managed) | ~70-120 |
| `.pre-commit-config.yaml` | Single hook: `invar guard` | ~8 |

**NOT generated:**
- `.invar/examples/`
- `.invar/context.md`
- `.claude/skills/`
- `.claude/hooks/`
- `.pi/hooks/`
- `.pi/tools/`
- Directory skeleton (`src/core/`, `src/shell/`)
- `.mcp.json` (manual setup only)

### 3.3 Managed Section Markers

**v2 uses single marker pair:**

```markdown
<!--invar:begin-->
... managed content ...
<!--invar:end-->
```

**v1 used four regions (removed):**
- `<!--invar:critical-->`
- `<!--invar:managed-->`
- `<!--invar:project-->`
- `<!--invar:user-->`

**Migration:**
- v1 multi-region content → v2 single region
- `<!--invar:user-->` content outside markers → preserved verbatim
- User content in CLAUDE.md outside markers → preserved

---

## 4. Migration Behavior (v1 → v2)

### 4.1 Detection

A project is considered **v1** if **any** of these exist:
- `.claude/skills/` directory
- `.claude/hooks/` directory
- `.pi/hooks/` directory
- `.pi/tools/` directory
- `.invar/examples/` directory
- `INVAR.md` with managed header comment (v1 format)
- CLAUDE.md with `<!--invar:critical-->` or `<!--invar:managed-->` markers

### 4.2 Migration Preview Requirement

**Fresh init (no v1 markers):** Non-interactive. Direct creation.

**Migration (v1 detected):** MUST require explicit preview + confirmation:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠  Legacy Invar v1 layout detected. Migration preview follows.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[DELETED] Stale agent config (non-fatal if absent):
  • .claude/skills/          (delete if present)
  • .claude/hooks/           (delete if present)
  • .pi/hooks/               (delete if present)
  • .pi/tools/               (delete if present)
  • .invar/examples/         (delete if present)

[PRESERVED] User data (backed up before deletion, if present):
  • .invar/context.md              → .invar/backup/v1-context.md (if present)
  • .invar/project-additions.md    → .invar/backup/v1-project-additions.md (if present)

[OVERWRITTEN] Managed files:
  • INVAR.md              (fully managed — no user edits)
  • CLAUDE.md invar block (managed section replaced)

────────────────────────────────────────────────────────────
Proceed? [y/N]
```

### 4.3 Migration Steps (Atomic)

**Required execution order:**

1. **Detect** v1 layout (check all detection criteria from 4.1)
2. **Calculate preview** — list file categories: deleted, preserved/backed up, overwritten
3. **Prompt for confirmation** — abort if user declines
4. **Create backup directory** — `.invar/backup/`
5. **Copy preserved user files** — only if `.invar/context.md` or `.invar/project-additions.md` exist (non-fatal if absent)
6. **Delete stale directories** — remove all agent-era assets in one pass (skip absent directories silently)
7. **Replace managed sections** — CLAUDE.md `<!--invar:begin/end-->` content replaced
8. **Create/overwrite INVAR.md** — new semantic spec
9. **Print migration summary** — deleted paths, backed up files, overwritten files

**Failure handling:**
- If backup fails → abort migration, do not proceed to deletion
- If deletion fails → stop, error message includes partial state
- If overwrite fails → stop, error message includes partial state

### 4.4 User Content Preservation

| File | User Content Location | Preservation |
|------|----------------------|--------------|
| `CLAUDE.md` | Outside `<!--invar:begin/end-->` | Preserved verbatim |
| `.invar/context.md` | Entire file (if present) | Backed up (non-fatal if absent), user retains original |
| `.invar/project-additions.md` | Entire file (if present) | Backed up (non-fatal if absent), user retains original |
| `INVAR.md` | N/A (fully managed) | Overwritten without backup (no user edits expected) |

**Optional-file semantics:**
- `.invar/context.md` and `.invar/project-additions.md` are optional
- If absent: migration proceeds without error, no backup needed
- If present: backup required before proceeding

**Last-writer-wins scope:**
- Applies **only** to regenerated managed sections between `<!--invar:begin/end-->`
- Does NOT apply to user content outside markers
- Does NOT apply to `.invar/context.md` (preserved, not overwritten)

### 4.5 Idempotent Re-run Expectations

| State | Behavior |
|-------|----------|
| Fresh project (no v1, no v2) | Creates v2 files |
| v2 already present, no changes needed | Replaces content between markers (idempotent) |
| v2 already present, user content outside markers | Preserves user content, replaces managed content |
| v1 detected | Runs migration (see 4.3) |
| v1 already migrated | Same as v2 re-run |

**No duplicate content:**
- Re-running `invar init` does not append duplicate sections
- Managed content is replaced in-place between existing markers

---

## 5. dev sync Scope (Reduced)

### 5.1 What dev sync Does After DX-91

| Action | Before DX-91 | After DX-91 |
|--------|--------------|-------------|
| Regenerate CLAUDE.md managed block | ✅ | ✅ |
| Regenerate INVAR.md | ✅ | ✅ |
| Sync skills templates | ✅ | ❌ REMOVED |
| Sync hooks templates | ✅ | ❌ REMOVED |
| Sync examples | ✅ | ❌ REMOVED |
| Sync onboard templates | ✅ | ❌ REMOVED |

### 5.2 Internal Use Only

`invar dev sync` becomes an internal maintenance command for:
- Invar developers updating managed content
- Regenerating semantic artifacts after template changes

**Not for end-user workflows.**

---

## 6. CLAUDE.md Injected Content (~50 lines)

```markdown
<!--invar:begin-->
## Invar

**CRITICAL: Write `@pre`/`@post` contracts and at least one doctest BEFORE implementing a Core function. Guard rejects uncontracted Core code.**

### Architecture

| Zone | Path | Rules |
|------|------|-------|
| Core | `**/core/**` | `@pre` + `@post` + doctest, no I/O imports |
| Shell | `**/shell/**` | returns `Result[T, E]`, handles I/O |

If code touches files, network, env vars, time, randomness, or subprocesses, use Shell.

### Verification

Run `invar guard` after changes. Fix errors before committing.

### Tools

| Tool | Use |
|------|-----|
| `invar guard` | verify architecture and contracts |
| `invar sig <file>` | inspect signatures and contracts |
| `invar map [path]` | inspect entry points |
| `invar refs <file>::<symbol>` | inspect references |

### Contract Traps

```python
# @pre must include all parameters, including defaults
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# @post only receives result
@post(lambda result: result >= 0)
```

### Escape Hatches

```python
# @invar:allow dead_export: CLI entry point called by framework
```

Exact syntax and repair patterns: `INVAR.md`
<!--invar:end-->
```

---

## 7. INVAR.md Content (~70-120 lines)

**Location:** Top-level `INVAR.md`
**Characteristics:**
- Imperative, compact, optimized for agent consumption
- Contains only normative patterns and repair guidance
- No references to `.invar/examples/` or deleted workflow files
- Stable section anchors for guard diagnostics

**Required sections:**
1. Before writing code (contracts first, Core vs Shell decision)
2. Core/Shell decision rule
3. Contract syntax traps (`@pre` lambda parameters, `@post(result)` scope)
4. Canonical Core example
5. Canonical Shell example
6. Escape hatches and markers
7. Minimal configuration
8. Common guard failures and repair patterns

**Draft:** See `docs/proposals/DX-91-invar-md-draft.md` for the ~70-120 line target.

---

## 8. Guard Changes

### 8.1 TypeScript Routing Removed

All TypeScript detection and routing removed from:
- `guard.py`
- `perception.py`
- `sig` command
- `map` command
- `refs` command
- MCP handlers

### 8.2 Error Message Requirements

Each guard violation must include:
1. **What's wrong** — clear description
2. **Where** — file:line
3. **How to fix** — corrected code example
4. **Why** — one sentence rationale
5. **Pattern hint** — general rule to apply elsewhere
6. **Semantic spec link** — `see INVAR.md#section`

### 8.3 Enforcement Layers

| Layer | Mechanism | When |
|-------|-----------|------|
| Primary | MCP tool + CLAUDE.md instruction | Development |
| Backstop | Pre-commit hook | Commit time |
| CI | `invar guard --all` in CI pipeline | PR time |

---

## 9. Documentation Changes

### 9.1 Archive Proposals

**Move to `docs/proposals/archive/`:**
- DX-22 through DX-81 (completed or superseded)
- DX-87 (superseded by DX-91)
- LX-05, LX-06, LX-07 (TS-related, obsolete)
- DX-79 (feedback, removed)

**Keep active:**
- DX-88 (dead_export precision)
- DX-89 (wiring integrity)
- DX-91 (this proposal)

### 9.2 README.md Rewrite

1. What Invar is (one paragraph)
2. Install (`uv add --dev invar-tools invar-runtime`)
3. Init (`invar init`)
4. Use (`invar guard`)
5. Tools reference table
6. Core/Shell in 5 lines
7. CI integration example (one line)

### 9.3 AGENTS.md Status

**Option A:** Archive as v1 historical artifact
**Option B:** Replace with minimal redirect to CLAUDE.md + INVAR.md

**Decision:** Option A recommended. AGENTS.md documents removed skill/hook model.

---

## 10. Failure Paths (Explicit)

### 10.1 Stale Legacy State

**Condition:** `.claude/skills/` exists but references non-existent functionality

**Handling:**
1. Detection includes stale directory check
2. Preview explicitly lists deletion
3. User confirmation required
4. Entire directory deleted, not left "inert"

### 10.2 Backup Failure

**Condition:** Cannot write to `.invar/backup/`

**Handling:**
- Abort migration
- Do not proceed to deletion
- Print clear error: "Backup failed. Migration aborted."

### 10.3 Deletion Failure

**Condition:** Cannot delete stale directory

**Handling:**
- Stop immediately
- Print partial state: which directories were deleted, which were not
- Exit with error code, require manual intervention

### 10.4 Idempotent Re-run Edge Cases

| Scenario | Action |
|----------|--------|
| v2 present, user modified managed section | Replace managed content exactly (managed section is regenerated, not merged) |
| v2 present, user added content inside markers | Replaced (user content inside markers is not preserved; see §4.4) |
| v2 present, user moved markers | Detect markers, use current position |
| v1 present but partially migrated | Treat as v1, run full migration |

**Canonical semantics (see §4.4):** User content belongs *outside* `<!--invar:begin/end-->` markers. Content inside markers is regenerated exactly, never merged.

---

## 11. Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| `invar init` generated files | 30+ | 3-4 |
| CLAUDE.md (invar section) | ~200 lines | ~50 lines |
| Template files in repo | 79 | ~5 |
| CLI commands | 18 | 6 |
| Agent compatibility | Claude Code only | Any agent |

---

## 12. Implementation Handoff

### Phase Order

1. **Semantics phase** (this document) — Final execution contract
2. **CLI surface phase** — Remove deprecated commands, rewrite init
3. **Template phase** — Create v2 templates, remove v1 templates
4. **Guard phase** — Remove TS routing, improve error messages
5. **Documentation phase** — Archive proposals, update README, AGENTS.md decision
6. **Tests phase** — Migration tests, idempotency tests

### Files Changed (Summary)

**Deleted:**
- `src/invar/node_tools/` (entire directory, 35 files)
- `src/invar/shell/commands/feedback.py`
- `src/invar/shell/commands/hooks.py`
- `src/invar/shell/commands/skill.py`
- `src/invar/shell/commands/test.py`
- `src/invar/shell/commands/verify.py`
- `src/invar/shell/commands/mutate.py`
- `src/invar/shell/commands/rules.py`
- `src/invar/shell/commands/uninstall.py`
- `src/invar/shell/commands/update.py`
- `src/invar/templates/skills/` (entire directory)
- `src/invar/templates/hooks/` (entire directory)
- `src/invar/templates/onboard/` (entire directory)
- `src/invar/templates/examples/typescript/` (entire directory)

**Rewritten:**
- `src/invar/shell/commands/init.py` (~700 → ~80 lines)
- `src/invar/shell/commands/guard.py` (remove TS routing)
- `src/invar/shell/commands/perception.py` (remove TS routing)
- `INVAR.md` (v2 semantic spec)
- `CLAUDE.md` (invar section only)

### Gaps / Open Questions

1. **DX-81 multi-agent init:** Spec says agent flags removed, but DX-81 was completed. Should v2 retain minimal `--claude`/`--pi` for backward compat? → **Decision: Remove flags entirely. Single target file via `--file`.**
2. **`invar dev sync` removal of examples sync:** Implementation should update to not attempt syncing `.invar/examples/` (directory deleted).
3. **MCP config generation:** Spec says no automatic `.mcp.json` generation. Implementation should remove MCP config from init output.

---

## 13. References

- **Source proposals:**
  - `docs/proposals/DX-91-simplification.md` — Motivation and scope
  - `docs/proposals/DX-91-claude-md-draft.md` — CLAUDE.md content
  - `docs/proposals/DX-91-invar-md-draft.md` — INVAR.md content

- **Related:**
  - DX-89 (Wiring Integrity) — Continues unchanged
  - DX-87 (Remove Multi-Agent) — Superseded, absorbed into DX-91
  - DX-79 (Feedback Collection) — Removed