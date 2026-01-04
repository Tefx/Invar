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
import { resolve } from 'path';
import plugin from './index.js';
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
    try {
        // Get the config (with type assertion since we know it exists)
        const selectedConfig = plugin.configs?.[args.config];
        if (!selectedConfig) {
            console.error(`Config "${args.config}" not found`);
            process.exit(1);
        }
        // Create ESLint instance with our plugin pre-configured
        const eslint = new ESLint({
            baseConfig: {
                ...selectedConfig, // Type assertion needed due to ESLint type complexity
                parser: '@typescript-eslint/parser',
                parserOptions: {
                    ecmaVersion: 2022,
                    sourceType: 'module',
                },
            },
            overrideConfig: {
                plugins: {
                    '@invar': plugin,
                },
            },
        });
        // Lint the project
        const results = await eslint.lintFiles([projectPath]);
        // Output in standard ESLint JSON format (compatible with guard_ts.py)
        const formatter = await eslint.loadFormatter('json');
        const resultText = formatter.format(results, {
            cwd: projectPath,
            rulesMeta: eslint.getRulesMetaForResults(results),
        });
        console.log(resultText);
        // Exit with error code if there are errors
        const hasErrors = results.some(result => result.errorCount > 0);
        process.exit(hasErrors ? 1 : 0);
    }
    catch (error) {
        console.error('Error running ESLint:', error);
        process.exit(1);
    }
}
main();
//# sourceMappingURL=cli.js.map