/**
 * Invar Functional Pattern Examples (DX-61) - TypeScript
 *
 * Reference patterns for higher-quality code. These are SUGGESTIONS, not requirements.
 * Guard will suggest them when it detects opportunities for improvement.
 *
 * Patterns covered:
 *   P0 (Core):
 *     1. Branded Types   - Semantic clarity for primitive types
 *     2. Validation      - Error accumulation instead of fail-fast
 *     3. NonEmpty        - Type-safe non-empty collections
 *     4. Literal         - Type-safe finite value sets
 *     5. ExhaustiveMatch - Catch missing cases at compile time
 *
 *   P1 (Extended):
 *     6. SmartConstructor - Validation at construction time
 *     7. StructuredError  - Typed errors for programmatic handling
 *
 * Managed by Invar - do not edit directly.
 */

import { z } from 'zod';
import { Result, ok, err } from 'neverthrow';

// =============================================================================
// Pattern 1: Branded Types for Semantic Clarity (P0)
// =============================================================================

// BEFORE: Easy to confuse parameters - all are just "string"
// function findSymbolBad(
//   modulePath: string,
//   symbolName: string,
//   filePattern: string,
// ): Symbol { ... }

// AFTER: Self-documenting, type-checker catches mistakes
// Using branded types (also called nominal types or opaque types)

declare const ModulePathBrand: unique symbol;
declare const SymbolNameBrand: unique symbol;
declare const FilePatternBrand: unique symbol;

type ModulePath = string & { readonly [ModulePathBrand]: typeof ModulePathBrand };
type SymbolName = string & { readonly [SymbolNameBrand]: typeof SymbolNameBrand };
type FilePattern = string & { readonly [FilePatternBrand]: typeof FilePatternBrand };

// Constructors for branded types
const ModulePath = (value: string): ModulePath => value as ModulePath;
const SymbolName = (value: string): SymbolName => value as SymbolName;
const FilePattern = (value: string): FilePattern => value as FilePattern;

interface Symbol {
  readonly name: string;
  readonly line: number;
}

/**
 * Find symbol by module path and name.
 *
 * With branded types, swapping arguments is a type error:
 * findSymbol(name, path)  // Type error!
 *
 * @example
 * findSymbol(ModulePath("src/core"), SymbolName("calculate"))
 * // => { name: 'calculate', line: 42 }
 */
export function findSymbol(path: ModulePath, name: SymbolName): Symbol {
  // Demo implementation
  return { name: name, line: 42 };
}

// =============================================================================
// Pattern 2: Validation for Error Accumulation (P0)
// =============================================================================

interface Config {
  readonly path: string;
  readonly maxLines: number;
  readonly enabled: boolean;
}

// BEFORE: User sees one error at a time
function validateConfigBad(data: unknown): Result<Config, string> {
  const obj = data as Record<string, unknown>;
  if (!('path' in obj)) {
    return err("Missing 'path'");
  }
  if (!('maxLines' in obj)) {
    return err("Missing 'maxLines'");  // Never reached if path missing
  }
  if (!('enabled' in obj)) {
    return err("Missing 'enabled'");
  }
  return ok(obj as unknown as Config);
}

// AFTER: User sees all errors at once
/**
 * Good: Accumulating validation.
 *
 * Collect all errors, return them together. User can fix everything
 * in one iteration. Much better UX!
 *
 * @example
 * validateConfigGood({})
 * // => Err(["Missing 'path'", "Missing 'maxLines'", "Missing 'enabled'"])
 *
 * @example
 * validateConfigGood({ path: "/tmp", maxLines: 100, enabled: true })
 * // => Ok({ path: '/tmp', maxLines: 100, enabled: true })
 */
export function validateConfigGood(
  data: unknown
): Result<Config, string[]> {
  const obj = data as Record<string, unknown>;
  const errors: string[] = [];

  // Collect ALL errors, don't return early
  if (!('path' in obj)) {
    errors.push("Missing 'path'");
  } else if (!obj.path) {
    errors.push("path cannot be empty");
  }

  if (!('maxLines' in obj)) {
    errors.push("Missing 'maxLines'");
  } else if (typeof obj.maxLines !== 'number') {
    errors.push("maxLines must be a number");
  } else if (obj.maxLines < 0) {
    errors.push("maxLines must be >= 0");
  }

  if (!('enabled' in obj)) {
    errors.push("Missing 'enabled'");
  }

  if (errors.length > 0) {
    return err(errors);
  }

  return ok({
    path: obj.path as string,
    maxLines: obj.maxLines as number,
    enabled: obj.enabled as boolean,
  });
}

// =============================================================================
// Pattern 3: NonEmpty for Type Safety (P0)
// =============================================================================

/**
 * Array guaranteed to have at least one element.
 *
 * Instead of runtime checks like `if (!items.length) throw`,
 * use the type system to guarantee non-emptiness.
 */
interface NonEmptyArray<T> {
  readonly head: T;
  readonly tail: readonly T[];
}

const NonEmptyArray = {
  /**
   * Safely construct from array.
   *
   * @example
   * NonEmptyArray.fromArray([])
   * // => Err('Cannot create NonEmptyArray from empty array')
   *
   * @example
   * NonEmptyArray.fromArray([1, 2, 3])
   * // => Ok({ head: 1, tail: [2, 3] })
   */
  fromArray<T>(items: readonly T[]): Result<NonEmptyArray<T>, string> {
    if (items.length === 0) {
      return err('Cannot create NonEmptyArray from empty array');
    }
    return ok({ head: items[0], tail: items.slice(1) });
  },

  /**
   * Get first element (always safe - guaranteed non-empty).
   */
  first<T>(ne: NonEmptyArray<T>): T {
    return ne.head;
  },

  /**
   * Get all elements.
   */
  toArray<T>(ne: NonEmptyArray<T>): readonly T[] {
    return [ne.head, ...ne.tail];
  },

  /**
   * Get length (always >= 1).
   */
  length<T>(ne: NonEmptyArray<T>): number {
    return 1 + ne.tail.length;
  },
};

// BEFORE: Defensive runtime check
function summarizeBad(items: string[]): string {
  if (items.length === 0) {
    throw new Error("Cannot summarize empty array");
  }
  return `First: ${items[0]}, Total: ${items.length}`;
}

// AFTER: Type-safe, no check needed
/**
 * Good: Type guarantees non-empty.
 *
 * No runtime check needed - if you have a NonEmptyArray,
 * it's guaranteed to have at least one element.
 *
 * @example
 * const ne = NonEmptyArray.fromArray(["a", "b", "c"]).unwrap();
 * summarizeGood(ne)
 * // => 'First: a, Total: 3'
 */
export function summarizeGood(items: NonEmptyArray<string>): string {
  return `First: ${NonEmptyArray.first(items)}, Total: ${NonEmptyArray.length(items)}`;
}

// =============================================================================
// Pattern 4: Literal Types for Finite Value Sets (P0)
// =============================================================================

// BEFORE: Runtime validation for finite set
function setLogLevelBad(level: string): void {
  if (!["debug", "info", "warning", "error"].includes(level)) {
    throw new Error(`Invalid log level: ${level}`);
  }
  // ... set the level
}

// AFTER: Compile-time safety with literal types
type LogLevel = "debug" | "info" | "warning" | "error";

/**
 * Good: Type checker catches invalid values.
 *
 * @example
 * setLogLevelGood("debug")
 * // => 'Log level set to: debug'
 *
 * // This would be a type error:
 * // setLogLevelGood("invalid")  // Error!
 */
export function setLogLevelGood(level: LogLevel): string {
  return `Log level set to: ${level}`;
}

// =============================================================================
// Pattern 5: Exhaustive Match (P0)
// =============================================================================

const Status = {
  PENDING: 'pending',
  RUNNING: 'running',
  DONE: 'done',
  FAILED: 'failed',
} as const;

type StatusType = typeof Status[keyof typeof Status];

// Helper for exhaustive matching
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

// BEFORE: Missing cases fail silently
function statusMessageBad(status: StatusType): string {
  switch (status) {
    case Status.PENDING:
      return "Waiting to start";
    case Status.RUNNING:
      return "In progress";
    // DONE and FAILED missing - falls through to default!
  }
  return "unknown";
}

// AFTER: Compiler catches missing cases
/**
 * Good: Exhaustive match with assertNever.
 *
 * If a new status is added, type checker reports an error
 * because assertNever expects type never, but gets the new status.
 *
 * @example
 * statusMessageGood(Status.PENDING)
 * // => 'Waiting to start'
 *
 * @example
 * statusMessageGood(Status.DONE)
 * // => 'Completed successfully'
 */
export function statusMessageGood(status: StatusType): string {
  switch (status) {
    case Status.PENDING:
      return "Waiting to start";
    case Status.RUNNING:
      return "In progress";
    case Status.DONE:
      return "Completed successfully";
    case Status.FAILED:
      return "Task failed";
    default:
      return assertNever(status);  // Type error if cases are missing!
  }
}

// =============================================================================
// Pattern 6: Smart Constructor with Zod (P1)
// =============================================================================

// BEFORE: Can create invalid objects
interface EmailBad {
  value: string;  // No validation, can be any string
}

// AFTER: Validation at construction with Zod
const EmailSchema = z.string()
  .min(1, "Email cannot be empty")
  .refine(s => s.includes("@"), "Email must contain @")
  .refine(
    s => s.includes("@") && s.split("@")[1].includes("."),
    "Email domain must have a dot"
  );

type EmailValue = z.infer<typeof EmailSchema>;

interface Email {
  readonly value: EmailValue;
}

const Email = {
  /**
   * Validate and construct email.
   *
   * Invalid emails can never exist - construction fails.
   *
   * @example
   * Email.create("user@example.com")
   * // => Ok({ value: 'user@example.com' })
   *
   * @example
   * Email.create("not-an-email")
   * // => Err('Email must contain @')
   */
  create(value: string): Result<Email, string> {
    const result = EmailSchema.safeParse(value);
    if (!result.success) {
      return err(result.error.errors[0].message);
    }
    return ok({ value: result.data });
  },
};

// =============================================================================
// Pattern 7: Structured Error (P1)
// =============================================================================

// BEFORE: String error messages with embedded data
function parseBad(text: string, line: number): Result<string, string> {
  if (!text) {
    return err(`Parse error at line ${line}: unexpected EOF`);
  }
  return ok(text);
}

// AFTER: Structured error type
interface ParseError {
  readonly message: string;
  readonly line: number;
  readonly column: number;
}

/**
 * Good: Structured error for programmatic handling.
 *
 * Code can extract line number for highlighting,
 * message for display, etc.
 *
 * @example
 * const result = parseGood("", 42);
 * if (result.isErr()) {
 *   result.error.line  // => 42
 *   result.error.message  // => 'unexpected EOF'
 * }
 *
 * @example
 * parseGood("valid", 1)
 * // => Ok('valid')
 */
export function parseGood(text: string, line: number): Result<string, ParseError> {
  if (!text) {
    return err({ message: "unexpected EOF", line, column: 0 });
  }
  return ok(text);
}

// =============================================================================
// Pattern 8: Promise → ResultAsync Conversion
// =============================================================================

import { ResultAsync } from 'neverthrow';

// BEFORE: Promise that throws
async function fetchUserBad(id: string): Promise<{ id: string; name: string }> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);  // Throws!
  }
  return response.json();
}

// AFTER: ResultAsync for typed errors
interface ApiError {
  readonly code: string;
  readonly message: string;
  readonly status?: number;
}

/**
 * Good: ResultAsync for async operations.
 *
 * Errors are typed and explicit, not thrown.
 *
 * @example
 * const result = await fetchUserGood("123");
 * if (result.isOk()) {
 *   console.log(result.value.name);
 * } else {
 *   console.error(result.error.message);
 * }
 */
function fetchUserGood(
  id: string
): ResultAsync<{ id: string; name: string }, ApiError> {
  return ResultAsync.fromPromise(
    fetch(`/api/users/${id}`).then(async (response) => {
      if (!response.ok) {
        throw { status: response.status };
      }
      return response.json();
    }),
    (error): ApiError => {
      const e = error as { status?: number };
      return {
        code: 'fetch_failed',
        message: `Failed to fetch user ${id}`,
        status: e.status,
      };
    }
  );
}

// =============================================================================
// Pattern 9: null/undefined → Result Conversion
// =============================================================================

// BEFORE: Returns null, caller must check
function findItemBad(
  items: readonly { id: string }[],
  id: string
): { id: string } | null {
  return items.find(item => item.id === id) ?? null;
}

// AFTER: Result with specific error
interface NotFoundError {
  readonly type: 'not_found';
  readonly id: string;
}

/**
 * Good: Result instead of null.
 *
 * @example
 * const result = findItemGood([{ id: "1" }], "1");
 * // => Ok({ id: "1" })
 *
 * @example
 * const result = findItemGood([{ id: "1" }], "2");
 * // => Err({ type: "not_found", id: "2" })
 */
export function findItemGood(
  items: readonly { id: string }[],
  id: string
): Result<{ id: string }, NotFoundError> {
  const item = items.find(i => i.id === id);
  if (!item) {
    return err({ type: 'not_found', id });
  }
  return ok(item);
}

// =============================================================================
// Pattern 10: ResultAsync Chaining
// =============================================================================

interface User {
  readonly id: string;
  readonly name: string;
  readonly profileId: string;
}

interface Profile {
  readonly id: string;
  readonly avatar: string;
}

// Mock async functions returning ResultAsync
function getUser(id: string): ResultAsync<User, ApiError> {
  return ResultAsync.fromPromise(
    Promise.resolve({ id, name: 'Demo', profileId: 'p1' }),
    (): ApiError => ({ code: 'user_error', message: 'Failed to get user' })
  );
}

function getProfile(id: string): ResultAsync<Profile, ApiError> {
  return ResultAsync.fromPromise(
    Promise.resolve({ id, avatar: '/avatar.png' }),
    (): ApiError => ({ code: 'profile_error', message: 'Failed to get profile' })
  );
}

/**
 * Good: ResultAsync chaining for sequential async operations.
 *
 * @example
 * const result = await getUserWithAvatar("123");
 * if (result.isOk()) {
 *   console.log(result.value);
 *   // => { userId: "123", userName: "Demo", avatar: "/avatar.png" }
 * }
 */
export function getUserWithAvatar(
  userId: string
): ResultAsync<{ userId: string; userName: string; avatar: string }, ApiError> {
  return getUser(userId).andThen((user) =>
    getProfile(user.profileId).map((profile) => ({
      userId: user.id,
      userName: user.name,
      avatar: profile.avatar,
    }))
  );
}

// =============================================================================
// Pattern 11: Combining Multiple ResultAsync
// =============================================================================

interface CombinedData {
  readonly user: User;
  readonly profile: Profile;
}

/**
 * Good: Parallel ResultAsync with combine.
 *
 * Both requests run in parallel, fails fast if either fails.
 *
 * @example
 * const result = await fetchUserAndProfile("u1", "p1");
 * if (result.isOk()) {
 *   const [user, profile] = result.value;
 * }
 */
export function fetchUserAndProfile(
  userId: string,
  profileId: string
): ResultAsync<[User, Profile], ApiError> {
  return ResultAsync.combine([
    getUser(userId),
    getProfile(profileId),
  ]);
}

// =============================================================================
// Summary: When to Use Each Pattern
// =============================================================================

// | Pattern           | Use When                                    |
// |-------------------|---------------------------------------------|
// | Branded Types     | 3+ params of same primitive type            |
// | Validation        | Multiple independent validations            |
// | NonEmptyArray     | Functions that require non-empty input      |
// | Literal Types     | Parameter with finite valid values          |
// | ExhaustiveMatch   | Matching on union types or const objects    |
// | SmartConstructor  | Types with invariants (use Zod)             |
// | StructuredError   | Errors with metadata (line, column, etc.)   |
// | Promise→ResultAsync| Async operations with typed errors         |
// | null→Result       | Functions returning null for "not found"    |
// | ResultAsync Chain | Sequential async with error propagation     |
// | ResultAsync.combine| Parallel async operations                  |
