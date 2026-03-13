# Invar Mechanisms

Technical documentation for Invar's verification and architecture mechanisms.

## Quick Reference

| Mechanism | Purpose | When Used |
|-----------|---------|-----------|
| [Verification](verification/index.md) | Smart Guard = static + doctests + CrossHair + Hypothesis | `invar guard` |
| [Architecture](architecture/index.md) | Core/Shell separation, Result monads, Entry points | Code design |
| [Contracts](contracts/index.md) | `@pre`/`@post` contracts, doctests, completeness | Writing functions |
| [Rules](rules/index.md) | Static analysis checks and Fix-or-Explain | Continuous |
| [Workflow](workflow/index.md) | DX-91: Contracts-first, minimal ceremony | Every session |
| [Proposal Workflow](proposal-workflow.md) | Feature-level planning, DX proposals | Large changes |
| [Documentation](documentation.md) | INVAR vs CLAUDE attribution, templates | Project setup |

## Key Concepts

### Verification Pipeline

```
invar guard
    ├─ Static analysis (rules.py)
    ├─ Doctests (pytest --doctest-modules)
    ├─ CrossHair (symbolic verification for contracts)
    └─ Hypothesis (property-based testing via deal.cases)
```

### Two-Layer Architecture

```
┌─────────────────────────────────────────┐
│  Shell Layer (I/O, CLI, HTTP)           │
│  - Returns Result[T, E]                 │
│  - Entry points (Flask, Typer, etc.)    │
│  - Orchestrates Core functions          │
├─────────────────────────────────────────┤
│  Core Layer (Pure Logic)                │
│  - @pre/@post contracts                 │
│  - No I/O imports (os, sys, pathlib)    │
│  - Doctests for verification            │
└─────────────────────────────────────────┘
```

### Fix-or-Explain Enforcement (DX-22)

When complexity violations accumulate:

1. **Per-function**: `shell_too_complex` → INFO (suggestion)
2. **Project-level**: ≥5 unaddressed → ERROR (blocks)

Resolution options:
- Refactor to reduce complexity
- Add `# @shell_complexity: <reason>` marker

See [Rules](rules/index.md) for full enforcement details.
