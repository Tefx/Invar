/**
 * Rule: no-impure-calls-in-core
 *
 * Forbid Core functions calling Shell functions.
 * Core should be pure - no imports from shell/ directories.
 *
 * Detects:
 * - Imports from ../shell/ in core/ files
 * - Imports from shell/ in core/ files
 */

import type { Rule } from 'eslint';
import type { ImportDeclaration } from 'estree';

export const noImpureCallsInCore: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Forbid Core functions calling Shell functions (imports from shell/)',
      recommended: true,
    },
    schema: [],
    messages: {
      shellImportInCore:
        'Core file importing from Shell: "{{source}}". Core must be pure - move I/O logic to Shell or extract pure logic.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();

    // Only check files in core/ directories
    const isCore = /[/\\]core[/\\]/.test(filename);
    if (!isCore) {
      return {}; // Skip non-core files
    }

    return {
      ImportDeclaration(node) {
        const importNode = node as unknown as ImportDeclaration;

        if (importNode.source && importNode.source.type === 'Literal') {
          const source = String(importNode.source.value);

          // Check if importing from shell/
          // Matches: ../shell/*, ../../shell/*, /shell/*, shell/*
          if (/[/\\]shell[/\\]/.test(source) || /^shell[/\\]/.test(source)) {
            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'shellImportInCore',
              data: {
                source: source,
              },
            });
          }
        }
      },
    };
  },
};

export default noImpureCallsInCore;
