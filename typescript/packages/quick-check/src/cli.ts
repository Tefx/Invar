#!/usr/bin/env node
/**
 * CLI for @invar/quick-check
 *
 * Usage:
 *   npx @invar/quick-check [path] [options]
 *
 * Options:
 *   --json        Output JSON format
 *   --skip-tsc    Skip TypeScript compilation
 *   --skip-eslint Skip ESLint checks
 *   --verbose     Show detailed output
 *   --help        Show help
 */

import { quickCheck, type QuickCheckResult } from './index.js';

function printHelp(): void {
  console.log(`
@invar/quick-check - Fast pre-commit verification

Usage:
  npx @invar/quick-check [path] [options]

Arguments:
  path          Project path (default: current directory)

Options:
  --json        Output JSON format (for programmatic use)
  --skip-tsc    Skip TypeScript type checking
  --skip-eslint Skip ESLint checks
  --verbose     Show detailed output
  --help, -h    Show this help message

Examples:
  npx @invar/quick-check                    # Check current directory
  npx @invar/quick-check ./my-project       # Check specific directory
  npx @invar/quick-check --json             # Output JSON for CI
  npx @invar/quick-check --skip-eslint      # Only run tsc
`);
}

function formatResult(result: QuickCheckResult, json: boolean): string {
  if (json) {
    return JSON.stringify(result, null, 2);
  }

  const lines: string[] = [];
  const status = result.passed ? '\u2713 PASSED' : '\u2717 FAILED';
  lines.push(`\n${status} (${result.duration_ms}ms)\n`);

  if (result.checks.tsc) {
    const tsc = result.checks.tsc;
    const tscStatus = tsc.passed ? '\u2713' : '\u2717';
    const cached = tsc.cached ? ' (cached)' : '';
    lines.push(`  ${tscStatus} tsc: ${tsc.duration_ms}ms${cached}`);
    if (tsc.error && !tsc.passed) {
      lines.push(`     ${tsc.error.split('\n')[0]}`);
    }
  }

  if (result.checks.eslint) {
    const eslint = result.checks.eslint;
    const eslintStatus = eslint.passed ? '\u2713' : '\u2717';
    const cached = eslint.cached ? ' (cached)' : '';
    lines.push(`  ${eslintStatus} eslint: ${eslint.duration_ms}ms${cached}`);
    if (eslint.error && !eslint.passed) {
      lines.push(`     ${eslint.error.split('\n')[0]}`);
    }
  }

  return lines.join('\n');
}

function main(): void {
  const args = process.argv.slice(2);

  // Parse options
  const options = {
    path: '.',
    skipTsc: false,
    skipEslint: false,
    verbose: false,
    json: false,
  };

  const positional: string[] = [];

  for (const arg of args) {
    if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--skip-tsc') {
      options.skipTsc = true;
    } else if (arg === '--skip-eslint') {
      options.skipEslint = true;
    } else if (arg === '--verbose') {
      options.verbose = true;
    } else if (!arg.startsWith('-')) {
      positional.push(arg);
    } else {
      console.error(`Unknown option: ${arg}`);
      process.exit(1);
    }
  }

  if (positional.length > 0) {
    options.path = positional[0];
  }

  // Run checks
  const result = quickCheck(options);

  // Output result
  console.log(formatResult(result, options.json));

  // Exit with appropriate code
  process.exit(result.passed ? 0 : 1);
}

main();
