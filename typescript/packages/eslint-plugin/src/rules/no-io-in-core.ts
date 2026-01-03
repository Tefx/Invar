/**
 * Rule: no-io-in-core
 *
 * Forbid I/O imports in /core/ directories.
 * This enforces the Core/Shell separation pattern.
 */

import type { Rule } from 'eslint';

const IO_MODULES = new Set([
  'fs',
  'fs/promises',
  'node:fs',
  'node:fs/promises',
  'path',
  'node:path',
  'http',
  'https',
  'node:http',
  'node:https',
  'net',
  'node:net',
  'child_process',
  'node:child_process',
  'readline',
  'node:readline',
  'process',
  'node:process',
]);

const IO_PACKAGE_PATTERNS = [
  /^axios/,
  /^node-fetch/,
  /^got$/,
  /^superagent/,
  /^request/,
  /^pg$/,
  /^mysql/,
  /^mongodb/,
  /^redis/,
  /^ioredis/,
  /^@aws-sdk\//,
  /^@vercel\//,
];

function isIoModule(source: string): boolean {
  if (IO_MODULES.has(source)) return true;
  return IO_PACKAGE_PATTERNS.some(pattern => pattern.test(source));
}

function isInCoreDirectory(filename: string): boolean {
  // Normalize to lowercase and forward slashes for consistent cross-platform matching
  const normalized = filename.replace(/\\/g, '/').toLowerCase();
  return normalized.includes('/core/');
}

export const noIoInCore: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Forbid I/O imports in /core/ directories',
      recommended: true,
    },
    schema: [],
    messages: {
      ioInCore:
        'I/O module "{{module}}" is not allowed in /core/ directory. Move I/O to /shell/ or inject as parameter.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();

    if (!isInCoreDirectory(filename)) {
      return {};
    }

    return {
      ImportDeclaration(node) {
        const source = node.source.value;
        if (typeof source === 'string' && isIoModule(source)) {
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'ioInCore',
            data: { module: source },
          });
        }
      },

      CallExpression(node) {
        // Check for require() calls
        if (
          node.callee.type === 'Identifier' &&
          node.callee.name === 'require' &&
          node.arguments.length > 0 &&
          node.arguments[0].type === 'Literal'
        ) {
          const source = node.arguments[0].value;
          if (typeof source === 'string' && isIoModule(source)) {
            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'ioInCore',
              data: { module: source },
            });
          }
        }
      },
    };
  },
};

export default noIoInCore;
