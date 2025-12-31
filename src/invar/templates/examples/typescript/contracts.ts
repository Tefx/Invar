/**
 * Invar Contract Examples (TypeScript)
 *
 * Reference patterns for Zod schemas as contracts.
 * Managed by Invar - do not edit directly.
 */

import { z } from 'zod';

// =============================================================================
// GOOD: Complete Contract with Zod Schema
// =============================================================================

/**
 * Precondition: price > 0, 0 <= discount <= 1
 * Postcondition: result >= 0
 */
const DiscountedPriceInput = z.object({
  price: z.number().positive(),
  discount: z.number().min(0).max(1),
});

const DiscountedPriceOutput = z.number().nonnegative();

/**
 * Apply discount to price.
 *
 * @example
 * discountedPrice({ price: 100.0, discount: 0.2 })  // => 80.0
 *
 * @example
 * discountedPrice({ price: 100.0, discount: 0 })    // => 100.0 (no discount)
 *
 * @example
 * discountedPrice({ price: 100.0, discount: 1 })    // => 0.0 (full discount)
 */
export function discountedPrice(
  input: z.infer<typeof DiscountedPriceInput>
): number {
  const { price, discount } = DiscountedPriceInput.parse(input);
  const result = price * (1 - discount);
  return DiscountedPriceOutput.parse(result);
}

// =============================================================================
// GOOD: List Processing with Length Constraint
// =============================================================================

/**
 * Precondition: items.length > 0
 * Postcondition: result is finite (no NaN/Infinity)
 */
const AverageInput = z.array(z.number()).nonempty();
const AverageOutput = z.number().finite();

/**
 * Calculate average of non-empty array.
 *
 * @example
 * average([1, 2, 3])  // => 2.0
 *
 * @example
 * average([5])        // => 5.0 (single element)
 *
 * @example
 * average([0, 0, 0])  // => 0.0 (all zeros)
 */
export function average(items: number[]): number {
  const validated = AverageInput.parse(items);
  const sum = validated.reduce((a, b) => a + b, 0);
  const result = sum / validated.length;
  return AverageOutput.parse(result);
}

// =============================================================================
// GOOD: Object Transformation
// =============================================================================

/**
 * Precondition: Object.keys(data).length > 0
 * Postcondition: Object.keys(result).length > 0
 */
const NormalizeKeysInput = z.record(z.string(), z.number()).refine(
  (obj) => Object.keys(obj).length > 0,
  { message: 'Object must have at least one key' }
);

const NormalizeKeysOutput = z.record(z.string(), z.number()).refine(
  (obj) => Object.keys(obj).length > 0,
  { message: 'Result must have at least one key' }
);

/**
 * Lowercase all keys.
 *
 * @example
 * normalizeKeys({ A: 1, B: 2 })  // => { a: 1, b: 2 }
 *
 * @example
 * normalizeKeys({ X: 10 })       // => { x: 10 }
 */
export function normalizeKeys(
  data: Record<string, number>
): Record<string, number> {
  const validated = NormalizeKeysInput.parse(data);
  const result = Object.fromEntries(
    Object.entries(validated).map(([k, v]) => [k.toLowerCase(), v])
  );
  return NormalizeKeysOutput.parse(result);
}

// =============================================================================
// BAD: Incomplete Contract (anti-pattern)
// =============================================================================

// DON'T: Schema that accepts anything
// const BadInput = z.any();
// function process(x: unknown) { ... }

// DON'T: Missing edge cases in examples
// function divide(a: number, b: number) {
//   // @example divide(10, 2)  // => 5.0
//   // Missing: what about b=0?
// }

// =============================================================================
// GOOD: Multiple Preconditions
// =============================================================================

/**
 * Precondition: start >= 0
 * Precondition: end >= start
 * Postcondition: result >= 0
 */
const RangeSizeInput = z.object({
  start: z.number().nonnegative(),
  end: z.number(),
}).refine(
  (data) => data.end >= data.start,
  { message: 'end must be >= start' }
);

const RangeSizeOutput = z.number().nonnegative();

/**
 * Calculate size of range [start, end).
 *
 * @example
 * rangeSize({ start: 0, end: 10 })  // => 10
 *
 * @example
 * rangeSize({ start: 5, end: 5 })   // => 0 (empty range)
 *
 * @example
 * rangeSize({ start: 0, end: 1 })   // => 1 (single element)
 */
export function rangeSize(
  input: z.infer<typeof RangeSizeInput>
): number {
  const { start, end } = RangeSizeInput.parse(input);
  const result = end - start;
  return RangeSizeOutput.parse(result);
}
