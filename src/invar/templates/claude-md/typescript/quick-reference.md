## Project Structure

```
src/{project}/
├── core/    # Pure logic (Zod schemas, JSDoc examples, no I/O)
└── shell/   # I/O operations (Result<T, E> return type)
```

**Key insight:** Core receives data (validated types), Shell handles I/O (files, network).

## Quick Reference

| Zone | Requirements |
|------|-------------|
| Core | Zod schemas + JSDoc @example, pure (no I/O) |
| Shell | Returns `Result<T, E>` from `neverthrow` library |

### Core vs Shell (Edge Cases)

- fs/path/http/fetch → **Shell**
- `Date.now()`, `Math.random()` → **Inject param** OR Shell
- Pure logic → **Core**

> Full decision tree: [INVAR.md#core-shell](./INVAR.md#decision-tree-core-vs-shell)
