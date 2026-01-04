# @invar/eslint-plugin - Usage Examples & Best Practices

Real-world examples showing how to use the Invar ESLint rules effectively.

## Table of Contents

- [Core/Shell Architecture Basics](#coreshell-architecture-basics)
- [Purity Checks Examples](#purity-checks-examples)
- [Shell Architecture Examples](#shell-architecture-examples)
- [Entry Point Examples](#entry-point-examples)
- [Real-World Refactoring](#real-world-refactoring)
- [Testing Patterns](#testing-patterns)

---

## Core/Shell Architecture Basics

### The Core/Shell Pattern

**Core** = Pure logic, no I/O
- Mathematical calculations
- Data transformations
- Business rule validation
- Algorithm implementations

**Shell** = I/O orchestration
- File system operations
- Network requests
- Database queries
- Console output

```
┌─────────────────────────────────────┐
│  Entry Points (index/main/cli)     │
│  - Thin adapters                   │
│  - Import/export only              │
└─────────────────┬───────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼─────┐    ┌──────▼────┐
    │  Shell   │───▶│   Core    │
    │  (I/O)   │    │  (Pure)   │
    └──────────┘    └───────────┘
```

**Rule:** Shell can import Core, but Core cannot import Shell.

---

## Purity Checks Examples

### `@invar/no-runtime-imports`

#### ❌ Anti-Pattern: Conditional Imports

```typescript
// conditional-loader.ts
function loadParser(format: string) {
  if (format === 'json') {
    const { parseJSON } = require('./json-parser');  // ❌ Runtime import!
    return parseJSON;
  } else {
    const { parseXML } = require('./xml-parser');    // ❌ Runtime import!
    return parseXML;
  }
}
```

#### ✅ Best Practice: Top-Level Imports with Strategy Pattern

```typescript
// parsers.ts
import { parseJSON } from './json-parser';
import { parseXML } from './xml-parser';

const PARSERS = {
  json: parseJSON,
  xml: parseXML,
} as const;

export function loadParser(format: keyof typeof PARSERS) {
  return PARSERS[format];
}
```

#### ❌ Anti-Pattern: Lazy Loading

```typescript
// plugin-loader.ts
let cachedPlugin: Plugin | null = null;

async function getPlugin() {
  if (!cachedPlugin) {
    const module = await import('./plugin');  // ❌ Dynamic import!
    cachedPlugin = module.default;
  }
  return cachedPlugin;
}
```

#### ✅ Best Practice: Explicit Dependency Injection

```typescript
// plugin-loader.ts
import defaultPlugin from './plugin';

export function createPluginLoader(plugin: Plugin = defaultPlugin) {
  return {
    getPlugin: () => plugin,
  };
}

// usage.ts
const loader = createPluginLoader();
const plugin = loader.getPlugin();
```

---

### `@invar/no-impure-calls-in-core`

#### ❌ Anti-Pattern: Core Reading Config Files

```typescript
// src/core/calculator.ts
import { readFileSync } from 'fs';  // ❌ I/O in Core!

export function calculateDiscount(price: number): number {
  const config = JSON.parse(
    readFileSync('config.json', 'utf-8')  // ❌ File I/O!
  );
  return price * config.discountRate;
}
```

#### ✅ Best Practice: Configuration as Parameter

```typescript
// src/core/calculator.ts
export interface DiscountConfig {
  discountRate: number;
}

export function calculateDiscount(
  price: number,
  config: DiscountConfig
): number {
  return price * config.discountRate;
}

// src/shell/discount.ts
import { calculateDiscount } from '../core/calculator';
import { loadConfig } from './config';

export function applyDiscount(price: number): Result<number, Error> {
  const configResult = loadConfig();
  if (configResult.isFailure()) return configResult;

  return Success(calculateDiscount(price, configResult.value));
}
```

#### ❌ Anti-Pattern: Core Calling API

```typescript
// src/core/validator.ts
import axios from 'axios';  // ❌ HTTP in Core!

export async function validateEmail(email: string): Promise<boolean> {
  const response = await axios.post('/api/validate', { email });  // ❌ API call!
  return response.data.valid;
}
```

#### ✅ Best Practice: Validation Service Pattern

```typescript
// src/core/validator.ts
export function isValidEmailFormat(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function validateEmailWithService(
  email: string,
  isEmailRegistered: (email: string) => boolean
): { valid: boolean; reason?: string } {
  if (!isValidEmailFormat(email)) {
    return { valid: false, reason: 'Invalid format' };
  }

  if (isEmailRegistered(email)) {
    return { valid: false, reason: 'Already registered' };
  }

  return { valid: true };
}

// src/shell/validator.ts
import { validateEmailWithService } from '../core/validator';
import { checkEmailInDatabase } from './database';

export async function validateEmail(email: string): Result<boolean, Error> {
  const dbCheck = await checkEmailInDatabase(email);
  if (dbCheck.isFailure()) return dbCheck;

  const result = validateEmailWithService(email, () => dbCheck.value);
  return Success(result.valid);
}
```

---

## Shell Architecture Examples

### `@invar/no-pure-logic-in-shell`

#### ❌ Anti-Pattern: Complex Calculations in Shell

```typescript
// src/shell/report-generator.ts
export async function generateReport(userId: string): Result<Report, Error> {
  const user = await db.getUser(userId);  // I/O

  // ❌ WARNING: Complex pure logic in Shell!
  const totalPurchases = user.orders.reduce((sum, order) => {
    const orderTotal = order.items.reduce((itemSum, item) => {
      return itemSum + (item.price * item.quantity);
    }, 0);
    const withTax = orderTotal * 1.1;
    const withShipping = withTax + (orderTotal > 100 ? 0 : 10);
    return sum + withShipping;
  }, 0);

  const averageOrderValue = totalPurchases / user.orders.length;
  const loyaltyTier = averageOrderValue > 500 ? 'gold' :
                      averageOrderValue > 200 ? 'silver' : 'bronze';

  await db.saveReport({ userId, totalPurchases, loyaltyTier });  // I/O
  return Success({ totalPurchases, loyaltyTier });
}
```

#### ✅ Best Practice: Extract Pure Logic to Core

```typescript
// src/core/report-calculator.ts
export interface Order {
  items: { price: number; quantity: number }[];
}

export interface User {
  orders: Order[];
}

export function calculateOrderTotal(order: Order): number {
  const itemTotal = order.items.reduce(
    (sum, item) => sum + (item.price * item.quantity),
    0
  );
  const withTax = itemTotal * 1.1;
  const withShipping = itemTotal > 100 ? withTax : withTax + 10;
  return withShipping;
}

export function calculateUserMetrics(user: User) {
  const totalPurchases = user.orders.reduce(
    (sum, order) => sum + calculateOrderTotal(order),
    0
  );

  const averageOrderValue = user.orders.length > 0
    ? totalPurchases / user.orders.length
    : 0;

  const loyaltyTier = averageOrderValue > 500 ? 'gold' :
                      averageOrderValue > 200 ? 'silver' : 'bronze';

  return { totalPurchases, averageOrderValue, loyaltyTier };
}

// src/shell/report-generator.ts
import { calculateUserMetrics } from '../core/report-calculator';

export async function generateReport(userId: string): Result<Report, Error> {
  // I/O: Load user
  const userResult = await db.getUser(userId);
  if (userResult.isFailure()) return userResult;

  // Pure: Calculate metrics (delegated to Core)
  const metrics = calculateUserMetrics(userResult.value);

  // I/O: Save report
  const saveResult = await db.saveReport({ userId, ...metrics });
  if (saveResult.isFailure()) return saveResult;

  return Success(metrics);
}
```

---

### `@invar/shell-complexity`

#### ❌ Anti-Pattern: God Function in Shell

```typescript
// src/shell/order-processor.ts
export async function processOrder(orderId: string): Result<Order, Error> {
  // ❌ WARNING: Too complex! (30+ statements, complexity 15)

  // Load data
  const order = await db.getOrder(orderId);
  const user = await db.getUser(order.userId);
  const inventory = await db.getInventory();

  // Validate
  if (!order) throw new Error('Order not found');
  if (!user) throw new Error('User not found');
  if (user.status === 'banned') throw new Error('User banned');

  // Check inventory
  for (const item of order.items) {
    const stock = inventory.find(i => i.id === item.id);
    if (!stock || stock.quantity < item.quantity) {
      throw new Error(`Insufficient stock for ${item.name}`);
    }
  }

  // Calculate totals
  let subtotal = 0;
  for (const item of order.items) {
    subtotal += item.price * item.quantity;
  }

  // Apply discounts
  let discount = 0;
  if (user.loyaltyPoints > 1000) discount = subtotal * 0.1;
  if (order.couponCode) {
    const coupon = await db.getCoupon(order.couponCode);
    if (coupon && coupon.valid) {
      discount += subtotal * coupon.rate;
    }
  }

  // Calculate tax and shipping
  const taxRate = await fetchTaxRate(user.address.state);
  const tax = (subtotal - discount) * taxRate;
  const shipping = subtotal > 100 ? 0 : 10;
  const total = subtotal - discount + tax + shipping;

  // Process payment
  const payment = await paymentAPI.charge(user, total);
  if (!payment.success) throw new Error('Payment failed');

  // Update inventory
  for (const item of order.items) {
    await db.updateInventory(item.id, -item.quantity);
  }

  // Create shipment
  const shipment = await shippingAPI.createShipment({
    orderId,
    items: order.items,
    address: user.address,
  });

  // Send notifications
  await emailAPI.sendOrderConfirmation(user.email, order);
  await smsAPI.sendShippingNotification(user.phone, shipment.trackingNumber);

  // Update order
  await db.updateOrder(orderId, {
    status: 'complete',
    total,
    paymentId: payment.id,
    shipmentId: shipment.id,
  });

  return Success(order);
}
```

#### ✅ Best Practice: Decompose into Smaller Functions

```typescript
// src/core/order-validation.ts
export function validateOrderRequest(
  order: Order,
  user: User,
  inventory: InventoryItem[]
): Result<void, string> {
  if (!order) return Failure('Order not found');
  if (!user) return Failure('User not found');
  if (user.status === 'banned') return Failure('User banned');

  for (const item of order.items) {
    const stock = inventory.find(i => i.id === item.id);
    if (!stock || stock.quantity < item.quantity) {
      return Failure(`Insufficient stock for ${item.name}`);
    }
  }

  return Success(undefined);
}

// src/core/order-calculator.ts
export function calculateOrderTotal(
  order: Order,
  discount: number,
  taxRate: number
): { subtotal: number; total: number; tax: number; shipping: number } {
  const subtotal = order.items.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  const discounted = subtotal - discount;
  const tax = discounted * taxRate;
  const shipping = subtotal > 100 ? 0 : 10;
  const total = discounted + tax + shipping;

  return { subtotal, total, tax, shipping };
}

// src/shell/order-processor.ts
export async function processOrder(orderId: string): Result<Order, Error> {
  // Step 1: Load data
  const dataResult = await loadOrderData(orderId);
  if (dataResult.isFailure()) return dataResult;
  const { order, user, inventory } = dataResult.value;

  // Step 2: Validate (Core logic)
  const validationResult = validateOrderRequest(order, user, inventory);
  if (validationResult.isFailure()) return validationResult;

  // Step 3: Calculate totals (Core logic)
  const pricing = await calculatePricing(order, user);
  if (pricing.isFailure()) return pricing;

  // Step 4: Process payment
  const paymentResult = await processPayment(user, pricing.value.total);
  if (paymentResult.isFailure()) return paymentResult;

  // Step 5: Fulfill order
  const fulfillmentResult = await fulfillOrder(order, user, paymentResult.value);
  if (fulfillmentResult.isFailure()) return fulfillmentResult;

  return Success(order);
}

// Each helper function is simple Shell orchestration (< 20 statements, complexity < 10)
async function loadOrderData(orderId: string) { /* ... */ }
async function calculatePricing(order: Order, user: User) { /* ... */ }
async function processPayment(user: User, total: number) { /* ... */ }
async function fulfillOrder(order: Order, user: User, payment: Payment) { /* ... */ }
```

---

## Entry Point Examples

### `@invar/thin-entry-points`

#### ❌ Anti-Pattern: Business Logic in CLI

```typescript
// cli.ts
import { program } from 'commander';
import * as fs from 'fs';
import axios from 'axios';

program
  .command('deploy')
  .action(async (options) => {
    // ❌ Complex logic in entry point!

    // Validation
    if (!options.config) {
      console.error('No config file specified');
      process.exit(1);
    }

    // Read config
    const configData = fs.readFileSync(options.config, 'utf-8');
    const config = JSON.parse(configData);

    // Validate schema
    if (!config.appName || !config.version) {
      console.error('Invalid config: missing appName or version');
      process.exit(1);
    }

    // Build package
    const packageData = {
      name: config.appName,
      version: config.version,
      files: fs.readdirSync('./dist'),
    };

    // Upload
    try {
      const response = await axios.post('/api/deploy', packageData);
      console.log(`Deployed ${config.appName}@${config.version}`);
      console.log(`URL: ${response.data.url}`);
    } catch (error) {
      console.error('Deployment failed:', error.message);
      process.exit(1);
    }
  });

program.parse();
```

#### ✅ Best Practice: Thin CLI Adapter

```typescript
// cli.ts
import { program } from 'commander';
import { deployApp } from './shell/deployer';
import { formatDeployResult } from './shell/formatters';

program
  .command('deploy')
  .option('-c, --config <path>', 'Config file path')
  .action(async (options) => {
    const result = await deployApp(options.config);

    if (result.isFailure()) {
      console.error(formatDeployResult(result));
      process.exit(1);
    }

    console.log(formatDeployResult(result));
  });

program.parse();

// src/core/deploy-validator.ts
export interface DeployConfig {
  appName: string;
  version: string;
}

export function validateDeployConfig(
  config: unknown
): Result<DeployConfig, string> {
  if (!config || typeof config !== 'object') {
    return Failure('Invalid config: not an object');
  }

  const c = config as Record<string, unknown>;

  if (!c.appName || typeof c.appName !== 'string') {
    return Failure('Invalid config: missing or invalid appName');
  }

  if (!c.version || typeof c.version !== 'string') {
    return Failure('Invalid config: missing or invalid version');
  }

  return Success({ appName: c.appName, version: c.version });
}

// src/shell/deployer.ts
import { validateDeployConfig } from '../core/deploy-validator';
import { readJsonFile } from './file-system';
import { uploadPackage } from './api-client';

export async function deployApp(configPath: string): Result<DeployInfo, Error> {
  // Load config
  const configResult = await readJsonFile(configPath);
  if (configResult.isFailure()) return configResult;

  // Validate config (Core logic)
  const validConfig = validateDeployConfig(configResult.value);
  if (validConfig.isFailure()) return validConfig;

  // Build package info
  const packageResult = await buildPackageInfo(validConfig.value);
  if (packageResult.isFailure()) return packageResult;

  // Upload
  return await uploadPackage(packageResult.value);
}
```

---

## Real-World Refactoring

### Example: E-commerce Checkout Flow

#### Before: Monolithic Shell with Mixed Concerns

```typescript
// checkout.ts (BEFORE)
export async function checkout(userId: string, cartId: string) {
  // Load data
  const user = await db.getUser(userId);
  const cart = await db.getCart(cartId);
  const settings = await db.getSettings();

  // Validation + calculation (mixed pure and I/O)
  if (cart.items.length === 0) throw new Error('Empty cart');

  let total = 0;
  for (const item of cart.items) {
    const product = await db.getProduct(item.productId);
    if (product.stock < item.quantity) {
      throw new Error(`Insufficient stock: ${product.name}`);
    }
    total += product.price * item.quantity;
  }

  // Apply promotions (pure logic in Shell)
  if (total > 100) total *= 0.9;  // 10% off
  if (user.isFirstOrder) total *= 0.95;  // 5% off first order

  // Tax calculation (pure logic)
  const taxRate = settings.taxRates[user.state];
  const tax = total * taxRate;
  const finalTotal = total + tax;

  // Payment
  const payment = await stripe.charge(user.paymentMethod, finalTotal);
  await db.saveOrder({ userId, cartId, total: finalTotal, paymentId: payment.id });

  return { total: finalTotal, orderId: payment.id };
}
```

**Issues:**
- ❌ Mixed pure logic and I/O
- ❌ Database calls inside loop
- ❌ No error handling with Result types
- ❌ Hard to test calculations
- ❌ High cyclomatic complexity

#### After: Clean Core/Shell Separation

```typescript
// src/core/checkout-calculator.ts
export interface CartItem {
  productId: string;
  quantity: number;
  price: number;
}

export interface CheckoutParams {
  items: CartItem[];
  isFirstOrder: boolean;
  taxRate: number;
}

export function calculateCheckoutTotal(params: CheckoutParams) {
  let subtotal = 0;
  for (const item of params.items) {
    subtotal += item.price * item.quantity;
  }

  // Apply promotions
  let discount = 0;
  if (subtotal > 100) discount += subtotal * 0.1;
  if (params.isFirstOrder) discount += subtotal * 0.05;

  const discounted = subtotal - discount;
  const tax = discounted * params.taxRate;
  const total = discounted + tax;

  return { subtotal, discount, tax, total };
}

export function validateCartItems(items: CartItem[]): Result<void, string> {
  if (items.length === 0) {
    return Failure('Cart is empty');
  }
  return Success(undefined);
}

// src/core/stock-validator.ts
export interface StockCheck {
  productId: string;
  requested: number;
  available: number;
}

export function validateStock(checks: StockCheck[]): Result<void, string> {
  for (const check of checks) {
    if (check.available < check.requested) {
      return Failure(`Insufficient stock for product ${check.productId}`);
    }
  }
  return Success(undefined);
}

// src/shell/checkout.ts
import { calculateCheckoutTotal, validateCartItems } from '../core/checkout-calculator';
import { validateStock } from '../core/stock-validator';

export async function checkout(
  userId: string,
  cartId: string
): Result<CheckoutResult, Error> {
  // 1. Load all data in parallel
  const [userResult, cartResult, settingsResult] = await Promise.all([
    db.getUser(userId),
    db.getCart(cartId),
    db.getSettings(),
  ]);

  if (userResult.isFailure()) return userResult;
  if (cartResult.isFailure()) return cartResult;
  if (settingsResult.isFailure()) return settingsResult;

  const user = userResult.value;
  const cart = cartResult.value;
  const settings = settingsResult.value;

  // 2. Validate cart (Core)
  const cartValidation = validateCartItems(cart.items);
  if (cartValidation.isFailure()) return cartValidation;

  // 3. Load products and check stock
  const stockValidation = await validateStockAvailability(cart.items);
  if (stockValidation.isFailure()) return stockValidation;

  // 4. Calculate totals (Core)
  const pricing = calculateCheckoutTotal({
    items: cart.items,
    isFirstOrder: user.isFirstOrder,
    taxRate: settings.taxRates[user.state],
  });

  // 5. Process payment
  const paymentResult = await stripe.charge(user.paymentMethod, pricing.total);
  if (paymentResult.isFailure()) return paymentResult;

  // 6. Save order
  const orderResult = await db.saveOrder({
    userId,
    cartId,
    total: pricing.total,
    paymentId: paymentResult.value.id,
  });

  if (orderResult.isFailure()) return orderResult;

  return Success({
    orderId: paymentResult.value.id,
    total: pricing.total,
  });
}

async function validateStockAvailability(
  items: CartItem[]
): Result<void, Error> {
  const products = await db.getProducts(items.map(i => i.productId));
  if (products.isFailure()) return products;

  const checks = items.map(item => ({
    productId: item.productId,
    requested: item.quantity,
    available: products.value.find(p => p.id === item.productId)?.stock ?? 0,
  }));

  return validateStock(checks);  // Core logic
}
```

**Benefits:**
- ✅ Pure logic in Core (easily testable)
- ✅ I/O in Shell only
- ✅ Result types for error handling
- ✅ Parallel data loading
- ✅ Clear separation of concerns
- ✅ Low complexity (each function < 20 statements)

---

## Testing Patterns

### Testing Core Functions (Pure Logic)

```typescript
// src/core/__tests__/checkout-calculator.test.ts
import { describe, it, expect } from 'vitest';
import { calculateCheckoutTotal } from '../checkout-calculator';

describe('calculateCheckoutTotal', () => {
  it('applies 10% discount for orders over $100', () => {
    const result = calculateCheckoutTotal({
      items: [{ productId: '1', quantity: 2, price: 60 }],
      isFirstOrder: false,
      taxRate: 0.1,
    });

    expect(result.subtotal).toBe(120);
    expect(result.discount).toBe(12);  // 10% of 120
    expect(result.total).toBe(118.8);  // (120 - 12) * 1.1
  });

  it('applies first order discount', () => {
    const result = calculateCheckoutTotal({
      items: [{ productId: '1', quantity: 1, price: 50 }],
      isFirstOrder: true,
      taxRate: 0.1,
    });

    expect(result.discount).toBe(2.5);  // 5% of 50
  });

  it('stacks discounts correctly', () => {
    const result = calculateCheckoutTotal({
      items: [{ productId: '1', quantity: 2, price: 60 }],
      isFirstOrder: true,
      taxRate: 0.1,
    });

    // Subtotal: 120
    // Discounts: 10% (12) + 5% (6) = 18
    expect(result.discount).toBe(18);
    expect(result.total).toBe(112.2);  // (120 - 18) * 1.1
  });
});
```

### Testing Shell Functions (Mocked I/O)

```typescript
// src/shell/__tests__/checkout.test.ts
import { describe, it, expect, vi } from 'vitest';
import { checkout } from '../checkout';
import * as db from '../database';
import * as stripe from '../stripe-client';

vi.mock('../database');
vi.mock('../stripe-client');

describe('checkout', () => {
  it('processes successful checkout', async () => {
    // Mock database calls
    vi.mocked(db.getUser).mockResolvedValue(Success({
      id: 'user1',
      isFirstOrder: false,
      state: 'CA',
      paymentMethod: 'pm_123',
    }));

    vi.mocked(db.getCart).mockResolvedValue(Success({
      id: 'cart1',
      items: [{ productId: 'prod1', quantity: 2, price: 60 }],
    }));

    vi.mocked(db.getSettings).mockResolvedValue(Success({
      taxRates: { CA: 0.1 },
    }));

    vi.mocked(db.getProducts).mockResolvedValue(Success([
      { id: 'prod1', stock: 10 },
    ]));

    // Mock payment
    vi.mocked(stripe.charge).mockResolvedValue(Success({
      id: 'pay_123',
      amount: 118.8,
    }));

    vi.mocked(db.saveOrder).mockResolvedValue(Success({ id: 'order_123' }));

    // Execute
    const result = await checkout('user1', 'cart1');

    // Verify
    expect(result.isSuccess()).toBe(true);
    expect(result.value.total).toBe(118.8);
    expect(db.saveOrder).toHaveBeenCalledWith({
      userId: 'user1',
      cartId: 'cart1',
      total: 118.8,
      paymentId: 'pay_123',
    });
  });

  it('fails on insufficient stock', async () => {
    vi.mocked(db.getUser).mockResolvedValue(Success({ /* ... */ }));
    vi.mocked(db.getCart).mockResolvedValue(Success({
      items: [{ productId: 'prod1', quantity: 10, price: 50 }],
    }));
    vi.mocked(db.getProducts).mockResolvedValue(Success([
      { id: 'prod1', stock: 5 },  // Only 5 available, need 10
    ]));

    const result = await checkout('user1', 'cart1');

    expect(result.isFailure()).toBe(true);
    expect(result.error).toContain('Insufficient stock');
    expect(stripe.charge).not.toHaveBeenCalled();  // Payment never attempted
  });
});
```

---

## Summary Checklist

When refactoring to follow Core/Shell pattern:

**Core Functions:**
- [ ] No `import` from Shell directories
- [ ] No I/O operations (fs, fetch, db, etc.)
- [ ] Accept data as parameters, not paths/URLs
- [ ] Return data, not `Result<T, E>`
- [ ] Easy to test with pure inputs/outputs

**Shell Functions:**
- [ ] No complex calculations (delegate to Core)
- [ ] Return `Result<T, E>` for all public functions
- [ ] Async where appropriate
- [ ] < 20 statements per function
- [ ] Cyclomatic complexity < 10

**Entry Points:**
- [ ] Import/export only
- [ ] Delegate to Shell/Core immediately
- [ ] < 10 non-import statements
- [ ] No function/class definitions

**Tests:**
- [ ] Core: Pure unit tests, no mocking
- [ ] Shell: Mocked I/O, integration tests
- [ ] Entry points: E2E tests if needed
