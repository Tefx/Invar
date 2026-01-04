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

      function visit(n: Node): void {
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

        // Recursively visit children
        for (const key of Object.keys(n)) {
          const value = (n as unknown as Record<string, unknown>)[key];
          if (value && typeof value === 'object') {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === 'object' && 'type' in item) {
                  visit(item as Node);
                }
              }
            } else if ('type' in value) {
              visit(value as Node);
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

      function visit(n: Node): void {
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

        // Recursively visit children
        for (const key of Object.keys(n)) {
          const value = (n as unknown as Record<string, unknown>)[key];
          if (value && typeof value === 'object') {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === 'object' && 'type' in item) {
                  visit(item as Node);
                }
              }
            } else if ('type' in value) {
              visit(value as Node);
            }
          }
        }
      }

      visit(node.body as Node);
      return complexity;
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
