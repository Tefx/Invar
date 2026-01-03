# LX-14: TypeScript Doctest Execution Integration

**Status:** Archived (Merged into LX-15)
**Created:** 2026-01-04
**Archived:** 2026-01-04
**Superseded By:** [LX-15: TypeScript Guard Parity](../LX-15-typescript-guard-parity.md)

> **Note:** This proposal has been merged into LX-15 for unified tracking.
> - Layer 1 (ESLint enforcement): ✅ Complete
> - Layer 2 (Doctest execution) → LX-15 Phase 1.1-1.2
> - Layer 3 (Coverage tracking) → LX-15 Phase 1.3

---

**Original Priority:** Medium (Phase A complete, this is Phase B)
**Original Depends On:** LX-06 (TypeScript Tooling)

## Executive Summary

Integrate `generate-jsdoc-example-tests` to execute @example annotations from JSDoc as tests, achieving parity with Python's doctest enforcement.

**Current State (Phase A - Complete)**:
- ✅ ESLint rule `require-jsdoc-example` upgraded to `error` (Layer 1)
- ✅ Exported functions MUST have @example in JSDoc
- ❌ Examples are not executed as tests (Layer 2)
- ❌ No coverage tracking (Layer 3)

**Next Steps**:
- Layer 2: Generate and execute tests from @example
- Layer 3: Track doctest coverage with custom Vitest reporter

---

## Problem Statement

### Current Gap

TypeScript has **enforcement without execution**:

```typescript
// ✅ PASS: ESLint requires @example to exist
/**
 * Calculate square of a number.
 *
 * @example
 * square(5); // => 25
 */
export function square(x: number): number {
  return x * x * x;  // 💥 BUG! But no test catches it
}
```

Python equivalent **fails immediately**:

```python
def square(x: int) -> int:
    """
    >>> square(5)
    25
    """
    return x * x * x  # 💥 Doctest FAILS: expected 25, got 125
```

### Required: 3-Layer Enforcement

| Layer | Status | Purpose |
|-------|--------|---------|
| **Layer 1: Existence** | ✅ Complete | ESLint error if @example missing |
| **Layer 2: Execution** | ❌ Planned | Run examples as tests |
| **Layer 3: Coverage** | ❌ Future | Track which functions have tested examples |

---

## Solution Design

### Layer 2: Doctest Execution

#### Tool: generate-jsdoc-example-tests

**Repository:** [jsdoc-example-to-test](https://github.com/tjenkinson/jsdoc-example-to-test)
**Status:** Active (2025), Vitest-compatible

**How it works:**
1. Scans TypeScript files for JSDoc @example blocks
2. Generates `.test.ts` files from examples
3. Uses special syntax `// =>` for assertions
4. Integrates with Vitest (no extra test runner)

#### Example Workflow

**Source file** (`src/core/math.ts`):
```typescript
/**
 * Calculate square of a number.
 *
 * @example
 * square(5); // => 25
 * square(0); // => 0
 * square(-3); // => 9
 */
export function square(x: number): number {
  return x * x;
}
```

**Generated test** (`src/core/__doctest__/math.test.ts`):
```typescript
// Auto-generated from JSDoc @example
import { square } from '../math.js';
import { describe, it, expect } from 'vitest';

describe('Doctests: math.ts', () => {
  it('square example 1', () => {
    expect(square(5)).toBe(25);
  });

  it('square example 2', () => {
    expect(square(0)).toBe(0);
  });

  it('square example 3', () => {
    expect(square(-3)).toBe(9);
  });
});
```

**Execution:**
```bash
npx vitest run  # Runs both regular tests AND doctest-generated tests
```

---

## Implementation Plan

### Phase B1: Basic Integration (3 days)

#### Step 1: Add Dependency
```bash
cd typescript
pnpm add -D jsdoc-example-to-test
```

#### Step 2: Add Script to package.json
```json
{
  "scripts": {
    "doctest:generate": "jsdoc-example-to-test --input 'packages/*/src/**/*.ts' --output '__doctest__'",
    "test": "npm run doctest:generate && vitest run",
    "test:watch": "vitest"
  }
}
```

#### Step 3: Configure Generation

Create `jsdoc-example-to-test.config.js`:
```javascript
export default {
  // Input glob patterns
  include: ['packages/*/src/**/*.ts'],

  // Exclude patterns
  exclude: ['**/*.test.ts', '**/__doctest__/**'],

  // Output directory for generated tests
  outputDir: '__doctest__',

  // Test framework
  framework: 'vitest',

  // Clean generated tests before regenerating
  clean: true,
};
```

#### Step 4: Update .gitignore
```
# Generated doctest files
**/__doctest__/
```

#### Step 5: Integrate with guard_ts.py

Modify `src/invar/shell/prove/guard_ts.py`:

```python
def run_vitest(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run Vitest for test execution."""

    # NEW: Generate doctest files before running vitest
    try:
        subprocess.run(
            ["npm", "run", "doctest:generate"],
            cwd=project_path,
            capture_output=True,
            timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        return Failure(f"Doctest generation failed: {e.stderr}")

    # Existing vitest execution code...
    result = subprocess.run(
        ["npx", "vitest", "run", "--reporter=json"],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=300,
    )

    # Parse results (existing code)
    ...
```

**Result**: Every `invar guard` run on TypeScript projects will:
1. Generate tests from @example blocks
2. Run generated tests + regular tests
3. Report failures as violations

---

### Phase B2: Coverage Tracking (5 days)

**Goal**: Implement `@invar/vitest-reporter` (LX-06 Phase 2)

#### Custom Vitest Reporter

Create `typescript/packages/vitest-reporter/`:

```typescript
// src/index.ts
import type { Reporter, Test } from 'vitest';

export default class InvarReporter implements Reporter {
  onFinished(files?: File[]) {
    const stats = {
      total_functions: 0,
      functions_with_doctests: 0,
      doctest_pass: 0,
      doctest_fail: 0,
    };

    // Analyze test files to distinguish doctests from regular tests
    for (const file of files || []) {
      if (file.name.includes('__doctest__')) {
        // This is a generated doctest file
        stats.functions_with_doctests += file.tasks.length;
        for (const test of file.tasks) {
          if (test.result?.state === 'pass') {
            stats.doctest_pass++;
          } else {
            stats.doctest_fail++;
          }
        }
      }
    }

    // Count total exported functions (requires static analysis)
    // ... (integrate with ts-analyzer)

    const coverage = stats.functions_with_doctests / stats.total_functions;

    console.log('\n📊 Doctest Coverage:');
    console.log(`   Functions with doctests: ${stats.functions_with_doctests}/${stats.total_functions}`);
    console.log(`   Coverage: ${(coverage * 100).toFixed(1)}%`);
    console.log(`   Pass: ${stats.doctest_pass} | Fail: ${stats.doctest_fail}`);
  }
}
```

#### Configuration

`vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import InvarReporter from '@invar/vitest-reporter';

export default defineConfig({
  test: {
    reporters: ['default', new InvarReporter()],
  },
});
```

---

## Success Criteria

### Phase B1 (Basic Integration)

- [x] `jsdoc-example-to-test` installed
- [x] `doctest:generate` script works
- [x] Generated tests run with `vitest`
- [x] `guard_ts.py` runs doctest generation automatically
- [x] Doctest failures reported as violations

### Phase B2 (Coverage Tracking)

- [ ] `@invar/vitest-reporter` package created
- [ ] Coverage percentage calculated
- [ ] Output integrated into `guard_ts.py` JSON
- [ ] Warning if coverage < 80%

---

## Comparison with Python

| Feature | Python | TypeScript (After Phase B) |
|---------|--------|---------------------------|
| Require examples | ✅ guard error | ✅ ESLint error |
| Execute examples | ✅ pytest --doctest | ✅ vitest (generated) |
| Coverage tracking | ✅ Built-in | ✅ Custom reporter |
| Failure reporting | ✅ pytest output | ✅ Vitest output |

**Parity achieved** ✅

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `jsdoc-example-to-test` unmaintained | Medium | Fork if needed, simple tool (~500 LOC) |
| Generated tests increase CI time | Low | Cache generated files, only regenerate on source changes |
| False positives from generated tests | Medium | Provide escape hatch: `@example-skip` annotation |

---

## Alternative Tools Considered

| Tool | Pros | Cons | Decision |
|------|------|------|----------|
| `generate-jsdoc-example-tests` | Active (2025), Vitest-compatible | - | ✅ **Selected** |
| `doctest-ts` | Mature | Requires separate runner, not Vitest | ❌ Rejected |
| `jsdoctest` | Old | Mocha-only, unmaintained | ❌ Rejected |

---

## References

### External

- [jsdoc-example-to-test](https://github.com/tjenkinson/jsdoc-example-to-test)
- [Vitest Custom Reporters](https://vitest.dev/guide/reporters.html)

### Internal

- [LX-06: TypeScript Tooling](completed/LX-06-typescript-tooling.md) - Phase 2 mentions `@invar/vitest-reporter`
- [LX-12: TypeScript Contract Enforcement](LX-12-typescript-contract-enforcement.md) - Doctest discussion

---

## Decision Log

### 2026-01-04: Phase A Complete, Plan Phase B

**Completed (Phase A)**:
- ✅ ESLint rule `require-jsdoc-example` upgraded to `error`
- ✅ Layer 1 enforcement complete

**Planned (Phase B)**:
- Layer 2: Doctest execution (3 days)
- Layer 3: Coverage tracking (5 days)

**Rationale**: Phase A provides immediate value (enforcement). Phase B unlocks full parity with Python but requires more integration work.

**Next**: Implement Phase B1 (basic integration) first, validate with real examples, then proceed to Phase B2 (coverage tracking).
