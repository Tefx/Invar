/**
 * @invar/eslint-plugin - ESLint plugin with Invar-specific rules
 *
 * Rules:
 * - @invar/require-schema-validation: Zod-typed params must have .parse()
 * - @invar/no-io-in-core: Forbid I/O imports in /core/ directories
 * - @invar/shell-result-type: Shell functions must return Result<T, E>
 * - @invar/no-any-in-schema: Forbid z.any() in schemas
 * - @invar/require-jsdoc-example: Exported functions need @example
 * - @invar/max-file-lines: Enforce max file length (layer-based)
 * - @invar/max-function-lines: Enforce max function length (layer-based)
 * - @invar/no-empty-schema: Forbid empty or permissive Zod schemas
 * - @invar/no-redundant-type-schema: Forbid schemas that only repeat TypeScript types
 * - @invar/require-complete-validation: All function params must be validated, or none
 * - @invar/no-runtime-imports: Forbid require()/import() inside functions
 * - @invar/no-impure-calls-in-core: Forbid Core importing from Shell
 * - @invar/no-pure-logic-in-shell: Warn when Shell contains pure logic
 * - @invar/shell-complexity: Warn when Shell functions are too complex
 * - @invar/thin-entry-points: Warn when entry points contain substantial logic
 */
import { requireSchemaValidation } from './rules/require-schema-validation.js';
import { noIoInCore } from './rules/no-io-in-core.js';
import { shellResultType } from './rules/shell-result-type.js';
import { noAnyInSchema } from './rules/no-any-in-schema.js';
import { requireJsdocExample } from './rules/require-jsdoc-example.js';
import { maxFileLines } from './rules/max-file-lines.js';
import { maxFunctionLines } from './rules/max-function-lines.js';
import { noEmptySchema } from './rules/no-empty-schema.js';
import { noRedundantTypeSchema } from './rules/no-redundant-type-schema.js';
import { requireCompleteValidation } from './rules/require-complete-validation.js';
import { noRuntimeImports } from './rules/no-runtime-imports.js';
import { noImpureCallsInCore } from './rules/no-impure-calls-in-core.js';
import { noPureLogicInShell } from './rules/no-pure-logic-in-shell.js';
import { shellComplexity } from './rules/shell-complexity.js';
import { thinEntryPoints } from './rules/thin-entry-points.js';
// ============================================================================
// Plugin Definition
// ============================================================================
const rules = {
    'require-schema-validation': requireSchemaValidation,
    'no-io-in-core': noIoInCore,
    'shell-result-type': shellResultType,
    'no-any-in-schema': noAnyInSchema,
    'require-jsdoc-example': requireJsdocExample,
    'max-file-lines': maxFileLines,
    'max-function-lines': maxFunctionLines,
    'no-empty-schema': noEmptySchema,
    'no-redundant-type-schema': noRedundantTypeSchema,
    'require-complete-validation': requireCompleteValidation,
    'no-runtime-imports': noRuntimeImports,
    'no-impure-calls-in-core': noImpureCallsInCore,
    'no-pure-logic-in-shell': noPureLogicInShell,
    'shell-complexity': shellComplexity,
    'thin-entry-points': thinEntryPoints,
};
// ESLint legacy config format (for ESLint 8 compatibility)
const configs = {
    recommended: {
        plugins: ['@invar'],
        rules: {
            '@invar/require-schema-validation': ['error', { mode: 'recommended' }],
            '@invar/no-io-in-core': 'error',
            '@invar/shell-result-type': 'warn',
            '@invar/no-any-in-schema': 'warn',
            '@invar/require-jsdoc-example': 'error',
            '@invar/max-file-lines': 'error',
            '@invar/max-function-lines': 'warn', // DX-22: Align with Python (WARN, not ERROR)
            '@invar/no-empty-schema': 'error',
            '@invar/no-redundant-type-schema': 'warn',
            '@invar/require-complete-validation': 'warn',
            '@invar/no-runtime-imports': 'error',
            '@invar/no-impure-calls-in-core': 'error',
            '@invar/no-pure-logic-in-shell': 'warn',
            '@invar/shell-complexity': 'warn',
            '@invar/thin-entry-points': 'warn',
        },
    },
    strict: {
        plugins: ['@invar'],
        rules: {
            '@invar/require-schema-validation': ['error', { mode: 'strict' }],
            '@invar/no-io-in-core': 'error',
            '@invar/shell-result-type': 'error',
            '@invar/no-any-in-schema': 'error',
            '@invar/require-jsdoc-example': 'error',
            '@invar/max-file-lines': 'error',
            '@invar/max-function-lines': 'error',
            '@invar/no-empty-schema': 'error',
            '@invar/no-redundant-type-schema': 'error',
            '@invar/require-complete-validation': 'error',
            '@invar/no-runtime-imports': 'error',
            '@invar/no-impure-calls-in-core': 'error',
            '@invar/no-pure-logic-in-shell': 'error',
            '@invar/shell-complexity': 'error',
            '@invar/thin-entry-points': 'error',
        },
    },
};
const plugin = {
    rules,
    configs: configs, // Type assertion due to ESLint config type complexity
};
export default plugin;
export { rules, configs };
//# sourceMappingURL=index.js.map