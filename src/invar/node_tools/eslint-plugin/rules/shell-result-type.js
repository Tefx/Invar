/**
 * Rule: shell-result-type
 *
 * Shell functions must return Result<T, E> type.
 * This enforces explicit error handling in the Shell layer.
 */
const RESULT_TYPE_PATTERNS = [
    /^Result</,
    /^ResultAsync</,
    /^Ok</,
    /^Err</,
    /^Either</,
    /^Left</,
    /^Right</,
];
function isResultType(typeAnnotation) {
    return RESULT_TYPE_PATTERNS.some(pattern => pattern.test(typeAnnotation));
}
function isInShellDirectory(filename) {
    return filename.includes('/shell/') || filename.includes('\\shell\\');
}
function isExported(node) {
    const parent = node.parent;
    if (!parent)
        return false;
    if (parent.type === 'ExportNamedDeclaration')
        return true;
    if (parent.type === 'ExportDefaultDeclaration')
        return true;
    // Check for module.exports assignment
    if (parent.type === 'VariableDeclarator') {
        const grandparent = parent.parent;
        if (grandparent?.type === 'VariableDeclaration') {
            const greatGrandparent = grandparent.parent;
            if (greatGrandparent?.type === 'ExportNamedDeclaration')
                return true;
        }
    }
    return false;
}
export const shellResultType = {
    meta: {
        type: 'suggestion',
        docs: {
            description: 'Shell functions must return Result<T, E> type',
            recommended: true,
        },
        hasSuggestions: true,
        schema: [
            {
                type: 'object',
                properties: {
                    checkPrivate: {
                        type: 'boolean',
                        default: false,
                    },
                },
                additionalProperties: false,
            },
        ],
        messages: {
            missingResultType: 'Shell function "{{name}}" should return Result<T, E> type for explicit error handling',
            wrapWithResult: 'Wrap return type with Result<{{returnType}}, Error>',
        },
    },
    create(context) {
        const filename = context.filename || context.getFilename();
        const sourceCode = context.sourceCode || context.getSourceCode();
        const options = context.options[0] || {};
        const checkPrivate = options.checkPrivate || false;
        if (!isInShellDirectory(filename)) {
            return {};
        }
        /**
         * Get the text of a return type annotation from source code.
         * Strips the leading ": " to return just the type (e.g., "Result<T, E>").
         */
        function getReturnTypeText(node) {
            const typedNode = node;
            if (!typedNode.returnType)
                return null;
            const text = sourceCode.getText(typedNode.returnType);
            // Strip leading ": " from type annotation (e.g., ": Result<T, E>" -> "Result<T, E>")
            return text.replace(/^:\s*/, '');
        }
        function checkFunction(node, name, returnType) {
            // Skip anonymous functions
            if (!name)
                return;
            // Skip private functions unless configured
            if (!checkPrivate && name.startsWith('_'))
                return;
            // Skip non-exported functions
            if (!isExported(node))
                return;
            // Check return type
            if (!returnType || !isResultType(returnType)) {
                const suggestedReturnType = returnType || 'void';
                const typedNode = node;
                context.report({
                    node,
                    messageId: 'missingResultType',
                    data: { name },
                    suggest: typedNode.returnType ? [
                        {
                            messageId: 'wrapWithResult',
                            data: { returnType: suggestedReturnType },
                            fix(fixer) {
                                if (!typedNode.returnType)
                                    return null;
                                const newType = `Result<${suggestedReturnType}, Error>`;
                                return fixer.replaceText(typedNode.returnType, `: ${newType}`);
                            },
                        },
                    ] : [],
                });
            }
        }
        return {
            FunctionDeclaration(node) {
                const name = node.id?.name || null;
                const returnType = getReturnTypeText(node);
                checkFunction(node, name, returnType);
            },
            ArrowFunctionExpression(node) {
                // Get name from parent variable declaration
                const parent = node.parent;
                const name = parent?.type === 'VariableDeclarator' && parent.id?.name
                    ? parent.id.name
                    : null;
                const returnType = getReturnTypeText(node);
                checkFunction(node, name, returnType);
            },
        };
    },
};
export default shellResultType;
//# sourceMappingURL=shell-result-type.js.map