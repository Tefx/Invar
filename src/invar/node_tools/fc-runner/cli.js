#!/usr/bin/env node
/**
 * CLI for @invar/fc-runner
 *
 * Note: This CLI is for running property tests defined in a config file.
 * For programmatic use, import the library directly.
 *
 * Usage:
 *   npx @invar/fc-runner [config-file] [options]
 */
import { runProperties, defineProperty, fc } from './index.js';
function printHelp() {
    console.log(`
@invar/fc-runner - Property-based testing with rich failure analysis

Usage:
  npx @invar/fc-runner [options]

Options:
  --seed <n>        Reproducible seed for random generation
  --num-runs <n>    Number of test runs per property (default: 100)
  --verbose         Show detailed output
  --json            Output JSON format
  --help, -h        Show this help message

Note:
  This CLI provides a summary of capabilities. For full property testing,
  import the library programmatically and define your properties in code.

Example programmatic usage:
  import { runProperties, defineProperty, fc } from '@invar/fc-runner';

  const props = [
    defineProperty({
      name: 'array reverse is involutive',
      arbitraries: { arr: fc.array(fc.integer()) },
      predicate: ({ arr }) => {
        const reversed = [...arr].reverse().reverse();
        return JSON.stringify(reversed) === JSON.stringify(arr);
      },
    }),
  ];

  const result = runProperties(props, { numRuns: 1000 });
`);
}
function formatPropertyResult(prop) {
    const status = prop.passed ? '\u2713' : '\u2717';
    let output = `${status} ${prop.name} (${prop.numRuns} runs, ${prop.duration_ms}ms)`;
    if (!prop.passed && prop.counterexample) {
        output += `\n    Counterexample: ${JSON.stringify(prop.counterexample.values)}`;
        if (prop.counterexample.shrunk) {
            output += ` (shrunk in ${prop.counterexample.shrinkSteps} steps)`;
        }
        if (prop.analysis) {
            output += `\n    Root cause: ${prop.analysis.rootCause}`;
            output += `\n    Suggested fix: ${prop.analysis.suggestedFix}`;
        }
    }
    return output;
}
function formatResult(result, json) {
    if (json) {
        return JSON.stringify(result, null, 2);
    }
    const lines = [];
    const status = result.passed ? '\u2713 ALL PASSED' : '\u2717 FAILED';
    lines.push(`\n=== Property Test Results ===\n`);
    lines.push(`Status: ${status}`);
    lines.push(`Total: ${result.total}, Failed: ${result.failed}`);
    lines.push(`Duration: ${result.duration_ms}ms`);
    lines.push(`Confidence: ${result.confidence}`);
    lines.push('');
    for (const prop of result.properties) {
        lines.push(formatPropertyResult(prop));
    }
    return lines.join('\n');
}
function main() {
    const args = process.argv.slice(2);
    const options = {
        seed: undefined,
        numRuns: 100,
        verbose: false,
        json: false,
    };
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        if (arg === '--help' || arg === '-h') {
            printHelp();
            process.exit(0);
        }
        else if (arg === '--json') {
            options.json = true;
        }
        else if (arg === '--verbose') {
            options.verbose = true;
        }
        else if (arg === '--seed' && args[i + 1]) {
            const seed = parseInt(args[++i], 10);
            if (isNaN(seed)) {
                console.error(`Error: --seed requires a valid number, got "${args[i]}"`);
                process.exit(1);
            }
            options.seed = seed;
        }
        else if (arg === '--num-runs' && args[i + 1]) {
            const numRuns = parseInt(args[++i], 10);
            if (isNaN(numRuns)) {
                console.error(`Error: --num-runs requires a valid number, got "${args[i]}"`);
                process.exit(1);
            }
            options.numRuns = numRuns;
        }
    }
    // Demo: run a simple built-in property using already imported modules
    const demoProps = [
        defineProperty({
            name: 'demo: array concatenation length',
            arbitraries: {
                a: fc.array(fc.integer()),
                b: fc.array(fc.integer()),
            },
            predicate: ({ a, b }) => {
                return a.concat(b).length === a.length + b.length;
            },
        }),
        defineProperty({
            name: 'demo: string repeat',
            arbitraries: {
                s: fc.string({ maxLength: 10 }),
                n: fc.integer({ min: 0, max: 5 }),
            },
            predicate: ({ s, n }) => {
                return s.repeat(n).length === s.length * n;
            },
        }),
    ];
    // Only show progress message in non-JSON mode
    if (!options.json) {
        console.log('Running demo properties...\n');
    }
    // Cast needed because TypeScript infers specific types for each property definition
    const result = runProperties(demoProps, options);
    console.log(formatResult(result, options.json));
    process.exit(result.passed ? 0 : 1);
}
main();
//# sourceMappingURL=cli.js.map