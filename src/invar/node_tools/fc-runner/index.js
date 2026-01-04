/**
 * @invar/fc-runner - Programmatic fast-check runner with rich failure analysis
 *
 * Provides:
 * - Typed counterexamples (not just strings)
 * - Shrinking path and step count
 * - Root cause classification
 * - Suggested fix based on failure pattern
 */
import * as fc from 'fast-check';
import { z } from 'zod';
// ============================================================================
// Schemas
// ============================================================================
export const RootCauseSchema = z.enum([
    'boundary_violation', // Off-by-one, bounds exceeded
    'null_reference', // Null/undefined access
    'type_coercion', // Unexpected type conversion
    'floating_point', // Precision issues
    'empty_collection', // Empty array/object issues
    'overflow', // Integer overflow
    'invalid_state', // State machine violation
    'race_condition', // Concurrent access issues
    'unknown', // Unclassified
]);
export const CounterexampleSchema = z.object({
    values: z.record(z.unknown()),
    shrunk: z.boolean(),
    shrinkSteps: z.number(),
    seed: z.number().optional(),
});
export const FailureAnalysisSchema = z.object({
    failedAssertion: z.string(),
    actual: z.unknown().optional(),
    expected: z.unknown().optional(),
    rootCause: RootCauseSchema,
    suggestedFix: z.string(),
});
export const PropertyResultSchema = z.object({
    name: z.string(),
    passed: z.boolean(),
    numRuns: z.number(),
    counterexample: CounterexampleSchema.optional(),
    analysis: FailureAnalysisSchema.optional(),
    duration_ms: z.number(),
    error: z.string().optional(),
});
export const RunnerResultSchema = z.object({
    passed: z.boolean(),
    total: z.number(),
    failed: z.number(),
    duration_ms: z.number(),
    properties: z.array(PropertyResultSchema),
    confidence: z.enum(['statistical', 'exhaustive']),
});
export const RunnerOptionsSchema = z.object({
    seed: z.number().optional(),
    numRuns: z.number().default(100),
    verbose: z.boolean().default(false),
    endOnFailure: z.boolean().default(false),
});
// ============================================================================
// Root Cause Detection
// ============================================================================
/**
 * Analyze error to determine root cause.
 */
function classifyRootCause(error, counterexample) {
    const errorStr = String(error).toLowerCase();
    // Check for null/undefined
    if (errorStr.includes('null') || errorStr.includes('undefined') || errorStr.includes('cannot read')) {
        return 'null_reference';
    }
    // Check for type errors
    if (errorStr.includes('type') || errorStr.includes('nan') || errorStr.includes('not a')) {
        return 'type_coercion';
    }
    // Check for boundary issues
    if (errorStr.includes('index') || errorStr.includes('bound') || errorStr.includes('range')) {
        return 'boundary_violation';
    }
    // Check for overflow
    if (errorStr.includes('overflow') || errorStr.includes('infinity')) {
        return 'overflow';
    }
    // Check counterexample values for patterns
    const values = Object.values(counterexample);
    // Empty collections
    if (values.some(v => Array.isArray(v) && v.length === 0)) {
        return 'empty_collection';
    }
    // Floating point precision
    if (values.some(v => typeof v === 'number' && !Number.isInteger(v))) {
        if (errorStr.includes('precision') || errorStr.includes('equal')) {
            return 'floating_point';
        }
    }
    // Boundary values
    if (values.some(v => v === 0 || v === -1 || v === 1 ||
        v === Number.MAX_SAFE_INTEGER || v === Number.MIN_SAFE_INTEGER)) {
        return 'boundary_violation';
    }
    return 'unknown';
}
/**
 * Generate suggested fix based on root cause.
 */
function suggestFix(rootCause, _counterexample) {
    switch (rootCause) {
        case 'boundary_violation':
            return 'Add bounds checking: validate array indices and loop boundaries';
        case 'null_reference':
            return 'Add null check: use optional chaining (?.) or explicit null guard';
        case 'type_coercion':
            return 'Add type validation: use Zod schema or explicit type check';
        case 'floating_point':
            return 'Use Math.round() or Number.EPSILON for floating point comparison';
        case 'empty_collection':
            return 'Add empty check: validate collection length before access';
        case 'overflow':
            return 'Add overflow protection: use BigInt or clamp values';
        case 'invalid_state':
            return 'Add state validation: check preconditions before state transition';
        case 'race_condition':
            return 'Add synchronization: use mutex or atomic operations';
        default:
            return 'Review the counterexample and add appropriate validation';
    }
}
/**
 * Define a property test.
 *
 * @example
 * ```typescript
 * const prop = defineProperty({
 *   name: 'addition is commutative',
 *   arbitraries: {
 *     a: fc.integer(),
 *     b: fc.integer(),
 *   },
 *   predicate: ({ a, b }) => a + b === b + a,
 * });
 * ```
 */
export function defineProperty(def) {
    return def;
}
// ============================================================================
// Runner
// ============================================================================
/**
 * Run a single property test.
 */
function runProperty(prop, options) {
    const start = Date.now();
    // Create record arbitrary
    const recordArbitrary = fc.record(prop.arbitraries);
    try {
        const checkParams = {
            numRuns: options.numRuns,
            verbose: options.verbose ? fc.VerbosityLevel.Verbose : fc.VerbosityLevel.None,
            endOnFailure: options.endOnFailure,
        };
        if (options.seed !== undefined) {
            checkParams.seed = options.seed;
        }
        const property = fc.property(recordArbitrary, (input) => {
            return prop.predicate(input);
        });
        const result = fc.check(property, checkParams);
        if (result.failed) {
            const counterexampleValues = result.counterexample?.[0] ?? {};
            const counterexample = {
                values: counterexampleValues,
                shrunk: (result.numShrinks ?? 0) > 0,
                shrinkSteps: result.numShrinks ?? 0,
                seed: result.seed,
            };
            const rootCause = classifyRootCause(result.error, counterexampleValues);
            const analysis = {
                failedAssertion: prop.name,
                actual: result.error,
                rootCause,
                suggestedFix: suggestFix(rootCause, counterexampleValues),
            };
            return {
                name: prop.name,
                passed: false,
                numRuns: result.numRuns,
                counterexample,
                analysis,
                duration_ms: Date.now() - start,
                error: String(result.error),
            };
        }
        return {
            name: prop.name,
            passed: true,
            numRuns: result.numRuns,
            duration_ms: Date.now() - start,
        };
    }
    catch (error) {
        return {
            name: prop.name,
            passed: false,
            numRuns: 0,
            duration_ms: Date.now() - start,
            error: String(error),
        };
    }
}
/**
 * Run multiple property tests.
 *
 * @param properties - Array of property definitions
 * @param options - Runner options
 * @returns Combined result
 *
 * @example
 * ```typescript
 * import { runProperties, defineProperty } from '@invar/fc-runner';
 *
 * const props = [
 *   defineProperty({
 *     name: 'addition is commutative',
 *     arbitraries: { a: fc.integer(), b: fc.integer() },
 *     predicate: ({ a, b }) => a + b === b + a,
 *   }),
 * ];
 *
 * const result = runProperties(props, { numRuns: 1000 });
 * console.log(`Passed: ${result.passed}`);
 * ```
 */
export function runProperties(properties, options = {}) {
    const opts = RunnerOptionsSchema.parse(options);
    const start = Date.now();
    const results = [];
    for (const prop of properties) {
        const result = runProperty(prop, opts);
        results.push(result);
        if (!result.passed && opts.endOnFailure) {
            break;
        }
    }
    const failed = results.filter(r => !r.passed).length;
    return {
        passed: failed === 0,
        total: results.length,
        failed,
        duration_ms: Date.now() - start,
        properties: results,
        confidence: 'statistical',
    };
}
// Re-export fast-check arbitraries for convenience
export { fc };
export default runProperties;
//# sourceMappingURL=index.js.map