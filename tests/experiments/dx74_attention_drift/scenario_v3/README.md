# DX-74 Experiment V3: General Bug Detection

**Goal:** Test strategies for detecting ALL bug types, not just security patterns.

## Key Difference from V2

| Aspect | V2 | V3 |
|--------|----|----|
| Focus | Security review | General bug detection |
| Bug types | 87% pattern-based | 50% semantic-based |
| Grep advantage | High | Moderate |
| Contract relevance | Low | High |

## Bug Distribution

| Category | Count | % | Grep-able |
|----------|-------|---|-----------|
| Syntactic (security) | 10 | 33% | Yes |
| Semantic (logic) | 15 | 50% | No |
| Contract violations | 5 | 17% | No |
| **Total** | **30** | 100% | 33% |

## Semantic Bug Types

| Type | Description | Example |
|------|-------------|---------|
| Off-by-one | Boundary errors | `range(len(arr))` vs `range(len(arr)-1)` |
| Wrong operator | Comparison errors | `>` vs `>=` |
| Missing edge case | Unhandled inputs | No empty list check |
| Mutable default | Python gotcha | `def f(x=[])` |
| Type mismatch | Return type wrong | Returns None when type says User |
| State mutation | Shared state bugs | Modifying passed-in list |
| Logic inversion | Condition reversed | `if x` should be `if not x` |
| Missing return | Implicit None | Function falls through |

## Files

| File | Lines | Bugs | Focus |
|------|-------|------|-------|
| data_processor.py | ~400 | 8 | Logic, edge cases |
| user_manager.py | ~350 | 7 | State, types |
| calculator.py | ~300 | 6 | Math, boundaries |
| validator.py | ~250 | 5 | Conditions, contracts |
| cache_service.py | ~300 | 4 | State, concurrency |

## Strategies to Test

| Strategy | Method | Expected Strength |
|----------|--------|-------------------|
| B | Grep-only | Syntactic bugs |
| J | Map + Grep | Coverage + patterns |
| K | Sig + Contracts | Semantic bugs |
| L | Full hybrid | All types |

## Hypothesis

For general bug detection:
- K (Contract-driven) > B (Grep) for semantic bugs
- L (Full hybrid) achieves highest overall detection
- Strategy choice should depend on bug type distribution
