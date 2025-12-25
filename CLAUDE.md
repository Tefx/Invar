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
├── core/           # Pure logic, @pre/@post required, no I/O
└── shell/          # I/O operations, Result[T, E] required
    ├── commands/   # CLI commands (guard, init)
    └── prove/      # Verification (crosshair, hypothesis)
```

---

## Commands (User-Invokable)

| Command | Purpose |
|---------|---------|
| `/audit` | Read-only code review (reports issues, no fixes) |
| `/guard` | Run Invar verification (reports results) |

---

## Workflows (Agent Skills)

| Skill | Triggers | Details |
|-------|----------|---------|
| `/investigate` | "why", "explain", vague tasks | [sections/investigate.md](sections/investigate.md) |
| `/propose` | "should we", "compare" | [sections/propose.md](sections/propose.md) |
| `/develop` | "add", "fix", "implement" | [sections/develop.md](sections/develop.md) |
| `/review` | After /develop, `review_suggested` | [sections/review.md](sections/review.md) |

**Note:** Skills are invoked by agent based on context. Use `/audit` for user-initiated review.

**Override:** `/develop!` forces workflow, skips routing.

---

## Workflow Routing (MANDATORY)

When user message contains these triggers, you MUST invoke the corresponding skill:

| Trigger Words | Skill | Notes |
|---------------|-------|-------|
| "review", "review and fix" | `/review` | Adversarial review with fix loop |
| "implement", "add", "fix", "update" | `/develop` | Unless in review context |
| "why", "explain", "investigate" | `/investigate` | Research mode, no code changes |
| "compare", "should we", "design" | `/propose` | Decision facilitation |

**Violation check (before writing ANY code):**
- "Am I in a workflow?"
- "Did I invoke the correct skill?"

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
