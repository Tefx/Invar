/**
 * Rule: require-schema-validation
 *
 * Zod-typed parameters must have a corresponding .parse() or .safeParse() call.
 *
 * Supports three modes:
 * - recommended: Warn on missing validation (default)
 * - strict: Error on missing validation
 * - risk-based: Error only for high-risk functions (payment, auth, etc.)
 */

import type { Rule } from 'eslint';
import type { Identifier, FunctionDeclaration, ArrowFunctionExpression, Node } from 'estree';

const ZOD_TYPE_PATTERNS = [
  /^z\./,
  /ZodType/,
  /z\.infer/,
  /Schema$/,
];

// High-risk keywords for risk-based mode
const RISK_KEYWORDS = [
  'payment',
  'pay',
  'auth',
  'authenticate',
  'login',
  'token',
  'validate',
  'verify',
  'encrypt',
  'decrypt',
  'password',
  'credential',
  'secret',
];

/**
 * Check if a function name or path contains high-risk keywords
 */
function isHighRiskFunction(functionName: string, filePath: string): boolean {
  const combined = `${functionName} ${filePath}`.toLowerCase();
  return RISK_KEYWORDS.some(keyword => combined.includes(keyword));
}

/**
 * Check if file path matches any of the enforceFor patterns.
 * Supports glob-like patterns with wildcards.
 * Protected against ReDoS attacks with pattern length limits.
 */
function matchesEnforcePattern(filePath: string, patterns: string[]): boolean {
  if (patterns.length === 0) return false;

  const normalizedPath = filePath.replace(/\\/g, '/').toLowerCase();

  for (const pattern of patterns) {
    // Protect against ReDoS: limit pattern length
    if (pattern.length > 200) {
      continue; // Skip overly long patterns
    }

    const normalizedPattern = pattern.replace(/\\/g, '/').toLowerCase();

    // Escape special regex characters except glob wildcards
    const escaped = normalizedPattern.replace(/[.+^${}()|[\]]/g, '\\$&');

    // Convert glob pattern to regex with safe replacements
    // ** matches any directory depth (use reluctant quantifier)
    // * matches any characters except / (use reluctant quantifier)
    const regexPattern = escaped
      .replace(/\\\*\\\*/g, '.*?') // ** → .*? (reluctant)
      .replace(/\\\*/g, '[^/]*?')  // * → [^/]*? (reluctant)
      .replace(/\\\?/g, '.');       // ? → .

    try {
      const regex = new RegExp(`^${regexPattern}$`);
      if (regex.test(normalizedPath)) {
        return true;
      }
    } catch (e) {
      // Invalid regex from pattern - skip
      continue;
    }
  }

  return false;
}

function isZodType(typeAnnotation: string): boolean {
  return ZOD_TYPE_PATTERNS.some(pattern => pattern.test(typeAnnotation));
}

function hasParseCall(body: Node | null, paramName: string): boolean {
  if (!body) return false;

  let found = false;
  const MAX_DEPTH = 50; // Prevent stack overflow on deeply nested types

  const visit = (node: Node, depth: number = 0): void => {
    if (found) return;
    if (depth > MAX_DEPTH) return; // Depth limit to prevent stack overflow

    if (node.type === 'CallExpression') {
      const callee = node.callee;
      if (callee.type === 'MemberExpression') {
        const property = callee.property;
        if (
          property.type === 'Identifier' &&
          (property.name === 'parse' || property.name === 'safeParse')
        ) {
          // Check if argument is our param
          if (node.arguments.some(arg =>
            arg.type === 'Identifier' && arg.name === paramName
          )) {
            found = true;
            return;
          }
        }
      }
    }

    // Recursively visit children with depth tracking
    for (const key of Object.keys(node)) {
      const value = (node as unknown as Record<string, unknown>)[key];
      if (value && typeof value === 'object') {
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
  };

  visit(body);
  return found;
}

export const requireSchemaValidation: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Require .parse() call for Zod-typed parameters',
      recommended: true,
    },
    hasSuggestions: true,
    schema: [
      {
        type: 'object',
        properties: {
          mode: {
            type: 'string',
            enum: ['recommended', 'strict', 'risk-based'],
            default: 'recommended',
          },
          enforceFor: {
            type: 'array',
            items: {
              type: 'string',
            },
            default: [],
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      missingValidation:
        'Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
      missingValidationRisk:
        'High-risk function "{{functionName}}": Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
      addParseCall:
        'Add .parse() validation for "{{name}}"',
    },
  },

  create(context): Rule.RuleListener {
    const sourceCode = context.sourceCode || context.getSourceCode();
    const options = context.options[0] || {};
    const mode = options.mode || 'recommended';
    const enforceFor = options.enforceFor || [];
    const filename = context.filename || context.getFilename();

    /**
     * Get the text of a type annotation from source code.
     * Strips the leading ": " to return just the type.
     */
    function getTypeAnnotationText(param: Node): string | null {
      const typedParam = param as unknown as { typeAnnotation?: Node };
      if (!typedParam.typeAnnotation) return null;
      const text = sourceCode.getText(typedParam.typeAnnotation as unknown as Rule.Node);
      // Strip leading ": " from type annotation
      return text.replace(/^:\s*/, '');
    }

    /**
     * Get function name from node
     */
    function getFunctionName(node: FunctionDeclaration | ArrowFunctionExpression): string {
      if (node.type === 'FunctionDeclaration' && node.id) {
        return node.id.name;
      }
      // For arrow functions, try to get name from parent variable declarator
      return 'anonymous';
    }

    /**
     * Determine if this function should be checked based on mode and options
     */
    function shouldCheck(functionName: string): boolean {
      if (mode === 'strict') {
        return true; // Always check in strict mode
      }

      if (mode === 'risk-based') {
        // Check if function is high-risk by name/path
        if (isHighRiskFunction(functionName, filename)) {
          return true;
        }
        // Check if file path matches enforceFor patterns
        if (matchesEnforcePattern(filename, enforceFor)) {
          return true;
        }
        return false;
      }

      // recommended mode - always check (but will warn instead of error)
      return true;
    }

    function checkFunction(
      node: FunctionDeclaration | ArrowFunctionExpression,
      params: Array<{ name: string; typeAnnotation: string | null }>
    ): void {
      const functionName = getFunctionName(node);

      // Skip if shouldn't check based on mode
      if (!shouldCheck(functionName)) {
        return;
      }

      const body = 'body' in node ? node.body : null;
      const isRiskFunction = isHighRiskFunction(functionName, filename);

      for (const param of params) {
        if (param.typeAnnotation && isZodType(param.typeAnnotation)) {
          if (!hasParseCall(body as Node | null, param.name)) {
            // Extract schema name from type annotation (e.g., "z.infer<typeof UserSchema>" -> "UserSchema")
            const schemaMatch = param.typeAnnotation.match(/typeof\s+(\w+)/);
            const schemaName = schemaMatch ? schemaMatch[1] : 'Schema';
            const validatedVarName = `validated${param.name.charAt(0).toUpperCase()}${param.name.slice(1)}`;

            context.report({
              node: node as unknown as Rule.Node,
              messageId: isRiskFunction ? 'missingValidationRisk' : 'missingValidation',
              data: {
                name: param.name,
                functionName: functionName,
              },
              suggest: [
                {
                  messageId: 'addParseCall',
                  data: { name: param.name },
                  fix(fixer) {
                    // Find the opening brace of the function body
                    if (!body || body.type !== 'BlockStatement') return null;
                    const blockBody = body as unknown as { body: Node[] };
                    if (!blockBody.body || blockBody.body.length === 0) return null;

                    const firstStatement = blockBody.body[0];
                    // Detect indentation from the first statement
                    const firstStatementStart = (firstStatement as unknown as { loc?: { start: { column: number } } }).loc?.start.column ?? 2;
                    const indent = ' '.repeat(firstStatementStart);
                    const parseCode = `const ${validatedVarName} = ${schemaName}.parse(${param.name});\n${indent}`;
                    return fixer.insertTextBefore(firstStatement as unknown as Rule.Node, parseCode);
                  },
                },
              ],
            });
          }
        }
      }
    }

    /**
     * Extract param name and type annotation from various param patterns.
     */
    function extractParamInfo(param: Node): { name: string; typeAnnotation: string | null } | null {
      if (param.type === 'Identifier') {
        return {
          name: (param as Identifier).name,
          typeAnnotation: getTypeAnnotationText(param),
        };
      }
      // Handle destructuring patterns: { a, b }: ZodSchema
      if (param.type === 'ObjectPattern' || param.type === 'ArrayPattern') {
        // For destructuring, we use a placeholder name and check the pattern's type
        const patternName = param.type === 'ObjectPattern' ? '{...}' : '[...]';
        return {
          name: patternName,
          typeAnnotation: getTypeAnnotationText(param),
        };
      }
      // Handle rest parameters: ...args: ZodSchema[]
      if (param.type === 'RestElement') {
        const restParam = param as unknown as { argument?: Identifier };
        const name = restParam.argument?.name || '...rest';
        return {
          name,
          typeAnnotation: getTypeAnnotationText(param),
        };
      }
      // Handle assignment patterns: param = default
      if (param.type === 'AssignmentPattern') {
        const assignParam = param as unknown as { left?: Node };
        if (assignParam.left) {
          return extractParamInfo(assignParam.left);
        }
      }
      return null;
    }

    return {
      FunctionDeclaration(node) {
        const params = node.params
          .map(p => extractParamInfo(p as unknown as Node))
          .filter((p): p is { name: string; typeAnnotation: string | null } => p !== null);

        checkFunction(node as unknown as FunctionDeclaration, params);
      },

      ArrowFunctionExpression(node) {
        const params = node.params
          .map(p => extractParamInfo(p as unknown as Node))
          .filter((p): p is { name: string; typeAnnotation: string | null } => p !== null);

        checkFunction(node as unknown as ArrowFunctionExpression, params);
      },
    };
  },
};

export default requireSchemaValidation;
