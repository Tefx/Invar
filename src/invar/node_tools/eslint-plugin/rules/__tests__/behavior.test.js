/**
 * Behavior tests for Invar ESLint rules
 *
 * Tests rules with inline code examples (JavaScript syntax for compatibility)
 */
import { describe, it, expect } from 'vitest';
import { RuleTester } from 'eslint';
// Import rules
import { maxFileLines } from '../max-file-lines.js';
import { maxFunctionLines } from '../max-function-lines.js';
import { requireJsdocExample } from '../require-jsdoc-example.js';
import { noIoInCore } from '../no-io-in-core.js';
import { noEmptySchema } from '../no-empty-schema.js';
import { noRedundantTypeSchema } from '../no-redundant-type-schema.js';
import { requireCompleteValidation } from '../require-complete-validation.js';
import { requireSchemaValidation } from '../require-schema-validation.js';
import { noRuntimeImports } from '../no-runtime-imports.js';
import { noImpureCallsInCore } from '../no-impure-calls-in-core.js';
import { noPureLogicInShell } from '../no-pure-logic-in-shell.js';
import { shellComplexity } from '../shell-complexity.js';
import { thinEntryPoints } from '../thin-entry-points.js';
import { getLayer, getLimits } from '../../utils/layer-detection.js';
// Create RuleTester with modern JS configuration
const ruleTester = new RuleTester({
    languageOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
    },
});
describe('layer-detection', () => {
    it('should detect core layer from /core/ path', () => {
        expect(getLayer('/project/src/core/parser.ts')).toBe('core');
    });
    it('should detect shell layer from /shell/ path', () => {
        expect(getLayer('/project/src/shell/io.ts')).toBe('shell');
    });
    it('should detect tests layer from .test.ts extension', () => {
        expect(getLayer('/project/src/utils.test.ts')).toBe('tests');
    });
    it('should detect tests layer from .spec.ts extension', () => {
        expect(getLayer('/project/src/utils.spec.ts')).toBe('tests');
    });
    it('should detect tests layer from /tests/ directory', () => {
        expect(getLayer('/project/tests/unit.ts')).toBe('tests');
    });
    it('should prioritize tests over core', () => {
        expect(getLayer('/project/src/core/parser.test.ts')).toBe('tests');
    });
    it('should detect core from relative path', () => {
        expect(getLayer('core/parser.ts')).toBe('core');
    });
    it('should detect shell from relative path', () => {
        expect(getLayer('shell/io.ts')).toBe('shell');
    });
    it('should handle Windows paths', () => {
        expect(getLayer('C:\\Project\\core\\parser.ts')).toBe('core');
        expect(getLayer('C:\\Project\\shell\\io.ts')).toBe('shell');
    });
    it('should not match /hardcore/ as core', () => {
        expect(getLayer('/project/hardcore/file.ts')).toBe('default');
    });
    it('should not match /eggshell/ as shell', () => {
        expect(getLayer('/project/eggshell/file.ts')).toBe('default');
    });
    it('should return correct limits for each layer', () => {
        expect(getLimits('/core/file.ts')).toEqual({
            maxFileLines: 650,
            maxFunctionLines: 65,
        });
        expect(getLimits('/shell/file.ts')).toEqual({
            maxFileLines: 910,
            maxFunctionLines: 130,
        });
        expect(getLimits('/file.test.ts')).toEqual({
            maxFileLines: 1300,
            maxFunctionLines: 260,
        });
        expect(getLimits('/file.ts')).toEqual({
            maxFileLines: 780,
            maxFunctionLines: 104,
        });
    });
});
describe('max-file-lines', () => {
    it('should detect files exceeding core limit (650 lines)', () => {
        ruleTester.run('max-file-lines', maxFileLines, {
            valid: [
                {
                    code: '// Valid core file\n' + 'const x = 1;\n'.repeat(648), // 649 lines total
                    filename: '/project/core/valid.js',
                },
            ],
            invalid: [
                {
                    code: '// Invalid core file\n' + 'const x = 1;\n'.repeat(650), // 651 lines total
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
    it('should use different limits for shell (910 lines)', () => {
        ruleTester.run('max-file-lines', maxFileLines, {
            valid: [
                {
                    code: '// Valid shell file\n' + 'const x = 1;\n'.repeat(908), // 909 lines total
                    filename: '/project/shell/valid.js',
                },
            ],
            invalid: [
                {
                    code: '// Invalid shell file\n' + 'const x = 1;\n'.repeat(910), // 911 lines total
                    filename: '/project/shell/invalid.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
    it('should use different limits for tests (1300 lines)', () => {
        ruleTester.run('max-file-lines', maxFileLines, {
            valid: [
                {
                    code: '// Valid test file\n' + 'const x = 1;\n'.repeat(1298), // 1299 lines total
                    filename: '/project/tests/valid.test.js',
                },
            ],
            invalid: [
                {
                    code: '// Invalid test file\n' + 'const x = 1;\n'.repeat(1300), // 1301 lines total
                    filename: '/project/tests/invalid.test.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
});
describe('max-function-lines', () => {
    it('should detect functions exceeding core limit (65 lines)', () => {
        ruleTester.run('max-function-lines', maxFunctionLines, {
            valid: [
                {
                    code: `function validCoreFunction() {\n${'  const x = 1;\n'.repeat(63)}}`, // 65 lines total
                    filename: '/project/core/valid.js',
                },
            ],
            invalid: [
                {
                    code: `function invalidCoreFunction() {\n${'  const x = 1;\n'.repeat(65)}}`, // 67 lines total
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
    it('should use different limits for shell (130 lines)', () => {
        ruleTester.run('max-function-lines', maxFunctionLines, {
            valid: [
                {
                    code: `function validShellFunction() {\n${'  const x = 1;\n'.repeat(128)}}`, // 130 lines total
                    filename: '/project/shell/valid.js',
                },
            ],
            invalid: [
                {
                    code: `function invalidShellFunction() {\n${'  const x = 1;\n'.repeat(130)}}`, // 132 lines total
                    filename: '/project/shell/invalid.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
    it('should use different limits for tests (260 lines)', () => {
        ruleTester.run('max-function-lines', maxFunctionLines, {
            valid: [
                {
                    code: `function validTestFunction() {\n${'  const x = 1;\n'.repeat(258)}}`, // 260 lines total
                    filename: '/project/tests/valid.test.js',
                },
            ],
            invalid: [
                {
                    code: `function invalidTestFunction() {\n${'  const x = 1;\n'.repeat(260)}}`, // 262 lines total
                    filename: '/project/tests/invalid.test.js',
                    errors: [{ messageId: 'tooManyLines' }],
                },
            ],
        });
    });
});
describe('require-jsdoc-example', () => {
    it('should require @example for exported functions', () => {
        ruleTester.run('require-jsdoc-example', requireJsdocExample, {
            valid: [
                {
                    code: `
            /**
             * Valid function with example
             * @example
             * foo() // => 'bar'
             */
            export function foo() { return 'bar'; }
          `,
                    filename: '/project/test.js',
                },
                {
                    code: `
            // Non-exported function - no @example required
            function privateHelper() { return 'private'; }
          `,
                    filename: '/project/test.js',
                },
            ],
            invalid: [
                {
                    code: `
            /**
             * Missing @example
             */
            export function foo() { return 'bar'; }
          `,
                    filename: '/project/test.js',
                    errors: [{ messageId: 'missingExample' }],
                },
            ],
        });
    });
    it('should require @example for exported arrow functions', () => {
        ruleTester.run('require-jsdoc-example', requireJsdocExample, {
            valid: [
                {
                    code: `
            /**
             * Valid arrow function with example
             * @example
             * foo() // => 'bar'
             */
            export const foo = () => 'bar';
          `,
                    filename: '/project/test.js',
                },
            ],
            invalid: [
                {
                    code: `
            /**
             * Missing @example
             */
            export const foo = () => 'bar';
          `,
                    filename: '/project/test.js',
                    errors: [{ messageId: 'missingExample' }],
                },
            ],
        });
    });
});
describe('no-io-in-core', () => {
    it('should forbid I/O imports in /core/ directories', () => {
        ruleTester.run('no-io-in-core', noIoInCore, {
            valid: [
                {
                    code: `import { something } from 'lodash';`,
                    filename: '/project/core/valid.js',
                },
                {
                    code: `import * as fs from 'fs';`,
                    filename: '/project/shell/valid.js', // Allowed in shell
                },
            ],
            invalid: [
                {
                    code: `import * as fs from 'fs';`,
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
                {
                    code: `import { readFile } from 'node:fs/promises';`,
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
                {
                    code: `import axios from 'axios';`,
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
                {
                    code: `import { S3Client } from '@aws-sdk/client-s3';`,
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
                {
                    code: `import { deploy } from '@vercel/node';`,
                    filename: '/project/core/invalid.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
            ],
        });
    });
    it('should handle Windows-style core paths', () => {
        ruleTester.run('no-io-in-core', noIoInCore, {
            valid: [],
            invalid: [
                {
                    code: `import * as fs from 'fs';`,
                    filename: 'C:\\\\Project\\\\core\\\\test.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
            ],
        });
    });
    it('should detect require() calls', () => {
        ruleTester.run('no-io-in-core', noIoInCore, {
            valid: [],
            invalid: [
                {
                    code: `const fs = require('fs');`,
                    filename: '/project/core/test.js',
                    errors: [{ messageId: 'ioInCore' }],
                },
            ],
        });
    });
});
describe('Integration: Cross-platform path normalization', () => {
    it('should handle Unix paths correctly', () => {
        expect(getLayer('/Users/project/core/parser.ts')).toBe('core');
        expect(getLayer('/home/user/project/shell/io.ts')).toBe('shell');
    });
    it('should handle Windows paths correctly', () => {
        expect(getLayer('C:\\Users\\project\\core\\parser.ts')).toBe('core');
        expect(getLayer('D:\\Projects\\shell\\io.ts')).toBe('shell');
    });
    it('should handle relative paths correctly', () => {
        expect(getLayer('core/parser.ts')).toBe('core');
        expect(getLayer('shell/io.ts')).toBe('shell');
        expect(getLayer('src/core/parser.ts')).toBe('core');
    });
});
describe('no-empty-schema', () => {
    it('should detect empty z.object({})', () => {
        ruleTester.run('no-empty-schema', noEmptySchema, {
            valid: [
                { code: `const Schema = z.object({ id: z.string() });` },
                { code: `const Schema = z.object({ name: z.string(), age: z.number() });` },
            ],
            invalid: [
                {
                    code: `const Schema = z.object({});`,
                    errors: [{ messageId: 'emptyObject' }],
                },
            ],
        });
    });
    it('should detect .passthrough() calls', () => {
        ruleTester.run('no-empty-schema', noEmptySchema, {
            valid: [
                { code: `const Schema = z.object({ id: z.string() }).strict();` },
            ],
            invalid: [
                {
                    code: `const Schema = z.object({ id: z.string() }).passthrough();`,
                    errors: [{ messageId: 'passthrough' }],
                },
            ],
        });
    });
    it('should detect .loose() calls', () => {
        ruleTester.run('no-empty-schema', noEmptySchema, {
            valid: [
                { code: `const Schema = z.object({ id: z.string() });` },
            ],
            invalid: [
                {
                    code: `const Schema = z.object({ id: z.string() }).loose();`,
                    errors: [{ messageId: 'loose' }],
                },
            ],
        });
    });
});
describe('no-redundant-type-schema', () => {
    it('should detect z.string() without constraints', () => {
        ruleTester.run('no-redundant-type-schema', noRedundantTypeSchema, {
            valid: [
                { code: `const Schema = z.string().min(1);` },
                { code: `const Schema = z.string().max(100);` },
                { code: `const Schema = z.string().email();` },
                { code: `const Schema = z.string().regex(/^[a-z]+$/);` },
            ],
            invalid: [
                {
                    code: `const Schema = z.string();`,
                    errors: [{ messageId: 'redundantString' }],
                },
            ],
        });
    });
    it('should detect z.number() without constraints', () => {
        ruleTester.run('no-redundant-type-schema', noRedundantTypeSchema, {
            valid: [
                { code: `const Schema = z.number().min(0);` },
                { code: `const Schema = z.number().max(100);` },
                { code: `const Schema = z.number().int();` },
                { code: `const Schema = z.number().positive();` },
            ],
            invalid: [
                {
                    code: `const Schema = z.number();`,
                    errors: [{ messageId: 'redundantNumber' }],
                },
            ],
        });
    });
    it('should detect z.boolean() (always redundant)', () => {
        ruleTester.run('no-redundant-type-schema', noRedundantTypeSchema, {
            valid: [],
            invalid: [
                {
                    code: `const Schema = z.boolean();`,
                    errors: [{ messageId: 'redundantBoolean' }],
                },
            ],
        });
    });
});
describe('require-complete-validation', () => {
    // Create RuleTester with TypeScript parser for this suite
    const tsRuleTester = new RuleTester({
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            parser: require('@typescript-eslint/parser'),
        },
    });
    it('should detect mixed validated/unvalidated parameters', () => {
        tsRuleTester.run('require-complete-validation', requireCompleteValidation, {
            valid: [
                {
                    code: `function transfer(
            user: z.infer<typeof UserSchema>,
            amount: z.infer<typeof AmountSchema>
          ) {}`,
                },
                {
                    code: `function calculate(x: number, y: number) {}`,
                },
                {
                    code: `function greet() {}`,
                },
            ],
            invalid: [
                {
                    code: `function transfer(
            user: z.infer<typeof UserSchema>,
            amount: number
          ) {}`,
                    errors: [{ messageId: 'partialValidation' }],
                },
                {
                    code: `function process(
            data: z.infer<typeof DataSchema>,
            count: number,
            name: string
          ) {}`,
                    errors: [{ messageId: 'partialValidation' }],
                },
            ],
        });
    });
    it('should handle arrow functions', () => {
        tsRuleTester.run('require-complete-validation', requireCompleteValidation, {
            valid: [
                {
                    code: `const fn = (user: z.infer<typeof UserSchema>, id: z.infer<typeof IdSchema>) => {};`,
                },
            ],
            invalid: [
                {
                    code: `const fn = (user: z.infer<typeof UserSchema>, id: number) => {};`,
                    errors: [{ messageId: 'partialValidation' }],
                },
            ],
        });
    });
});
describe('require-schema-validation modes', () => {
    const tsRuleTester = new RuleTester({
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            parser: require('@typescript-eslint/parser'),
        },
    });
    it('should check all functions in recommended mode (default)', () => {
        tsRuleTester.run('require-schema-validation', requireSchemaValidation, {
            valid: [
                {
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              const validated = UserSchema.parse(user);
            }
          `,
                },
            ],
            invalid: [
                {
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    errors: [{ messageId: 'missingValidation' }],
                },
            ],
        });
    });
    it('should check all functions in strict mode', () => {
        tsRuleTester.run('require-schema-validation', requireSchemaValidation, {
            valid: [
                {
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              const validated = UserSchema.parse(user);
            }
          `,
                    options: [{ mode: 'strict' }],
                },
            ],
            invalid: [
                {
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    options: [{ mode: 'strict' }],
                    errors: [{ messageId: 'missingValidation' }],
                },
            ],
        });
    });
    it('should only check high-risk functions in risk-based mode', () => {
        tsRuleTester.run('require-schema-validation', requireSchemaValidation, {
            valid: [
                {
                    // Non-risk function should pass even without validation
                    code: `
            function getData(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    options: [{ mode: 'risk-based' }],
                },
                {
                    // Risk function with validation should pass
                    code: `
            function processPayment(user: z.infer<typeof UserSchema>) {
              const validated = UserSchema.parse(user);
            }
          `,
                    options: [{ mode: 'risk-based' }],
                },
            ],
            invalid: [
                {
                    // Risk function without validation should fail
                    code: `
            function processPayment(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    options: [{ mode: 'risk-based' }],
                    errors: [{ messageId: 'missingValidationRisk' }],
                },
                {
                    code: `
            function authenticateUser(token: z.infer<typeof TokenSchema>) {
              console.log(token);
            }
          `,
                    options: [{ mode: 'risk-based' }],
                    errors: [{ messageId: 'missingValidationRisk' }],
                },
            ],
        });
    });
    it('should enforce for specific paths when enforceFor is set', () => {
        tsRuleTester.run('require-schema-validation', requireSchemaValidation, {
            valid: [
                {
                    // File outside enforceFor paths should pass
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    filename: '/project/src/utils/helper.ts',
                    options: [{ mode: 'risk-based', enforceFor: ['**/payment/**', '**/auth/**'] }],
                },
            ],
            invalid: [
                {
                    // File in payment path should fail
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    filename: '/project/src/payment/processor.ts',
                    options: [{ mode: 'risk-based', enforceFor: ['**/payment/**', '**/auth/**'] }],
                    errors: [{ messageId: 'missingValidation' }],
                },
                {
                    // File in auth path should fail
                    code: `
            function process(user: z.infer<typeof UserSchema>) {
              console.log(user);
            }
          `,
                    filename: '/project/src/auth/login.ts',
                    options: [{ mode: 'risk-based', enforceFor: ['**/payment/**', '**/auth/**'] }],
                    errors: [{ messageId: 'missingValidation' }],
                },
            ],
        });
    });
});
describe('no-runtime-imports', () => {
    it('should detect require() inside functions', () => {
        ruleTester.run('no-runtime-imports', noRuntimeImports, {
            valid: [
                {
                    code: `const fs = require('fs');`, // Top-level require is OK
                },
                {
                    code: `import fs from 'fs';`, // Top-level import is OK
                },
            ],
            invalid: [
                {
                    code: `
            function loadModule() {
              const fs = require('fs');
            }
          `,
                    errors: [{ messageId: 'runtimeRequire' }],
                },
                {
                    code: `
            const handler = () => {
              const path = require('path');
            };
          `,
                    errors: [{ messageId: 'runtimeRequire' }],
                },
            ],
        });
    });
    it('should detect dynamic import() inside functions', () => {
        ruleTester.run('no-runtime-imports', noRuntimeImports, {
            valid: [],
            invalid: [
                {
                    code: `
            async function loadModule() {
              const mod = await import('./module');
            }
          `,
                    errors: [{ messageId: 'runtimeImport' }],
                },
                {
                    code: `
            const handler = async () => {
              const { foo } = await import('./foo');
            };
          `,
                    errors: [{ messageId: 'runtimeImport' }],
                },
            ],
        });
    });
});
describe('no-impure-calls-in-core', () => {
    it('should detect Core importing from Shell', () => {
        ruleTester.run('no-impure-calls-in-core', noImpureCallsInCore, {
            valid: [
                {
                    code: `import { helper } from '../utils';`,
                    filename: '/project/core/logic.js',
                },
                {
                    code: `import { ioFunc } from '../shell/io';`,
                    filename: '/project/shell/handler.js', // OK in shell
                },
            ],
            invalid: [
                {
                    code: `import { ioFunc } from '../shell/io';`,
                    filename: '/project/core/logic.js',
                    errors: [{ messageId: 'shellImportInCore' }],
                },
                {
                    code: `import { readData } from '../../shell/data';`,
                    filename: '/project/src/core/parser.js',
                    errors: [{ messageId: 'shellImportInCore' }],
                },
                {
                    code: `import { handler } from 'shell/handler';`,
                    filename: '/project/core/logic.js',
                    errors: [{ messageId: 'shellImportInCore' }],
                },
            ],
        });
    });
    it('should handle Windows-style paths', () => {
        ruleTester.run('no-impure-calls-in-core', noImpureCallsInCore, {
            valid: [],
            invalid: [
                {
                    code: `import { ioFunc } from '..\\\\shell\\\\io';`,
                    filename: 'C:\\\\Project\\\\core\\\\logic.js',
                    errors: [{ messageId: 'shellImportInCore' }],
                },
            ],
        });
    });
});
describe('no-pure-logic-in-shell', () => {
    it('should warn when Shell function has no I/O indicators', () => {
        ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
            valid: [
                {
                    // Async function - has I/O indicator
                    code: `
            async function fetchData() {
              const x = 1;
              const y = 2;
              const z = 3;
              const w = 4;
              return x + y + z + w;
            }
          `,
                    filename: '/project/shell/data.js',
                },
                {
                    // Uses fs - has I/O indicator
                    code: `
            function readConfig() {
              const x = 1;
              const y = 2;
              const z = 3;
              const w = 4;
              return fs.readFileSync('config.json');
            }
          `,
                    filename: '/project/shell/config.js',
                },
                {
                    // Returns Result - has I/O indicator
                    code: `
            function loadData() {
              const x = 1;
              const y = 2;
              const z = 3;
              const w = 4;
              return Success(data);
            }
          `,
                    filename: '/project/shell/loader.js',
                },
                {
                    // Small function - not substantial logic
                    code: `
            function helper() {
              const x = 1;
              return x;
            }
          `,
                    filename: '/project/shell/utils.js',
                },
            ],
            invalid: [
                {
                    // Pure logic in Shell - no I/O, substantial statements
                    code: `
            function calculateTotal() {
              const a = 1;
              const b = 2;
              const c = 3;
              const d = 4;
              return a + b + c + d;
            }
          `,
                    filename: '/project/shell/calculator.js',
                    errors: [{ messageId: 'pureLogicInShell' }],
                },
            ],
        });
    });
    it('should not check non-shell files', () => {
        ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
            valid: [
                {
                    // Core file - rule should skip it
                    code: `
            function pureCalculation() {
              const a = 1;
              const b = 2;
              const c = 3;
              const d = 4;
              return a + b + c + d;
            }
          `,
                    filename: '/project/core/logic.js',
                },
            ],
            invalid: [],
        });
    });
    it('should extract function name from FunctionExpression with id', () => {
        ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
            valid: [],
            invalid: [
                {
                    // Named FunctionExpression should use its own name
                    code: `
            const foo = function namedFunc() {
              const a = 1;
              const b = 2;
              const c = 3;
              const d = 4;
              return a + b + c + d;
            };
          `,
                    filename: '/project/shell/calculator.js',
                    errors: [{
                            messageId: 'pureLogicInShell',
                            data: { name: 'namedFunc' }, // Should use function's own name
                        }],
                },
            ],
        });
    });
    it('should extract function name from parent VariableDeclarator for anonymous FunctionExpression', () => {
        ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
            valid: [],
            invalid: [
                {
                    // Anonymous FunctionExpression should use variable name
                    code: `
            const calculateTotal = function() {
              const a = 1;
              const b = 2;
              const c = 3;
              const d = 4;
              return a + b + c + d;
            };
          `,
                    filename: '/project/shell/calculator.js',
                    errors: [{
                            messageId: 'pureLogicInShell',
                            data: { name: 'calculateTotal' }, // Should use variable name
                        }],
                },
            ],
        });
    });
    it('should extract function name from parent VariableDeclarator for ArrowFunctionExpression', () => {
        ruleTester.run('no-pure-logic-in-shell', noPureLogicInShell, {
            valid: [],
            invalid: [
                {
                    // Arrow function should use variable name
                    code: `
            const processData = () => {
              const a = 1;
              const b = 2;
              const c = 3;
              const d = 4;
              return a + b + c + d;
            };
          `,
                    filename: '/project/shell/processor.js',
                    errors: [{
                            messageId: 'pureLogicInShell',
                            data: { name: 'processData' }, // Should use variable name
                        }],
                },
            ],
        });
    });
});
describe('shell-complexity', () => {
    it('should detect functions with too many statements', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [
                {
                    code: `
            function simpleHandler() {
              ${'const x = 1;\n'.repeat(19)}
            }
          `,
                    filename: '/project/shell/handler.js',
                },
            ],
            invalid: [
                {
                    code: `
            function complexHandler() {
              ${'const x = 1;\n'.repeat(21)}
            }
          `,
                    filename: '/project/shell/handler.js',
                    errors: [{ messageId: 'tooManyStatements' }],
                },
            ],
        });
    });
    it('should detect functions with high cyclomatic complexity', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [
                {
                    code: `
            function lowComplexity() {
              if (a) return 1;
              if (b) return 2;
              if (c) return 3;
              return 0;
            }
          `,
                    filename: '/project/shell/handler.js',
                },
            ],
            invalid: [
                {
                    code: `
            function highComplexity() {
              if (a) return 1;
              else if (b) return 2;
              else if (c) return 3;
              else if (d) return 4;
              else if (e) return 5;
              else if (f) return 6;
              else if (g) return 7;
              else if (h) return 8;
              else if (i) return 9;
              else if (j) return 10;
              else return 0;
            }
          `,
                    filename: '/project/shell/handler.js',
                    errors: [{ messageId: 'tooComplex' }],
                },
            ],
        });
    });
    it('should use custom thresholds', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [
                {
                    code: `
            function handler() {
              ${'const x = 1;\n'.repeat(6)}
            }
          `,
                    filename: '/project/shell/handler.js',
                    options: [{ maxStatements: 5 }],
                },
            ],
            invalid: [
                {
                    code: `
            function handler() {
              ${'const x = 1;\n'.repeat(6)}
            }
          `,
                    filename: '/project/shell/handler.js',
                    options: [{ maxStatements: 5 }],
                    errors: [{ messageId: 'tooManyStatements' }],
                },
            ],
        });
    });
    it('should not count default case in complexity', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [
                {
                    // Switch with default should not add to complexity
                    code: `
            function handler(type) {
              switch (type) {
                case 'a': return 1;
                case 'b': return 2;
                case 'c': return 3;
                default: return 0;
              }
            }
          `,
                    filename: '/project/shell/handler.js',
                    options: [{ maxComplexity: 3 }],
                },
            ],
            invalid: [],
        });
    });
    it('should count nullish coalescing operator', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [],
            invalid: [
                {
                    // Nullish coalescing should add to complexity
                    code: `
            function handler() {
              const a = x ?? 1;
              const b = y ?? 2;
              const c = z ?? 3;
              const d = w ?? 4;
              const e = v ?? 5;
              if (a) return a;
              if (b) return b;
              if (c) return c;
              if (d) return d;
              if (e) return e;
              return 0;
            }
          `,
                    filename: '/project/shell/handler.js',
                    options: [{ maxComplexity: 10 }],
                    errors: [{ messageId: 'tooComplex' }],
                },
            ],
        });
    });
    it('should not check non-shell files', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [
                {
                    code: `
            function complexCore() {
              ${'const x = 1;\n'.repeat(30)}
            }
          `,
                    filename: '/project/core/logic.js',
                },
            ],
            invalid: [],
        });
    });
    it('should extract function name from FunctionExpression with id', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [],
            invalid: [
                {
                    // Named FunctionExpression should use its own name
                    code: `
            const foo = function namedHandler() {
              ${'const x = 1;\n'.repeat(21)}
            };
          `,
                    filename: '/project/shell/handler.js',
                    errors: [{
                            messageId: 'tooManyStatements',
                            data: { name: 'namedHandler' }, // Should use function's own name
                        }],
                },
            ],
        });
    });
    it('should extract function name from parent VariableDeclarator for anonymous FunctionExpression', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [],
            invalid: [
                {
                    // Anonymous FunctionExpression should use variable name
                    code: `
            const processOrder = function() {
              ${'const x = 1;\n'.repeat(21)}
            };
          `,
                    filename: '/project/shell/orders.js',
                    errors: [{
                            messageId: 'tooManyStatements',
                            data: { name: 'processOrder' }, // Should use variable name
                        }],
                },
            ],
        });
    });
    it('should extract function name from parent VariableDeclarator for ArrowFunctionExpression', () => {
        ruleTester.run('shell-complexity', shellComplexity, {
            valid: [],
            invalid: [
                {
                    // Arrow function should use variable name
                    code: `
            const handleRequest = () => {
              ${'const x = 1;\n'.repeat(21)}
            };
          `,
                    filename: '/project/shell/api.js',
                    errors: [{
                            messageId: 'tooManyStatements',
                            data: { name: 'handleRequest' }, // Should use variable name
                        }],
                },
            ],
        });
    });
});
describe('thin-entry-points', () => {
    it('should detect entry point files with too much logic', () => {
        ruleTester.run('thin-entry-points', thinEntryPoints, {
            valid: [
                {
                    // Simple index.ts with imports and exports
                    code: `
            import { foo } from './foo';
            import { bar } from './bar';
            export { foo, bar };
            export default foo;
          `,
                    filename: '/project/index.ts',
                },
                {
                    // Few config statements are OK
                    code: `
            import express from 'express';
            const app = express();
            const PORT = 3000;
            export { app, PORT };
          `,
                    filename: '/project/main.ts',
                },
            ],
            invalid: [
                {
                    // Too many statements
                    code: `
            import express from 'express';
            const app = express();
            const x1 = 1;
            const x2 = 2;
            const x3 = 3;
            const x4 = 4;
            const x5 = 5;
            const x6 = 6;
            const x7 = 7;
            const x8 = 8;
            const x9 = 9;
            const x10 = 10;
            const x11 = 11;
            export { app };
          `,
                    filename: '/project/index.ts',
                    errors: [{ messageId: 'tooMuchLogic' }],
                },
            ],
        });
    });
    it('should detect complex logic in entry points', () => {
        ruleTester.run('thin-entry-points', thinEntryPoints, {
            valid: [
                {
                    code: `
            import { handler } from './handler';
            export { handler };
          `,
                    filename: '/project/cli.ts',
                },
            ],
            invalid: [
                {
                    // Function definition in entry point
                    code: `
            function processData() {
              return 42;
            }
            export { processData };
          `,
                    filename: '/project/index.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
                {
                    // Class definition in entry point
                    code: `
            class App {
              run() { return 'running'; }
            }
            export { App };
          `,
                    filename: '/project/main.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
                {
                    // Control flow in entry point
                    code: `
            import { config } from './config';
            if (config.enabled) {
              console.log('enabled');
            }
            export { config };
          `,
                    filename: '/project/app.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
            ],
        });
    });
    it('should only check entry point files', () => {
        ruleTester.run('thin-entry-points', thinEntryPoints, {
            valid: [
                {
                    // Non-entry point file can have complex logic
                    code: `
            function complexFunction() {
              if (a) return 1;
              if (b) return 2;
              if (c) return 3;
              return 0;
            }
            export { complexFunction };
          `,
                    filename: '/project/utils/helper.ts',
                },
            ],
            invalid: [],
        });
    });
    it('should detect all entry point patterns', () => {
        const patterns = ['index.ts', 'main.ts', 'cli.ts', 'app.ts', 'server.ts'];
        for (const pattern of patterns) {
            ruleTester.run('thin-entry-points', thinEntryPoints, {
                valid: [],
                invalid: [
                    {
                        code: `
              function logic() { return 42; }
              export { logic };
            `,
                        filename: `/project/${pattern}`,
                        errors: [{ messageId: 'hasComplexLogic' }],
                    },
                ],
            });
        }
    });
    it('should handle Windows paths correctly in error messages', () => {
        ruleTester.run('thin-entry-points', thinEntryPoints, {
            valid: [],
            invalid: [
                {
                    // Windows path should be normalized to show just filename
                    code: `
            function logic() { return 42; }
            export { logic };
          `,
                    filename: 'C:\\\\Project\\\\src\\\\index.ts',
                    errors: [{
                            messageId: 'hasComplexLogic',
                            // Error message should show 'index.ts' not full path
                        }],
                },
            ],
        });
    });
    it('should treat export declarations with bodies as complex logic', () => {
        ruleTester.run('thin-entry-points', thinEntryPoints, {
            valid: [
                {
                    // Pure re-export is OK
                    code: `
            import { foo } from './foo';
            export { foo };
          `,
                    filename: '/project/index.ts',
                },
                {
                    // Type-only exports are OK
                    code: `
            export type { User } from './types';
            export interface Config { port: number; }
          `,
                    filename: '/project/index.ts',
                },
            ],
            invalid: [
                {
                    // Export with function definition is complex logic
                    code: `
            export function processData() {
              return 42;
            }
          `,
                    filename: '/project/index.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
                {
                    // Export with class definition is complex logic
                    code: `
            export class Handler {
              handle() { return 'handled'; }
            }
          `,
                    filename: '/project/index.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
                {
                    // Export default with function is complex logic
                    code: `
            export default function main() {
              console.log('running');
            }
          `,
                    filename: '/project/main.ts',
                    errors: [{ messageId: 'hasComplexLogic' }],
                },
            ],
        });
    });
});
//# sourceMappingURL=behavior.test.js.map