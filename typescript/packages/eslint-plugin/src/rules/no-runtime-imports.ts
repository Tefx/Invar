/**
 * Rule: no-runtime-imports
 *
 * Forbid imports inside functions (runtime imports).
 * All imports should be at module top-level for predictability and performance.
 *
 * Detects:
 * - require() calls inside functions
 * - dynamic import() calls inside functions
 */

import type { Rule } from 'eslint';
import type { CallExpression } from 'estree';

export const noRuntimeImports: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Forbid imports inside functions (require runtime imports at module top-level)',
      recommended: true,
    },
    schema: [],
    messages: {
      runtimeRequire:
        'Runtime require() detected. Move imports to module top-level for predictability.',
      runtimeImport:
        'Dynamic import() detected. Move imports to module top-level for predictability.',
    },
  },

  create(context): Rule.RuleListener {
    /**
     * Check if node is inside a function
     */
    function isInsideFunction(node: Rule.Node): boolean {
      const ancestors = context.sourceCode?.getAncestors?.(node) || context.getAncestors();

      for (const ancestor of ancestors) {
        if (
          ancestor.type === 'FunctionDeclaration' ||
          ancestor.type === 'FunctionExpression' ||
          ancestor.type === 'ArrowFunctionExpression'
        ) {
          return true;
        }
      }

      return false;
    }

    return {
      CallExpression(node) {
        const callNode = node as unknown as CallExpression;

        // Check for require() calls
        if (
          callNode.callee.type === 'Identifier' &&
          callNode.callee.name === 'require'
        ) {
          if (isInsideFunction(node as unknown as Rule.Node)) {
            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'runtimeRequire',
            });
          }
        }
      },

      ImportExpression(node) {
        // Check for dynamic import()
        if (isInsideFunction(node as unknown as Rule.Node)) {
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'runtimeImport',
          });
        }
      },
    };
  },
};

export default noRuntimeImports;
