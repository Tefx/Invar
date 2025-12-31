#!/usr/bin/env node
// Bundle CLI tools for standalone distribution.
// Uses esbuild to create single-file bundles with all dependencies included.
// Output goes to packages/*/dist/bundle.js (alongside the regular tsc output).

import * as esbuild from 'esbuild';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const packagesDir = join(__dirname, '..', 'packages');

// Packages to bundle (must have src/cli.ts)
const PACKAGES = ['ts-analyzer', 'fc-runner', 'quick-check'];

async function bundlePackage(name) {
  const pkgDir = join(packagesDir, name);
  const entry = join(pkgDir, 'src', 'cli.ts');
  const outfile = join(pkgDir, 'dist', 'bundle.js');

  if (!existsSync(entry)) {
    console.log(`  Skipping ${name} (no src/cli.ts)`);
    return false;
  }

  await esbuild.build({
    entryPoints: [entry],
    bundle: true,
    platform: 'node',
    target: 'node18',
    format: 'cjs',  // CJS for maximum compatibility with standalone execution
    outfile,
    // No banner - source files already have shebang which esbuild preserves
    // Minify for smaller size
    minify: true,
    // Keep names for better error messages
    keepNames: true,
    // External packages that should be available at runtime
    external: [],
  });

  console.log(`  Bundled ${name}`);
  return true;
}

async function main() {
  console.log('Bundling CLI tools...\n');

  let success = 0;
  for (const pkg of PACKAGES) {
    try {
      if (await bundlePackage(pkg)) {
        success++;
      }
    } catch (error) {
      console.error(`  ERROR bundling ${pkg}:`, error.message);
    }
  }

  console.log(`\nDone! Bundled ${success}/${PACKAGES.length} packages.`);
  process.exit(success === PACKAGES.length ? 0 : 1);
}

main();
