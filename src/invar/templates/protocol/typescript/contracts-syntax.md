## Contract Syntax (TypeScript)

### Zod Schema Patterns

```typescript
import { z } from 'zod';

// Input validation (precondition)
const CalcInput = z.object({
  x: z.number().int().nonnegative(),
  y: z.number().int().default(0),
});

// Output validation (postcondition)
const CalcOutput = z.number().int().nonnegative();

function calculate(input: z.infer<typeof CalcInput>): number {
  const { x, y } = CalcInput.parse(input);
  const result = x + y;
  return CalcOutput.parse(result);
}
```

### Meaningful Contracts

```typescript
// Redundant - TypeScript already checks this
const BadSchema = z.object({
  x: z.number(),  // Just type checking
});

// Meaningful - checks business logic
const GoodSchema = z.object({
  x: z.number().positive(),  // Domain constraint
});

// Meaningful - checks relationship
const RangeInput = z.object({
  start: z.number(),
  end: z.number(),
}).refine(data => data.start < data.end, {
  message: "start must be less than end",
});
```

### Postcondition Scope

```typescript
// Output schema can only validate the result
const OutputSchema = z.object({
  total: z.number().nonnegative(),
  items: z.array(z.string()).min(1),
});

// For input-dependent validation, use refinement in function
function process(items: string[]): z.infer<typeof OutputSchema> {
  const result = { total: items.length, items };
  return OutputSchema.parse(result);
}
```

### JSDoc Examples

```typescript
/**
 * Calculate doubled value.
 * @example calculate(5)  // => 10
 * @example calculate(0)  // => 0 (edge case)
 */
function calculate(x: number): number {
  return x * 2;
}
```
