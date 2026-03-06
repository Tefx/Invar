# DX-91: CLAUDE.md Injected Section Draft (v2.1)

## Design Constraints

1. **Append-only**: Invar adds a managed section to existing CLAUDE.md. Never replaces user content.
2. **Idempotent**: Running `invar init` twice produces same result. Uses `<!--invar:begin-->` / `<!--invar:end-->` markers.
3. **Default target**: CLAUDE.md (most users use Claude Code, which auto-loads it). `--file` flag for alternatives (AGENTS.md, .cursorrules, etc.)
4. **Reference pointer**: Points to top-level `INVAR.md` for full reference.

## Injected Content (~50 lines)

This is what `invar init` appends inside the managed region:

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

## Line count: ~50 lines (managed region only)

## Merge Behavior

| Scenario | Action |
|----------|--------|
| CLAUDE.md doesn't exist | Create with only the managed section |
| CLAUDE.md exists, no invar markers | Append managed section at end |
| CLAUDE.md exists, has invar markers | Replace content between markers (idempotent) |
| User content outside markers | Preserved unchanged |

## MCP Variant

When MCP is available, tool names adjust:

| CLI | MCP |
|-----|-----|
| `invar guard` | `invar_guard()` |
| `invar sig <file>` | `invar_sig(target="<file>")` |
| `invar map` | `invar_map()` |
| `invar refs <sym>` | `invar_refs(target="<sym>")` |

Template uses Jinja2 `{% if syntax == "mcp" %}` to switch (same as current).

## What Was Removed (vs current 257-line AGENT.md.jinja)

| Removed | Lines saved | Why |
|---------|------------|-----|
| Check-In / Final protocol | ~25 | Ceremony, guard is the only checkpoint |
| USBV workflow (4 phases) | ~70 | Agents don't follow, guard enforces outcome |
| Task Completion checklist | ~10 | Redundant with guard |
| Documentation Structure table | ~10 | Merged into INVAR.md |
| Tool Selection expanded table | ~15 | Merged into compact Tools table |
| Visible Workflow / Phase headers | ~20 | Noise |
| TypeScript variants | ~50 | TS support dropped |
| Skills routing | ~15 | Skills system dropped |
| **Total saved** | **~215 lines** | 257 → ~50 lines |
