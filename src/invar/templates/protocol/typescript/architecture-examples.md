## Core Example (TypeScript)

```typescript
import { z } from 'zod';

// Contracts as Zod schemas
const DiscountInput = z.object({
  price: z.number().positive(),
  discount: z.number().min(0).max(1),
});

const DiscountOutput = z.number().nonnegative();

/**
 * @example discountedPrice({ price: 100, discount: 0.2 }) // => 80
 * @example discountedPrice({ price: 100, discount: 0 })   // => 100 (edge: no discount)
 */
export function discountedPrice(input: z.infer<typeof DiscountInput>): number {
  const { price, discount } = DiscountInput.parse(input);
  const result = price * (1 - discount);
  return DiscountOutput.parse(result);
}
```

**Self-test:** Can someone else write the exact same function from just Zod schemas + @example?

**Forbidden in Core:** `fs`, `path`, `http`, `fetch`, `process.env`, `Date.now()`

## Shell Example (TypeScript)

```typescript
import { Result, ok, err } from 'neverthrow';
import { readFileSync } from 'fs';

interface Config { [key: string]: unknown }

export function readConfig(path: string): Result<Config, string> {
  try {
    const content = readFileSync(path, 'utf-8');
    return ok(JSON.parse(content));
  } catch (e) {
    if (e instanceof Error && 'code' in e && e.code === 'ENOENT') {
      return err(`File not found: ${path}`);
    }
    return err(`Invalid JSON: ${e}`);
  }
}
```

**Pattern:** Shell reads file → passes content to Core → returns Result.

More examples: `.invar/examples/`
