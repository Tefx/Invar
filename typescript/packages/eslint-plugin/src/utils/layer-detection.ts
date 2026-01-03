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
 */
export const LAYER_LIMITS: Record<Layer, LayerLimits> = {
  core: {
    maxFileLines: 500,
    maxFunctionLines: 50,
  },
  shell: {
    maxFileLines: 700,
    maxFunctionLines: 100,
  },
  tests: {
    maxFileLines: 800,
    maxFunctionLines: 150,
  },
  default: {
    maxFileLines: 600,
    maxFunctionLines: 50,
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
    normalized.endsWith('.test.js') ||
    normalized.endsWith('.spec.ts') ||
    normalized.endsWith('.spec.js')
  ) {
    return 'tests';
  }

  // Priority 2: Core layer
  if (normalized.includes('/core/')) {
    return 'core';
  }

  // Priority 3: Shell layer
  if (normalized.includes('/shell/')) {
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
 * // => { maxFileLines: 500, maxFunctionLines: 50 }
 */
export function getLimits(filename: string): LayerLimits {
  const layer = getLayer(filename);
  return LAYER_LIMITS[layer];
}
