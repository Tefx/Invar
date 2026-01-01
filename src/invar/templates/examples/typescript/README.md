# Invar Examples (TypeScript)

Reference patterns for TypeScript projects using the Invar Protocol.

## Files

| File | Purpose |
|------|---------|
| `contracts.ts` | Zod schema patterns for pre/postconditions |
| `core_shell.ts` | Core/Shell separation with neverthrow |
| `functional.ts` | Functional patterns (Branded Types, NonEmpty, Exhaustive Match) |
| `workflow.md` | Complete USBV workflow example |

## Dependencies

```bash
npm install zod neverthrow
```

## Quick Reference

| Concept | TypeScript Pattern |
|---------|-------------------|
| Precondition | `z.number().positive()` |
| Postcondition | Return type validation |
| Examples | JSDoc `@example` blocks |
| Shell errors | `Result<T, E>` from neverthrow |

---

*Managed by Invar - regenerated on `invar update`*
