## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```

**Key insight:** Core receives data (strings), Shell handles I/O (paths, files).

## Quick Reference

| Zone | Requirements |
|------|-------------|
| Core | `@pre`/`@post` + doctests, pure (no I/O) |
| Shell | Returns `Result[T, E]` from `returns` library |

### Core vs Shell (Edge Cases)

- File/network/env vars → **Shell**
- `datetime.now()`, `random` → **Inject param** OR Shell
- Pure logic → **Core**

> Full decision tree: [INVAR.md#core-shell](./INVAR.md#decision-tree-core-vs-shell)
