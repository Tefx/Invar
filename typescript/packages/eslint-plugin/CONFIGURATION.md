# @invar/eslint-plugin Configuration Guide

This guide explains how to configure and use the Invar ESLint rules for TypeScript projects following the Core/Shell architecture pattern.

## Table of Contents

- [Quick Start](#quick-start)
- [Preset Configurations](#preset-configurations)
- [Rule Reference](#rule-reference)
  - [Purity Checks](#purity-checks)
  - [Shell Architecture](#shell-architecture)
  - [Entry Point Architecture](#entry-point-architecture)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
npm install --save-dev @invar/eslint-plugin
# or
pnpm add -D @invar/eslint-plugin
```

### Basic Setup

```javascript
// eslint.config.js (ESLint 9+)
import invarPlugin from '@invar/eslint-plugin';

export default [
  {
    plugins: {
      '@invar': invarPlugin
    },
    rules: {
      ...invarPlugin.configs.recommended.rules
    }
  }
];
```

---

## Preset Configurations

### Recommended (Default)

Balanced enforcement for most projects. Warnings for architecture violations.

```javascript
export default [
  {
    plugins: { '@invar': invarPlugin },
    rules: {
      '@invar/no-runtime-imports': 'error',
      '@invar/no-impure-calls-in-core': 'error',
      '@invar/no-pure-logic-in-shell': 'warn',
      '@invar/shell-complexity': 'warn',
      '@invar/thin-entry-points': 'warn',
      // ... other rules
    }
  }
];
```

### Strict

Maximum enforcement for critical projects. All violations are errors.

```javascript
export default [
  {
    plugins: { '@invar': invarPlugin },
    rules: {
      '@invar/no-runtime-imports': 'error',
      '@invar/no-impure-calls-in-core': 'error',
      '@invar/no-pure-logic-in-shell': 'error',
      '@invar/shell-complexity': 'error',
      '@invar/thin-entry-points': 'error',
      // ... other rules
    }
  }
];
```

---

## Rule Reference

### Purity Checks

#### `@invar/no-runtime-imports`

**Purpose:** Prevent runtime imports (require/import inside functions) for better predictability.

**Default:** `error`

**Examples:**

```typescript
// ❌ BAD: Runtime import
function processData(x: number) {
  const { helper } = require('./helper');  // Error!
  return helper(x);
}

// ❌ BAD: Dynamic import in function
async function loadModule() {
  const mod = await import('./module');  // Error!
}

// ✅ GOOD: Top-level import
import { helper } from './helper';
function processData(x: number) {
  return helper(x);
}
```

**Why:** Runtime imports make code harder to analyze, break tree-shaking, and can cause unexpected side effects.

---

#### `@invar/no-impure-calls-in-core`

**Purpose:** Prevent Core modules from importing Shell modules to maintain purity.

**Default:** `error`

**Examples:**

```typescript
// src/core/calculator.ts
// ❌ BAD: Core importing from Shell
import { readConfig } from '../shell/config';  // Error!

function calculate(x: number) {
  const config = readConfig();  // Impure!
  return x * config.multiplier;
}

// ✅ GOOD: Accept config as parameter
function calculate(x: number, multiplier: number) {
  return x * multiplier;
}
```

**Path Detection:**
- Files in `/core/` directories cannot import from `/shell/` directories
- Patterns matched: `../shell/*`, `../../shell/*`, `shell/*`
- Works with both Unix and Windows paths

**Why:** Core should be pure logic with no I/O dependencies, making it easier to test and reason about.

---

### Shell Architecture

#### `@invar/no-pure-logic-in-shell`

**Purpose:** Warn when Shell functions contain pure logic that should be in Core.

**Default:** `warn` (recommended) / `error` (strict)

**Configuration:**

```javascript
// Default (no configuration needed)
'@invar/no-pure-logic-in-shell': 'warn'
```

**Examples:**

```typescript
// src/shell/processor.ts

// ❌ WARNING: Pure logic, move to Core
function calculateTotal(items: Item[]): number {
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  return a + b + c + d;  // No I/O, just math
}

// ✅ OK: Async function (I/O indicator)
async function fetchData() {
  const x = 1;
  const y = 2;
  return await fetch('/api/data');
}

// ✅ OK: Uses fs (I/O indicator)
function readConfig() {
  const data = fs.readFileSync('config.json');
  return JSON.parse(data);
}

// ✅ OK: Returns Result (I/O indicator)
function loadData(): Result<Data, Error> {
  const data = getDataFromDB();
  return Success(data);
}

// ✅ OK: Small helper (≤3 statements)
function helper() {
  const x = 1;
  return x;
}
```

**Detection Heuristics:**

Shell functions are flagged if they have:
1. No async/await
2. No I/O-related API calls (fs, fetch, db, etc.)
3. No Result type in the code
4. More than 3 statements

**I/O Indicators:**
- `fs`, `readFile`, `writeFile`, `fetch`, `axios`, `http`, `https`
- `db`, `database`, `query`, `execute`
- `Result`, `Success`, `Failure`
- `console`, `spawn`, `exec`, `child_process`
- `net`, `WebSocket`, `XMLHttpRequest`, `request`, `got`

**Why:** Shell should orchestrate I/O, not perform calculations. Pure logic in Core is easier to test.

---

#### `@invar/shell-complexity`

**Purpose:** Warn when Shell functions are too complex and should delegate to Core.

**Default:** `warn` (recommended) / `error` (strict)

**Configuration:**

```javascript
// Default thresholds
'@invar/shell-complexity': ['warn', {
  maxStatements: 20,     // Maximum statements in function body
  maxComplexity: 10      // Maximum cyclomatic complexity
}]

// Custom thresholds
'@invar/shell-complexity': ['warn', {
  maxStatements: 15,
  maxComplexity: 8
}]
```

**Examples:**

```typescript
// ❌ WARNING: Too many statements (>20)
function processOrder(orderId: string) {
  const order = await db.getOrder(orderId);
  const step1 = doStep1(order);
  const step2 = doStep2(step1);
  // ... 20+ statements
  await db.saveOrder(result);
}

// ❌ WARNING: Too complex (complexity >10)
function handleRequest(type: string) {
  if (a) return 1;
  else if (b) return 2;
  else if (c) return 3;
  // ... 10+ decision points
}

// ✅ GOOD: Simple orchestration
function processOrder(orderId: string) {
  const order = await db.getOrder(orderId);
  const result = processOrderLogic(order);  // Delegate to Core
  await db.saveOrder(result);
  return Success(result);
}
```

**Complexity Calculation (McCabe):**

Each of these adds +1 to complexity:
- `if`, `else if`, `for`, `while`, `do-while`
- `case` in switch (except `default`)
- `&&`, `||`, `??` operators
- `catch` clause
- `?` ternary operator

**Why:** Shell should be thin orchestration. Complex logic should be extracted to testable Core functions.

---

### Entry Point Architecture

#### `@invar/thin-entry-points`

**Purpose:** Enforce thin entry points (index/main/cli files should import/export, not implement).

**Default:** `warn` (recommended) / `error` (strict)

**Configuration:**

```javascript
// Default threshold
'@invar/thin-entry-points': ['warn', {
  maxStatements: 10  // Max non-import statements
}]

// Stricter for large projects
'@invar/thin-entry-points': ['warn', {
  maxStatements: 5
}]
```

**Entry Point Patterns:**

These files are checked:
- `index.{ts,js,tsx,jsx}`
- `main.{ts,js,tsx,jsx}`
- `cli.{ts,js,tsx,jsx}`
- `app.{ts,js,tsx,jsx}`
- `server.{ts,js,tsx,jsx}`

**Examples:**

```typescript
// ❌ BAD: Complex logic in entry point
// index.ts
export function handleCommand(args: Args) {
  const data = parseInput(args.input);
  const validated = validate(data);
  const processed = process(validated);
  const formatted = format(processed);
  console.log(formatted);
}

// ❌ BAD: Function definition in entry point
// main.ts
export function processData() {
  return 42;
}

// ❌ BAD: Class definition in entry point
// app.ts
export class App {
  run() { return 'running'; }
}

// ✅ GOOD: Just imports and exports
// index.ts
import { foo } from './foo';
import { bar } from './bar';
export { foo, bar };
export default foo;

// ✅ GOOD: Simple configuration
// main.ts
import express from 'express';
const app = express();
const PORT = 3000;
export { app, PORT };

// ✅ GOOD: Thin CLI handler
// cli.ts
import { processCommand } from './core/commands';
import { formatResult } from './shell/output';

export function handleCommand(args: Args) {
  const result = processCommand(args);  // Delegate!
  console.log(formatResult(result));
}
```

**What's Counted:**

Counted as statements:
- Function declarations
- Class declarations
- Complex variable declarations (function expressions, arrow functions)
- Control flow (if/for/while/try-catch)

Not counted:
- Import/export declarations without bodies
- Type aliases and interfaces
- Simple variable declarations (literals, identifiers)

**Why:** Entry points should be thin adapters. Logic should live in Core/Shell for testability.

---

## Common Patterns

### Pattern 1: Core with Shell Dependency

**Problem:** Core needs configuration loaded from file.

```typescript
// ❌ BAD: Core importing Shell
// src/core/calculator.ts
import { loadConfig } from '../shell/config';  // Error!

function calculate(x: number) {
  const config = loadConfig();
  return x * config.multiplier;
}
```

**Solution 1:** Dependency injection

```typescript
// ✅ GOOD: Accept config as parameter
// src/core/calculator.ts
export function calculate(x: number, multiplier: number) {
  return x * multiplier;
}

// src/shell/app.ts
import { calculate } from '../core/calculator';
import { loadConfig } from './config';

export function runCalculation(x: number): Result<number, Error> {
  const configResult = loadConfig();
  if (configResult.isFailure()) return configResult;

  const config = configResult.value;
  return Success(calculate(x, config.multiplier));
}
```

**Solution 2:** Shell wrapper

```typescript
// ✅ GOOD: Shell wraps Core
// src/core/calculator.ts
export function calculateWithMultiplier(x: number, multiplier: number) {
  return x * multiplier;
}

// src/shell/calculator.ts
import { calculateWithMultiplier } from '../core/calculator';
import { loadConfig } from './config';

export function calculate(x: number): Result<number, Error> {
  const configResult = loadConfig();
  if (configResult.isFailure()) return configResult;

  return Success(calculateWithMultiplier(x, configResult.value.multiplier));
}
```

---

### Pattern 2: Shell with Pure Logic

**Problem:** Shell function doing complex calculations.

```typescript
// ❌ WARNING: Pure logic in Shell
// src/shell/processor.ts
export async function processItems(path: string): Result<number, Error> {
  const items = await loadItems(path);  // I/O

  // Complex pure logic - should be in Core!
  const filtered = items.filter(i => i.active);
  const mapped = filtered.map(i => i.price * i.quantity);
  const total = mapped.reduce((sum, val) => sum + val, 0);
  const discounted = total * 0.9;
  const taxed = discounted * 1.1;

  return Success(taxed);
}
```

**Solution:** Extract pure logic to Core

```typescript
// ✅ GOOD: Pure logic in Core
// src/core/calculator.ts
export function calculateTotal(items: Item[]): number {
  const filtered = items.filter(i => i.active);
  const mapped = filtered.map(i => i.price * i.quantity);
  const total = mapped.reduce((sum, val) => sum + val, 0);
  const discounted = total * 0.9;
  const taxed = discounted * 1.1;
  return taxed;
}

// src/shell/processor.ts
import { calculateTotal } from '../core/calculator';

export async function processItems(path: string): Result<number, Error> {
  const itemsResult = await loadItems(path);  // I/O
  if (itemsResult.isFailure()) return itemsResult;

  const total = calculateTotal(itemsResult.value);  // Delegate to Core
  return Success(total);
}
```

---

### Pattern 3: Thick Entry Point

**Problem:** Entry point with business logic.

```typescript
// ❌ BAD: Thick entry point
// cli.ts
export async function handleUpload(args: UploadArgs) {
  // Validation
  if (!args.file) throw new Error('No file');
  if (!args.file.endsWith('.json')) throw new Error('Not JSON');

  // Reading
  const data = await fs.readFile(args.file, 'utf-8');
  const parsed = JSON.parse(data);

  // Processing
  const validated = validateSchema(parsed);
  const transformed = transformData(validated);

  // Uploading
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: JSON.stringify(transformed)
  });

  console.log('Uploaded:', response.status);
}
```

**Solution:** Thin entry point with delegation

```typescript
// ✅ GOOD: Thin entry point
// cli.ts
import { uploadFile } from './shell/uploader';
import { formatUploadResult } from './shell/output';

export async function handleUpload(args: UploadArgs) {
  const result = await uploadFile(args.file);
  console.log(formatUploadResult(result));
}

// shell/uploader.ts
import { validateUpload, transformUpload } from '../core/upload';

export async function uploadFile(filePath: string): Result<UploadResponse, Error> {
  // Validation
  const validationResult = validateUpload(filePath);
  if (validationResult.isFailure()) return validationResult;

  // I/O: Read file
  const readResult = await readJsonFile(filePath);
  if (readResult.isFailure()) return readResult;

  // Pure logic: Transform
  const transformed = transformUpload(readResult.value);

  // I/O: Upload
  return await postToAPI('/api/upload', transformed);
}
```

---

## Troubleshooting

### False Positives

#### "Pure logic in Shell" for legitimate I/O code

**Problem:** Function does I/O but isn't detected.

```typescript
// False positive - does I/O but not detected
function loadData() {
  const client = new DatabaseClient();  // I/O not detected
  const data = client.query('SELECT * FROM users');
  return data;
}
```

**Solution:** Add explicit I/O indicators

```typescript
// Option 1: Use async
async function loadData() {
  const client = new DatabaseClient();
  const data = await client.query('SELECT * FROM users');
  return data;
}

// Option 2: Return Result type
function loadData(): Result<User[], Error> {
  const client = new DatabaseClient();
  const data = client.query('SELECT * FROM users');
  return Success(data);
}

// Option 3: Use fs/fetch/db in variable names
function loadData() {
  const db = new DatabaseClient();  // 'db' is I/O indicator
  return db.query('SELECT * FROM users');
}
```

#### "Shell complexity" for unavoidable orchestration

**Problem:** Shell function coordinates many I/O steps.

```typescript
// Legitimate complexity - orchestrating many I/O operations
async function processOrder(orderId: string) {
  const order = await db.getOrder(orderId);
  const user = await db.getUser(order.userId);
  const inventory = await db.getInventory(order.itemId);
  const payment = await paymentAPI.charge(user, order.total);
  const shipment = await shippingAPI.ship(order, user.address);
  await db.updateOrder(orderId, { status: 'complete' });
  await emailAPI.sendConfirmation(user.email, order);
  return Success(order);
}
```

**Solution:** Increase threshold or disable for specific files

```javascript
// Increase threshold
'@invar/shell-complexity': ['warn', { maxStatements: 30 }]

// Or disable for specific patterns
{
  files: ['**/shell/orchestration/**'],
  rules: {
    '@invar/shell-complexity': 'off'
  }
}
```

---

### Rule Conflicts

#### Rule interaction with other plugins

Some rules may conflict with other ESLint plugins:

**TypeScript ESLint:**
```javascript
// Potential conflict: @typescript-eslint/no-var-requires
{
  rules: {
    '@invar/no-runtime-imports': 'error',
    '@typescript-eslint/no-var-requires': 'off'  // Covered by @invar rule
  }
}
```

**Import plugins:**
```javascript
// Potential conflict: import/no-dynamic-require
{
  rules: {
    '@invar/no-runtime-imports': 'error',
    'import/no-dynamic-require': 'off'  // Covered by @invar rule
  }
}
```

---

### Migration Guide

#### Migrating existing codebase

**Step 1:** Start with warnings only

```javascript
{
  rules: {
    '@invar/no-pure-logic-in-shell': 'warn',
    '@invar/shell-complexity': 'warn',
    '@invar/thin-entry-points': 'warn'
  }
}
```

**Step 2:** Fix critical violations first

```bash
# Show all violations
npx eslint . --rule '@invar/no-impure-calls-in-core: error'

# Fix automatically where possible
npx eslint . --fix
```

**Step 3:** Gradually increase strictness

```javascript
// Month 1: Warnings only
'@invar/no-pure-logic-in-shell': 'warn'

// Month 2: Error for new code
{
  files: ['src/**/*.new.ts'],
  rules: { '@invar/no-pure-logic-in-shell': 'error' }
}

// Month 3: Error for all
'@invar/no-pure-logic-in-shell': 'error'
```

---

## Support

- **Documentation:** [README.md](./README.md)
- **Issues:** [GitHub Issues](https://github.com/invar/typescript-tools/issues)
- **Proposal:** [LX-15: TypeScript Guard Parity](../../docs/proposals/LX-15-typescript-guard-parity.md)
