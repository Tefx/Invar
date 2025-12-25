# DX-37: Coverage Integration

> **"What you don't test, you don't know."**

**Status:** Draft
**Created:** 2025-12-25
**Origin:** Extracted from DX-33 Option D
**Effort:** Medium
**Risk:** Low

## Problem Statement

Guard currently verifies code through multiple phases:
- Static analysis (architecture rules)
- Doctests (example-based)
- CrossHair (symbolic execution)
- Hypothesis (property-based)

However, there's no visibility into which code paths are actually exercised. Dead code and untested branches remain invisible until adversarial review finds them.

## Proposed Solution

Add `--coverage` flag to Guard:

```bash
invar guard --coverage  # Report uncovered branches
```

### Output Example

```
Coverage Analysis:
  src/invar/core/parser.py: 94% (3 uncovered branches)
    Line 127: else branch never taken
    Line 203-205: exception handler never triggered
  src/invar/core/rules.py: 89% (5 uncovered branches)
    ...

Overall: 91% branch coverage
```

## Implementation Approach

### Option A: Pytest-cov Integration

```python
# In guard_helpers.py
def run_with_coverage(files: list[Path]) -> CoverageReport:
    """Run all test phases with coverage collection."""
    import coverage

    cov = coverage.Coverage(branch=True)
    cov.start()

    # Run existing phases
    run_doctests_phase(files)
    run_property_tests_phase(files)

    cov.stop()
    return cov.get_data()
```

**Pros:** Leverages existing coverage.py ecosystem
**Cons:** Adds dependency, slower execution

### Option B: Lightweight Branch Counter

Custom AST-based branch detection without full coverage:

```python
def find_uncovered_branches(source: str, executed_lines: set[int]) -> list[Branch]:
    """Find branches where only one path was taken."""
    ...
```

**Pros:** No new dependency, faster
**Cons:** Less accurate, more implementation work

## Technical Considerations

1. **Performance Impact**
   - Coverage collection adds ~20-30% overhead
   - Should be opt-in (`--coverage` flag)

2. **Integration Points**
   - Doctests: pytest-doctest with coverage
   - Hypothesis: Coverage during property test execution
   - CrossHair: May not be compatible with coverage

3. **Reporting**
   - Branch coverage (not just line coverage)
   - Integration with existing Guard output format
   - Agent-friendly JSON output

## Dependencies

```toml
[project.optional-dependencies]
coverage = ["coverage[toml]>=7.0"]
```

## Success Criteria

- [ ] `invar guard --coverage` collects branch coverage
- [ ] Reports uncovered branches with file:line references
- [ ] Performance overhead < 30%
- [ ] Works with existing verification phases

## Open Questions

1. Should coverage be opt-in or always-on?
2. What's the minimum coverage threshold for warnings?
3. Should we track coverage trends over time?

## Related

- DX-33: Verification Blind Spots Analysis (origin)
- DX-19: Smart Guard verification levels
