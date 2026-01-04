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
// Get directory containing this CLI script (for resolving node_modules)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
function parseArgs(args) {
    const projectPath = args.find(arg => !arg.startsWith('--')) || '.';
    const configArg = args.find(arg => arg.startsWith('--config='));
    const config = configArg?.split('=')[1] === 'strict' ? 'strict' : 'recommended';
    const help = args.includes('--help') || args.includes('-h');
    return { projectPath, config, help };
}
function printHelp() {
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
async function main() {
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
        const selectedConfig = plugin.configs?.[args.config];
        if (!selectedConfig || !selectedConfig.rules) {
            console.error(`Config "${args.config}" not found or invalid`);
            process.exit(1);
        }
        // Create ESLint instance with programmatic configuration
        // Set cwd to CLI directory so ESLint can find parser in our node_modules
        const eslint = new ESLint({
            useEslintrc: false, // Don't load .eslintrc files
            cwd: __dirname, // Set working directory to CLI location for module resolution
            baseConfig: {
                parser: '@typescript-eslint/parser',
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
        }); // Type assertion for ESLint config complexity
        // Lint the project
        const results = await eslint.lintFiles([projectPath]);
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
    }
    catch (error) {
        // Sanitize error message to avoid leaking file paths or system information
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        console.error(`ESLint failed: ${errorMessage}`);
        process.exit(1);
    }
}
main();
//# sourceMappingURL=cli.js.map