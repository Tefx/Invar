/**
 * Rule: max-function-lines
 *
 * Enforce maximum function length with layer-based limits.
 *
 * TypeScript layered limits (LX-10, Python × 1.3):
 * - Core: 65 lines (strict, pure logic)
 * - Shell: 130 lines (I/O operations)
 * - Tests: 260 lines (test functions)
 * - Default: 104 lines (other files)
 */

import type { Rule } from 'eslint';
import { getLayer, getLimits } from '../utils/layer-detection.js';

function getFunctionName(node: Rule.Node): string {
  const anyNode = node as any;

  // FunctionDeclaration with name
  if (anyNode.id?.name) {
    return anyNode.id.name;
  }

  // MethodDefinition
  if (anyNode.key?.name) {
    return anyNode.key.name;
  }

  // Arrow function assigned to variable
  if (anyNode.parent?.type === 'VariableDeclarator' && anyNode.parent.id?.name) {
    return anyNode.parent.id.name;
  }

  return '(anonymous)';
}

export const maxFunctionLines: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Enforce maximum function length with layer-based limits',
      recommended: true,
    },
    schema: [
      {
        type: 'object',
        properties: {
          max: {
            type: 'number',
            minimum: 1,
          },
          skipBlankLines: {
            type: 'boolean',
          },
          skipComments: {
            type: 'boolean',
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      tooManyLines:
        'Function "{{name}}" has {{actual}} lines ({{layer}} layer max: {{max}}). Consider breaking into smaller functions.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();
    const layer = getLayer(filename);
    const limits = getLimits(filename);

    // Allow override via options
    const options = context.options[0] || {};
    const maxLines = options.max !== undefined ? options.max : limits.maxFunctionLines;
    const skipBlankLines = options.skipBlankLines || false;
    const skipComments = options.skipComments || false;

    function checkFunction(node: Rule.Node): void {
      const sourceCode = context.sourceCode || context.getSourceCode();
      const loc = node.loc;
      if (!loc) return;

      let actualLines = loc.end.line - loc.start.line + 1;

      // Count non-blank/non-comment lines if requested
      if (skipBlankLines || skipComments) {
        const allComments = sourceCode.getAllComments();
        const commentLines = new Set<number>();

        if (skipComments) {
          allComments.forEach((comment: any) => {
            if (!comment.loc) return; // Skip comments without location info
            const start = comment.loc.start.line;
            const end = comment.loc.end.line;
            for (let i = start; i <= end; i++) {
              commentLines.add(i);
            }
          });
        }

        actualLines = 0;
        for (let lineNum = loc.start.line; lineNum <= loc.end.line; lineNum++) {
          const line = sourceCode.lines[lineNum - 1];

          // Skip if line doesn't exist (edge case with trailing newlines)
          if (!line) continue;

          // Skip comment lines
          if (skipComments && commentLines.has(lineNum)) {
            continue;
          }

          // Skip blank lines
          if (skipBlankLines && line.trim().length === 0) {
            continue;
          }

          actualLines++;
        }
      }

      if (actualLines > maxLines) {
        const name = getFunctionName(node);
        context.report({
          node,
          messageId: 'tooManyLines',
          data: {
            name,
            actual: String(actualLines),
            max: String(maxLines),
            layer,
          },
        });
      }
    }

    return {
      FunctionDeclaration(node) {
        checkFunction(node as unknown as Rule.Node);
      },
      FunctionExpression(node) {
        checkFunction(node as unknown as Rule.Node);
      },
      ArrowFunctionExpression(node) {
        checkFunction(node as unknown as Rule.Node);
      },
    };
  },
};

export default maxFunctionLines;
