## Invar Project Structure

```
src/invar/
├── core/           # Pure logic, @pre/@post required, no I/O
└── shell/          # I/O operations, Result[T, E] required
    ├── commands/   # CLI commands (guard, init, dev sync)
    └── prove/      # Verification (crosshair, hypothesis)
```

---

## Project Rules

1. **Language:** English for docs/code. User's language for conversation.
2. **Verify Always:** Run `invar_guard()` after changes.
3. **Warning Policy:** Fix warnings in files you modify.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol core |
| [docs/proposals/](./docs/proposals/) | Development proposals |
| [.invar/context.md](./.invar/context.md) | Project state |

---

## Dependencies

```bash
pip install -e ".[dev]"    # Development mode
pip install -e runtime/    # Runtime in dev mode
```

---

## PyPI Packages

| Package | Purpose |
|---------|---------|
| `invar-tools` | Dev tools (guard, sig, map) |
| `invar-runtime` | Runtime contracts (@pre, @post) |
