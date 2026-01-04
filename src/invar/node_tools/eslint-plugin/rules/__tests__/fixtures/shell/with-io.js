/**
 * Valid Shell file - I/O imports allowed
 * Tests: no-io-in-core (should pass in /shell/ directory)
 */
import * as fs from 'fs'; // ✅ Allowed in Shell
import axios from 'axios'; // ✅ Allowed in Shell
/**
 * Shell function with I/O operations
 *
 * @example
 * readConfig('/path') // => { ... }
 */
export function readConfig(path) {
    const content = fs.readFileSync(path, 'utf-8');
    return JSON.parse(content);
}
/**
 * Shell function with HTTP operations
 *
 * @example
 * fetchData('url') // => Promise<data>
 */
export async function fetchData(url) {
    const response = await axios.get(url);
    return response.data;
}
//# sourceMappingURL=with-io.js.map