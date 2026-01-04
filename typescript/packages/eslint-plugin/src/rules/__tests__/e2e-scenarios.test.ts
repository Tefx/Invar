/**
 * E2E Scenario Tests for Invar ESLint Rules
 *
 * These tests simulate real-world usage patterns by creating
 * complete code scenarios rather than isolated snippets.
 *
 * Unlike unit tests (behavior.test.ts), these tests:
 * - Use realistic file structures
 * - Test multiple rules together
 * - Simulate actual agent development patterns
 * - Verify cross-file interactions
 */

import { RuleTester } from 'eslint';
import { noRuntimeImports } from '../no-runtime-imports';
import { noImpureCallsInCore } from '../no-impure-calls-in-core';
import { noPureLogicInShell } from '../no-pure-logic-in-shell';
import { shellComplexity } from '../shell-complexity';
import { thinEntryPoints } from '../thin-entry-points';

const ruleTester = new RuleTester({
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
});

describe('E2E Scenario 1: Core/Shell Separation Violation', () => {
  /**
   * Scenario: Developer creates a Core calculator that reads config from file
   * Expected: Should detect Core importing from Shell and suggest refactoring
   */

  it('should detect Core importing Shell config reader', () => {
    const coreCalculatorCode = `
      // src/core/calculator.ts
      import { loadConfig } from '../shell/config-loader';

      export function calculateDiscount(price: number): number {
        const config = loadConfig();
        return price * config.discountRate;
      }
    `;

    ruleTester.run('no-impure-calls-in-core', noImpureCallsInCore, {
      valid: [],
      invalid: [{
        code: coreCalculatorCode,
        filename: '/project/src/core/calculator.ts',
        errors: [{
          messageId: 'shellImportInCore',
          data: { source: '../shell/config-loader' },
        }],
      }],
    });
  });

  it('should allow refactored version with dependency injection', () => {
    const refactoredCoreCode = `
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
    `;

    ruleTester.run('no-impure-calls-in-core', noImpureCallsInCore, {
      valid: [{
        code: refactoredCoreCode,
        filename: '/project/src/core/calculator.ts',
      }],
      invalid: [],
    });
  });
});

describe('E2E Scenario 2: Shell with Complex Business Logic', () => {
  /**
   * Scenario: Developer writes order processing in Shell with complex calculations
   * Expected: Should warn about pure logic in Shell and high complexity
   */

  it('should detect complex pure logic in Shell function', () => {
    const shellOrderProcessorCode = `
      // src/shell/order-processor.ts
      export async function processOrder(orderId: string) {
        const order = await db.getOrder(orderId);

        // Complex calculation logic (should be in Core)
        const subtotal = order.items.reduce((sum, item) => {
          return sum + (item.price * item.quantity);
        }, 0);

        const discount = subtotal > 100 ? subtotal * 0.1 : 0;
        const tax = (subtotal - discount) * 0.08;
        const shipping = subtotal > 50 ? 0 : 10;
        const total = subtotal - discount + tax + shipping;

        await db.saveOrder({ ...order, total });
        return total;
      }
    `;

    // Note: This might not trigger no-pure-logic-in-shell due to async and db calls
    // But should trigger shell-complexity due to many statements
    ruleTester.run('shell-complexity', shellComplexity, {
      valid: [],
      invalid: [{
        code: shellOrderProcessorCode,
        filename: '/project/src/shell/order-processor.ts',
        errors: [{
          messageId: 'tooManyStatements',
        }],
      }],
    });
  });

  it('should allow refactored version with logic extracted to Core', () => {
    const refactoredShellCode = `
      // src/shell/order-processor.ts
      import { calculateOrderTotal } from '../core/order-calculator';

      export async function processOrder(orderId: string) {
        const order = await db.getOrder(orderId);
        const total = calculateOrderTotal(order);
        await db.saveOrder({ ...order, total });
        return total;
      }
    `;

    ruleTester.run('shell-complexity', shellComplexity, {
      valid: [{
        code: refactoredShellCode,
        filename: '/project/src/shell/order-processor.ts',
      }],
      invalid: [],
    });
  });
});

describe('E2E Scenario 3: Thick Entry Point with Business Logic', () => {
  /**
   * Scenario: Developer implements CLI command with validation and processing
   * Expected: Should detect complex logic in entry point
   */

  it('should detect thick CLI handler with business logic', () => {
    const thickCliCode = `
      // cli.ts
      import * as fs from 'fs';

      export function handleDeploy(configPath: string) {
        // Validation logic
        if (!configPath) {
          throw new Error('Config path required');
        }

        if (!configPath.endsWith('.json')) {
          throw new Error('Config must be JSON');
        }

        // File I/O
        const configData = fs.readFileSync(configPath, 'utf-8');
        const config = JSON.parse(configData);

        // Validation logic
        if (!config.appName || !config.version) {
          throw new Error('Invalid config');
        }

        // Processing logic
        const deployInfo = {
          name: config.appName,
          version: config.version,
          timestamp: Date.now(),
        };

        console.log('Deploying:', deployInfo);
      }
    `;

    ruleTester.run('thin-entry-points', thinEntryPoints, {
      valid: [],
      invalid: [{
        code: thickCliCode,
        filename: '/project/cli.ts',
        errors: [
          { messageId: 'hasComplexLogic' },  // if statements
          { messageId: 'tooMuchLogic' },     // too many statements
        ],
      }],
    });
  });

  it('should allow thin CLI handler that delegates to Shell', () => {
    const thinCliCode = `
      // cli.ts
      import { deployApp } from './shell/deployer';

      export async function handleDeploy(configPath: string) {
        const result = await deployApp(configPath);
        console.log(result.success ? 'Deployed' : 'Failed');
      }
    `;

    ruleTester.run('thin-entry-points', thinEntryPoints, {
      valid: [{
        code: thinCliCode,
        filename: '/project/cli.ts',
      }],
      invalid: [],
    });
  });
});

describe('E2E Scenario 4: Runtime Import for Conditional Logic', () => {
  /**
   * Scenario: Developer uses dynamic import for conditional module loading
   * Expected: Should detect runtime import and suggest top-level import
   */

  it('should detect conditional require() in function', () => {
    const conditionalRequireCode = `
      // src/core/parser.ts
      export function parseData(format: string, data: string) {
        if (format === 'json') {
          const { parseJSON } = require('./json-parser');
          return parseJSON(data);
        } else {
          const { parseXML } = require('./xml-parser');
          return parseXML(data);
        }
      }
    `;

    ruleTester.run('no-runtime-imports', noRuntimeImports, {
      valid: [],
      invalid: [{
        code: conditionalRequireCode,
        filename: '/project/src/core/parser.ts',
        errors: [
          { messageId: 'runtimeRequire' },
          { messageId: 'runtimeRequire' },
        ],
      }],
    });
  });

  it('should allow refactored version with strategy pattern', () => {
    const refactoredParserCode = `
      // src/core/parser.ts
      import { parseJSON } from './json-parser';
      import { parseXML } from './xml-parser';

      const PARSERS = {
        json: parseJSON,
        xml: parseXML,
      } as const;

      export function parseData(
        format: keyof typeof PARSERS,
        data: string
      ) {
        return PARSERS[format](data);
      }
    `;

    ruleTester.run('no-runtime-imports', noRuntimeImports, {
      valid: [{
        code: refactoredParserCode,
        filename: '/project/src/core/parser.ts',
      }],
      invalid: [],
    });
  });
});

describe('E2E Scenario 5: Shell Function with Pure String Manipulation', () => {
  /**
   * Scenario: Developer writes string formatting in Shell instead of Core
   * Expected: Should warn that pure logic belongs in Core
   */

  it('should detect pure string manipulation in Shell', () => {
    const shellFormatterCode = `
      // src/shell/formatter.ts
      export function formatUserName(firstName: string, lastName: string) {
        const cleaned = firstName.trim() + ' ' + lastName.trim();
        const capitalized = cleaned.replace(/\\b\\w/g, c => c.toUpperCase());
        const abbreviated = capitalized.replace(/\\s+/g, ' ');
        return abbreviated;
      }
    `;

    ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
      valid: [],
      invalid: [{
        code: shellFormatterCode,
        filename: '/project/src/shell/formatter.ts',
        errors: [{
          messageId: 'pureLogicInShell',
          data: { name: 'formatUserName' },
        }],
      }],
    });
  });

  it('should allow Shell function with actual I/O', () => {
    const properShellCode = `
      // src/shell/user-loader.ts
      import { formatUserName } from '../core/formatter';

      export async function loadAndFormatUser(userId: string) {
        const user = await db.getUser(userId);
        return formatUserName(user.firstName, user.lastName);
      }
    `;

    ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
      valid: [{
        code: properShellCode,
        filename: '/project/src/shell/user-loader.ts',
      }],
      invalid: [],
    });
  });
});

describe('E2E Scenario 6: Complex Arrow Function in Shell', () => {
  /**
   * Scenario: Developer uses arrow function with complex logic
   * Expected: Should extract function name from variable and report violations
   */

  it('should detect complex arrow function and use variable name', () => {
    const complexArrowCode = `
      // src/shell/validator.ts
      export const validateOrder = (order) => {
        const item1 = order.items[0];
        const item2 = order.items[1];
        const item3 = order.items[2];
        const total1 = item1.price * item1.qty;
        const total2 = item2.price * item2.qty;
        const total3 = item3.price * item3.qty;
        const subtotal = total1 + total2 + total3;
        const tax = subtotal * 0.1;
        const shipping = subtotal > 100 ? 0 : 10;
        const total = subtotal + tax + shipping;
        return total;
      };
    `;

    ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
      valid: [],
      invalid: [{
        code: complexArrowCode,
        filename: '/project/src/shell/validator.ts',
        errors: [{
          messageId: 'pureLogicInShell',
          data: { name: 'validateOrder' },  // Should use variable name, not 'anonymous'
        }],
      }],
    });
  });

  it('should also detect high complexity in arrow function', () => {
    const highComplexityArrowCode = `
      // src/shell/router.ts
      export const routeRequest = (req) => {
        if (req.path === '/api/users') return handleUsers();
        else if (req.path === '/api/orders') return handleOrders();
        else if (req.path === '/api/products') return handleProducts();
        else if (req.path === '/api/auth') return handleAuth();
        else if (req.path === '/api/payments') return handlePayments();
        else if (req.path === '/api/shipping') return handleShipping();
        else if (req.path === '/api/inventory') return handleInventory();
        else if (req.path === '/api/reports') return handleReports();
        else if (req.path === '/api/settings') return handleSettings();
        else if (req.path === '/api/notifications') return handleNotifications();
        else return handle404();
      };
    `;

    ruleTester.run('shell-complexity', shellComplexity, {
      valid: [],
      invalid: [{
        code: highComplexityArrowCode,
        filename: '/project/src/shell/router.ts',
        errors: [{
          messageId: 'tooComplex',
          data: { name: 'routeRequest' },  // Should use variable name
        }],
      }],
    });
  });
});

describe('E2E Scenario 7: Entry Point with Export Declaration', () => {
  /**
   * Scenario: Developer exports function definition directly from entry point
   * Expected: Should detect as complex logic (not just re-export)
   */

  it('should detect export function definition in entry point', () => {
    const exportFunctionCode = `
      // index.ts
      export function processData(input: string) {
        const cleaned = input.trim();
        const validated = cleaned.length > 0;
        if (!validated) throw new Error('Invalid input');
        return cleaned.toUpperCase();
      }
    `;

    ruleTester.run('thin-entry-points', thinEntryPoints, {
      valid: [],
      invalid: [{
        code: exportFunctionCode,
        filename: '/project/index.ts',
        errors: [{
          messageId: 'hasComplexLogic',
          data: { type: 'function definition' },
        }],
      }],
    });
  });

  it('should allow pure re-exports from entry point', () => {
    const pureReExportCode = `
      // index.ts
      export { processData } from './core/processor';
      export { loadData } from './shell/loader';
      export type { DataConfig } from './types';
    `;

    ruleTester.run('thin-entry-points', thinEntryPoints, {
      valid: [{
        code: pureReExportCode,
        filename: '/project/index.ts',
      }],
      invalid: [],
    });
  });
});
