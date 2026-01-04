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
import { statSync, realpathSync } from 'fs';
import { fileURLToPath } from 'url';
import plugin from './index.js';

// Get the directory where this CLI script is located (embedded in site-packages)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

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

  // Validate resolved path is within current working directory
  // This prevents path traversal attacks via "../../../etc/passwd" patterns
  // and symlink-based bypasses (e.g., "./symlink_inside/../../../etc/passwd")
  const cwd = process.cwd();
  try {
    // Use realpath to resolve symlinks and prevent bypass attacks
    const realProjectPath = realpathSync(projectPath);
    const realCwd = realpathSync(cwd);

    if (!realProjectPath.startsWith(realCwd)) {
      console.error(`Error: Project path must be within current directory`);
      console.error(`  Requested: ${args.projectPath}`);
      console.error(`  Resolved: ${realProjectPath}`);
      console.error(`  Working dir: ${realCwd}`);
      process.exit(1);
    }
  } catch (error) {
    // If realpath fails (path doesn't exist), fall back to string comparison
    // This allows error messages to be more specific
    if (!projectPath.startsWith(cwd)) {
      console.error(`Error: Project path must be within current directory`);
      console.error(`  Requested: ${args.projectPath}`);
      console.error(`  Resolved: ${projectPath}`);
      console.error(`  Working dir: ${cwd}`);
      process.exit(1);
    }
  }

  try {
    // Get the rules config for the selected mode
    const selectedConfig = plugin.configs?.[args.config] as any;
    if (!selectedConfig || !selectedConfig.rules) {
      console.error(`Config "${args.config}" not found or invalid`);
      process.exit(1);
    }

    // Create ESLint instance with programmatic configuration
    // Use __dirname (where CLI is located) for module resolution
    // This allows ESLint to find embedded node_modules in site-packages
    const eslint = new ESLint({
      useEslintrc: false, // Don't load .eslintrc files
      cwd: __dirname, // Use CLI location for module resolution (embedded node_modules)
      resolvePluginsRelativeTo: __dirname, // Resolve plugins from embedded location
      baseConfig: {
        parser: '@typescript-eslint/parser', // Will resolve from __dirname/node_modules
        parserOptions: {
          ecmaVersion: 2022,
          sourceType: 'module',
        },
        plugins: ['@invar'],
        rules: selectedConfig.rules,
      },
      plugins: {
        '@invar': plugin, // Register plugin directly
      },
    } as any); // Type assertion for ESLint config complexity

    // Lint the project - detect if path is a file or directory
    // ESLint defaults to .js only, so we need glob patterns for .ts/.tsx
    let filesToLint: string[];

    try {
      const stats = statSync(projectPath);
      // Note: Advisory check for optimization - TOCTOU race condition is acceptable
      // because ESLint will handle file system changes gracefully during actual linting
      if (stats.isFile()) {
        // Single file - lint it directly
        filesToLint = [projectPath];
      } else if (stats.isDirectory()) {
        // Directory - use glob patterns for TypeScript files primarily
        // Note: Focus on TypeScript files as this is a TypeScript Guard tool
        filesToLint = [
          `${projectPath}/**/*.ts`,
          `${projectPath}/**/*.tsx`,
        ];
      } else {
        console.error(`Error: Path is neither a file nor a directory: ${projectPath}`);
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`Error: Cannot access path: ${errorMessage}`);
      process.exit(1);
    }

    const results = await eslint.lintFiles(filesToLint);

    // Output in standard ESLint JSON format (compatible with guard_ts.py)
    const formatter = await eslint.loadFormatter('json');
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
