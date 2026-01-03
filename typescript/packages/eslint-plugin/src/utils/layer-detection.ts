/**
 * Layer Detection Utilities
 *
 * Detects which architectural layer a file belongs to:
 * - Core: Pure logic, strict limits
 * - Shell: I/O operations, relaxed limits
 * - Tests: Test files, most relaxed limits
 * - Default: Other files
 */

export type Layer = 'core' | 'shell' | 'tests' | 'default';

export interface LayerLimits {
  maxFileLines: number;
  maxFunctionLines: number;
}

/**
 * Default limits for each layer (LX-10).
 *
 * TypeScript limits = Python limits × 1.3 (due to type overhead).
 * - Python Core: 500/50 → TypeScript Core: 650/65
 * - Python Shell: 700/100 → TypeScript Shell: 910/130
 * - Python Tests: 1000/200 → TypeScript Tests: 1300/260
 * - Python Default: 600/80 → TypeScript Default: 780/104
 */
export const LAYER_LIMITS: Record<Layer, LayerLimits> = {
  core: {
    maxFileLines: 650,
    maxFunctionLines: 65,
  },
  shell: {
    maxFileLines: 910,
    maxFunctionLines: 130,
  },
  tests: {
    maxFileLines: 1300,
    maxFunctionLines: 260,
  },
  default: {
    maxFileLines: 780,
    maxFunctionLines: 104,
  },
};

/**
 * Detect layer from filename.
 *
 * Priority: tests > core > shell > default
 *
 * @example
 * getLayer('/project/src/core/parser.ts') // => 'core'
 * getLayer('/project/tests/parser.test.ts') // => 'tests'
 * getLayer('/project/src/shell/io.ts') // => 'shell'
 */
export function getLayer(filename: string): Layer {
  const normalized = filename.replace(/\\/g, '/').toLowerCase();

  // Priority 1: Test files
  if (
    normalized.includes('/test/') ||
    normalized.includes('/tests/') ||
    normalized.includes('/__tests__/') ||
    normalized.endsWith('.test.ts') ||
    normalized.endsWith('.test.tsx') ||
    normalized.endsWith('.test.js') ||
    normalized.endsWith('.test.jsx') ||
    normalized.endsWith('.spec.ts') ||
    normalized.endsWith('.spec.tsx') ||
    normalized.endsWith('.spec.js') ||
    normalized.endsWith('.spec.jsx')
  ) {
    return 'tests';
  }

  // Priority 2: Core layer
  // Use path segment matching to avoid false positives like '/hardcore/'
  if (
    normalized.includes('/core/') ||
    normalized.endsWith('/core') ||
    normalized.startsWith('core/')
  ) {
    return 'core';
  }

  // Priority 3: Shell layer
  // Use path segment matching to avoid false positives like '/eggshell/'
  if (
    normalized.includes('/shell/') ||
    normalized.endsWith('/shell') ||
    normalized.startsWith('shell/')
  ) {
    return 'shell';
  }

  // Default layer
  return 'default';
}

/**
 * Get limits for a filename.
 *
 * @example
 * getLimits('/project/src/core/parser.ts')
 * // => { maxFileLines: 650, maxFunctionLines: 65 }
 */
export function getLimits(filename: string): LayerLimits {
  const layer = getLayer(filename);
  return LAYER_LIMITS[layer];
}
