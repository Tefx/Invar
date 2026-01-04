/**
 * Rule: no-redundant-type-schema
 *
 * Detect Zod schemas that only repeat TypeScript types without adding semantic constraints.
 *
 * Detects:
 * - z.string() without .min/.max/.regex/.email/etc
 * - z.number() without .int/.min/.max/.positive/etc
 * - z.boolean() (almost always redundant)
 */
/**
 * Check if a schema call chain has any refinements
 */
function hasRefinements(node, baseType) {
    const refinementMethods = {
        string: ['min', 'max', 'length', 'email', 'url', 'emoji', 'uuid', 'cuid', 'regex', 'startsWith', 'endsWith', 'trim', 'toLowerCase', 'toUpperCase', 'refine', 'transform'],
        number: ['min', 'max', 'int', 'positive', 'negative', 'nonnegative', 'nonpositive', 'multipleOf', 'finite', 'safe', 'refine', 'transform'],
        boolean: [], // boolean is always redundant
    };
    const allowedMethods = refinementMethods[baseType] || [];
    // Walk up the AST to find any method calls on this schema
    let current = node.parent;
    while (current) {
        if (current.type === 'CallExpression') {
            const callee = current.callee;
            if (callee.type === 'MemberExpression' && callee.property.type === 'Identifier') {
                const methodName = callee.property.name;
                if (allowedMethods.includes(methodName)) {
                    return true; // Found a refinement
                }
            }
            current = current.parent;
        }
        else if (current.type === 'VariableDeclarator' || current.type === 'Property') {
            // Reached variable declaration or object property, stop searching
            break;
        }
        else {
            current = current.parent;
        }
    }
    return false;
}
export const noRedundantTypeSchema = {
    meta: {
        type: 'suggestion',
        docs: {
            description: 'Forbid Zod schemas that only repeat TypeScript types without adding constraints',
            recommended: true,
        },
        schema: [],
        messages: {
            redundantString: 'z.string() without constraints is redundant. Add .min(), .max(), .regex(), or use plain TypeScript type.',
            redundantNumber: 'z.number() without constraints is redundant. Add .min(), .max(), .int(), or use plain TypeScript type.',
            redundantBoolean: 'z.boolean() is almost always redundant. Use plain TypeScript boolean type unless validating external input.',
        },
    },
    create(context) {
        const sourceCode = context.sourceCode || context.getSourceCode();
        return {
            CallExpression(node) {
                const callee = node.callee;
                // Only check direct z.type() calls, not chained calls
                if (callee.type === 'MemberExpression' &&
                    callee.object.type === 'Identifier' &&
                    callee.object.name === 'z' &&
                    callee.property.type === 'Identifier') {
                    const typeName = callee.property.name;
                    // Add parent reference for hasRefinements to work
                    if (!node.parent) {
                        const parents = sourceCode.getAncestors(node);
                        node.parent = parents[parents.length - 1];
                    }
                    if (typeName === 'string' && !hasRefinements(node, 'string')) {
                        context.report({
                            node: node,
                            messageId: 'redundantString',
                        });
                    }
                    if (typeName === 'number' && !hasRefinements(node, 'number')) {
                        context.report({
                            node: node,
                            messageId: 'redundantNumber',
                        });
                    }
                    if (typeName === 'boolean') {
                        // boolean is always redundant since TypeScript already enforces it
                        context.report({
                            node: node,
                            messageId: 'redundantBoolean',
                        });
                    }
                }
            },
        };
    },
};
export default noRedundantTypeSchema;
//# sourceMappingURL=no-redundant-type-schema.js.map