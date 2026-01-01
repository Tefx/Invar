#!/usr/bin/env node
/**
 * CLI for @invar/ts-analyzer
 *
 * Usage:
 *   npx @invar/ts-analyzer [path] [options]
 *
 * Options:
 *   --json            Output JSON format
 *   --include-private Include private (_prefixed) functions
 *   --verbose         Show detailed output
 *   --help            Show help
 */

import { analyze, type AnalysisResult, type BlindSpot } from './index.js';

function printHelp(): void {
  console.log(`
@invar/ts-analyzer - TypeScript contract analysis

Usage:
  npx @invar/ts-analyzer [path] [options]

Arguments:
  path              Project path (default: current directory)

Options:
  --json            Output JSON format (for programmatic use)
  --include-private Include private (_prefixed) functions
  --verbose         Show detailed output
  --help, -h        Show this help message

Examples:
  npx @invar/ts-analyzer                      # Analyze current directory
  npx @invar/ts-analyzer ./src                # Analyze specific directory
  npx @invar/ts-analyzer --json               # Output JSON for CI
`);
}

function formatBlindSpot(spot: BlindSpot): string {
  const riskIcon = spot.risk === 'critical' ? '\u2622' : '\u26A0';
  return `  ${riskIcon} ${spot.function} (${spot.file}:${spot.line})
     ${spot.reason}
     Suggested: ${spot.suggestedSchema}`;
}

function formatResult(result: AnalysisResult, json: boolean, verbose: boolean): string {
  if (json) {
    return JSON.stringify(result, null, 2);
  }

  const lines: string[] = [];

  lines.push(`\n=== Contract Analysis ===\n`);
  lines.push(`Files analyzed: ${result.files}`);
  lines.push(`Functions found: ${result.coverage.total}`);
  lines.push(`Contract coverage: ${result.coverage.percent}% (${result.coverage.withContracts}/${result.coverage.total})`);

  lines.push(`\nContract Quality:`);
  lines.push(`  Strong: ${result.quality.strong}`);
  lines.push(`  Medium: ${result.quality.medium}`);
  lines.push(`  Weak: ${result.quality.weak}`);
  lines.push(`  Useless: ${result.quality.useless}`);

  if (result.blindSpots.length > 0) {
    lines.push(`\n\u26A0 Blind Spots (${result.blindSpots.length}):`);
    for (const spot of result.blindSpots) {
      lines.push(formatBlindSpot(spot));
    }
  }

  if (verbose) {
    lines.push(`\n=== Function Details ===\n`);
    for (const func of result.functions) {
      const status = func.contractStatus === 'complete' ? '\u2713'
        : func.contractStatus === 'partial' ? '\u25CB'
        : '\u2717';
      lines.push(`${status} ${func.name} (${func.file}:${func.line})`);
      for (const param of func.params) {
        const pStatus = param.hasContract ? '\u2713' : '\u2717';
        lines.push(`    ${pStatus} ${param.name}: ${param.type}`);
      }
    }
  }

  return lines.join('\n');
}

function main(): void {
  const args = process.argv.slice(2);

  const options = {
    path: '.',
    includePrivate: false,
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
    } else if (arg === '--include-private') {
      options.includePrivate = true;
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

  const result = analyze(options);
  console.log(formatResult(result, options.json, options.verbose));

  // Exit with error if critical blind spots found
  const hasCritical = result.blindSpots.some(s => s.risk === 'critical');
  process.exit(hasCritical ? 1 : 0);
}

main();
