/**
 * Rule: require-schema-validation
 *
 * Zod-typed parameters must have a corresponding .parse() or .safeParse() call.
 */

import type { Rule } from 'eslint';
import type { Identifier, FunctionDeclaration, ArrowFunctionExpression, Node } from 'estree';

const ZOD_TYPE_PATTERNS = [
  /^z\./,
  /ZodType/,
  /z\.infer/,
  /Schema$/,
];

function isZodType(typeAnnotation: string): boolean {
  return ZOD_TYPE_PATTERNS.some(pattern => pattern.test(typeAnnotation));
}

function hasParseCall(body: Node | null, paramName: string): boolean {
  if (!body) return false;

  let found = false;

  const visit = (node: Node): void => {
    if (found) return;

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

    // Recursively visit children
    for (const key of Object.keys(node)) {
      const value = (node as Record<string, unknown>)[key];
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
    schema: [],
    messages: {
      missingValidation:
        'Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
      addParseCall:
        'Add .parse() validation for "{{name}}"',
    },
  },

  create(context): Rule.RuleListener {
    const sourceCode = context.sourceCode || context.getSourceCode();

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

    function checkFunction(
      node: FunctionDeclaration | ArrowFunctionExpression,
      params: Array<{ name: string; typeAnnotation: string | null }>
    ): void {
      const body = 'body' in node ? node.body : null;

      for (const param of params) {
        if (param.typeAnnotation && isZodType(param.typeAnnotation)) {
          if (!hasParseCall(body as Node | null, param.name)) {
            // Extract schema name from type annotation (e.g., "z.infer<typeof UserSchema>" -> "UserSchema")
            const schemaMatch = param.typeAnnotation.match(/typeof\s+(\w+)/);
            const schemaName = schemaMatch ? schemaMatch[1] : 'Schema';
            const validatedVarName = `validated${param.name.charAt(0).toUpperCase()}${param.name.slice(1)}`;

            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'missingValidation',
              data: { name: param.name },
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
