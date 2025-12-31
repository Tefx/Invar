/**
 * @invar/eslint-plugin - ESLint plugin with Invar-specific rules
 *
 * Rules:
 * - @invar/require-schema-validation: Zod-typed params must have .parse()
 * - @invar/no-io-in-core: Forbid I/O imports in /core/ directories
 * - @invar/shell-result-type: Shell functions must return Result<T, E>
 * - @invar/no-any-in-schema: Forbid z.any() in schemas
 * - @invar/require-jsdoc-example: Exported functions need @example
 */

import type { ESLint, Linter, Rule } from 'eslint';
import { requireSchemaValidation } from './rules/require-schema-validation.js';
import { noIoInCore } from './rules/no-io-in-core.js';
import { shellResultType } from './rules/shell-result-type.js';
import { noAnyInSchema } from './rules/no-any-in-schema.js';
import { requireJsdocExample } from './rules/require-jsdoc-example.js';

// ============================================================================
// Plugin Definition
// ============================================================================

const rules: Record<string, Rule.RuleModule> = {
  'require-schema-validation': requireSchemaValidation,
  'no-io-in-core': noIoInCore,
  'shell-result-type': shellResultType,
  'no-any-in-schema': noAnyInSchema,
  'require-jsdoc-example': requireJsdocExample,
};

const configs: Record<string, Linter.Config> = {
  recommended: {
    plugins: ['@invar'],
    rules: {
      '@invar/require-schema-validation': 'error',
      '@invar/no-io-in-core': 'error',
      '@invar/shell-result-type': 'warn',
      '@invar/no-any-in-schema': 'warn',
      '@invar/require-jsdoc-example': 'warn',
    },
  },
  strict: {
    plugins: ['@invar'],
    rules: {
      '@invar/require-schema-validation': 'error',
      '@invar/no-io-in-core': 'error',
      '@invar/shell-result-type': 'error',
      '@invar/no-any-in-schema': 'error',
      '@invar/require-jsdoc-example': 'error',
    },
  },
};

const plugin: ESLint.Plugin = {
  rules,
  configs,
};

export default plugin;
export { rules, configs };
