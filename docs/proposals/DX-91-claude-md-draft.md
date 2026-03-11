# DX-91: CLAUDE.md Injected Section Draft (v3)

## Design Constraints

1. **Append-only**: Invar adds a managed section to an existing agent file and never replaces user content outside markers.
2. **Idempotent**: Running `invar init` twice produces the same managed block via `<!--invar:begin-->` / `<!--invar:end-->`.
3. **Default target**: `CLAUDE.md`. `--file` supports alternatives such as `AGENTS.md`.
4. **Thin entry contract**: `CLAUDE.md` stays short and points to `INVAR.md` for durable agent semantics.
5. **Migration preview requirement**: fresh init is non-interactive; destructive migration requires preview plus confirmation.

## Injected Content (~50 lines)

This is what `invar init` appends inside the managed region:

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

## Line Count

Managed region target: ~60 lines.

## Merge Behavior

| Scenario | Action |
|----------|--------|
| `CLAUDE.md` missing | create file with managed section |
| file exists without markers | append managed section |
| file exists with markers | replace content between markers |
| user content outside markers | preserve unchanged |

## MCP Variant

When MCP is available, command examples may be rendered as MCP calls instead of CLI commands:

| CLI | MCP |
|-----|-----|
| `invar guard` | `invar_guard()` |
| `invar sig <file>` | `invar_sig(target="<file>")` |
| `invar map` | `invar_map()` |
| `invar refs <sym>` | `invar_refs(target="<sym>")` |

## What Was Removed

| Removed | Why |
|---------|-----|
| Check-In / Final protocol | ceremony, not durable agent guidance |
| USBV workflow phases | agents do not reliably follow them |
| Task completion checklists | redundant with guard |
| Skills and hooks | Claude-specific and unreliable |
| TypeScript variants | product boundary is now Python-only |
| Expanded prose tables | moved into concise `INVAR.md` semantic rules |
