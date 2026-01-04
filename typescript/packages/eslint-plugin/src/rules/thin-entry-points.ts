/**
 * Rule: thin-entry-points
 *
 * Detect entry point files that contain substantial logic.
 * Entry points should be thin - just importing and delegating to Core/Shell.
 *
 * Detects:
 * - index.ts, main.ts, cli.ts with >10 non-import statements
 * - Complex logic in entry points (functions, classes, etc.)
 * - Entry points should export/re-export, not implement
 */

import type { Rule } from 'eslint';
import type { Program, Node, ModuleDeclaration, Statement, Directive } from 'estree';

// Entry point file patterns
const ENTRY_POINT_PATTERNS = [
  /index\.(ts|js|tsx|jsx)$/,
  /main\.(ts|js|tsx|jsx)$/,
  /cli\.(ts|js|tsx|jsx)$/,
  /app\.(ts|js|tsx|jsx)$/,
  /server\.(ts|js|tsx|jsx)$/,
];

// Configurable threshold
interface Options {
  maxStatements?: number;
}

const DEFAULT_MAX_STATEMENTS = 10;

export const thinEntryPoints: Rule.RuleModule = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Warn when entry point files contain substantial logic (should delegate to Core/Shell)',
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
        },
        additionalProperties: false,
      },
    ],
    messages: {
      tooMuchLogic:
        'Entry point file "{{filename}}" has {{count}} non-import statements (max {{max}}). Entry points should be thin - delegate to Core/Shell.',
      hasComplexLogic:
        'Entry point file "{{filename}}" contains {{type}}. Entry points should only import/export, not implement logic.',
    },
  },

  create(context): Rule.RuleListener {
    const filename = context.filename || context.getFilename();

    // Check if this is an entry point file
    const isEntryPoint = ENTRY_POINT_PATTERNS.some(pattern => pattern.test(filename));
    if (!isEntryPoint) {
      return {}; // Skip non-entry-point files
    }

    const options = (context.options[0] || {}) as Options;
    const maxStatements = options.maxStatements || DEFAULT_MAX_STATEMENTS;

    /**
     * Check if statement is an import/export WITHOUT a declaration
     * Export with declarations like "export function foo()" should be treated as declarations
     */
    function isImportOrExport(stmt: ModuleDeclaration | Statement | Directive): boolean {
      if (stmt.type === 'ImportDeclaration' || stmt.type === 'ExportAllDeclaration') {
        return true;
      }
      
      // ExportNamedDeclaration and ExportDefaultDeclaration can have declarations
      if (stmt.type === 'ExportNamedDeclaration' || stmt.type === 'ExportDefaultDeclaration') {
        const exportStmt = stmt as unknown as { declaration: Node | null };
        // If there's a declaration, treat it as a regular statement (not just an export)
        return exportStmt.declaration === null;
      }
      
      return false;
    }

    /**
     * Check if statement is simple (type-only, interface, or simple variable declaration)
     */
    function isSimpleStatement(stmt: ModuleDeclaration | Statement | Directive): boolean {
      // Type aliases and interfaces are OK (TypeScript-specific node types)
      const stmtType = (stmt as any).type;
      if (stmtType === 'TSTypeAliasDeclaration' || stmtType === 'TSInterfaceDeclaration') {
        return true;
      }

      // Simple variable declarations without complex initializers
      if (stmt.type === 'VariableDeclaration') {
        const varDecl = stmt as unknown as { declarations: Array<{ init: Node | null }> };
        // Only allow simple assignments, not complex expressions
        for (const decl of varDecl.declarations) {
          if (decl.init && decl.init.type !== 'Literal' && decl.init.type !== 'Identifier') {
            return false; // Complex initializer
          }
        }
        return true;
      }

      return false;
    }

    /**
     * Check for complex logic (functions, classes, etc.)
     */
    function hasComplexLogic(stmt: ModuleDeclaration | Statement | Directive): { has: boolean; type: string } {
      if (stmt.type === 'FunctionDeclaration') {
        return { has: true, type: 'function definition' };
      }
      if (stmt.type === 'ClassDeclaration') {
        return { has: true, type: 'class definition' };
      }
      if (stmt.type === 'IfStatement' || stmt.type === 'ForStatement' || stmt.type === 'WhileStatement') {
        return { has: true, type: 'control flow statement' };
      }
      if (stmt.type === 'TryStatement') {
        return { has: true, type: 'try-catch block' };
      }

      // Check for complex variable declarations with function/class expressions
      if (stmt.type === 'VariableDeclaration') {
        const varDecl = stmt as unknown as { declarations: Array<{ init: Node | null }> };
        for (const decl of varDecl.declarations) {
          if (decl.init) {
            if (
              decl.init.type === 'FunctionExpression' ||
              decl.init.type === 'ArrowFunctionExpression' ||
              decl.init.type === 'ClassExpression'
            ) {
              return { has: true, type: 'function/class expression' };
            }
          }
        }
      }

      return { has: false, type: '' };
    }

    return {
      Program(node) {
        const program = node as unknown as Program;
        const statements = program.body;

        // Count non-import/export statements
        let nonImportExportCount = 0;
        const complexLogicItems: Array<{ type: string; line: number }> = [];

        for (const stmt of statements) {
          if (!isImportOrExport(stmt) && !isSimpleStatement(stmt)) {
            nonImportExportCount++;

            // Check for complex logic
            const complexCheck = hasComplexLogic(stmt);
            if (complexCheck.has) {
              const stmtNode = stmt as unknown as { loc?: { start: { line: number } } };
              complexLogicItems.push({
                type: complexCheck.type,
                line: stmtNode.loc?.start.line || 0,
              });
            }
          }
        }

        // Report complex logic violations (higher priority)
        if (complexLogicItems.length > 0) {
          for (const item of complexLogicItems) {
            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'hasComplexLogic',
              data: {
                filename: filename.replace(/\\/g, '/').split('/').pop() || filename,
                type: item.type,
              },
            });
          }
        }

        // Report statement count violation
        if (nonImportExportCount > maxStatements) {
          context.report({
            node: node as unknown as Rule.Node,
            messageId: 'tooMuchLogic',
            data: {
              filename: filename.replace(/\\/g, '/').split('/').pop() || filename,
              count: String(nonImportExportCount),
              max: String(maxStatements),
            },
          });
        }
      },
    };
  },
};

export default thinEntryPoints;
