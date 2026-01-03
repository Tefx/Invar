/**
 * Invalid Core file - has I/O imports
 * Tests: no-io-in-core (should fail in /core/ directory)
 */

import * as fs from 'fs'; // ❌ Should trigger no-io-in-core
import { readFile } from 'node:fs/promises'; // ❌ Should trigger no-io-in-core
import axios from 'axios'; // ❌ Should trigger no-io-in-core
import { S3Client } from '@aws-sdk/client-s3'; // ❌ Should trigger no-io-in-core

/**
 * Function that uses I/O (not allowed in Core)
 *
 * @example
 * readData('/path') // => 'data'
 */
export function readData(path: string): string {
  return fs.readFileSync(path, 'utf-8');
}
