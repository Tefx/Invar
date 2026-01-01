# LX-09: Legacy Project Onboarding

**Status:** Implemented
**Priority:** Medium
**Category:** Language/Agent eXtensions
**Created:** 2026-01-01
**Updated:** 2026-01-02
**Depends on:** LX-05 (language-agnostic templates), LX-07 (extension skills architecture)

## Executive Summary

Provide a standardized workflow for onboarding existing (legacy) projects to the Invar framework via a single skill: `/invar-onboard`.

**Core Deliverables:**

| Component | Type | Purpose |
|-----------|------|---------|
| `/invar-onboard` | Skill | Complete onboarding workflow (Assess → Discuss → Plan) |
| Language adapters | Docs | Pattern libraries per language (Python, TypeScript, Go) |

**Key Design Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skill naming | `/invar-onboard` | Explicit Invar context, differentiates from general refactoring |
| Skill structure | Single skill with phases | Natural pause points for user discussion |
| Analysis depth | Deep only | Refactoring is major decision, needs accurate assessment |
| Auto-chaining | No | User must confirm after assessment before planning |
| History tracking | Git-based | Single file, rely on git history for comparisons |
| Security audit | Excluded | Use `/security` skill separately |

---

## Problem Statement

### Current State

When onboarding an existing project to Invar:

1. **Manual analysis** - No structured assessment methodology
2. **Ad-hoc planning** - Roadmaps created from scratch each time
3. **Knowledge loss** - Lessons learned not captured
4. **Inconsistent approach** - Different patterns across projects

### Example: paralex Assessment

Recent assessment of the paralex project (19k LOC TypeScript) was entirely manual:

```
- 2 hours: Code exploration
- 1 hour: Pattern identification
- 1 hour: Gap analysis
- 2 hours: Roadmap creation
- Total: ~6 hours of agent time
```

A structured skill could reduce this to ~1-2 hours.

---

## Relationship with LX-07 /refactor

**These are completely different concepts:**

| Aspect | LX-07 `/refactor` | LX-09 `/invar-onboard` |
|--------|-------------------|------------------------|
| Context | Already Invar project | Non-Invar (legacy) project |
| Goal | Improve code structure | Migrate to Invar framework |
| Scope | Single module/function | Entire project architecture |
| Frequency | Continuous improvement | One-time migration |
| Example | "Refactor this class" | "Can this project use Invar?" |

```
┌─────────────────────────────────────────────────────────┐
│  Non-Invar Project (Legacy)                             │
└─────────────────────────────────────────────────────────┘
                          │
                          │ /invar-onboard (LX-09)
                          │ (one-time migration)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Invar Project                                          │
│                                                         │
│   /develop ────────────────────────────────────────────▶│
│   /review  ◀────────────────────────────────────────────│
│   /refactor (LX-07) ◀──────────────────────────────────▶│
│   (continuous improvement)                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Design Principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | **Claude as parser** | No language-specific code needed |
| 2 | **Skill over CLI** | Leverage Claude's understanding |
| 3 | **Deep analysis only** | Refactoring is major decision, no quick scan |
| 4 | **Human checkpoint** | Pause after assessment for user confirmation |
| 5 | **Cross-project capable** | Can assess projects outside Invar directory |

---

## Architecture

### Skill Workflow

```
/invar-onboard [path]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: ASSESS (Automatic)                            │
│                                                         │
│  ├── Code metrics (LOC, files, complexity)              │
│  ├── Architecture pattern detection                     │
│  ├── Error handling analysis                            │
│  ├── Validation pattern detection                       │
│  ├── Core/Shell separation assessment                   │
│  ├── Risk identification                                │
│  └── Effort estimation                                  │
│                                                         │
│  Output: docs/invar-onboard-assessment.md               │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 2: DISCUSS (With User)                           │
│                                                         │
│  ├── Present assessment summary                         │
│  ├── Highlight key decision points                      │
│  ├── Discuss risk mitigation options                    │
│  ├── Confirm scope and priorities                       │
│  └── Get user approval to proceed                       │
│                                                         │
│  Gate: User must confirm to continue                    │
└─────────────────────────────────────────────────────────┘
         │
         ▼ (only if user confirms)
┌─────────────────────────────────────────────────────────┐
│  Phase 3: PLAN (Automatic)                              │
│                                                         │
│  ├── File dependency analysis                           │
│  ├── Phase decomposition (layers)                       │
│  ├── Per-file effort allocation                         │
│  ├── Agent session planning                             │
│  ├── Gate criteria definition                           │
│  └── Rollback strategy                                  │
│                                                         │
│  Output: docs/invar-onboard-roadmap.md                  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Execution (via /develop)                               │
│                                                         │
│  User executes roadmap phase-by-phase using /develop    │
│  Each phase verified with /review                       │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/invar/templates/skills/extensions/
└── invar-onboard/
    ├── SKILL.md                    # Skill instructions
    ├── patterns/                   # Language-specific patterns
    │   ├── python.md
    │   └── typescript.md
    └── templates/                  # Report templates
        ├── assessment.md.jinja
        └── roadmap.md.jinja

# After `invar skill add invar-onboard`:
.claude/skills/
└── invar-onboard/
    ├── SKILL.md
    ├── patterns/
    │   ├── python.md
    │   └── typescript.md
    └── templates/
        ├── assessment.md.jinja
        └── roadmap.md.jinja
```

---

## Skill Design: /invar-onboard

### Trigger

User wants to evaluate or migrate an existing project to Invar framework.

### Input

```
/invar-onboard [path]

path: Target project path (optional, defaults to current directory)
```

### Phase 1: ASSESS (Automatic)

Deep analysis of target project:

```
Step 1: Discovery
├── Glob scan for source files
├── Detect package.json / pyproject.toml / go.mod
├── Identify primary language and framework
└── Calculate code metrics (LOC, files)

Step 2: Architecture Analysis
├── Identify layering pattern (MVC, Clean, etc.)
├── Map module dependencies
├── Detect existing test framework
└── Identify entry points

Step 3: Pattern Detection
├── Error handling (throw / Result / error return)
├── Validation (Zod / Pydantic / manual)
├── Dependency injection
└── Logging/monitoring patterns

Step 4: Gap Analysis
├── Core/Shell separation status
├── Contract coverage estimation
├── Test coverage assessment
└── Documentation coverage

Step 5: Risk Assessment
├── Complexity hotspots
├── Dependency risks
├── Refactoring blockers
└── Regression risk areas

Step 6: Estimation
├── LOC per layer
├── Complexity factors
├── Risk buffer (×1.3-1.5)
└── Total effort estimate
```

**Output:** `docs/invar-onboard-assessment.md`

### Phase 2: DISCUSS (With User)

Present findings and gather user input:

```
1. Summary Display
   - Invar compatibility score (0-100%)
   - Estimated effort (days)
   - Risk level (Low/Medium/High)

2. Key Decision Points
   - Error handling strategy (Result vs throw)
   - Core extraction priority
   - Test coverage requirements

3. Risk Discussion
   - Identified blockers
   - Mitigation options
   - Scope adjustment suggestions

4. Confirmation
   - "Proceed to planning phase? [Y/n]"
   - Option to abort or adjust scope
```

**Gate:** User must explicitly confirm to proceed to Phase 3.

### Phase 3: PLAN (Automatic)

Generate detailed migration roadmap:

```
Step 1: Load Assessment
├── Read assessment report
├── Extract metrics and gaps
└── Apply user preferences from discussion

Step 2: Dependency Analysis
├── Map file dependencies
├── Determine refactoring order
└── Identify parallelization opportunities

Step 3: Phase Decomposition
├── Group by layer (Repository → Service → Actions)
├── Estimate per-file effort
└── Define Gate criteria for each phase

Step 4: Session Planning
├── Break into agent sessions (2-3 files each)
├── Allocate context checkpoints
└── Define verification points

Step 5: Risk Mitigation
├── Define rollback points
├── Identify verification gates
└── Plan E2E test checkpoints

Step 6: Generate Roadmap
└── Write docs/invar-onboard-roadmap.md
```

**Output:** `docs/invar-onboard-roadmap.md`

---

## Output: Assessment Report

```markdown
# Invar Onboarding Assessment

> Project: {project_name}
> Assessed: {timestamp}
> Invar Version: {invar_version}

## 1. Summary

| Metric | Value |
|--------|-------|
| Primary Language | {language} |
| Framework | {framework} |
| Code Size | {loc} lines / {files} files |
| Test Coverage | {test_type}: {test_count} tests |
| **Invar Compatibility** | **{compatibility}%** |
| **Estimated Effort** | **{total_days} days** |
| **Risk Level** | **{risk_level}** |

## 2. Architecture Analysis

### 2.1 Layer Structure

{architecture_diagram}

### 2.2 Dependency Map

{dependency_map}

## 3. Pattern Analysis

| Dimension | Current | Invar Target | Gap |
|-----------|---------|--------------|-----|
| Error Handling | {current_error} | Result<T,E> | {gap_error} |
| Validation | {current_validation} | @pre/@post / Zod | {gap_validation} |
| Core/Shell | {current_separation} | Explicit separation | {gap_separation} |
| Testing | {current_test} | Doctest + Property | {gap_test} |

## 4. Risk Assessment

### 4.1 High Risk Areas

{high_risk_areas}

### 4.2 Blockers

{blockers}

### 4.3 Dependency Risks

{dependency_risks}

## 5. Effort Breakdown

| Phase | Scope | Estimate |
|-------|-------|----------|
| Foundation | Error types, Result infrastructure | {phase1_days} days |
| Core Extraction | Pure function isolation | {phase2_days} days |
| Shell Refactor | I/O layer Result conversion | {phase3_days} days |
| Contracts | @pre/@post / Zod schemas | {phase4_days} days |
| Validation | Guard integration, test coverage | {phase5_days} days |
| **Total** | | **{total_days} days** |

### 5.1 Estimation Assumptions

- Complexity factor: {complexity_factor}
- Risk buffer: {risk_buffer}
- Daily output: {daily_loc} lines

## 6. Recommendations

### 6.1 Suggested Approach

{recommendation}

### 6.2 Prerequisites

- [ ] E2E test coverage > 80% for critical paths
- [ ] Result library installed (neverthrow / returns)
- [ ] Error type hierarchy defined

---

*Generated by /invar-onboard*
```

---

## Output: Migration Roadmap

Similar structure to the paralex roadmap:

- Phase breakdown with daily tasks
- Gate checklists per phase
- Agent session strategy
- Rollback points
- E2E verification checkpoints

---

## Language Adapters

> **Scope:** Python and TypeScript only (Go deferred)

Each adapter provides comprehensive patterns for migrating to Invar framework.

### Adapter Structure

```
.invar/templates/onboard-patterns/
├── python.md      (~200 lines)
└── typescript.md  (~250 lines)

Each adapter contains:
1. Overview (library, installation, concepts)
2. Error Handling (6 patterns)
3. Contracts (4 patterns)
4. Core/Shell Separation (directory + examples)
5. Framework Integration
6. Migration Checklist
7. Must Keep throw Scenarios
```

---

### Python Adapter (.invar/templates/onboard-patterns/python.md)

#### 1. Overview

```python
# Library: returns (dry-python)
# Install: pip install returns

from returns.result import Result, Success, Failure
from returns.io import IOResultE
from returns.future import FutureResultE
```

#### 2. Error Handling

##### 2.1 Basic Transformation

```python
# ❌ Before: raise
def get_user(id: str) -> User:
    user = db.find(id)
    if not user:
        raise NotFoundError(f"User {id} not found")
    return user

# ✅ After: Result
from returns.result import Result, Success, Failure

def get_user(id: str) -> Result[User, NotFoundError]:
    user = db.find(id)
    if not user:
        return Failure(NotFoundError(f"User {id} not found"))
    return Success(user)
```

##### 2.2 Async Handling

```python
from returns.future import FutureResultE
from returns.io import IOResultE

# Async I/O operations
async def get_user_async(id: str) -> FutureResultE[User, GetUserError]:
    """Use FutureResultE for async operations."""
    ...

# Sync I/O operations
def read_config() -> IOResultE[Config, ConfigError]:
    """Use IOResultE for sync I/O with Result."""
    ...
```

##### 2.3 Exception Catching (@safe)

```python
from returns.result import safe

@safe
def parse_json(data: str) -> dict:
    """Automatically converts exceptions to Failure.

    >>> parse_json('{"a": 1}').unwrap()
    {'a': 1}
    >>> parse_json('invalid').is_failure()
    True
    """
    return json.loads(data)  # JSONDecodeError → Failure
```

##### 2.4 Chaining (bind, map)

```python
def process_order(order_id: str) -> Result[Receipt, OrderError]:
    """Chain multiple Result operations."""
    return (
        get_order(order_id)          # Result[Order, NotFoundError]
        .bind(validate_order)        # → Result[Order, ValidationError]
        .map(calculate_total)        # → Result[float, ...] (pure transform)
        .bind(charge_payment)        # → Result[Payment, PaymentError]
        .map(generate_receipt)       # → Result[Receipt, ...]
    )
```

##### 2.5 Error Type Hierarchy

```python
from dataclasses import dataclass
from typing import Union

@dataclass
class DomainError:
    """Base error type."""
    message: str
    code: str

@dataclass
class NotFoundError(DomainError):
    entity: str
    id: str

@dataclass
class ValidationError(DomainError):
    field: str
    reason: str

# Union type for function signatures
OrderError = Union[NotFoundError, ValidationError, PaymentError]

def process(id: str) -> Result[Order, OrderError]:
    ...
```

##### 2.6 Combining Multiple Results

```python
from returns.result import Result
from returns.pointfree import bind
from returns.pipeline import flow

def validate_all(items: list[Item]) -> Result[list[Item], ValidationError]:
    """Collect all validation results."""
    results = [validate_item(item) for item in items]

    # Fail on first error
    for r in results:
        if r.is_failure():
            return r

    return Success([r.unwrap() for r in results])
```

#### 3. Contracts

##### 3.1 Input Validation (@pre)

```python
from invar import pre

@pre(lambda id: len(id) > 0 and len(id) <= 36)
@pre(lambda id: id.replace("-", "").isalnum())  # UUID format
def get_user(id: str) -> Result[User, NotFoundError]:
    """
    Get user by ID.

    >>> get_user("user-123").unwrap().name
    'Alice'
    >>> get_user("").is_failure()  # Precondition fails
    True
    """
    ...
```

##### 3.2 Pure Function Contracts

```python
from invar import pre, post

@pre(lambda amount, rate=0.1: amount > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """
    Calculate tax amount.

    >>> calculate_tax(100)
    10.0
    >>> calculate_tax(100, 0.2)
    20.0
    >>> calculate_tax(-100)  # Precondition fails
    Traceback (most recent call last):
        ...
    """
    return amount * rate
```

##### 3.3 Pydantic Integration

```python
from pydantic import BaseModel, field_validator

class CreateUserRequest(BaseModel):
    """Input validation via Pydantic."""
    email: str
    name: str

    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()

# Invar contract for business rules
@pre(lambda req: not user_exists(req.email))  # Business rule
def create_user(req: CreateUserRequest) -> Result[User, CreateUserError]:
    ...
```

#### 4. Core/Shell Separation

##### 4.1 Directory Structure

```
src/myapp/
├── core/                    # Pure functions, no I/O
│   ├── __init__.py
│   ├── order/
│   │   ├── validation.py    # @pre/@post + doctests
│   │   ├── calculation.py   # Pure calculations
│   │   └── types.py         # Domain types
│   └── user/
│       └── ...
└── shell/                   # I/O operations
    ├── __init__.py
    ├── repositories/        # Data access
    │   └── order_repo.py
    ├── services/            # Business orchestration
    │   └── order_service.py
    └── api/                 # HTTP layer
        └── routes.py
```

##### 4.2 Core Layer Example

```python
# core/order/validation.py
from invar import pre, post
from returns.result import Result, Success, Failure
from .types import Order, ValidationError

@pre(lambda order: len(order.items) > 0)
def validate_order(order: Order) -> Result[Order, ValidationError]:
    """
    Validate order business rules.

    >>> order = Order(items=[OrderItem(sku="A", qty=1)])
    >>> validate_order(order).is_success()
    True
    >>> validate_order(Order(items=[])).is_failure()
    True
    """
    for item in order.items:
        if item.qty <= 0:
            return Failure(ValidationError(field="qty", reason="must be positive"))
    return Success(order)

def calculate_total(order: Order) -> float:
    """
    Calculate order total (pure function).

    >>> order = Order(items=[OrderItem(sku="A", qty=2, price=10.0)])
    >>> calculate_total(order)
    20.0
    """
    return sum(item.qty * item.price for item in order.items)
```

##### 4.3 Shell Layer Example

```python
# shell/services/order_service.py
from returns.result import Result
from myapp.core.order.validation import validate_order, calculate_total
from myapp.shell.repositories.order_repo import OrderRepository

class OrderService:
    def __init__(self, repo: OrderRepository):
        self._repo = repo

    def process_order(self, order_id: str) -> Result[Receipt, OrderError]:
        """Orchestrate Core functions and I/O operations."""
        return (
            self._repo.find(order_id)           # Shell: I/O
            .bind(validate_order)               # Core: pure validation
            .map(calculate_total)               # Core: pure calculation
            .bind(lambda total:
                self._repo.save_total(order_id, total))  # Shell: I/O
        )
```

#### 5. FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from returns.result import Result

app = FastAPI()

def result_to_response(result: Result):
    """Convert Result to HTTP response."""
    if result.is_success():
        return result.unwrap()

    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message)
    elif isinstance(error, ValidationError):
        raise HTTPException(status_code=400, detail=error.message)
    else:
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str):
    result = user_service.get_user(user_id)
    return result_to_response(result)
```

#### 6. Must Keep raise Scenarios

```python
# 1. WSGI/ASGI error handlers (framework expects exceptions)
# 2. Click/Typer CLI (uses exceptions for flow control)
# 3. pytest fixtures (uses exceptions)
# 4. Context managers (__enter__/__exit__)
```

---

### TypeScript Adapter (.invar/templates/onboard-patterns/typescript.md)

#### 1. Overview

```typescript
// Library: neverthrow
// Install: npm install neverthrow

import { Result, ResultAsync, ok, err, okAsync, errAsync } from 'neverthrow';
```

#### 2. Error Handling

##### 2.1 Sync vs Async Result

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

##### 2.2 Basic Transformation

```typescript
// ❌ Before: throw
async function getUser(id: string): Promise<User> {
  const user = await db.user.findUnique({ where: { id } });
  if (!user) throw new NotFoundError(`User ${id} not found`);
  return user;
}

// ✅ After: ResultAsync
function getUser(id: string): ResultAsync<User, GetUserError> {
  return ResultAsync.fromPromise(
    db.user.findUnique({ where: { id } }),
    () => new DbError('query_failed')
  ).andThen(user =>
    user ? okAsync(user) : errAsync(new NotFoundError(`User ${id} not found`))
  );
}
```

##### 2.3 Chaining (andThen, map)

```typescript
function processOrder(orderId: string): ResultAsync<Receipt, OrderError> {
  return getOrder(orderId)                    // ResultAsync<Order, NotFoundError>
    .andThen(validateOrder)                   // → ResultAsync<Order, ValidationError>
    .map(calculateTotal)                      // → ResultAsync<number, ...>
    .andThen(chargePayment)                   // → ResultAsync<Payment, PaymentError>
    .map(generateReceipt);                    // → ResultAsync<Receipt, ...>
}
```

##### 2.4 Error Type Hierarchy (Discriminated Union)

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

##### 2.5 Safe Wrappers

```typescript
// Catch exceptions → Result
function safeJsonParse<T>(json: string): Result<T, ParseError> {
  return Result.fromThrowable(
    () => JSON.parse(json) as T,
    (e) => new ParseError('invalid_json', e)
  )();
}

// Wrap Promise → ResultAsync
function safeFetch<T>(url: string): ResultAsync<T, FetchError> {
  return ResultAsync.fromPromise(
    fetch(url).then(r => r.json()),
    (e) => new FetchError('fetch_failed', e)
  );
}
```

##### 2.6 Combining Multiple Results

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
// → Result<[string, string, number], ValidationError>
```

#### 3. Contracts (Zod)

##### 3.1 Schema Definition

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

##### 3.2 Zod + Result Integration

```typescript
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

##### 3.3 Branded Types

```typescript
// Type-safe IDs that can't be mixed up
const UserId = z.string().uuid().brand<'UserId'>();
type UserId = z.infer<typeof UserId>;

const OrderId = z.string().uuid().brand<'OrderId'>();
type OrderId = z.infer<typeof OrderId>;

function getUser(id: UserId): ResultAsync<User, UserError> { ... }
function getOrder(id: OrderId): ResultAsync<Order, OrderError> { ... }

// ❌ Compile error: OrderId cannot be assigned to UserId
// getUser(orderId);
```

##### 3.4 JSDoc Contracts

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

#### 4. Core/Shell Separation

##### 4.1 Directory Structure

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

##### 4.2 Core Layer Example

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

##### 4.3 Shell Layer Example

```typescript
// lib/services/order.service.ts
import { ResultAsync } from 'neverthrow';
import { validateOrder, calculateSubtotal } from '../core/order/validation';
import { OrderRepository } from '../repositories/order.repository';

export class OrderService {
  constructor(private readonly repo: OrderRepository) {}

  processOrder(orderId: string): ResultAsync<Receipt, OrderError> {
    return this.repo.findById(orderId)              // Shell: I/O
      .andThen(validateOrder)                       // Core: pure (sync→async)
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

#### 5. Next.js Integration

##### 5.1 Server Actions + Result

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

##### 5.2 React Hook

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

#### 6. Must Keep throw Scenarios

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

## Implementation Plan

### Phase 1: Templates ✅ COMPLETE

```
src/invar/templates/skills/extensions/invar-onboard/
├── patterns/
│   ├── python.md      # ~350 lines
│   └── typescript.md  # ~450 lines
└── templates/
    ├── assessment.md.jinja
    └── roadmap.md.jinja
```

### Phase 2: Skill ✅ COMPLETE

```
src/invar/templates/skills/extensions/invar-onboard/SKILL.md
```

Registered in `_registry.yaml`. Install via: `invar skill add invar-onboard`

### Phase 3: Validation (1-2 days)

- [ ] Test on paralex (TypeScript)
- [ ] Test on a Python project
- [ ] Iterate based on findings

### Phase 4: Documentation ✅ COMPLETE

- [x] Update proposal with learnings
- [x] Add to extension skill registry
- [x] Update directory structure documentation

**Total: 4-5 days** (increased due to comprehensive adapters)

---

## Cross-Project Invocation

```bash
# From Invar project, assess external project
/invar-onboard ../paralex

# From target project (if skill installed)
/invar-onboard .
```

Skill accepts path parameter, operates on specified directory.

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Total workflow time | < 1 hour (vs 6 hours manual) |
| Assessment completeness | All sections filled |
| Estimation accuracy | ±30% of actual effort |
| Language coverage | Python, TypeScript |

---

## Design Decisions Log

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Include security audit? | No | Use `/security` separately, single responsibility |
| 2 | Quick scan mode? | No | Deep only; refactoring is major decision |
| 3 | Auto-chain to planning? | No | User must confirm after assessment |
| 4 | History tracking? | Git | Single file, use git history for comparisons |
| 5 | Naming? | `/invar-onboard` | Explicit Invar + "onboard" = framework adoption |
| 6 | LX-07 relationship? | Independent | Different concepts entirely |

---

## Related Proposals

- [LX-05: Language-Agnostic Tooling](LX-05-lang-agnostic.md) - Skill templates
- [LX-07: Extension Skills](LX-07-extension-skills.md) - Extension architecture (note: `/refactor` there is different)
- [LX-08: Future Extensions](LX-08-extension-skills-future.md) - Deferred skills

---

## Appendix: Detection Patterns

### Error Handling

| Pattern | Regex |
|---------|-------|
| throw (JS/TS) | `throw new \w+Error` |
| raise (Python) | `raise \w+Error` |
| Result (Rust-style) | `Result<`, `Ok\(`, `Err\(` |
| neverthrow (TS) | `ok\(`, `err\(`, `ResultAsync` |
| returns (Python) | `Success\(`, `Failure\(`, `Result\[` |

### Validation

| Pattern | Detection |
|---------|-----------|
| Zod | `z.object`, `z.string`, `.safeParse` |
| Pydantic | `BaseModel`, `Field`, `validator` |
| Joi | `Joi.object`, `Joi.string` |
| Manual | `if (!x) throw`, `if x is None: raise` |

### Architecture

| Pattern | Detection |
|---------|-----------|
| MVC | `controllers/`, `models/`, `views/` |
| Clean | `domain/`, `application/`, `infrastructure/` |
| Layered | Repository, Service, Controller naming |

---

*Draft: 2026-01-01 | Updated with comprehensive Language Adapters (Python, TypeScript)*
