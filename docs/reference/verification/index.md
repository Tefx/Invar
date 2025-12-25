# Verification Mechanisms

Smart Guard (`invar guard`) provides multi-phase verification with automatic tool routing.

## Verification Levels

| Level | Command | What Runs |
|-------|---------|-----------|
| STATIC | `invar guard --static` | Static analysis only |
| STANDARD | `invar guard` (default) | Static + Doctests + CrossHair + Hypothesis |

## Verification Pipeline

### Phase 1: Static Analysis

**What it checks:**
- File and function size limits
- Contract presence and quality
- Purity violations (Core layer)
- Shell architecture rules

**Files:** `src/invar/core/rules.py`, `src/invar/core/shell_architecture.py`

### Phase 2: Doctests

**What it checks:**
- Example correctness in docstrings
- Contract satisfaction on examples

**Command:** `pytest --doctest-modules` (internal)

**Why doctests matter:**
```python
def sqrt(x: float) -> float:
    """
    >>> sqrt(4.0)  # This RUNS during guard
    2.0
    >>> sqrt(0.0)
    0.0
    """
    return x ** 0.5
```

### Phase 3: CrossHair (Symbolic Verification)

**What it checks:**
- Contract consistency (no impossible @pre)
- Postcondition satisfaction for ALL inputs
- Finds counterexamples automatically

**When it helps:**
```python
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    return x ** 0.5  # CrossHair proves this is correct
```

**Files:** `src/invar/shell/prove.py`

### Phase 4: Hypothesis (Property Testing)

**What it checks:**
- Contract satisfaction with random inputs
- Edge case discovery via shrinking

**Uses:** `deal.cases()` which respects @pre and validates @post

**Files:** `src/invar/core/property_gen.py`

## Tool Selection Logic

| Code Type | Primary Tool | Fallback |
|-----------|-------------|----------|
| Pure functions with contracts | CrossHair | Hypothesis |
| Library-dependent code | Hypothesis | - |
| I/O operations | Doctests | - |

## Performance

| Phase | Typical Time |
|-------|--------------|
| Static | ~0.3s |
| Doctests | ~0.5s |
| CrossHair | ~2-5s (incremental) |
| Hypothesis | ~1-3s |

**Total:** ~3-8s for full verification, ~0.5s for `--static`

## Incremental Mode

CrossHair uses file hashing to skip unchanged files:
- First run: Full verification
- Subsequent: Only changed files

Cache location: `.invar/crosshair_cache.json`
