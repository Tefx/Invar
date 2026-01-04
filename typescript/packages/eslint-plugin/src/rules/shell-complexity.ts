/**
 * Rule: shell-complexity
 *
 * Warn when Shell functions are too complex and should be split.
 * Shell functions should orchestrate I/O, not contain complex business logic.
 *
 * Detects:
 * - High cyclomatic complexity (many branches)
 * - Too many statements (>20 lines of logic)
 * - Multiple nested control structures
 */

import type { Rule } from 'eslint';
import type { FunctionDeclaration, FunctionExpression, ArrowFunctionExpression, Node } from 'estree';

type FunctionNode = FunctionDeclaration | FunctionExpression | ArrowFunctionExpression;

// Configurable thresholds
interface Options {
  maxStatements?: number;
  maxComplexity?: number;
}

const DEFAULT_MAX_STATEMENTS = 20;
const DEFAULT_MAX_COMPLEXITY = 10;

export const shellComplexity: Rule.RuleModule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Warn when Shell functions are too complex (should extract logic to Core)',
      recommended: false,
    },
    schema: [
      {
        type: 'object',
        properties: {
          maxStatements: {
            type: 'number',
            default: DEFAULT_MAX_STATEMENTS,
          },
          maxComplexity: {
            type: 'number',
            default: DEFAULT_MAX_COMPLEXITY,
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      tooManyStatements:
        'Shell function "{{name}}" has {{count}} statements (max {{max}}). Consider extracting pure logic to Core.',
      tooComplex:
        'Shell function "{{name}}" has complexity {{complexity}} (max {{max}}). Consider splitting into smaller functions.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();

    // Only check files in shell/ directories
    const isShell = /[/\\]shell[/\\]/.test(filename);
    if (!isShell) {
      return {}; // Skip non-shell files
    }

    const options = (context.options[0] || {}) as Options;
    const maxStatements = options.maxStatements || DEFAULT_MAX_STATEMENTS;
    const maxComplexity = options.maxComplexity || DEFAULT_MAX_COMPLEXITY;

    /**
     * Count statements in function body
     */
    function countStatements(node: FunctionNode): number {
      if (!node.body || node.body.type !== 'BlockStatement') {
        return 0;
      }

      let count = 0;
      const MAX_DEPTH = 10; // Reduced from 50 for better performance

      function visit(n: Node, depth: number = 0): void {
        if (depth > MAX_DEPTH) return; // Depth limit

        // Count different statement types
        if (
          n.type === 'ExpressionStatement' ||
          n.type === 'VariableDeclaration' ||
          n.type === 'ReturnStatement' ||
          n.type === 'IfStatement' ||
          n.type === 'ForStatement' ||
          n.type === 'WhileStatement' ||
          n.type === 'DoWhileStatement' ||
          n.type === 'SwitchStatement' ||
          n.type === 'TryStatement' ||
          n.type === 'ThrowStatement'
        ) {
          count++;
        }

        // Performance: Skip non-statement nodes
        if (
          n.type === 'Literal' ||
          n.type === 'Identifier' ||
          n.type === 'ThisExpression'
        ) {
          return;
        }

        // Only visit relevant keys
        const relevantKeys = ['body', 'consequent', 'alternate', 'cases', 'block', 'finalizer'];

        for (const key of relevantKeys) {
          const value = (n as unknown as Record<string, unknown>)[key];
          if (!value) continue;

          if (typeof value === 'object') {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === 'object' && 'type' in item) {
                  visit(item as Node, depth + 1);
                }
              }
            } else if ('type' in value) {
              visit(value as Node, depth + 1);
            }
          }
        }
      }

      visit(node.body);
      return count;
    }

    /**
     * Calculate cyclomatic complexity
     * Complexity increases with each decision point: if, for, while, case, &&, ||, ?:
     */
    function calculateComplexity(node: FunctionNode): number {
      if (!node.body) {
        return 1; // Base complexity
      }

      let complexity = 1; // Start at 1
      const MAX_DEPTH = 10; // Reduced from 50 for better performance

      function visit(n: Node, depth: number = 0): void {
        if (depth > MAX_DEPTH) return; // Depth limit

        // Decision points that increase complexity
        if (
          n.type === 'IfStatement' ||
          n.type === 'ForStatement' ||
          n.type === 'ForInStatement' ||
          n.type === 'ForOfStatement' ||
          n.type === 'WhileStatement' ||
          n.type === 'DoWhileStatement' ||
          n.type === 'ConditionalExpression' || // ternary ? :
          n.type === 'CatchClause'
        ) {
          complexity++;
        }

        // SwitchCase: only count non-default cases
        if (n.type === 'SwitchCase') {
          const caseNode = n as unknown as { test: unknown | null };
          if (caseNode.test !== null) {
            complexity++;
          }
        }

        // Logical operators (&&, ||, ??) add complexity
        if (n.type === 'LogicalExpression') {
          const logicalNode = n as unknown as { operator: string };
          if (logicalNode.operator === '&&' || logicalNode.operator === '||' || logicalNode.operator === '??') {
            complexity++;
          }
        }

        // Performance: Skip leaf nodes
        if (
          n.type === 'Literal' ||
          n.type === 'Identifier' ||
          n.type === 'ThisExpression'
        ) {
          return;
        }

        // Only visit relevant keys
        const relevantKeys = ['body', 'test', 'consequent', 'alternate', 'left', 'right', 'argument', 'cases'];

        for (const key of relevantKeys) {
          const value = (n as unknown as Record<string, unknown>)[key];
          if (!value) continue;

          if (typeof value === 'object') {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === 'object' && 'type' in item) {
                  visit(item as Node, depth + 1);
                }
              }
            } else if ('type' in value) {
              visit(value as Node, depth + 1);
            }
          }
        }
      }

      visit(node.body as Node);
      return complexity;
    }

    /**
     * Check if function has @shell_complexity marker comment (DX-22 Fix-or-Explain)
     *
     * Looks for `// @shell_complexity: <reason>` in the 4 lines before the function.
     * This allows developers to explicitly justify complexity that cannot be refactored.
     */
    function hasComplexityMarker(node: FunctionNode): boolean {
      const sourceCode = context.getSourceCode();
      const functionStart = node.loc?.start.line;

      if (!functionStart) {
        return false;
      }

      // Check 4 lines before function (matching Python implementation)
      const startLine = Math.max(1, functionStart - 4);
      const endLine = functionStart;

      for (let line = startLine; line < endLine; line++) {
        const text = sourceCode.lines[line - 1]; // lines array is 0-indexed
        if (text && /\/\/\s*@shell_complexity\s*:/.test(text)) {
          return true;
        }
      }

      return false;
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

      // Skip anonymous or very short helper functions
      if (functionName === 'anonymous' || functionName.length < 3) {
        return;
      }

      // DX-22: Skip if marked with @shell_complexity (Fix-or-Explain mechanism)
      if (hasComplexityMarker(node)) {
        return;
      }

      // Check statement count
      const statementCount = countStatements(node);
      if (statementCount > maxStatements) {
        context.report({
          node: node as unknown as Rule.Node,
          messageId: 'tooManyStatements',
          data: {
            name: functionName,
            count: String(statementCount),
            max: String(maxStatements),
          },
        });
      }

      // Check cyclomatic complexity
      const complexity = calculateComplexity(node);
      if (complexity > maxComplexity) {
        context.report({
          node: node as unknown as Rule.Node,
          messageId: 'tooComplex',
          data: {
            name: functionName,
            complexity: String(complexity),
            max: String(maxComplexity),
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

export default shellComplexity;
