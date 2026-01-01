/**
 * Rule: require-jsdoc-example
 *
 * Exported functions must have @example in JSDoc.
 * Examples serve as documentation and can be used for doctest-style testing.
 */

import type { Rule } from 'eslint';

function isExported(node: Rule.Node): boolean {
  const parent = (node as unknown as { parent?: { type: string } }).parent;
  if (!parent) return false;

  if (parent.type === 'ExportNamedDeclaration') return true;
  if (parent.type === 'ExportDefaultDeclaration') return true;

  return false;
}

export const requireJsdocExample: Rule.RuleModule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Exported functions must have @example in JSDoc',
      recommended: true,
    },
    schema: [],
    messages: {
      missingExample:
        'Exported function "{{name}}" should have @example in JSDoc for documentation',
    },
  },

  create(context): Rule.RuleListener {
    function checkFunction(node: Rule.Node, name: string | null): void {
      if (!name) return;
      if (!isExported(node)) return;

      // Check for @example in leading comments
      const sourceCode = context.sourceCode || context.getSourceCode();
      const comments = sourceCode.getCommentsBefore(node);

      const hasExample = comments.some(
        comment =>
          comment.type === 'Block' &&
          comment.value.includes('@example')
      );

      if (!hasExample) {
        context.report({
          node,
          messageId: 'missingExample',
          data: { name },
        });
      }
    }

    return {
      FunctionDeclaration(node) {
        checkFunction(node as unknown as Rule.Node, node.id?.name || null);
      },

      // Also check arrow functions assigned to exported variables
      'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression'(
        node: Rule.Node
      ) {
        const parent = (node as unknown as { parent?: { id?: { name: string } } }).parent;
        const name = parent?.id?.name || null;
        checkFunction(node, name);
      },
    };
  },
};

export default requireJsdocExample;
