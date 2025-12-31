/**
 * Invar Core/Shell Separation Examples (TypeScript)
 *
 * Reference patterns for Core vs Shell architecture.
 * Managed by Invar - do not edit directly.
 */

import { z } from 'zod';
import { Result, ok, err } from 'neverthrow';
import * as fs from 'fs/promises';

// =============================================================================
// CORE: Pure Logic (no I/O)
// =============================================================================
// Location: src/*/core/
// Requirements: Zod schemas, pure functions, no I/O imports
// =============================================================================

/**
 * Precondition: content is defined (can be empty string)
 * Postcondition: all lines are trimmed and non-empty
 */
const ParseLinesInput = z.string();
const ParseLinesOutput = z.array(z.string().min(1));

/**
 * Parse content into non-empty lines.
 *
 * @example
 * parseLines("a\nb\nc")   // => ["a", "b", "c"]
 *
 * @example
 * parseLines("")          // => []
 *
 * @example
 * parseLines("  \n  ")    // => [] (whitespace only)
 */
export function parseLines(content: string): string[] {
  const validated = ParseLinesInput.parse(content);
  const result = validated
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0);
  return ParseLinesOutput.parse(result);
}

/**
 * Precondition: all items are strings
 * Postcondition: all counts are positive
 */
const CountItemsInput = z.array(z.string());
const CountItemsOutput = z.record(z.string(), z.number().positive());

/**
 * Count occurrences of each item.
 *
 * @example
 * countItems(["a", "b", "a"])  // => { a: 2, b: 1 }
 *
 * @example
 * countItems([])               // => {}
 */
export function countItems(items: string[]): Record<string, number> {
  const validated = CountItemsInput.parse(items);
  const counts: Record<string, number> = {};
  for (const item of validated) {
    counts[item] = (counts[item] ?? 0) + 1;
  }
  // Note: Output validation skipped for empty result (no positive numbers)
  if (Object.keys(counts).length === 0) {
    return counts;
  }
  return CountItemsOutput.parse(counts);
}

// =============================================================================
// SHELL: I/O Operations
// =============================================================================
// Location: src/*/shell/
// Requirements: Result<T, E> return type, calls Core for logic
// =============================================================================

/**
 * Error types for file operations.
 */
export class FileNotFoundError extends Error {
  constructor(path: string) {
    super(`File not found: ${path}`);
    this.name = 'FileNotFoundError';
  }
}

export class PermissionError extends Error {
  constructor(path: string) {
    super(`Permission denied: ${path}`);
    this.name = 'PermissionError';
  }
}

type FileError = FileNotFoundError | PermissionError | Error;

/**
 * Read file content.
 *
 * Shell handles I/O, returns Result for error handling.
 */
export async function readFile(
  path: string
): Promise<Result<string, FileError>> {
  try {
    const content = await fs.readFile(path, 'utf-8');
    return ok(content);
  } catch (error) {
    if (error instanceof Error) {
      if ('code' in error && error.code === 'ENOENT') {
        return err(new FileNotFoundError(path));
      }
      if ('code' in error && error.code === 'EACCES') {
        return err(new PermissionError(path));
      }
      return err(error);
    }
    return err(new Error(String(error)));
  }
}

/**
 * Count lines in file - demonstrates Core/Shell integration.
 *
 * Shell reads file -> Core parses content -> Shell returns result.
 */
export async function countLinesInFile(
  path: string
): Promise<Result<Record<string, number>, FileError>> {
  // Shell: I/O operation
  const contentResult = await readFile(path);

  if (contentResult.isErr()) {
    return err(contentResult.error);
  }

  const content = contentResult.value;

  // Core: Pure logic (no I/O)
  const lines = parseLines(content);
  const counts = countItems(lines);

  // Shell: Return result
  return ok(counts);
}

// =============================================================================
// ANTI-PATTERNS
// =============================================================================

// DON'T: I/O in Core
// function parseFile(path: string) {  // BAD: path in Core
//   const content = fs.readFileSync(path);  // BAD: I/O in Core
//   return parseLines(content);
// }

// DO: Core receives content, not paths
// function parseContent(content: string) {  // GOOD: receives data
//   return parseLines(content);
// }


// DON'T: Throw exceptions in Shell
// async function loadConfig(path: string): Promise<Config> {  // BAD: no Result
//   return JSON.parse(await fs.readFile(path));  // Exceptions not handled
// }

// DO: Return Result<T, E>
// async function loadConfig(path: string): Promise<Result<Config, Error>> {
//   try {
//     const content = await fs.readFile(path, 'utf-8');
//     return ok(JSON.parse(content));
//   } catch (error) {
//     return err(error instanceof Error ? error : new Error(String(error)));
//   }
// }
