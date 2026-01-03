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
    type: 'problem',
    docs: {
      description: 'Exported functions must have @example in JSDoc',
      recommended: true,
    },
    schema: [],
    messages: {
      missingExample:
        'Exported function "{{name}}" must have @example in JSDoc (required for doctest)',
    },
  },

  create(context): Rule.RuleListener {
    function checkFunction(node: Rule.Node, name: string | null, skipExportCheck = false): void {
      if (!name) return;

      // Only check export status if not already verified by selector
      if (!skipExportCheck && !isExported(node)) return;

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
      // Selector guarantees this is already exported, so skipExportCheck=true
      'ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression'(
        node: Rule.Node
      ) {
        const anyNode = node as any;
        const name = anyNode.parent?.id?.name || null;
        if (!name) return;

        // For exported variables, the JSDoc is typically before the ExportNamedDeclaration,
        // not before the ArrowFunctionExpression
        const sourceCode = context.sourceCode || context.getSourceCode();
        const exportDeclaration = anyNode.parent?.parent?.parent;
        const comments =
          exportDeclaration?.type === 'ExportNamedDeclaration'
            ? sourceCode.getCommentsBefore(exportDeclaration)
            : sourceCode.getCommentsBefore(node);

        const hasExample = comments.some(
          (comment: any) =>
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
      },
    };
  },
};

export default requireJsdocExample;
