/**
 * Rule: no-empty-schema
 *
 * Detect Zod schemas that match everything, providing false security.
 *
 * Detects:
 * - z.object({}) with no properties
 * - .passthrough() calls (defeats validation)
 * - .loose() calls (ignores unknown properties)
 */

import type { Rule } from 'eslint';
import type { CallExpression, Property } from 'estree';

export const noEmptySchema: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Forbid empty or permissive Zod schemas that defeat validation',
      recommended: true,
    },
    schema: [],
    messages: {
      emptyObject: 'Empty z.object({}) accepts any object. Add properties or use z.record()',
      passthrough: 'Schema with .passthrough() bypasses unknown property validation. Remove or use .strict()',
      loose: 'Schema with .loose() ignores unknown properties. Remove or use .strict()',
    },
  },

  create(context): Rule.RuleListener {
    return {
      CallExpression(node) {
        const callee = (node as CallExpression).callee;

        // Check for z.object({})
        if (
          callee.type === 'MemberExpression' &&
          callee.object.type === 'Identifier' &&
          callee.object.name === 'z' &&
          callee.property.type === 'Identifier' &&
          callee.property.name === 'object'
        ) {
          const args = (node as CallExpression).arguments;
          if (args.length === 1 && args[0].type === 'ObjectExpression') {
            const properties = args[0].properties as Property[];
            if (properties.length === 0) {
              context.report({
                node: node as unknown as Rule.Node,
                messageId: 'emptyObject',
              });
            }
          }
        }

        // Check for .passthrough() calls
        if (
          callee.type === 'MemberExpression' &&
          callee.property.type === 'Identifier' &&
          callee.property.name === 'passthrough'
        ) {
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'passthrough',
          });
        }

        // Check for .loose() calls
        if (
          callee.type === 'MemberExpression' &&
          callee.property.type === 'Identifier' &&
          callee.property.name === 'loose'
        ) {
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'loose',
          });
        }
      },
    };
  },
};

export default noEmptySchema;
