# TypeScript Onboarding Patterns

> Patterns for migrating TypeScript projects to Invar framework.
> Library: `neverthrow`

## 1. Overview

```typescript
// Library: neverthrow
// Install: npm install neverthrow

import { Result, ResultAsync, ok, err, okAsync, errAsync } from 'neverthrow';
```

---

## 2. Error Handling

### 2.1 Sync vs Async Result

```typescript
import { Result, ResultAsync, ok, err, okAsync, errAsync } from 'neverthrow';

// Sync (Core layer)
function validateEmail(email: string): Result<string, ValidationError> {
  if (!email.includes('@')) {
    return err(new ValidationError('invalid_email'));
  }
  return ok(email);
}

// Async (Shell layer)
function sendEmail(to: string): ResultAsync<void, EmailError> {
  return ResultAsync.fromPromise(
    emailClient.send({ to }),
    (e) => new EmailError('send_failed', e)
  );
}
```

### 2.2 Basic Transformation

```typescript
// Before: throw
async function getUser(id: string): Promise<User> {
  const user = await db.user.findUnique({ where: { id } });
  if (!user) throw new NotFoundError(`User ${id} not found`);
  return user;
}

// After: ResultAsync
function getUser(id: string): ResultAsync<User, GetUserError> {
  return ResultAsync.fromPromise(
    db.user.findUnique({ where: { id } }),
    () => new DbError('query_failed')
  ).andThen(user =>
    user ? okAsync(user) : errAsync(new NotFoundError(`User ${id} not found`))
  );
}
```

### 2.3 Chaining (andThen, map)

```typescript
function processOrder(orderId: string): ResultAsync<Receipt, OrderError> {
  return getOrder(orderId)                    // ResultAsync<Order, NotFoundError>
    .andThen(validateOrder)                   // -> ResultAsync<Order, ValidationError>
    .map(calculateTotal)                      // -> ResultAsync<number, ...>
    .andThen(chargePayment)                   // -> ResultAsync<Payment, PaymentError>
    .map(generateReceipt);                    // -> ResultAsync<Receipt, ...>
}
```

### 2.4 Error Type Hierarchy (Discriminated Union)

```typescript
// Discriminated union for exhaustive checking
type OrderError =
  | { type: 'NOT_FOUND'; orderId: string }
  | { type: 'VALIDATION'; field: string; message: string }
  | { type: 'PAYMENT'; code: string; retry: boolean };

function handleOrderError(error: OrderError): Response {
  switch (error.type) {
    case 'NOT_FOUND':
      return notFound(`Order ${error.orderId} not found`);
    case 'VALIDATION':
      return badRequest(`${error.field}: ${error.message}`);
    case 'PAYMENT':
      return error.retry
        ? serviceUnavailable('Payment failed, please retry')
        : badRequest(`Payment error: ${error.code}`);
  }
}
```

### 2.5 Safe Wrappers

```typescript
// Catch exceptions -> Result
function safeJsonParse<T>(json: string): Result<T, ParseError> {
  return Result.fromThrowable(
    () => JSON.parse(json) as T,
    (e) => new ParseError('invalid_json', e)
  )();
}

// Wrap Promise -> ResultAsync
function safeFetch<T>(url: string): ResultAsync<T, FetchError> {
  return ResultAsync.fromPromise(
    fetch(url).then(r => r.json()),
    (e) => new FetchError('fetch_failed', e)
  );
}
```

### 2.6 Combining Multiple Results

```typescript
import { Result, ResultAsync } from 'neverthrow';

// Combine array of Results
function validateOrderItems(items: OrderItem[]): Result<OrderItem[], ValidationError[]> {
  const results = items.map(validateItem);
  return Result.combineWithAllErrors(results);  // Collect all errors
}

// Combine multiple independent Results
const combined = Result.combine([
  validateName(name),
  validateEmail(email),
  validateAge(age),
]);
// -> Result<[string, string, number], ValidationError>
```

---

## 3. Contracts (Zod)

### 3.1 Schema Definition

```typescript
import { z } from 'zod';

// Basic schemas
const UserIdSchema = z.string()
  .min(1, 'ID is required')
  .max(36, 'ID too long')
  .regex(/^[a-zA-Z0-9-]+$/, 'Invalid ID format');

const EmailSchema = z.string()
  .email('Invalid email format')
  .transform(s => s.toLowerCase());

// Composite schema
const CreateUserSchema = z.object({
  email: EmailSchema,
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'guest']).default('user'),
});

// Schema with refinement
const OrderSchema = z.object({
  items: z.array(z.object({
    sku: z.string(),
    qty: z.number().int().positive(),
    price: z.number().positive(),
  })).min(1, 'Order must have at least one item'),
}).refine(
  (order) => order.items.reduce((sum, i) => sum + i.qty, 0) <= 100,
  { message: 'Order cannot exceed 100 items total' }
);
```

### 3.2 Zod + Result Integration

```typescript
import { z } from 'zod';
import { Result, ok, err } from 'neverthrow';

type ValidationError = {
  type: 'VALIDATION';
  issues: z.ZodIssue[];
};

function validate<T>(schema: z.ZodSchema<T>, data: unknown): Result<T, ValidationError> {
  const result = schema.safeParse(data);
  if (result.success) {
    return ok(result.data);
  }
  return err({ type: 'VALIDATION', issues: result.error.issues });
}

// Usage
function createUser(input: unknown): ResultAsync<User, CreateUserError> {
  return validate(CreateUserSchema, input)
    .asyncAndThen(validated =>
      checkEmailUnique(validated.email)
        .map(() => validated)
    )
    .andThen(saveUser);
}
```

### 3.3 Branded Types

```typescript
import { z } from 'zod';
import { ResultAsync } from 'neverthrow';

// Type-safe IDs that can't be mixed up
const UserId = z.string().uuid().brand<'UserId'>();
type UserId = z.infer<typeof UserId>;

const OrderId = z.string().uuid().brand<'OrderId'>();
type OrderId = z.infer<typeof OrderId>;

function getUser(id: UserId): ResultAsync<User, UserError> { ... }
function getOrder(id: OrderId): ResultAsync<Order, OrderError> { ... }

// Compile error: OrderId cannot be assigned to UserId
// getUser(orderId);
```

### 3.4 JSDoc Contracts

```typescript
/**
 * Calculate order total with tax.
 *
 * @pre items.length > 0
 * @pre taxRate >= 0 && taxRate <= 1
 * @post result >= 0
 *
 * @example
 * ```ts
 * const total = calculateTotal([{price: 100, qty: 2}], 0.1);
 * assert(total === 220); // 200 + 20 tax
 * ```
 */
function calculateTotal(items: OrderItem[], taxRate: number): number {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  return subtotal * (1 + taxRate);
}
```

---

## 4. Core/Shell Separation

### 4.1 Directory Structure

```
lib/
├── core/                    # Pure functions, sync preferred
│   ├── order/
│   │   ├── validation.ts    # Zod schemas + pure validation
│   │   ├── calculation.ts   # Pure calculations
│   │   └── types.ts         # Domain types
│   └── user/
│       └── ...
├── services/                # Shell: I/O orchestration
│   ├── order.service.ts
│   └── user.service.ts
├── repositories/            # Shell: Data access
│   ├── order.repository.ts
│   └── user.repository.ts
└── errors/                  # Error type definitions
    └── index.ts
```

### 4.2 Core Layer Example

```typescript
// lib/core/order/validation.ts
import { z } from 'zod';
import { Result, ok, err } from 'neverthrow';

export const OrderItemSchema = z.object({
  sku: z.string().min(1),
  qty: z.number().int().positive(),
  price: z.number().positive(),
});

export type OrderItem = z.infer<typeof OrderItemSchema>;

// Pure validation (sync Result)
export function validateOrder(order: unknown): Result<Order, ValidationError> {
  const result = OrderSchema.safeParse(order);
  if (!result.success) {
    return err({ type: 'VALIDATION', issues: result.error.issues });
  }
  return ok(result.data);
}

// Pure calculation
export function calculateSubtotal(items: OrderItem[]): number {
  return items.reduce((sum, item) => sum + item.qty * item.price, 0);
}

export function applyDiscount(amount: number, rate: number): number {
  return amount * (1 - rate);
}
```

### 4.3 Shell Layer Example

```typescript
// lib/services/order.service.ts
import { ResultAsync } from 'neverthrow';
import { validateOrder, calculateSubtotal } from '../core/order/validation';
import { OrderRepository } from '../repositories/order.repository';

export class OrderService {
  constructor(private readonly repo: OrderRepository) {}

  processOrder(orderId: string): ResultAsync<Receipt, OrderError> {
    return this.repo.findById(orderId)              // Shell: I/O
      .andThen(validateOrder)                       // Core: pure (sync->async)
      .map(order => ({                              // Core: pure transform
        order,
        subtotal: calculateSubtotal(order.items),
      }))
      .andThen(({ order, subtotal }) =>
        this.getDiscount(order.id)
          .map(discount => applyDiscount(subtotal, discount))
      )
      .andThen(total => this.chargePayment(total))  // Shell: I/O
      .map(this.generateReceipt);                   // Core: pure
  }
}
```

---

## 5. Next.js Integration

### 5.1 Server Actions + Result

```typescript
// app/actions/order.ts
'use server';

import { ResultAsync } from 'neverthrow';
import { orderService } from '@/lib/services';

type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: { type: string; message: string } };

export async function createOrder(formData: FormData): Promise<ActionResult<Order>> {
  const input = Object.fromEntries(formData);
  const result = await orderService.createOrder(input);

  return result.match(
    (order) => ({ success: true, data: order }),
    (error) => ({
      success: false,
      error: { type: error.type, message: formatError(error) }
    })
  );
}
```

### 5.2 React Hook

```typescript
// hooks/useAction.ts
import { useState, useCallback } from 'react';

export function useAction<TInput, TOutput>(
  action: (input: TInput) => Promise<ActionResult<TOutput>>
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TOutput | null>(null);

  const execute = useCallback(async (input: TInput) => {
    setIsLoading(true);
    setError(null);

    const result = await action(input);

    if (result.success) {
      setData(result.data);
    } else {
      setError(result.error.message);
    }

    setIsLoading(false);
    return result;
  }, [action]);

  return { execute, isLoading, error, data };
}
```

---

## 6. Must Keep `throw` Scenarios

```typescript
// 1. React Error Boundary (must throw)
async function OrderDetails({ id }: { id: string }) {
  const result = await orderService.getOrder(id);
  if (result.isErr()) {
    throw new Error(result.error.message);  // Let ErrorBoundary catch
  }
  return <OrderView order={result.value} />;
}

// 2. Next.js redirect/notFound (must throw)
import { redirect, notFound } from 'next/navigation';

export default async function OrderPage({ params }: { params: { id: string } }) {
  const result = await orderService.getOrder(params.id);

  if (result.isErr()) {
    if (result.error.type === 'NOT_FOUND') {
      notFound();  // throws internally
    }
    if (result.error.type === 'UNAUTHORIZED') {
      redirect('/login');  // throws internally
    }
    throw new Error(result.error.message);
  }

  return <OrderDetails order={result.value} />;
}

// 3. Constructors (cannot return Result)
// 4. Top-level try-catch in entry points
```

---

## 7. Migration Checklist

- [ ] Install `neverthrow` library: `npm install neverthrow`
- [ ] Install `zod` for validation: `npm install zod`
- [ ] Define error type hierarchy (discriminated unions)
- [ ] Transform entry points to return `ResultAsync<T, E>`
- [ ] Extract pure functions to `lib/core/` directory
- [ ] Add Zod schemas for Core validation
- [ ] Add JSDoc `@pre/@post` comments to Core functions
- [ ] Run TypeScript compiler in strict mode
- [ ] Update API handlers to use `result.match()`

---

*Pattern Library v1.0 — LX-09*
