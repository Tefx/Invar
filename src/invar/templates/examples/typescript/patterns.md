# TypeScript Patterns for Agents

Reference patterns for AI agents working with TypeScript under Invar Protocol.

## Tool × Feature Matrix

| Feature | TypeScript Pattern | Tool Command |
|---------|-------------------|--------------|
| Signatures | `function name(params): Return` | `invar sig file.ts` |
| Contracts | `@pre`, `@post` JSDoc + Zod | `invar sig file.ts` |
| References | Cross-file symbol usage | `invar refs file.ts::Symbol` |
| Verification | tsc + eslint + vitest | `invar guard` |
| Document nav | Markdown structure | `invar doc toc file.md` |

---

## Pattern 1: Preconditions with Zod

```typescript
import { z } from 'zod';

// Schema IS the precondition
const UserInputSchema = z.object({
  email: z.string().email(),
  age: z.number().int().positive().max(150),
});

type UserInput = z.infer<typeof UserInputSchema>;

/**
 * Create a user with validated input.
 * @pre UserInputSchema.parse(input) succeeds
 * @post result.id is set
 */
function createUser(input: UserInput): User {
  // Zod already validated - safe to use
  return { id: generateId(), ...input };
}
```

**Agent workflow:**
1. Define Zod schema FIRST (the @pre)
2. Derive TypeScript type from schema
3. Implement function body
4. Zod validates at runtime

---

## Pattern 2: Postconditions

```typescript
/**
 * Calculate discount price.
 * @pre price > 0 && discount >= 0 && discount <= 1
 * @post result >= 0 && result <= price
 */
function applyDiscount(price: number, discount: number): number {
  const result = price * (1 - discount);

  // Postcondition check (development only)
  console.assert(result >= 0 && result <= price,
    `Postcondition failed: ${result}`);

  return result;
}
```

**Note:** Unlike Python's `@post` decorator, TypeScript postconditions
are documented in JSDoc and checked manually or via assertion.

---

## Pattern 3: Core/Shell Separation

```typescript
// ─── Core (Pure) ───
// No I/O, no side effects, only data transformations

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}

// ─── Shell (I/O) ───
// All external interactions, returns Result<T, E>

import { Result, ok, err } from 'neverthrow';

async function fetchUser(id: string): Promise<Result<User, ApiError>> {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) return err({ code: response.status });
    return ok(await response.json());
  } catch (e) {
    return err({ code: 500, message: String(e) });
  }
}
```

**Agent checklist:**
- [ ] Core functions: No imports from `fs`, `http`, `fetch`, etc.
- [ ] Shell functions: Return `Result<T, E>` for fallible operations
- [ ] Dependency injection: Pass data to Core, not paths

---

## Pattern 4: Exhaustive Switch

```typescript
type Status = 'pending' | 'approved' | 'rejected';

function getStatusMessage(status: Status): string {
  switch (status) {
    case 'pending': return 'Waiting for review';
    case 'approved': return 'Request approved';
    case 'rejected': return 'Request denied';
    default:
      // TypeScript ensures this is never reached
      const _exhaustive: never = status;
      throw new Error(`Unknown status: ${_exhaustive}`);
  }
}
```

**Why:** Adding a new status forces handling in all switches.

---

## Pattern 5: Branded Types

```typescript
// Nominal typing for semantic safety
type UserId = string & { readonly __brand: 'UserId' };
type OrderId = string & { readonly __brand: 'OrderId' };

function createUserId(id: string): UserId {
  return id as UserId;
}

// Compiler prevents mixing IDs
function getUser(id: UserId): User { ... }
function getOrder(id: OrderId): Order { ... }

getUser(orderId);  // ❌ Type error: OrderId is not UserId
```

---

## Tool Usage Examples

### View signatures

```bash
$ invar sig src/auth.ts
src/auth.ts
  function validateToken(token: string): boolean
    @pre token.length > 0
    @post result indicates valid JWT

  class AuthService
    method login(email: string, password: string): Promise<Result<Token, AuthError>>
    method logout(): Promise<void>
```

### Find references

```bash
$ invar refs src/auth.ts::validateToken
src/auth.ts:15 — Definition
src/routes/api.ts:42 — if (validateToken(req.headers.auth)) {
src/middleware/auth.ts:18 — const isValid = validateToken(token);
tests/auth.test.ts:8 — expect(validateToken('invalid')).toBe(false);
```

### Verify code

```bash
$ invar guard
TypeScript Guard Report
========================================
[PASS] tsc --noEmit (no type errors)
[PASS] eslint (0 errors, 2 warnings)
[PASS] vitest (24 tests passed)
----------------------------------------
Guard passed.
```

---

*Managed by Invar - regenerated on `invar update`*
