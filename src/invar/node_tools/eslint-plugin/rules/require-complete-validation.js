/**
 * Rule: require-complete-validation
 *
 * Detect functions where some parameters have Zod schema validation but others don't.
 * Either all parameters should be validated, or none should be.
 *
 * Detects:
 * - Functions with mixed z.infer<typeof Schema> and plain types
 */
/**
 * Check if a parameter type is a Zod inferred type
 * Looks for: z.infer<typeof SchemaName>
 */
function isZodInferType(typeAnnotation) {
    if (!typeAnnotation || typeAnnotation.type !== 'TSTypeReference') {
        return false;
    }
    const typeRef = typeAnnotation;
    // Check for z.infer type
    if (typeRef.typeName.type === 'TSQualifiedName' &&
        typeRef.typeName.left.type === 'Identifier' &&
        typeRef.typeName.left.name === 'z' &&
        typeRef.typeName.right.type === 'Identifier' &&
        typeRef.typeName.right.name === 'infer') {
        return true;
    }
    // Also check for direct TypeOf reference: typeof SchemaName
    if (typeRef.typeParameters && typeRef.typeParameters.params.length > 0) {
        const firstParam = typeRef.typeParameters.params[0];
        if (firstParam.type === 'TSTypeQuery') {
            return true;
        }
    }
    return false;
}
export const requireCompleteValidation = {
    meta: {
        type: 'suggestion',
        docs: {
            description: 'Require all function parameters to be validated, or none',
            recommended: true,
        },
        schema: [],
        messages: {
            partialValidation: 'Function has {{validated}} parameter(s) with Zod schema validation but {{unvalidated}} without. ' +
                'Either validate all parameters or use plain TypeScript types for all.',
        },
    },
    create(context) {
        function checkFunction(node) {
            const params = node.params;
            if (params.length === 0) {
                return; // No parameters to check
            }
            let validatedCount = 0;
            let unvalidatedCount = 0;
            for (const param of params) {
                if (param.type === 'Identifier' && param.typeAnnotation) {
                    const typeAnnotation = param.typeAnnotation.typeAnnotation;
                    if (isZodInferType(typeAnnotation)) {
                        validatedCount++;
                    }
                    else {
                        unvalidatedCount++;
                    }
                }
                else if (param.type === 'AssignmentPattern') {
                    // Handle default parameters: param: Type = defaultValue
                    if (param.left.type === 'Identifier' && param.left.typeAnnotation) {
                        const typeAnnotation = param.left.typeAnnotation.typeAnnotation;
                        if (isZodInferType(typeAnnotation)) {
                            validatedCount++;
                        }
                        else {
                            unvalidatedCount++;
                        }
                    }
                }
                else {
                    // Other parameter types (rest, destructuring) count as unvalidated
                    unvalidatedCount++;
                }
            }
            // Report if we have a mix of validated and unvalidated parameters
            if (validatedCount > 0 && unvalidatedCount > 0) {
                context.report({
                    node: node,
                    messageId: 'partialValidation',
                    data: {
                        validated: String(validatedCount),
                        unvalidated: String(unvalidatedCount),
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
export default requireCompleteValidation;
//# sourceMappingURL=require-complete-validation.js.map