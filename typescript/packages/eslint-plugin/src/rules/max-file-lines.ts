/**
 * Rule: max-file-lines
 *
 * Enforce maximum file length with layer-based limits.
 *
 * TypeScript layered limits (LX-10, Python × 1.3):
 * - Core: 650 lines (strict, pure logic)
 * - Shell: 910 lines (I/O operations)
 * - Tests: 1300 lines (test files)
 * - Default: 780 lines (other files)
 */

import type { Rule } from 'eslint';
import { getLayer, getLimits } from '../utils/layer-detection.js';

export const maxFileLines: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Enforce maximum file length with layer-based limits',
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
        'File has {{actual}} lines ({{layer}} layer max: {{max}}). Consider splitting into smaller modules.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();
    const layer = getLayer(filename);
    const limits = getLimits(filename);

    // Allow override via options
    const options = context.options[0] || {};
    const maxLines = options.max !== undefined ? options.max : limits.maxFileLines;
    const skipBlankLines = options.skipBlankLines || false;
    const skipComments = options.skipComments || false;

    return {
      Program(node): void {
        const sourceCode = context.sourceCode || context.getSourceCode();
        const lines = sourceCode.lines;

        let actualLines = lines.length;

        // Count non-blank/non-comment lines if requested
        if (skipBlankLines || skipComments) {
          const allComments = sourceCode.getAllComments();
          const commentLines = new Set<number>();

          if (skipComments) {
            allComments.forEach(comment => {
              if (!comment.loc) return; // Skip comments without location info
              const start = comment.loc.start.line;
              const end = comment.loc.end.line;
              for (let i = start; i <= end; i++) {
                commentLines.add(i);
              }
            });
          }

          actualLines = 0;
          for (let i = 0; i < lines.length; i++) {
            const lineNum = i + 1;
            const line = lines[i];

            // Skip if line doesn't exist (edge case)
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
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'tooManyLines',
            data: {
              actual: String(actualLines),
              max: String(maxLines),
              layer,
            },
          });
        }
      },
    };
  },
};

export default maxFileLines;
