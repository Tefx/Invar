/**
 * Rule: no-pure-logic-in-shell
 *
 * Warn when Shell functions contain pure logic that should be in Core.
 * Shell functions should perform I/O operations, not pure computations.
 *
 * Heuristics for detecting pure logic:
 * - No async/await usage
 * - No I/O-related API calls (fs, http, fetch, db, etc.)
 * - No Result type in return
 * - Function body has more than 3 statements (substantial logic)
 */

import type { Rule } from 'eslint';
import type { FunctionDeclaration, FunctionExpression, ArrowFunctionExpression, BlockStatement, Node } from 'estree';

type FunctionNode = FunctionDeclaration | FunctionExpression | ArrowFunctionExpression;

// I/O-related identifiers that indicate impure operations
// Note: Result/Success/Failure are NOT I/O indicators - they're just return type wrappers
// that can be used with pure logic. Only actual I/O operations should be listed here.
const IO_IDENTIFIERS = [
  'fs',
  'readFile',
  'writeFile',
  'fetch',
  'axios',
  'http',
  'https',
  'db',
  'database',
  'query',
  'execute',
  'readFileSync',
  'writeFileSync',
  'existsSync',
  'mkdir',
  'rmdir',
  'unlink',
  'readdir',
  'stat',
  'access',
  'net',
  'spawn',
  'exec',
  'execSync',
  'child_process',
  'WebSocket',
  'XMLHttpRequest',
  'request',
  'got',
  'console',
];

export const noPureLogicInShell: Rule.RuleModule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Warn when Shell functions contain pure logic that should be in Core',
      recommended: false,
    },
    schema: [],
    messages: {
      pureLogicInShell:
        'Shell function "{{name}}" appears to contain pure logic. Consider moving to Core if it performs no I/O.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();

    // Only check files in shell/ directories
    const isShell = /[/\\]shell[/\\]/.test(filename);
    if (!isShell) {
      return {}; // Skip non-shell files
    }

    /**
     * Check if function contains I/O indicators
     */
    function hasIOIndicators(node: FunctionNode): boolean {
      let hasIO = false;

      // Check if function is async
      if (node.async) {
        hasIO = true;
      }

      // Walk the function body looking for I/O-related identifiers
      // Optimization: Limit depth and skip non-identifier containers
      const MAX_DEPTH = 10; // Reduced from 50 for better performance

      function visit(n: Node, depth: number = 0): void {
        if (hasIO) return; // Early return if already found
        if (depth > MAX_DEPTH) return; // Depth limit

        // Performance: Check node type first
        if (n.type === 'Identifier') {
          if (IO_IDENTIFIERS.includes(n.name)) {
            hasIO = true;
            return;
          }
        }

        // Performance: Skip node types that cannot contain identifiers
        if (
          n.type === 'Literal' ||
          n.type === 'TemplateElement' ||
          n.type === 'Super' ||
          n.type === 'ThisExpression'
        ) {
          return; // These cannot contain identifier children
        }

        // Recursively visit children with depth tracking
        // Only visit properties that typically contain code
        const relevantKeys = ['body', 'expression', 'callee', 'object', 'property', 'left', 'right', 'test', 'consequent', 'alternate', 'arguments', 'params'];

        for (const key of relevantKeys) {
          const value = (n as unknown as Record<string, unknown>)[key];
          if (!value) continue;

          if (typeof value === 'object') {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === 'object' && 'type' in item) {
                  visit(item as Node, depth + 1);
                  if (hasIO) return; // Early exit
                }
              }
            } else if ('type' in value) {
              visit(value as Node, depth + 1);
            }
          }
        }
      }

      if (node.body) {
        visit(node.body as Node);
      }

      return hasIO;
    }

    /**
     * Check if function body is substantial (more than 3 statements)
     */
    function hasSubstantialLogic(node: FunctionNode): boolean {
      if (!node.body || node.body.type !== 'BlockStatement') {
        return false;
      }

      const blockBody = node.body as BlockStatement;
      return blockBody.body.length > 3;
    }

    /**
     * Get function name with improved extraction from parent context
     */
    function getFunctionName(node: FunctionNode): string {
      // 1. FunctionDeclaration - use direct id
      if (node.type === 'FunctionDeclaration' && node.id) {
        return node.id.name;
      }

      // 2. FunctionExpression - try id first, then parent
      if (node.type === 'FunctionExpression' && node.id) {
        return node.id.name;
      }

      // 3. For unnamed FunctionExpression or ArrowFunctionExpression,
      //    try to get name from parent VariableDeclarator
      try {
        const ancestors = context.getAncestors();

        // Look for parent VariableDeclarator
        for (let i = ancestors.length - 1; i >= 0; i--) {
          const ancestor = ancestors[i];
          if (ancestor.type === 'VariableDeclarator') {
            const varDecl = ancestor as unknown as { id: { type: string; name?: string } };
            if (varDecl.id && varDecl.id.type === 'Identifier' && varDecl.id.name) {
              return varDecl.id.name;
            }
          }
        }
      } catch {
        // If ancestor lookup fails, fall through to 'anonymous'
      }

      return 'anonymous';
    }

    function checkFunction(node: FunctionNode): void {
      const functionName = getFunctionName(node);

      // Skip if function name is anonymous or very short (likely helper)
      if (functionName === 'anonymous' || functionName.length < 3) {
        return;
      }

      // Skip if function has I/O indicators
      if (hasIOIndicators(node)) {
        return;
      }

      // Warn if function has substantial logic but no I/O
      if (hasSubstantialLogic(node)) {
        context.report({
          node: node as unknown as Rule.Node,
          messageId: 'pureLogicInShell',
          data: {
            name: functionName,
          },
        });
      }
    }

    return {
      FunctionDeclaration: checkFunction,
      FunctionExpression: checkFunction,
      ArrowFunctionExpression: checkFunction,
    };
  },
};

export default noPureLogicInShell;
