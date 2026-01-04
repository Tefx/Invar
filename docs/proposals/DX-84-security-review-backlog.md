# DX-84: Security Review Backlog (TypeScript & Python Guard)

**Status:** Active
**Created:** 2026-01-04
**Priority:** Medium (Code Quality)
**Category:** Technical Debt

---

## Context

During comprehensive security review of TypeScript and Python Guard implementations (2026-01-04), we identified and fixed 9 security issues (1 Critical, 8 Major). This proposal tracks the remaining minor issues that were not addressed in the immediate fix cycle.

**Security fixes completed:**
- TypeScript: 1 Critical + 6 Major issues fixed
- Python: 2 Major issues fixed
- All e2e tests passing
- Production-ready for deployment

**Remaining backlog:** 13 minor code quality issues

---

## TypeScript Guard - Remaining Issues (9)

### R2-002: Type Safety Bypass
**File:** `typescript/packages/eslint-plugin/src/cli.ts:113`
**Issue:** Type assertion `as any` on ESLint config bypasses TypeScript safety
**Severity:** Minor
**Fix:** Define proper type for ESLint config or use type-safe configuration
**Impact:** Potential runtime type errors if ESLint config changes

### R2-003: Magic Number Duplication
**File:** `typescript/packages/eslint-plugin/src/rules/shell-complexity.ts:80,145`
**Issue:** `MAX_DEPTH = 10` repeated twice (in `countStatements` and `calculateComplexity`)
**Severity:** Minor
**Fix:** Extract to named constant at module level
**Impact:** Maintenance - changing depth limit requires two edits

### R2-004: Arbitrary Length Check
**File:** `typescript/packages/eslint-plugin/src/rules/shell-complexity.ts:254`
**Issue:** Function name length check `functionName.length < 3` is arbitrary
**Severity:** Minor
**Fix:** Make configurable or document why 3 characters
**Impact:** May skip valid short function names (e.g., `do`, `go`)

### R2-005: Magic Numbers in Pure Logic Detection
**File:** `typescript/packages/eslint-plugin/src/rules/no-pure-logic-in-shell.ts:91,95`
**Issue:** `MAX_DEPTH = 10` and `hasSubstantialLogic > 3` are magic numbers
**Severity:** Minor
**Fix:** Extract to named constants with semantic names
**Impact:** Code clarity and maintainability

### R2-006: Incomplete Argument Validation
**File:** `typescript/packages/fc-runner/src/cli.ts:110,117`
**Issue:** Argument parsing assumes next arg exists via `args[i + 1]` check, but doesn't validate it's not another flag
**Example:** `--seed --verbose` would try to parse `--verbose` as a number
**Severity:** Minor
**Fix:** Add check: `args[i + 1] && !args[i + 1].startsWith('--')`
**Impact:** Confusing error messages on malformed CLI usage

### R2-007: Unsafe Type Cast
**File:** `typescript/packages/fc-runner/src/cli.ts:157`
**Issue:** `as unknown as PropertyDefinition<Record<string, unknown>>[]` loses type safety
**Severity:** Minor
**Fix:** Use proper generic typing or validation
**Impact:** Potential runtime type errors

### R2-008: Tool Name Validation Too Strict
**File:** `guard_ts.py:313` (affects TypeScript tools too)
**Issue:** Tool name validation allows underscore but rejects dots. Tool names like `tsc.cmd` (Windows) would fail
**Severity:** Minor
**Fix:** Extend validation: `c.isalnum() or c in "-_."`
**Impact:** Windows compatibility issues

### R2-010: Silent JSON Suppression
**File:** `guard_ts.py:474`
**Issue:** `contextlib.suppress(json.JSONDecodeError)` silently ignores invalid JSON
**Severity:** Minor
**Fix:** Log warning or add comment explaining why silent suppression is acceptable
**Impact:** Difficult debugging when JSON is malformed

### R2-011: Lost Diagnostic Information
**File:** `guard_ts.py:791-793`
**Issue:** Empty `pass` statement on doctest failure loses diagnostic information
**Severity:** Info
**Fix:** At minimum, log to `result.tool_errors` for visibility
**Impact:** Harder to debug doctest generation failures

---

## Python Guard - Remaining Issues (4)

### PY-02: Silent Cache Failure
**File:** `src/invar/shell/prove/cache.py:67`
**Issue:** Silent JSON decode failure in cache loading - errors are swallowed
**Severity:** Minor
**Fix:** Log warning when cache is corrupted
**Impact:** Cache corruption goes unnoticed, leading to performance degradation

### PY-04: Generic Error String
**File:** `src/invar/shell/prove/cache.py:135`
**Issue:** `OSError` catch returns generic "error" string without details
**Severity:** Info
**Fix:** Include error message: `f"Cache error: {e}"`
**Impact:** Difficult debugging of cache-related issues

### PY-05: Overly Broad Exception Handler
**File:** `src/invar/shell/guard_output.py:84`
**Issue:** Bare `except Exception` in `show_file_context`
**Severity:** Info
**Fix:** Catch specific exceptions (OSError, UnicodeDecodeError)
**Impact:** May mask unexpected errors

### PY-06: Missing Explicit Timeout
**File:** `src/invar/shell/prove/guard_ts.py:779-787`
**Issue:** Doctest generation subprocess missing explicit timeout parameter
**Severity:** Info
**Fix:** Add `timeout=60` to subprocess.run call
**Impact:** Doctest generation could hang indefinitely

---

## Positive Patterns to Preserve

**TypeScript:**
- Symlink resolution via `realpathSync()` before security checks
- Comprehensive NaN validation on numeric inputs
- Explicit TOCTOU acknowledgment in comments

**Python:**
- Result[T, E] monad enforcing explicit error handling
- No `shell=True` usage (all subprocess calls use list args)
- Consistent timeout parameters on all subprocess calls
- Comprehensive exception handling (OSError, UnicodeDecodeError, TimeoutExpired)

---

## Recommendation

**Priority:** Medium
**Timeline:** Address in future refactoring cycles (not blocking current release)

**Suggested Approach:**
1. Create issues for each category (TypeScript minor, Python minor)
2. Address during normal maintenance when touching related code
3. No dedicated sprint needed - opportunistic fixes

**Not Blocking Because:**
- All security and functionality issues resolved
- e2e tests passing
- Code quality issues, not correctness issues
- Production deployment ready

---

## References

- Security Review: 2026-01-04 adversarial code review (2 rounds)
- Fixed Issues: 1 Critical + 8 Major (see completed fixes)
- e2e Validation: Paralex project TypeScript Guard passing
- Python Guard: All verification passing (static + doctest + CrossHair + property tests)
