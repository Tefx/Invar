## Troubleshooting (TypeScript)

### Guard Output Interpretation

```json
{
  "status": "failed",
  "contracts": {
    "coverage": {"total": 10, "withContracts": 5, "percent": 50},
    "blind_spots": [
      {"function": "deleteUser", "risk": "high", "suggested_schema": "z.object({userId: z.string()})"}
    ]
  }
}
```

| Field | Meaning | Action |
|-------|---------|--------|
| `status: failed` | Verification errors | Fix tsc/eslint/test errors first |
| `coverage.percent < 70` | Low contract coverage | Add Zod schemas to uncovered functions |
| `blind_spots` (high risk) | Critical functions without contracts | Priority: add schemas before next commit |
| `blind_spots` (medium risk) | Functions that should have contracts | Add schemas when modifying |

### Fixing Blind Spots

```typescript
// Before: blind spot (no validation)
function deleteUser(userId: string): void {
  db.delete(userId);
}

// After: contract added
const DeleteUserInput = z.object({
  userId: z.string().uuid(),
});

function deleteUser(input: z.infer<typeof DeleteUserInput>): void {
  const { userId } = DeleteUserInput.parse(input);
  db.delete(userId);
}
```

### Size Limits (Agent Quick Reference)

| Rule | Limit | Fix |
|------|-------|-----|
| `function_too_long` | **50 lines** | Extract helper: `_impl()` + main with JSDoc |
| `file_too_long` | **500 lines** | Split by responsibility |
| `entry_point_too_thick` | **15 lines** | Delegate to Shell functions |

*JSDoc/comment lines excluded from counts.*

### Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ZodError` at runtime | Schema mismatch | Check input against Zod schema |
| `shell_result` error | Shell func no Result | Add Result<T,E> or @invar:allow |
| `isErr()` not found | Wrong Result import | Use `neverthrow` Result type |

### Result Type Usage

```typescript
import { Result, ok, err } from 'neverthrow';

// Creating results
return ok(value);
return err(error);

// Checking results
if (result.isErr()) {
  handleError(result.error);
} else {
  useValue(result.value);
}

// Chaining
result
  .map(transform)
  .andThen(nextOperation);

// Async operations
import { ResultAsync } from 'neverthrow';

const asyncResult = ResultAsync.fromPromise(
  fetch(url),
  (e) => new Error(`Fetch failed: ${e}`)
);
```

### Zod Validation Patterns

```typescript
import { z } from 'zod';

// Safe parse (returns Result-like object)
const parsed = Schema.safeParse(data);
if (!parsed.success) {
  console.error(parsed.error.issues);
}

// Strict parse (throws on error)
const validated = Schema.parse(data);
```
