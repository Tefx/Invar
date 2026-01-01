# Invar TypeScript Tooling

This directory contains optional TypeScript/Node.js packages that enhance Invar's TypeScript verification capabilities.

## Packages

| Package | Description |
|---------|-------------|
| `@invar/quick-check` | Fast pre-commit verification (<1s) |
| `@invar/ts-analyzer` | Deep contract analysis using TypeScript Compiler API |
| `@invar/fc-runner` | Property-based testing with fast-check |
| `@invar/eslint-plugin` | Invar-specific ESLint rules |

## Installation

### For Users

These packages are **optional**. Basic TypeScript verification works without them via subprocess calls to `tsc`, `eslint`, and `vitest`.

To install enhanced features:

```bash
# Install individual packages
npm install -D @invar/quick-check @invar/ts-analyzer @invar/fc-runner @invar/eslint-plugin

# Or install all at once
npm install -D @invar/quick-check @invar/ts-analyzer @invar/fc-runner @invar/eslint-plugin
```

### For Developers

This is a pnpm monorepo:

```bash
cd typescript
pnpm install
pnpm build
pnpm test
```

## Architecture

```
Python (invar-tools)          Node (optional packages)
       │                              │
       │ subprocess                   │
       └──────────────────────────────┘
              │
              ├── npx @invar/quick-check --json
              ├── npx @invar/ts-analyzer --json
              └── npx @invar/fc-runner --json
```

Python calls these packages via `npx` and parses their JSON output. If packages are not installed, Python falls back to basic subprocess verification.

## Development

### Build All Packages

```bash
pnpm build
```

### Run Tests

```bash
pnpm test
```

### Publish

```bash
pnpm -r publish --access public
```

## ESLint Plugin Rules

| Rule | Description |
|------|-------------|
| `@invar/require-schema-validation` | Zod-typed params must have `.parse()` |
| `@invar/no-io-in-core` | Forbid I/O imports in `/core/` |
| `@invar/shell-result-type` | Shell functions must return `Result<T, E>` |
| `@invar/no-any-in-schema` | Forbid `z.any()` in schemas |
| `@invar/require-jsdoc-example` | Exported functions need `@example` |

### Usage

```javascript
// eslint.config.js
import invarPlugin from '@invar/eslint-plugin';

export default [
  {
    plugins: { '@invar': invarPlugin },
    rules: {
      '@invar/require-schema-validation': 'error',
      '@invar/no-io-in-core': 'error',
    },
  },
];
```

## Part of LX-06

See [LX-06 Proposal](../docs/proposals/LX-06-typescript-tooling.md) for full design documentation.
