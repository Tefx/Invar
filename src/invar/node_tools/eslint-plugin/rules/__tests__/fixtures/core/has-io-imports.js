/**
 * Invalid Core file - has I/O imports
 * Tests: no-io-in-core (should fail in /core/ directory)
 */
import * as fs from 'fs'; // ❌ Should trigger no-io-in-core
/**
 * Function that uses I/O (not allowed in Core)
 *
 * @example
 * readData('/path') // => 'data'
 */
export function readData(path) {
    return fs.readFileSync(path, 'utf-8');
}
//# sourceMappingURL=has-io-imports.js.map