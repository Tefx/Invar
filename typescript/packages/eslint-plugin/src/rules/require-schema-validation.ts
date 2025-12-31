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
    schema: [],
    messages: {
      missingValidation:
        'Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
    },
  },

  create(context): Rule.RuleListener {
    function checkFunction(
      node: FunctionDeclaration | ArrowFunctionExpression,
      params: Array<{ name: string; typeAnnotation?: string }>
    ): void {
      const body = 'body' in node ? node.body : null;

      for (const param of params) {
        if (param.typeAnnotation && isZodType(param.typeAnnotation)) {
          if (!hasParseCall(body as Node | null, param.name)) {
            context.report({
              node: node as unknown as Rule.Node,
              messageId: 'missingValidation',
              data: { name: param.name },
            });
          }
        }
      }
    }

    return {
      FunctionDeclaration(node) {
        const params = node.params
          .filter((p): p is Identifier => p.type === 'Identifier')
          .map(p => ({
            name: p.name,
            typeAnnotation: (p as unknown as { typeAnnotation?: { typeAnnotation?: { type: string } } })
              .typeAnnotation?.typeAnnotation?.type,
          }));

        checkFunction(node as unknown as FunctionDeclaration, params);
      },

      ArrowFunctionExpression(node) {
        const params = node.params
          .filter((p): p is Identifier => p.type === 'Identifier')
          .map(p => ({
            name: p.name,
            typeAnnotation: (p as unknown as { typeAnnotation?: { typeAnnotation?: { type: string } } })
              .typeAnnotation?.typeAnnotation?.type,
          }));

        checkFunction(node as unknown as ArrowFunctionExpression, params);
      },
    };
  },
};

export default requireSchemaValidation;
