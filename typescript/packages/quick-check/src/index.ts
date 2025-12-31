/**
 * @invar/quick-check - Fast pre-commit verification for TypeScript projects
 *
 * Provides sub-second verification using tsc --incremental and eslint --cache.
 * Designed for git pre-commit hooks where speed is critical.
 */

import { execSync, type ExecSyncOptions } from 'node:child_process';
import { existsSync, statSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { z } from 'zod';

// ============================================================================
// Schemas (Zod for runtime validation)
// ============================================================================

export const QuickCheckOptionsSchema = z.object({
  path: z.string().default('.'),
  skipTsc: z.boolean().default(false),
  skipEslint: z.boolean().default(false),
  verbose: z.boolean().default(false),
});

export type QuickCheckOptions = z.infer<typeof QuickCheckOptionsSchema>;

export const CheckResultSchema = z.object({
  passed: z.boolean(),
  cached: z.boolean(),
  duration_ms: z.number(),
  error: z.string().optional(),
});

export type CheckResult = z.infer<typeof CheckResultSchema>;

export const QuickCheckResultSchema = z.object({
  passed: z.boolean(),
  duration_ms: z.number(),
  checks: z.object({
    tsc: CheckResultSchema.optional(),
    eslint: CheckResultSchema.optional(),
  }),
});

export type QuickCheckResult = z.infer<typeof QuickCheckResultSchema>;

// ============================================================================
// Cache Detection
// ============================================================================

/**
 * Check if tsc incremental cache exists and is recent.
 */
function hasTscCache(projectPath: string): boolean {
  const tsBuildInfo = join(projectPath, 'tsconfig.tsbuildinfo');
  if (!existsSync(tsBuildInfo)) return false;

  try {
    const stats = statSync(tsBuildInfo);
    const ageMs = Date.now() - stats.mtimeMs;
    // Consider cache valid if less than 1 hour old
    return ageMs < 60 * 60 * 1000;
  } catch {
    return false;
  }
}

/**
 * Check if eslint cache exists.
 */
function hasEslintCache(projectPath: string): boolean {
  const eslintCache = join(projectPath, '.eslintcache');
  return existsSync(eslintCache);
}

/**
 * Find tsconfig.json in project path or parent directories.
 */
function findTsconfig(projectPath: string): string | null {
  let current = resolve(projectPath);
  const root = resolve('/');

  while (current !== root) {
    const tsconfig = join(current, 'tsconfig.json');
    if (existsSync(tsconfig)) {
      return tsconfig;
    }
    current = resolve(current, '..');
  }

  return null;
}

/**
 * Check if eslint config exists.
 */
function hasEslintConfig(projectPath: string): boolean {
  const configFiles = [
    '.eslintrc',
    '.eslintrc.js',
    '.eslintrc.cjs',
    '.eslintrc.json',
    '.eslintrc.yaml',
    '.eslintrc.yml',
    'eslint.config.js',
    'eslint.config.mjs',
    'eslint.config.cjs',
  ];

  for (const file of configFiles) {
    if (existsSync(join(projectPath, file))) {
      return true;
    }
  }

  // Check package.json for eslintConfig
  const pkgPath = join(projectPath, 'package.json');
  if (existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
      if (pkg.eslintConfig) return true;
    } catch {
      // Ignore parse errors
    }
  }

  return false;
}

// ============================================================================
// Runners
// ============================================================================

/**
 * Run tsc with incremental compilation.
 */
function runTsc(projectPath: string, verbose: boolean): CheckResult {
  const start = Date.now();
  const cached = hasTscCache(projectPath);

  const tsconfig = findTsconfig(projectPath);
  if (!tsconfig) {
    return {
      passed: true,
      cached: false,
      duration_ms: Date.now() - start,
      error: 'No tsconfig.json found, skipping tsc',
    };
  }

  try {
    const options: ExecSyncOptions = {
      cwd: projectPath,
      stdio: verbose ? 'inherit' : 'pipe',
      encoding: 'utf-8',
    };

    // Use --incremental for speed, --noEmit for type-check only
    execSync('npx tsc --noEmit --incremental --pretty false', options);

    return {
      passed: true,
      cached,
      duration_ms: Date.now() - start,
    };
  } catch (error) {
    const stderr =
      error instanceof Error && 'stderr' in error
        ? String((error as { stderr?: unknown }).stderr)
        : String(error);

    return {
      passed: false,
      cached,
      duration_ms: Date.now() - start,
      error: stderr.slice(0, 500), // Truncate for JSON output
    };
  }
}

/**
 * Run eslint with cache.
 */
function runEslint(projectPath: string, verbose: boolean): CheckResult {
  const start = Date.now();
  const cached = hasEslintCache(projectPath);

  if (!hasEslintConfig(projectPath)) {
    return {
      passed: true,
      cached: false,
      duration_ms: Date.now() - start,
      error: 'No eslint config found, skipping eslint',
    };
  }

  try {
    const options: ExecSyncOptions = {
      cwd: projectPath,
      stdio: verbose ? 'inherit' : 'pipe',
      encoding: 'utf-8',
    };

    // Use --cache for speed
    execSync('npx eslint --cache "src/**/*.ts"', options);

    return {
      passed: true,
      cached,
      duration_ms: Date.now() - start,
    };
  } catch (error) {
    const stderr =
      error instanceof Error && 'stderr' in error
        ? String((error as { stderr?: unknown }).stderr)
        : String(error);

    return {
      passed: false,
      cached,
      duration_ms: Date.now() - start,
      error: stderr.slice(0, 500),
    };
  }
}

// ============================================================================
// Main API
// ============================================================================

/**
 * Run quick verification checks.
 *
 * @param options - Configuration options
 * @returns Result object with pass/fail status and timing
 *
 * @example
 * ```typescript
 * import { quickCheck } from '@invar/quick-check';
 *
 * const result = await quickCheck({ path: './my-project' });
 * if (result.passed) {
 *   console.log(`Checks passed in ${result.duration_ms}ms`);
 * }
 * ```
 */
export function quickCheck(options: Partial<QuickCheckOptions> = {}): QuickCheckResult {
  const opts = QuickCheckOptionsSchema.parse(options);
  const projectPath = resolve(opts.path);
  const start = Date.now();

  const result: QuickCheckResult = {
    passed: true,
    duration_ms: 0,
    checks: {},
  };

  // Run tsc
  if (!opts.skipTsc) {
    const tscResult = runTsc(projectPath, opts.verbose);
    result.checks.tsc = tscResult;
    if (!tscResult.passed) {
      result.passed = false;
    }
  }

  // Run eslint
  if (!opts.skipEslint) {
    const eslintResult = runEslint(projectPath, opts.verbose);
    result.checks.eslint = eslintResult;
    if (!eslintResult.passed) {
      result.passed = false;
    }
  }

  result.duration_ms = Date.now() - start;
  return result;
}

export default quickCheck;
