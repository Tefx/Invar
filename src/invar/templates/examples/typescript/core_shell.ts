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


// =============================================================================
// Next.js Integration Pattern
// =============================================================================
// Demonstrates how to use Result with Next.js API routes and Server Components.
// Shell (API handler) → Core (business logic) → Shell (HTTP response)

// NOTE: This is pseudocode - requires Next.js to be installed
// import { NextRequest, NextResponse } from 'next/server';
// import { ResultAsync } from 'neverthrow';

// -----------------------------------------------------------------------------
// Error Types
// -----------------------------------------------------------------------------

// interface ApiError {
//   readonly code: string;
//   readonly message: string;
//   readonly status: number;
// }
//
// const NotFoundError = (id: string): ApiError => ({
//   code: 'not_found',
//   message: `Resource ${id} not found`,
//   status: 404,
// });
//
// const ValidationError = (message: string): ApiError => ({
//   code: 'validation_error',
//   message,
//   status: 400,
// });
//
// const InternalError = (message: string): ApiError => ({
//   code: 'internal_error',
//   message,
//   status: 500,
// });

// -----------------------------------------------------------------------------
// CORE: Pure business logic (no Next.js imports)
// -----------------------------------------------------------------------------

// const UserSchema = z.object({
//   id: z.string().min(1),
//   name: z.string().min(1),
//   email: z.string().email(),
// });
//
// type User = z.infer<typeof UserSchema>;
//
// /**
//  * Core: Validate user data (pure, no I/O).
//  */
// function validateUserData(data: unknown): Result<User, string> {
//   const result = UserSchema.safeParse(data);
//   if (!result.success) {
//     return err(result.error.errors.map(e => e.message).join(', '));
//   }
//   return ok(result.data);
// }

// -----------------------------------------------------------------------------
// SHELL: Database I/O layer
// -----------------------------------------------------------------------------

// /**
//  * Shell: Fetch user from database.
//  */
// function fetchUserFromDb(id: string): ResultAsync<User, ApiError> {
//   return ResultAsync.fromPromise(
//     prisma.user.findUnique({ where: { id } }).then(user => {
//       if (!user) throw new Error('not_found');
//       return user;
//     }),
//     (error): ApiError => {
//       if (error instanceof Error && error.message === 'not_found') {
//         return NotFoundError(id);
//       }
//       return InternalError('Database error');
//     }
//   );
// }

// -----------------------------------------------------------------------------
// SHELL: Next.js API Route (App Router)
// -----------------------------------------------------------------------------

// /**
//  * Shell: API route handler.
//  *
//  * Pattern: Shell → Core → Shell
//  * 1. Shell receives HTTP request
//  * 2. Core validates/processes
//  * 3. Shell converts Result to HTTP response
//  */
// export async function GET(
//   request: NextRequest,
//   { params }: { params: { id: string } }
// ) {
//   const result = await fetchUserFromDb(params.id);
//
//   // Convert Result to NextResponse
//   return result.match(
//     (user) => NextResponse.json(user),
//     (error) => NextResponse.json(
//       { error: error.message },
//       { status: error.status }
//     )
//   );
// }
//
// export async function POST(request: NextRequest) {
//   const body = await request.json();
//
//   // Core: validate
//   const validationResult = validateUserData(body);
//   if (validationResult.isErr()) {
//     return NextResponse.json(
//       { error: validationResult.error },
//       { status: 400 }
//     );
//   }
//
//   // Shell: save to DB
//   const saveResult = await saveUserToDb(validationResult.value);
//
//   return saveResult.match(
//     (user) => NextResponse.json(user, { status: 201 }),
//     (error) => NextResponse.json(
//       { error: error.message },
//       { status: error.status }
//     )
//   );
// }

// -----------------------------------------------------------------------------
// SHELL: React Server Component
// -----------------------------------------------------------------------------

// /**
//  * Shell: Server Component with Result handling.
//  *
//  * Server Components can call Shell functions directly.
//  * Use .match() to handle success/error rendering.
//  */
// export async function UserProfile({ userId }: { userId: string }) {
//   const result = await fetchUserFromDb(userId);
//
//   return result.match(
//     (user) => (
//       <div>
//         <h1>{user.name}</h1>
//         <p>{user.email}</p>
//       </div>
//     ),
//     (error) => (
//       <div className="error">
//         {error.code === 'not_found'
//           ? <p>User not found</p>
//           : <p>Something went wrong</p>
//         }
//       </div>
//     )
//   );
// }

// =============================================================================
// Result → HTTP Response Mapping
// =============================================================================
// Common pattern for converting Result errors to HTTP status codes:
//
// | Error Type      | HTTP Status | When to Use                    |
// |-----------------|-------------|--------------------------------|
// | NotFoundError   | 404         | Resource doesn't exist         |
// | ValidationError | 400         | Invalid input from client      |
// | AuthError       | 401/403     | Authentication/authorization   |
// | ConflictError   | 409         | Resource state conflict        |
// | InternalError   | 500         | Unexpected server error        |
//
// Helper function:
// function resultToResponse<T>(
//   result: Result<T, ApiError>
// ): NextResponse {
//   return result.match(
//     (value) => NextResponse.json(value),
//     (error) => NextResponse.json(
//       { code: error.code, message: error.message },
//       { status: error.status }
//     )
//   );
// }
