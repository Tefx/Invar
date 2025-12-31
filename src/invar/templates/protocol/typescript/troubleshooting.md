## Troubleshooting (TypeScript)

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
