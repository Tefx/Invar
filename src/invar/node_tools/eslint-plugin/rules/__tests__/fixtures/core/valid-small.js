/**
 * Valid Core file - within 650 line limit
 * Tests: layer-detection (core), max-file-lines (core: 650)
 */
/**
 * Example function with JSDoc
 *
 * @example
 * multiply(2, 3) // => 6
 */
export function multiply(a, b) {
    return a * b;
}
/**
 * Another function
 *
 * @example
 * add(2, 3) // => 5
 */
export function add(a, b) {
    return a + b;
}
// Non-exported function - no @example required
function helper() {
    console.log('helper');
}
//# sourceMappingURL=valid-small.js.map