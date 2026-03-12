<!--invar:begin-->
## Invar

**CRITICAL: Write `@pre`/`@post` contracts and at least one doctest before implementing a Core function. Guard rejects uncontracted Core code.**

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
