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
    hasSuggestions: true,
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
      wrapWithResult:
        'Wrap return type with Result<{{returnType}}, Error>',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();
    const sourceCode = context.sourceCode || context.getSourceCode();
    const options = context.options[0] || {};
    const checkPrivate = options.checkPrivate || false;

    if (!isInShellDirectory(filename)) {
      return {};
    }

    /**
     * Get the text of a return type annotation from source code.
     * Strips the leading ": " to return just the type (e.g., "Result<T, E>").
     */
    function getReturnTypeText(node: Rule.Node): string | null {
      const typedNode = node as unknown as { returnType?: Rule.Node };
      if (!typedNode.returnType) return null;
      const text = sourceCode.getText(typedNode.returnType);
      // Strip leading ": " from type annotation (e.g., ": Result<T, E>" -> "Result<T, E>")
      return text.replace(/^:\s*/, '');
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
        const suggestedReturnType = returnType || 'void';
        const typedNode = node as unknown as { returnType?: Rule.Node };

        context.report({
          node,
          messageId: 'missingResultType',
          data: { name },
          suggest: typedNode.returnType ? [
            {
              messageId: 'wrapWithResult',
              data: { returnType: suggestedReturnType },
              fix(fixer) {
                if (!typedNode.returnType) return null;
                const newType = `Result<${suggestedReturnType}, Error>`;
                return fixer.replaceText(typedNode.returnType, `: ${newType}`);
              },
            },
          ] : [],
        });
      }
    }

    return {
      FunctionDeclaration(node) {
        const name = node.id?.name || null;
        const returnType = getReturnTypeText(node as unknown as Rule.Node);

        checkFunction(
          node as unknown as Rule.Node,
          name,
          returnType
        );
      },

      ArrowFunctionExpression(node) {
        // Get name from parent variable declaration
        const parent = (node as unknown as { parent?: { type: string; id?: { name: string } } }).parent;
        const name = parent?.type === 'VariableDeclarator' && parent.id?.name
          ? parent.id.name
          : null;

        const returnType = getReturnTypeText(node as unknown as Rule.Node);

        checkFunction(
          node as unknown as Rule.Node,
          name,
          returnType
        );
      },
    };
  },
};

export default shellResultType;
