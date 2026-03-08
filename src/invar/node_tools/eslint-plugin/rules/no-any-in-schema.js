/**
 * Rule: no-any-in-schema
 *
 * Forbid z.any() in Zod schemas.
 * z.any() defeats the purpose of schema validation.
 */
export const noAnyInSchema = {
    meta: {
        type: 'problem',
        docs: {
            description: 'Forbid z.any() in Zod schemas',
            recommended: true,
        },
        schema: [],
        messages: {
            noAny: 'Avoid z.any() - use a specific type or z.unknown() with refinement',
        },
    },
    create(context) {
        return {
            CallExpression(node) {
                const callee = node.callee;
                // Check for z.any()
                if (callee.type === 'MemberExpression' &&
                    callee.object.type === 'Identifier' &&
                    callee.object.name === 'z' &&
                    callee.property.type === 'Identifier' &&
                    callee.property.name === 'any') {
                    context.report({
                        node: node,
                        messageId: 'noAny',
                    });
                }
            },
        };
    },
};
export default noAnyInSchema;
//# sourceMappingURL=no-any-in-schema.js.map