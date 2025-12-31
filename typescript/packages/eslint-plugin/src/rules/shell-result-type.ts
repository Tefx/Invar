/**
 * Rule: shell-result-type
 *
 * Shell functions must return Result<T, E> type.
 * This enforces explicit error handling in the Shell layer.
 */

import type { Rule } from 'eslint';

const RESULT_TYPE_PATTERNS = [
  /^Result</,
  /^ResultAsync</,
  /^Ok</,
  /^Err</,
  /^Either</,
  /^Left</,
  /^Right</,
];

function isResultType(typeAnnotation: string): boolean {
  return RESULT_TYPE_PATTERNS.some(pattern => pattern.test(typeAnnotation));
}

function isInShellDirectory(filename: string): boolean {
  return filename.includes('/shell/') || filename.includes('\\shell\\');
}

function isExported(node: Rule.Node): boolean {
  const parent = (node as unknown as { parent?: { type: string } }).parent;
  if (!parent) return false;

  if (parent.type === 'ExportNamedDeclaration') return true;
  if (parent.type === 'ExportDefaultDeclaration') return true;

  // Check for module.exports assignment
  if (parent.type === 'VariableDeclarator') {
    const grandparent = (parent as unknown as { parent?: { type: string; parent?: { type: string } } }).parent;
    if (grandparent?.type === 'VariableDeclaration') {
      const greatGrandparent = grandparent.parent;
      if (greatGrandparent?.type === 'ExportNamedDeclaration') return true;
    }
  }

  return false;
}

export const shellResultType: Rule.RuleModule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Shell functions must return Result<T, E> type',
      recommended: true,
    },
    schema: [
      {
        type: 'object',
        properties: {
          checkPrivate: {
            type: 'boolean',
            default: false,
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      missingResultType:
        'Shell function "{{name}}" should return Result<T, E> type for explicit error handling',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();
    const options = context.options[0] || {};
    const checkPrivate = options.checkPrivate || false;

    if (!isInShellDirectory(filename)) {
      return {};
    }

    function checkFunction(
      node: Rule.Node,
      name: string | null,
      returnType: string | null
    ): void {
      // Skip anonymous functions
      if (!name) return;

      // Skip private functions unless configured
      if (!checkPrivate && name.startsWith('_')) return;

      // Skip non-exported functions
      if (!isExported(node)) return;

      // Check return type
      if (!returnType || !isResultType(returnType)) {
        context.report({
          node,
          messageId: 'missingResultType',
          data: { name },
        });
      }
    }

    return {
      FunctionDeclaration(node) {
        const name = node.id?.name || null;
        const returnTypeAnnotation = (node as unknown as {
          returnType?: { typeAnnotation?: { type: string } }
        }).returnType?.typeAnnotation?.type;

        checkFunction(
          node as unknown as Rule.Node,
          name,
          returnTypeAnnotation || null
        );
      },

      ArrowFunctionExpression(node) {
        // Get name from parent variable declaration
        const parent = (node as unknown as { parent?: { type: string; id?: { name: string } } }).parent;
        const name = parent?.type === 'VariableDeclarator' && parent.id?.name
          ? parent.id.name
          : null;

        const returnTypeAnnotation = (node as unknown as {
          returnType?: { typeAnnotation?: { type: string } }
        }).returnType?.typeAnnotation?.type;

        checkFunction(
          node as unknown as Rule.Node,
          name,
          returnTypeAnnotation || null
        );
      },
    };
  },
};

export default shellResultType;
