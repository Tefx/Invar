## Task Completion

A task is complete only when ALL conditions are met:
- Check-In displayed: `✓ Check-In: [project] | [branch] | [clean/dirty]`
- Intent explicitly stated
- Contract written before implementation
- Final displayed: `✓ Final: verification PASS | <errors>, <warnings>`
- User requirement satisfied

**Missing any = Task incomplete.**

---

## Baseline Protocol (Technical Debt)

When working on projects with existing verification failures:

### Establishing Baseline

Before starting implementation:
1. Run verification from **repository root**: `invar_guard(path=".")`
2. If failures exist and are pre-existing debt → **Record as baseline**
3. Note the failure count and affected files

### During Implementation

**Allowed:**
- Continue work despite baseline failures
- Use language-specific local checks (e.g., linters, type checkers, unit tests)
- Focus on ensuring new code doesn't introduce violations

**Required:**
- New code must not expand the failure surface
- Changes to existing files must not add new violations

### Final Output Format

**When baseline is cleared:**
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

**When baseline still exists (known debt):**
```
✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS
```

**If new violations introduced:**
```
✗ Final: guard FAIL | X new errors (baseline: Y)
```

### Guard Best Practices

**Always run from repository root:**
```python
# ✅ CORRECT - Runs from repo root
invar_guard(path=".")

# ❌ WRONG - May fail language detection in subdirectories
invar_guard(path="src/components")
```

**Reason:** Subdirectories may lack language marker files (pyproject.toml, tsconfig.json), causing incorrect detection defaults.

---

*Protocol v5.0 — USBV workflow | [Examples](.invar/examples/)*
