<!--invar:critical-->
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
{% if syntax == "mcp" -%}
| **Verify** | `invar_guard` — NOT just `tsc`, NOT just `vitest` |
{% else -%}
| **Verify** | `invar guard` — NOT just `tsc`, NOT just `vitest` |
{% endif -%}
| **Core** | Zod schemas + JSDoc examples, NO I/O imports |
| **Shell** | Returns `Result<T, E>` from `neverthrow` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

### Contract Rules (CRITICAL)

```typescript
import { z } from 'zod';

// ❌ WRONG: No validation, just type annotation
function calc(x: number): number { ... }

// ✅ CORRECT: Zod schema validates at runtime
const CalcInput = z.number().positive();
const CalcOutput = z.number().nonnegative();

function calc(x: number): number {
  const validated = CalcInput.parse(x);
  const result = validated * 2;
  return CalcOutput.parse(result);
}

// ❌ WRONG: Schema only checks type
const BadSchema = z.number();

// ✅ CORRECT: Schema checks domain constraints
const GoodSchema = z.number().positive().max(100);
```

<!--/invar:critical-->
