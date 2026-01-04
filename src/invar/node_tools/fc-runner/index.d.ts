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
export declare const RootCauseSchema: z.ZodEnum<["boundary_violation", "null_reference", "type_coercion", "floating_point", "empty_collection", "overflow", "invalid_state", "race_condition", "unknown"]>;
export type RootCause = z.infer<typeof RootCauseSchema>;
export declare const CounterexampleSchema: z.ZodObject<{
    values: z.ZodRecord<z.ZodString, z.ZodUnknown>;
    shrunk: z.ZodBoolean;
    shrinkSteps: z.ZodNumber;
    seed: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    values: Record<string, unknown>;
    shrunk: boolean;
    shrinkSteps: number;
    seed?: number | undefined;
}, {
    values: Record<string, unknown>;
    shrunk: boolean;
    shrinkSteps: number;
    seed?: number | undefined;
}>;
export type Counterexample = z.infer<typeof CounterexampleSchema>;
export declare const FailureAnalysisSchema: z.ZodObject<{
    failedAssertion: z.ZodString;
    actual: z.ZodOptional<z.ZodUnknown>;
    expected: z.ZodOptional<z.ZodUnknown>;
    rootCause: z.ZodEnum<["boundary_violation", "null_reference", "type_coercion", "floating_point", "empty_collection", "overflow", "invalid_state", "race_condition", "unknown"]>;
    suggestedFix: z.ZodString;
}, "strip", z.ZodTypeAny, {
    failedAssertion: string;
    rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
    suggestedFix: string;
    expected?: unknown;
    actual?: unknown;
}, {
    failedAssertion: string;
    rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
    suggestedFix: string;
    expected?: unknown;
    actual?: unknown;
}>;
export type FailureAnalysis = z.infer<typeof FailureAnalysisSchema>;
export declare const PropertyResultSchema: z.ZodObject<{
    name: z.ZodString;
    passed: z.ZodBoolean;
    numRuns: z.ZodNumber;
    counterexample: z.ZodOptional<z.ZodObject<{
        values: z.ZodRecord<z.ZodString, z.ZodUnknown>;
        shrunk: z.ZodBoolean;
        shrinkSteps: z.ZodNumber;
        seed: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        values: Record<string, unknown>;
        shrunk: boolean;
        shrinkSteps: number;
        seed?: number | undefined;
    }, {
        values: Record<string, unknown>;
        shrunk: boolean;
        shrinkSteps: number;
        seed?: number | undefined;
    }>>;
    analysis: z.ZodOptional<z.ZodObject<{
        failedAssertion: z.ZodString;
        actual: z.ZodOptional<z.ZodUnknown>;
        expected: z.ZodOptional<z.ZodUnknown>;
        rootCause: z.ZodEnum<["boundary_violation", "null_reference", "type_coercion", "floating_point", "empty_collection", "overflow", "invalid_state", "race_condition", "unknown"]>;
        suggestedFix: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        failedAssertion: string;
        rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
        suggestedFix: string;
        expected?: unknown;
        actual?: unknown;
    }, {
        failedAssertion: string;
        rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
        suggestedFix: string;
        expected?: unknown;
        actual?: unknown;
    }>>;
    duration_ms: z.ZodNumber;
    error: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    passed: boolean;
    numRuns: number;
    duration_ms: number;
    counterexample?: {
        values: Record<string, unknown>;
        shrunk: boolean;
        shrinkSteps: number;
        seed?: number | undefined;
    } | undefined;
    analysis?: {
        failedAssertion: string;
        rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
        suggestedFix: string;
        expected?: unknown;
        actual?: unknown;
    } | undefined;
    error?: string | undefined;
}, {
    name: string;
    passed: boolean;
    numRuns: number;
    duration_ms: number;
    counterexample?: {
        values: Record<string, unknown>;
        shrunk: boolean;
        shrinkSteps: number;
        seed?: number | undefined;
    } | undefined;
    analysis?: {
        failedAssertion: string;
        rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
        suggestedFix: string;
        expected?: unknown;
        actual?: unknown;
    } | undefined;
    error?: string | undefined;
}>;
export type PropertyResult = z.infer<typeof PropertyResultSchema>;
export declare const RunnerResultSchema: z.ZodObject<{
    passed: z.ZodBoolean;
    total: z.ZodNumber;
    failed: z.ZodNumber;
    duration_ms: z.ZodNumber;
    properties: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        passed: z.ZodBoolean;
        numRuns: z.ZodNumber;
        counterexample: z.ZodOptional<z.ZodObject<{
            values: z.ZodRecord<z.ZodString, z.ZodUnknown>;
            shrunk: z.ZodBoolean;
            shrinkSteps: z.ZodNumber;
            seed: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        }, {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        }>>;
        analysis: z.ZodOptional<z.ZodObject<{
            failedAssertion: z.ZodString;
            actual: z.ZodOptional<z.ZodUnknown>;
            expected: z.ZodOptional<z.ZodUnknown>;
            rootCause: z.ZodEnum<["boundary_violation", "null_reference", "type_coercion", "floating_point", "empty_collection", "overflow", "invalid_state", "race_condition", "unknown"]>;
            suggestedFix: z.ZodString;
        }, "strip", z.ZodTypeAny, {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        }, {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        }>>;
        duration_ms: z.ZodNumber;
        error: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        passed: boolean;
        numRuns: number;
        duration_ms: number;
        counterexample?: {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        } | undefined;
        analysis?: {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        } | undefined;
        error?: string | undefined;
    }, {
        name: string;
        passed: boolean;
        numRuns: number;
        duration_ms: number;
        counterexample?: {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        } | undefined;
        analysis?: {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        } | undefined;
        error?: string | undefined;
    }>, "many">;
    confidence: z.ZodEnum<["statistical", "exhaustive"]>;
}, "strip", z.ZodTypeAny, {
    passed: boolean;
    duration_ms: number;
    total: number;
    failed: number;
    properties: {
        name: string;
        passed: boolean;
        numRuns: number;
        duration_ms: number;
        counterexample?: {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        } | undefined;
        analysis?: {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        } | undefined;
        error?: string | undefined;
    }[];
    confidence: "statistical" | "exhaustive";
}, {
    passed: boolean;
    duration_ms: number;
    total: number;
    failed: number;
    properties: {
        name: string;
        passed: boolean;
        numRuns: number;
        duration_ms: number;
        counterexample?: {
            values: Record<string, unknown>;
            shrunk: boolean;
            shrinkSteps: number;
            seed?: number | undefined;
        } | undefined;
        analysis?: {
            failedAssertion: string;
            rootCause: "boundary_violation" | "null_reference" | "type_coercion" | "floating_point" | "empty_collection" | "overflow" | "invalid_state" | "race_condition" | "unknown";
            suggestedFix: string;
            expected?: unknown;
            actual?: unknown;
        } | undefined;
        error?: string | undefined;
    }[];
    confidence: "statistical" | "exhaustive";
}>;
export type RunnerResult = z.infer<typeof RunnerResultSchema>;
export declare const RunnerOptionsSchema: z.ZodObject<{
    seed: z.ZodOptional<z.ZodNumber>;
    numRuns: z.ZodDefault<z.ZodNumber>;
    verbose: z.ZodDefault<z.ZodBoolean>;
    endOnFailure: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    numRuns: number;
    verbose: boolean;
    endOnFailure: boolean;
    seed?: number | undefined;
}, {
    seed?: number | undefined;
    numRuns?: number | undefined;
    verbose?: boolean | undefined;
    endOnFailure?: boolean | undefined;
}>;
export type RunnerOptions = z.infer<typeof RunnerOptionsSchema>;
export interface PropertyDefinition<T extends Record<string, unknown>> {
    name: string;
    arbitraries: {
        [K in keyof T]: fc.Arbitrary<T[K]>;
    };
    predicate: (input: T) => boolean | void;
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
export declare function defineProperty<T extends Record<string, unknown>>(def: PropertyDefinition<T>): PropertyDefinition<T>;
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
export declare function runProperties(properties: PropertyDefinition<Record<string, unknown>>[], options?: Partial<RunnerOptions>): RunnerResult;
export { fc };
export default runProperties;
//# sourceMappingURL=index.d.ts.map