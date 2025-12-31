## Commands (TypeScript)

```bash
# Verification
npm run guard                # Full: tsc + eslint + vitest + fast-check
npm run guard:static         # Static only (quick debug)
npm run guard:changed        # Modified files only

# Analysis (when invar-ts available)
invar sig <file>             # Show Zod schemas + signatures
invar map --top 10           # Most-referenced symbols
```

## Configuration (TypeScript)

```json
// package.json
{
  "scripts": {
    "guard": "tsc --noEmit && eslint . && vitest run",
    "guard:static": "tsc --noEmit && eslint .",
    "test": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

```javascript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json'],
    },
  },
});
```
