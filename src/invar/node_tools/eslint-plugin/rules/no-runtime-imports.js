/**
 * Rule: no-runtime-imports
 *
 * Forbid imports inside functions (runtime imports).
 * All imports should be at module top-level for predictability and performance.
 *
 * Detects:
 * - require() calls inside functions
 * - dynamic import() calls inside functions
 */
export const noRuntimeImports = {
    meta: {
        type: 'problem',
        docs: {
            description: 'Forbid imports inside functions (require runtime imports at module top-level)',
            recommended: true,
        },
        schema: [],
        messages: {
            runtimeRequire: 'Runtime require() detected. Move imports to module top-level for predictability.',
            runtimeImport: 'Dynamic import() detected. Move imports to module top-level for predictability.',
        },
    },
    create(context) {
        /**
         * Check if node is inside a function
         */
        function isInsideFunction(node) {
            const ancestors = context.sourceCode?.getAncestors?.(node) || context.getAncestors();
            for (const ancestor of ancestors) {
                if (ancestor.type === 'FunctionDeclaration' ||
                    ancestor.type === 'FunctionExpression' ||
                    ancestor.type === 'ArrowFunctionExpression') {
                    return true;
                }
            }
            return false;
        }
        return {
            CallExpression(node) {
                const callNode = node;
                // Check for require() calls
                if (callNode.callee.type === 'Identifier' &&
                    callNode.callee.name === 'require') {
                    if (isInsideFunction(node)) {
                        context.report({
                            node: node,
                            messageId: 'runtimeRequire',
                        });
                    }
                }
            },
            ImportExpression(node) {
                // Check for dynamic import()
                if (isInsideFunction(node)) {
                    context.report({
                        node: node,
                        messageId: 'runtimeImport',
                    });
                }
            },
        };
    },
};
export default noRuntimeImports;
//# sourceMappingURL=no-runtime-imports.js.map