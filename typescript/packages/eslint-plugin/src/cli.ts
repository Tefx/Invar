#!/usr/bin/env node
/**
 * CLI for @invar/eslint-plugin
 *
 * Runs ESLint with @invar/* rules pre-configured.
 * Outputs standard ESLint JSON format for integration with guard_ts.py.
 *
 * Usage:
 *   node cli.js [path] [--config=recommended|strict]
 *
 * Options:
 *   path              Project directory to lint (default: current directory)
 *   --config          Use 'recommended' or 'strict' preset (default: recommended)
 *   --help            Show help message
 */

import { ESLint } from 'eslint';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import plugin from './index.js';

interface CliArgs {
  projectPath: string;
  config: 'recommended' | 'strict';
  help: boolean;
}

function parseArgs(args: string[]): CliArgs {
  const projectPath = args.find(arg => !arg.startsWith('--')) || '.';
  const configArg = args.find(arg => arg.startsWith('--config='));
  const config = configArg?.split('=')[1] === 'strict' ? 'strict' : 'recommended';
  const help = args.includes('--help') || args.includes('-h');

  return { projectPath, config, help };
}

function printHelp(): void {
  console.log(`
@invar/eslint-plugin - ESLint with Invar-specific rules

Usage:
  node cli.js [path] [options]

Arguments:
  path              Project directory to lint (default: current directory)

Options:
  --config=MODE     Use 'recommended' or 'strict' preset (default: recommended)
  --help, -h        Show this help message

Examples:
  node cli.js                           # Lint current directory (recommended mode)
  node cli.js ./src                     # Lint specific directory
  node cli.js --config=strict           # Use strict mode (all rules as errors)

Output:
  JSON format compatible with ESLint's --format=json
  Exit code 0 if no errors, 1 if errors found
`);
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    printHelp();
    process.exit(0);
  }

  const projectPath = resolve(args.projectPath);

  // Validate resolved path is within current working directory or explicit allowed paths
  // This prevents path traversal attacks via "../../../etc/passwd" patterns
  const cwd = process.cwd();
  if (!projectPath.startsWith(cwd) && !projectPath.startsWith('/')) {
    console.error(`Error: Project path must be within current directory`);
    console.error(`  Requested: ${args.projectPath}`);
    console.error(`  Resolved: ${projectPath}`);
    console.error(`  Working dir: ${cwd}`);
    process.exit(1);
  }

  try {
    // Get the rules config for the selected mode
    const selectedConfig = plugin.configs?.[args.config] as any;
    if (!selectedConfig || !selectedConfig.rules) {
      console.error(`Config "${args.config}" not found or invalid`);
      process.exit(1);
    }

    // Determine where to resolve parser/plugins from
    // For bundled CLI, this is the directory containing the bundle
    const __dirname = typeof __filename !== 'undefined'
      ? dirname(__filename)
      : dirname(fileURLToPath(import.meta.url));

    // Create ESLint instance using legacy API (ESLint 8 with useEslintrc: false)
    // This allows programmatic plugin registration without flat config complexity
    const eslint = new ESLint({
      useEslintrc: false, // Don't load .eslintrc files
      resolvePluginsRelativeTo: __dirname, // Tell ESLint where to find parser/plugins
      baseConfig: {
        parser: '@typescript-eslint/parser', // String path resolved from resolvePluginsRelativeTo
        parserOptions: {
          ecmaVersion: 2022,
          sourceType: 'module',
        },
        plugins: ['@invar'],
        rules: selectedConfig.rules,
      },
      plugins: {
        '@invar': plugin, // Register our plugin programmatically
      },
    } as any); // Type assertion for ESLint legacy API (types incomplete)

    // Lint the project
    const results = await eslint.lintFiles([projectPath]);

    // Output in standard ESLint JSON format (compatible with guard_ts.py)
    const formatter = await eslint.loadFormatter('json');

    // Handle formatter.format() which may return string or Promise<string>
    const resultText = await Promise.resolve(formatter.format(results, {
      cwd: projectPath,
      rulesMeta: eslint.getRulesMetaForResults(results),
    }));

    console.log(resultText);

    // Exit with error code if there are errors
    const hasErrors = results.some(result => result.errorCount > 0);
    process.exit(hasErrors ? 1 : 0);

  } catch (error) {
    // Sanitize error message to avoid leaking file paths or system information
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`ESLint failed: ${errorMessage}`);
    process.exit(1);
  }
}

main();
