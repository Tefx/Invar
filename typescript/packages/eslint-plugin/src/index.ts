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

import type { ESLint, Rule } from 'eslint';
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

// ESLint legacy config format (for ESLint 8 compatibility)
const configs = {
  recommended: {
    plugins: ['@invar'],
    rules: {
      '@invar/require-schema-validation': 'error' as const,
      '@invar/no-io-in-core': 'error' as const,
      '@invar/shell-result-type': 'warn' as const,
      '@invar/no-any-in-schema': 'warn' as const,
      '@invar/require-jsdoc-example': 'warn' as const,
    },
  },
  strict: {
    plugins: ['@invar'],
    rules: {
      '@invar/require-schema-validation': 'error' as const,
      '@invar/no-io-in-core': 'error' as const,
      '@invar/shell-result-type': 'error' as const,
      '@invar/no-any-in-schema': 'error' as const,
      '@invar/require-jsdoc-example': 'error' as const,
    },
  },
};

const plugin: ESLint.Plugin = {
  rules,
  configs,
};

export default plugin;
export { rules, configs };
