## Commands (TypeScript)

```bash
# Verification (Python CLI - works for TypeScript)
invar guard                  # Full: tsc + eslint + vitest + ts-analyzer
invar guard --json           # Agent-friendly v2.0 JSON output
invar guard --changed        # Modified files only

# Analysis
invar sig <file>             # Show function signatures
invar map --top 10           # Most-referenced symbols
```

## Guard Output (v2.0 JSON)

```json
{
  "version": "2.0",
  "language": "typescript",
  "status": "passed",
  "contracts": {
    "coverage": {"total": 10, "withContracts": 7, "percent": 70},
    "quality": {"strong": 3, "medium": 2, "weak": 1, "useless": 0},
    "blind_spots": [
      {"function": "deleteUser", "risk": "high", "suggested_schema": "z.object({...})"}
    ]
  }
}
```

## Configuration (TypeScript)

```json
// package.json
{
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "lint": "eslint src/"
  }
}
```

```javascript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.property.ts'],
  },
});
```

## Embedded Node Tools

Invar includes bundled TypeScript analysis tools (no npm install required):

| Tool | Purpose |
|------|---------|
| **ts-analyzer** | Contract coverage, blind spot detection |
| **fc-runner** | Property-based testing with fast-check |
| **quick-check** | Fast pre-commit verification (<1s) |

These are called automatically by `invar guard` when analyzing TypeScript projects.
