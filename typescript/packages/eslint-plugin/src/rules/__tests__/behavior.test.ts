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
