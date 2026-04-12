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
| `invar guard` | verify architecture and contracts (changed=true default) |
| `invar guard --all` | full project verification (may defer for large repos) |
| `invar sig <file>` | inspect signatures and contracts |
| `invar map [path]` | inspect entry points |
| `invar refs <file>::<symbol>` | inspect references |
| `invar_guard_status(run_id)` | check deferred run status (DX-94) |
| `invar_guard_wait(run_id)` | long-poll deferred run (DX-94) |

**Changed Default:** Both CLI and MCP default to `changed=true` (only modified files)
for fast feedback. Use `--all` or `changed=false` for full scans.

**Deferred Full-Scan (DX-94):** Large repositories may return `status: deferred`.
Poll with `invar_guard_status` or long-poll with `invar_guard_wait`.

**Mutation Testing (DX-97):** Enable with `--mutation` flag or `mutation_enabled=true`
in config. Output includes `score`, `passed`, `survivor_evidence`, and file classification
(`eligible_files`, `ineligible_files`, `files_with_zero_sites`). Fail-closed: `timeout>0`
or `error>0` causes failure regardless of score.

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
def my_cli_command(): ...

# @invar:allow dead_export: Abstract base class for subclassing
class MyProtocol(Protocol): ...
```

Protocol/ABC subclasses are automatically exempt from dead_export (no escape hatch needed).
Exact syntax and repair patterns: `INVAR.md`
<!--invar:end-->


<!-- VECTL:AGENTS:BEGIN -->
## Plan Tracking (vectl)

vectl tracks this repo's implementation plan as a structured `plan.yaml`:
what to do next, who claimed it, and what counts as done (with verification evidence).

Full guide: `vectl_guide` (CLI fallback: `vectl guide`)
Quick view: `vectl_status` (CLI fallback: `vectl status`)

### MCP vs CLI
- Source of truth: `plan.yaml` (channel-agnostic).
- **Always prefer MCP tools** (`vectl_status`, `vectl_claim`, `vectl_complete`, etc.) when available.
- CLI fallback priority: `uv run vectl` > `vectl` > `uvx vectl`.
- Evidence requirements are identical across MCP and CLI.

### Claim-time Guidance
- `vectl claim` may emit a bounded Guidance block delimited by:
  - `--- VECTL:GUIDANCE:BEGIN ---`
  - `--- VECTL:GUIDANCE:END ---`
- For automation/CI: use `vectl claim --no-guidance` to keep stdout clean.

### plan.yaml — Managed File (DO NOT EDIT DIRECTLY)

`plan.yaml` is exclusively owned by vectl. Direct edits (Edit, Write, sed, or
any file tool) **will** corrupt plan state — vectl performs CAS writes, lock
recalculation, and schema validation on every save, none of which run on direct
edits.

**To modify plan state, ONLY use:**
- MCP (preferred): `vectl_claim`, `vectl_complete`, `vectl_mutate`, etc.
- CLI (fallback): `uv run vectl claim`, `vectl claim`, or `uvx vectl claim`, etc.

If a vectl command fails, report the error — do **not** edit `plan.yaml`
directly as a workaround. Use `vectl guide stuck` for troubleshooting.

### Rules
- One claimed step at a time.
- Evidence is mandatory when completing (commands run + outputs + gaps).
- Spec uncertainty: leave `# SPEC QUESTION: ...` in code, do not guess.

### Step ID Uniqueness
**Step IDs must be globally unique across ALL phases.**
- Example: `auth.login` and `api.login` are different step IDs.
- Example: Using just `login` in two phases creates a duplicate — not allowed.
- If you have legacy duplicate step IDs, use `vectl migrate-step-id --dry-run`
  to preview and `--yes` to repair.

### For Architects / Planners
- **Design Mode**: Run `vectl_guide` (CLI fallback: `vectl guide --on planning`) to learn the Architect Protocol.
- **Ambiguity = Failure**: Workers will hallucinate if steps are vague.
- **Constraint Tools**:
  - `--evidence-template`: Force workers to provide specific proof (e.g., "Paste logs here").
  - `--refs`: Pin specific files (e.g., "src/auth.py") to the worker's context.
<!-- VECTL:AGENTS:END -->
