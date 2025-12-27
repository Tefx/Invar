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

**Files:** `src/invar/shell/prove/crosshair.py`

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

## Branch Coverage (DX-37)

Optional branch coverage collection for doctest and hypothesis phases.

### Usage

```bash
invar guard --coverage           # Full verification + coverage
invar guard --coverage --changed # Coverage for changed files only
```

### What It Tracks

| Phase | Coverage | Method |
|-------|----------|--------|
| Doctests | ✅ Yes | `coverage run` subprocess wrapper |
| Hypothesis | ✅ Yes | coverage.py context manager |
| CrossHair | ❌ No | Symbolic execution (Z3 solver) |

**Note:** CrossHair uses symbolic execution in a subprocess, which coverage.py cannot track. This is a fundamental limitation, not a bug.

### Output

```
Coverage Analysis (doctest + hypothesis):
  src/core/parser.py: 94% branch (3 uncovered)
    Line 127: else branch never taken
  src/core/rules.py: 89% branch (5 uncovered)

Overall: 91% branch coverage (doctest + hypothesis)

Note: CrossHair uses symbolic execution; coverage not applicable.
```

### JSON Output (Agent Mode)

```json
{
  "coverage": {
    "enabled": true,
    "phases_tracked": ["doctest", "hypothesis"],
    "phases_excluded": ["crosshair"],
    "overall_branch_coverage": 91.2,
    "files": [...]
  }
}
```

### Requirements

```bash
pip install coverage[toml]>=7.0  # Or: pip install -e ".[dev]"
```

If coverage.py is not installed, guard gracefully degrades with a warning message.

## Incremental Mode

CrossHair uses file hashing to skip unchanged files:
- First run: Full verification
- Subsequent: Only changed files

Cache location: `.invar/crosshair_cache.json`
