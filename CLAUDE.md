# Invar Project Development Guide

> **"Agent-Native Execution, Human-Directed Purpose"**

This project follows the Invar methodology. See [INVAR.md](./INVAR.md) for protocol, [sections/](./sections/) for workflow details.

**Protocol:** v5.0 | **PyPI:** `invar-tools` + `invar-runtime`

---

## Check-In / Final

**First message:** `✓ Check-In: guard PASS | top: <entry1>, <entry2>`
**Last message:** `✓ Final: guard PASS | 0 errors, N warnings`

Then read `.invar/context.md` for project state.

---

## Project Structure

```
src/invar/
├── core/    # Pure logic, @pre/@post required, no I/O
└── shell/   # I/O operations, Result[T, E] required
```

---

## Workflows (DX-35)

| Workflow | Triggers | Details |
|----------|----------|---------|
| `/investigate` | "why", "explain", vague tasks | [sections/investigate.md](sections/investigate.md) |
| `/propose` | "should we", "compare" | [sections/propose.md](sections/propose.md) |
| `/develop` | "add", "fix", "implement" | [sections/develop.md](sections/develop.md) |
| `/review` | After /develop, `review_suggested` | [sections/review.md](sections/review.md) |

**Override:** `/develop!` forces workflow, skips routing.

---

## Project Rules

1. **Language:** English for docs/code. User's language for conversation.
2. **Verify Always:** Run `invar guard` after changes.
3. **Warning Policy:** Fix warnings in files you modify.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol core |
| [sections/](./sections/) | Workflow details |
| [.invar/context.md](./.invar/context.md) | Project state |

---

## Dependencies

```bash
pip install -e ".[dev]"    # Development mode
pip install -e runtime/    # Runtime in dev mode
```
