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
function isHighRiskFunction(functionName, filePath) {
    const combined = `${functionName} ${filePath}`.toLowerCase();
    return RISK_KEYWORDS.some(keyword => combined.includes(keyword));
}
/**
 * Check if file path matches any of the enforceFor patterns.
 * Supports glob-like patterns with wildcards.
 * Protected against ReDoS attacks with pattern length limits.
 */
function matchesEnforcePattern(filePath, patterns) {
    if (patterns.length === 0)
        return false;
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
            .replace(/\\\*/g, '[^/]*?') // * → [^/]*? (reluctant)
            .replace(/\\\?/g, '.'); // ? → .
        try {
            const regex = new RegExp(`^${regexPattern}$`);
            if (regex.test(normalizedPath)) {
                return true;
            }
        }
        catch (e) {
            // Invalid regex from pattern - skip
            continue;
        }
    }
    return false;
}
function isZodType(typeAnnotation) {
    return ZOD_TYPE_PATTERNS.some(pattern => pattern.test(typeAnnotation));
}
function collectParseArgs(body, visitorKeys) {
    const parsed = new Set();
    if (!body)
        return parsed;

    const MAX_DEPTH = 50;
    const stack = [{ node: body, depth: 0 }];

    while (stack.length > 0) {
        const current = stack.pop();
        if (!current)
            continue;
        const node = current.node;
        const depth = current.depth;
        if (!node || typeof node !== 'object')
            continue;
        if (depth > MAX_DEPTH)
            continue;

        if (node.type === 'CallExpression') {
            const callee = node.callee;
            if (callee && callee.type === 'MemberExpression') {
                const property = callee.property;
                if (property && property.type === 'Identifier' && (property.name === 'parse' || property.name === 'safeParse')) {
                    for (const arg of node.arguments || []) {
                        if (arg && arg.type === 'Identifier') {
                            parsed.add(arg.name);
                        }
                    }
                }
            }
        }

        const keys = (visitorKeys && node.type && visitorKeys[node.type]) || [];
        for (const key of keys) {
            const value = node[key];
            if (!value)
                continue;
            if (Array.isArray(value)) {
                for (const item of value) {
                    if (item && typeof item === 'object' && item.type) {
                        stack.push({ node: item, depth: depth + 1 });
                    }
                }
            }
            else if (typeof value === 'object' && value.type) {
                stack.push({ node: value, depth: depth + 1 });
            }
        }
    }

    return parsed;
}
export const requireSchemaValidation = {
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
            missingValidation: 'Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
            missingValidationRisk: 'High-risk function "{{functionName}}": Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
            addParseCall: 'Add .parse() validation for "{{name}}"',
        },
    },
    create(context) {
        const sourceCode = context.sourceCode || context.getSourceCode();
        const options = context.options[0] || {};
        const mode = options.mode || 'recommended';
        const enforceFor = options.enforceFor || [];
        const filename = context.filename || context.getFilename();
        /**
         * Get the text of a type annotation from source code.
         * Strips the leading ": " to return just the type.
         */
        function getTypeAnnotationText(param) {
            const typedParam = param;
            if (!typedParam.typeAnnotation)
                return null;
            const text = sourceCode.getText(typedParam.typeAnnotation);
            // Strip leading ": " from type annotation
            return text.replace(/^:\s*/, '');
        }
        /**
         * Get function name from node
         */
        function getFunctionName(node) {
            if (node.type === 'FunctionDeclaration' && node.id) {
                return node.id.name;
            }
            // For arrow functions, try to get name from parent variable declarator
            return 'anonymous';
        }
        /**
         * Determine if this function should be checked based on mode and options
         */
        function shouldCheck(functionName) {
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
        function checkFunction(node, params) {
            const functionName = getFunctionName(node);
            if (!shouldCheck(functionName)) {
                return;
            }

            const body = 'body' in node ? node.body : null;
            const zodParams = params.filter((p) => p.typeAnnotation && isZodType(p.typeAnnotation) && p.name && p.name !== '{...}' && p.name !== '[...]');
            if (zodParams.length === 0) {
                return;
            }

            const parsedArgs = collectParseArgs(body, sourceCode.visitorKeys);
            const isRiskFunction = isHighRiskFunction(functionName, filename);

            for (const param of zodParams) {
                if (parsedArgs.has(param.name)) {
                    continue;
                }

                const schemaMatch = param.typeAnnotation.match(/typeof\s+(\w+)/);
                const schemaName = schemaMatch ? schemaMatch[1] : 'Schema';
                const validatedVarName = `validated${param.name.charAt(0).toUpperCase()}${param.name.slice(1)}`;

                context.report({
                    node: node,
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
                                if (!body || body.type !== 'BlockStatement')
                                    return null;
                                const blockBody = body;
                                if (!blockBody.body || blockBody.body.length === 0)
                                    return null;
                                const firstStatement = blockBody.body[0];
                                const firstStatementStart = firstStatement.loc?.start.column ?? 2;
                                const indent = ' '.repeat(firstStatementStart);
                                const parseCode = `const ${validatedVarName} = ${schemaName}.parse(${param.name});\n${indent}`;
                                return fixer.insertTextBefore(firstStatement, parseCode);
                            },
                        },
                    ],
                });
            }
        }
        /**
         * Extract param name and type annotation from various param patterns.
         */
        function extractParamInfo(param) {
            if (param.type === 'Identifier') {
                return {
                    name: param.name,
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
                const restParam = param;
                const name = restParam.argument?.name || '...rest';
                return {
                    name,
                    typeAnnotation: getTypeAnnotationText(param),
                };
            }
            // Handle assignment patterns: param = default
            if (param.type === 'AssignmentPattern') {
                const assignParam = param;
                if (assignParam.left) {
                    return extractParamInfo(assignParam.left);
                }
            }
            return null;
        }
        return {
            FunctionDeclaration(node) {
                const params = node.params
                    .map(p => extractParamInfo(p))
                    .filter((p) => p !== null);
                checkFunction(node, params);
            },
            ArrowFunctionExpression(node) {
                const params = node.params
                    .map(p => extractParamInfo(p))
                    .filter((p) => p !== null);
                checkFunction(node, params);
            },
        };
    },
};
export default requireSchemaValidation;
//# sourceMappingURL=require-schema-validation.js.map