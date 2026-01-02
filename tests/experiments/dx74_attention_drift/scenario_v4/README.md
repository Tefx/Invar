# DX-74 Experiment V4: Full Checklist Coverage

**Goal:** Test strategies against ALL review checklist categories (A-G)

## Comparison with Previous Experiments

| Aspect | V2 | V3 | V4 |
|--------|----|----|----|
| Focus | Security | Logic | **Full Checklist** |
| Checklist coverage | F only | E, F, G | **A-G complete** |
| Bug distribution | 87% syntactic | 50% semantic | **Realistic** |
| Invar-specific | No | No | **Yes (A, B, D)** |

## Bug Distribution (Realistic)

| Category | Count | % | Description |
|----------|-------|---|-------------|
| A. Contract Issues | 8 | 16% | Weak/missing @pre/@post |
| B. Doctest Issues | 8 | 16% | Missing/weak tests |
| C. Code Quality | 6 | 12% | Duplication, naming, complexity |
| D. Escape Hatch | 4 | 8% | Unjustified @invar:allow |
| E. Logic Issues | 10 | 20% | Errors, dead code, bypass |
| F. Security | 6 | 12% | Secrets, injection, auth |
| G. Error Handling | 8 | 16% | Exceptions, leaks, fallback |
| **Total** | **50** | 100% | |

## Files

| File | Lines | Focus |
|------|-------|-------|
| math_utils.py | ~300 | Contracts (A), Logic (E) |
| user_auth.py | ~350 | Security (F), Error (G) |
| data_service.py | ~400 | Doctests (B), Quality (C) |
| config_manager.py | ~250 | Escape Hatch (D), Error (G) |
| report_generator.py | ~300 | All categories mixed |

## Strategies to Test

| Strategy | Method | Expected Strength |
|----------|--------|-------------------|
| B | Grep only | F (security patterns) |
| K | Sig + Contracts | A, B, E (semantic) |
| L | Full Hybrid | All categories |
| **M** | **Invar-Native** | A, B, D (Invar-specific) |

### Strategy M: Invar-Native Review

```python
def review_invar_native(scope):
    for file in scope:
        # 1. Check contract quality (A)
        sigs = invar_sig(file)
        for fn in sigs:
            if fn.pre == "lambda x: True":
                report("Trivial @pre")
            if not fn.post:
                report("Missing @post")

        # 2. Check doctest coverage (B)
        for fn in sigs:
            if not fn.has_doctest:
                report("Missing doctest")
            if fn.doctest_count < 3:
                report("Insufficient doctests")

        # 3. Check escape hatches (D)
        allows = grep("@invar:allow", file)
        for allow in allows:
            if not has_justification(allow):
                report("Unjustified escape hatch")

        # 4. Run guard for mechanical checks
        invar_guard(file)
```

## Expected Outcomes

| Strategy | A | B | C | D | E | F | G | Total |
|----------|---|---|---|---|---|---|---|-------|
| B: Grep | 0% | 0% | 0% | 50% | 20% | 100% | 30% | ~25% |
| K: Sig | 80% | 80% | 30% | 0% | 80% | 50% | 50% | ~55% |
| L: Hybrid | 80% | 80% | 50% | 50% | 90% | 100% | 70% | ~75% |
| M: Invar | 100% | 100% | 30% | 100% | 50% | 50% | 40% | ~65% |
