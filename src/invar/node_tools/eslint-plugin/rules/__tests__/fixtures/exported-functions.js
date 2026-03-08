/**
 * Test require-jsdoc-example rule
 * Tests exported functions and arrow functions
 */
/**
 * Valid: Exported function with @example
 *
 * @example
 * validFunction() // => 'valid'
 */
export function validFunction() {
    return 'valid';
}
/**
 * Invalid: Exported function WITHOUT @example
 */
export function invalidFunction() {
    return 'invalid';
}
/**
 * Valid: Exported arrow function with @example
 *
 * @example
 * validArrow() // => 'valid'
 */
export const validArrow = () => {
    return 'valid';
};
/**
 * Invalid: Exported arrow function WITHOUT @example
 */
export const invalidArrow = () => {
    return 'invalid';
};
// Valid: Non-exported function without @example (allowed)
function privateFunction() {
    return 'private';
}
// Valid: Non-exported arrow function without @example (allowed)
const privateArrow = () => {
    return 'private';
};
//# sourceMappingURL=exported-functions.js.map