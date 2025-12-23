# Developer Experience Improvements Proposal

**Date:** 2025-12-21
**Status:** Draft
**Source:** Ultrathink analysis of 9-feature implementation session

---

## Executive Summary

During implementation of 9 proposals (TTY, A1/A2, B4, C1-C5), several friction points were identified that impact both human and AI agent development experience. This proposal addresses these with minimal-effort, high-impact improvements.

**Overall Assessment:** 8/10 - Invar significantly improves development confidence, but ergonomic issues remain.

**Critical Finding (DX-06):** `invar test` and `invar verify` were implemented but never used during development. The developer continued using `pytest --doctest-modules` directly. This reveals that new commands must be integrated into the primary workflow (`invar guard`) to achieve adoption.

---

## Proposals

### DX-01: Improve @pre Lambda Error Messages

**Priority:** ★★★★★ (High impact, low effort)
**Effort:** 0.5 day

#### Problem

When a function has default parameters, the @pre lambda must include them:

```python
# This triggers an error:
@pre(lambda x, y: x > 0)
def process(x: int, y: int, z: int = 10) -> int: ...

# Error message:
# Function 'process' @pre lambda has 2 param(s) but function has 3
```

**Issue:** The fix pattern is non-obvious. Developers (including AI agents) naturally write lambdas without defaults.

#### Solution

Improve the error message to include the fix template:

```python
# Current message:
"Function 'process' @pre lambda has 2 param(s) but function has 3"

# Proposed message:
"Function 'process' @pre lambda has 2 param(s) but function has 3.
 Fix: @pre(lambda x, y, z=10: <condition>)"
```

#### Implementation

```python
# src/invar/core/contracts.py - modify check_param_count_mismatch

def _generate_lambda_fix(func_name: str, params: list[Parameter]) -> str:
    """Generate correct lambda signature including defaults."""
    parts = []
    for p in params:
        if p.default is not None:
            parts.append(f"{p.name}={p.default!r}")
        else:
            parts.append(p.name)
    return f"@pre(lambda {', '.join(parts)}: <condition>)"
```

#### Tasks

```
□ Modify check_param_count_mismatch in contracts.py
  ├── Extract function parameters with defaults
  ├── Generate lambda fix template
  └── Include in error message

□ Update rule_meta.py hint for param_count_mismatch

□ Add doctest for the improved message
```

---

### DX-02: Document Dict Comparison Patterns for Doctests

**Priority:** ★★★ (Documentation)
**Effort:** 0.25 day

#### Problem

Dict ordering in doctests causes failures:

```python
>>> result.constraints
{'min_value': 1, 'max_value': 99}  # May fail!
# Got: {'max_value': 99, 'min_value': 1}
```

#### Solution

Add recommended patterns to INVAR.md:

```markdown
## Doctest Best Practices

**Dict comparison:** Use `sorted()` for deterministic output:
```python
>>> sorted(result.items())
[('max_value', 99), ('min_value', 1)]
```

**Alternative:** Use `==` comparison:
```python
>>> result == {'min_value': 1, 'max_value': 99}
True
```
```

#### Tasks

```
□ Add "Doctest Best Practices" section to INVAR.md
□ Include dict, set, and unordered collection patterns
□ Add example in docs/INVAR-GUIDE.md
```

---

### DX-03: Document `exclude_doctest_lines` Configuration

**Priority:** ★★★★ (High impact on function size limits)
**Effort:** 0.25 day

#### Problem

Guard reports function size violations, suggesting `exclude_doctest_lines=true`:

```
Function 'must_close' has 53 lines (max: 50)
  Extract helper or set exclude_doctest_lines=true (32 code + 21 doctest)
```

But this config option is not documented in INVAR.md.

#### Solution

Add to INVAR.md Configuration section:

```markdown
## Configuration

```toml
[tool.invar.guard]
# ... existing options ...

# Exclude doctest lines from function size calculation
# Useful when comprehensive doctests cause size violations
exclude_doctest_lines = true
```
```

Also add to the function_size rule hint:

```
hint: "Extract helper functions, or set exclude_doctest_lines=true if doctests cause the overflow"
```

#### Tasks

```
□ Add exclude_doctest_lines to INVAR.md Configuration section
□ Update function_size hint in rule_meta.py
□ Add example in pyproject.toml template
```

---

### DX-04: `invar fix --auto` Command

**Priority:** ★★★ (Nice to have)
**Effort:** 1-2 days

#### Problem

Common issues have mechanical fixes that agents and humans must apply manually:
- Missing contracts → Add template `@pre(lambda: True)`
- Param count mismatch → Adjust lambda signature
- Missing Result return type → Add `-> Result[T, E]`

#### Solution

Add `invar fix` command with auto-fix capabilities:

```bash
# Show what would be fixed
invar fix --dry-run

# Apply safe fixes
invar fix --auto

# Fix specific rule
invar fix --rule missing_contract
```

#### Implementation

```python
# src/invar/shell/fix.py

SAFE_FIXES = {
    "missing_contract": add_template_contract,
    "param_count_mismatch": adjust_lambda_params,
    "missing_doctest": add_doctest_placeholder,
}

def fix_file(path: Path, rules: list[str], dry_run: bool) -> Result[FixReport, str]:
    """Apply safe fixes to a file."""
    ...
```

#### Tasks

```
□ Phase 1: Infrastructure (0.5 day)
  ├── Create src/invar/shell/fix.py
  ├── Add fix command to CLI
  └── Implement dry-run mode

□ Phase 2: Safe Fixes (1 day)
  ├── Implement missing_contract fix
  ├── Implement param_count_mismatch fix
  ├── Add --rule filtering
  └── Tests

□ Phase 3: Documentation (0.5 day)
  ├── Add to INVAR.md Commands section
  ├── Document safe vs unsafe fixes
  └── Add to CLAUDE.md workflow
```

---

### DX-05: Contract Templates Library

**Priority:** ★★ (Future enhancement)
**Effort:** 2-3 days

#### Problem

Writing contracts for common patterns is repetitive:
- List processing functions
- File path validators
- Numeric range checkers

#### Solution

Provide a templates library that Guard can suggest:

```python
# src/invar/templates/contracts.py

LIST_PROCESSOR = """
@pre(lambda items: isinstance(items, list))
@post(lambda result: isinstance(result, list))
"""

FILE_PATH = """
@pre(lambda path: isinstance(path, (str, Path)))
"""

# Guard suggestion:
# "Function 'process_items' takes list parameter. Consider: LIST_PROCESSOR template"
```

#### Tasks

```
□ Create src/invar/templates/contracts.py
□ Add pattern detection in Guard
□ Generate template suggestions
□ Document in INVAR.md
```

---

### DX-06: Unified Verification Command

**Priority:** ★★★★★ (Critical for workflow adoption)
**Effort:** 0.5 day

#### Problem

During the implementation session, `invar test` and `invar verify` were implemented but **never actually used**. Instead, the developer continued using:

```bash
invar guard          # Static analysis
pytest --doctest-modules  # Doctests
```

**Root causes:**
1. **Habit inertia** - Existing pytest workflow is ingrained
2. **Two commands vs one** - `invar guard && invar test` is more friction than `invar guard`
3. **No enforcement** - ICIDIV workflow mentions `invar test` but nothing prevents using pytest directly
4. **Unclear value proposition** - Why `invar test` over `pytest --doctest-modules`?

This is a **critical finding**: even the implementing agent didn't adopt the new tools.

#### Solution

**Agent-Native Design: Smart Defaults, No Flags Needed**

The tool should automatically do the right thing based on context. Agents should just run `invar guard` without thinking.

```bash
invar guard              # Smart: auto-detects what to run
invar guard --quick      # Override: static only (human escape hatch)
```

**Automatic Behavior:**

| Context | What Runs | Why |
|---------|-----------|-----|
| Local, interactive | Static + Doctests | Fast feedback (~5s) |
| Pre-commit hook | Static + Doctests | Block bad commits |
| CI / `CI=true` | Static + Doctests + Hypothesis | Thorough |
| `--changed` mode | Above + CrossHair on changed files | Deep verify changes |

**Detection Logic:**
```python
def determine_verification_level() -> Level:
    if os.environ.get("CI"):
        return Level.THOROUGH  # CI: run everything fast
    if is_precommit_hook():
        return Level.STANDARD  # Pre-commit: static + doctests
    if crosshair_available() and is_small_changeset():
        return Level.PROVE     # Small change: can afford to prove
    return Level.STANDARD      # Default: static + doctests
```

**Key Principle:** Agent runs ONE command. Tool decides what's appropriate.

#### Why This is Agent-Native

| Old Design (Bad) | New Design (Good) |
|------------------|-------------------|
| Agent chooses `--test`/`--full`/`--prove` | Agent runs `invar guard` |
| Agent must know when to use each | Tool knows context |
| More flags = more decisions | Zero decisions needed |
| "Which tier should I use?" | "Just run guard" |

**Escape Hatches (for humans):**
- `--quick`: Static analysis only, skip tests
- `--prove`: Force CrossHair even locally
- `--no-doctest`: Skip doctests

These are for humans overriding smart defaults, not for agents to learn.

#### Implementation

```python
# src/invar/shell/cli.py

@app.command()
def guard(
    paths: list[Path] = ...,
    quick: bool = typer.Option(False, help="Static analysis only"),
    prove: bool = typer.Option(False, help="Force symbolic verification"),
):
    # 1. Always run static analysis
    violations = run_static_analysis(paths)

    if quick:
        return format_results(violations)

    # 2. Auto-detect context and run appropriate tests
    level = determine_verification_level()

    # Doctests: always run unless --quick
    doctest_results = run_doctests(paths)

    # Hypothesis: run in CI or if explicitly requested
    if level >= Level.THOROUGH or prove:
        hypothesis_results = run_hypothesis(paths)

    # CrossHair: run if available and (CI with --prove, or small changeset)
    if prove or (level >= Level.PROVE and crosshair_available()):
        crosshair_results = run_crosshair(paths)

    return format_merged_results(...)


def determine_verification_level() -> Level:
    """Auto-detect appropriate verification depth."""
    # CI environment → thorough
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return Level.THOROUGH

    # Pre-commit hook → standard
    if os.environ.get("PRE_COMMIT"):
        return Level.STANDARD

    # Small changeset + CrossHair available → can prove
    if crosshair_available():
        changed = get_changed_files()
        if len(changed) <= 3:  # Small change
            return Level.PROVE

    return Level.STANDARD
```

#### Dependencies

Update `pyproject.toml` with optional dependency groups:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
]

# Verification tiers (agent doesn't need to know these exist)
test = ["hypothesis>=6.0"]
prove = ["crosshair-tool>=0.0.60"]
full = ["hypothesis>=6.0", "crosshair-tool>=0.0.60"]
```

**Installation patterns:**

| User Type | Command | Gets |
|-----------|---------|------|
| Basic | `pip install python-invar` | Static + Doctests |
| Developer | `pip install python-invar[test]` | + Hypothesis |
| Thorough | `pip install python-invar[prove]` | + CrossHair |
| Everything | `pip install python-invar[full]` | All verification |

**Agent-Native behavior:** Guard auto-detects what's installed and uses it. No flags needed.

```python
def get_available_verifiers() -> list[str]:
    """Detect installed verification tools."""
    available = ["static", "doctest"]  # Always available

    try:
        import hypothesis
        available.append("hypothesis")
    except ImportError:
        pass

    try:
        import crosshair
        available.append("crosshair")
    except ImportError:
        pass

    return available
```

#### Tasks

```
□ Update pyproject.toml
  ├── Add [test] optional dependency (hypothesis)
  ├── Add [prove] optional dependency (crosshair-tool)
  ├── Add [full] optional dependency (both)
  └── Move hypothesis from [dev] to [test]

□ Change default behavior
  ├── Guard runs doctests by default (not opt-in)
  ├── Auto-detect installed verifiers
  ├── Auto-detect CI/pre-commit context
  ├── Add --quick flag for static-only override
  └── Update documentation

□ Smart CrossHair integration
  ├── Auto-run on small changesets if available
  ├── Skip silently when not installed
  └── Show "CrossHair available" in verbose mode

□ Update CLAUDE.md
  ├── Simplify: just "invar guard"
  ├── Remove tier selection guidance
  └── Document context-aware behavior
```

#### Evidence

From session analysis:
- `invar guard` runs: ~15
- `invar test` runs: 0
- `invar verify` runs: 0
- `pytest` runs: ~5 (for doctest verification)

**Conclusion:** Tools that aren't integrated into the primary workflow won't be used.

---

### DX-07: Integration Verification (Feature-Level Contracts)

**Priority:** ★★★★★ (Methodology gap)
**Effort:** 2-3 days
**Source:** Post-mortem of `--prove` flag not being wired to CrossHair execution

#### Problem

During DX-06 implementation, the `--prove` flag was added but never connected to CrossHair execution. The flag existed, the enum existed, but the actual call to `run_crosshair_on_files()` was missing. This wasn't caught until manual testing.

**Root Cause Analysis:**

| What Invar Covers | What Was Missing |
|-------------------|------------------|
| Function-level contracts (`@pre`/`@post`) | Feature-level contracts ("--prove → CrossHair runs") |
| Code structure (Core/Shell separation) | Integration paths (flag → execution) |
| Static properties (file size, imports) | Runtime behavior verification |

**The Fundamental Gap:**

```
Invar's Five Laws cover HOW to write correct functions.
They don't cover HOW to verify functions are correctly assembled.
```

#### Evidence

```python
# This code existed after "implementation":
prove: bool = typer.Option(False, "--prove", ...)

elif prove:
    verification_level = VerificationLevel.PROVE

# But this code was MISSING:
if verification_level >= VerificationLevel.PROVE:
    run_crosshair_on_files(...)  # ← NOT WIRED UP
```

Guard passed. Doctests passed. But the feature didn't work.

#### Proposed Solutions

##### Solution A: CLI Behavior Tests (Recommended)

Add integration tests that verify CLI flags produce expected behavior:

```python
# tests/integration/test_cli_flags.py

def test_prove_flag_runs_crosshair():
    """DX-07: Verify --prove actually triggers CrossHair."""
    result = subprocess.run(
        ["invar", "guard", "--prove", "src/invar/core/utils.py"],
        capture_output=True, text=True
    )
    output = json.loads(result.stdout)

    # Feature-level assertion
    assert "crosshair" in output, "--prove must produce crosshair section"
    assert output["crosshair"]["status"] in ("verified", "counterexample_found", "skipped")

def test_quick_flag_skips_doctests():
    """DX-07: Verify --quick skips doctests."""
    result = subprocess.run(
        ["invar", "guard", "--quick"],
        capture_output=True, text=True
    )
    output = json.loads(result.stdout)

    # Feature-level assertion
    assert "doctest" not in output or output["doctest"]["passed"] is True
```

##### Solution B: Feature-Level Contracts (Future)

Extend the contract system to CLI commands:

```python
# Conceptual - not current Python syntax
@cli_contract(
    flags=["--prove"],
    requires=["crosshair installed"],
    ensures=["output.crosshair exists", "crosshair.status in valid_statuses"]
)
def guard(): ...
```

##### Solution C: Connection Verification Rule (Future)

Add a Guard rule that detects disconnected code paths:

```
Rule: feature_disconnected
Detects: Flag/enum exists but corresponding execution code is missing
Example: --prove sets VerificationLevel.PROVE, but no code checks for PROVE level
```

#### Implementation Tasks

```
□ Phase 1: CLI Integration Tests (1 day)
  ├── Create tests/integration/test_cli_flags.py
  ├── Test each flag path (--quick, --prove, --changed)
  ├── Verify JSON output structure
  └── Add to CI workflow

□ Phase 2: ICIDIV Workflow Update (0.5 day)
  ├── Add "Integration Verify" step after "Verify"
  ├── Document: "For CLI changes, test each flag independently"
  └── Update CLAUDE.md with flag testing checklist

□ Phase 3: Pre-commit Hook (0.5 day)
  ├── Add integration tests to pre-commit
  └── Only run for shell/ changes

□ Future: Feature Contract System
  ├── Design @cli_contract decorator
  ├── Implement feature-level assertions
  └── Integrate with Guard
```

#### Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Disconnected features shipped | 1 (--prove) | 0 |
| Flag paths with tests | 0% | 100% |
| Time to detect integration issues | Post-release | Pre-commit |

#### New Lesson for Protocol

**Proposed Law 6: Integration**
> Local correctness does not guarantee global correctness.
> Every feature path must have end-to-end verification.

```
Current Five Laws:
1. Separation   - Separate pure logic and I/O
2. Contract     - Define complete boundaries
3. Context      - Read context economically
4. Decompose    - Decompose before implementing
5. Verify       - Verify reflectively

Proposed Sixth Law:
6. Integration  - Verify all paths connect correctly
```

---

### DX-08: Contract-Driven Property Testing ✅ IMPLEMENTED

**Priority:** ★★★★ (High value, builds on existing infrastructure)
**Effort:** 2-3 days
**Status:** ✅ Implemented (2025-12-23)
**Source:** Analysis of Hypothesis integration opportunities

#### Problem

Invar has Hypothesis as an optional dependency (`[test]`), but there are no actual property tests. Writing `@given` tests manually creates friction and duplicates contract logic:

```python
# Current: Manual duplication
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float: ...

# Separate test file - duplicates contract logic
@given(st.floats(min_value=0.01))  # Duplicates @pre
def test_sqrt(x):
    result = sqrt(x)
    assert result >= 0  # Duplicates @post
```

**The contracts ARE the test specification. Why write them twice?**

#### Key Insight

`src/invar/core/strategies.py` already parses `@pre` lambdas to infer Hypothesis strategies:

```python
# This already exists!
infer_from_lambda("x > 0 and x < 100", "x", int)
# → StrategyHint(constraints={"min_value": 1, "max_value": 99})
```

**Missing piece:** Auto-generate and execute property tests from contracts.

#### Solution: Auto-Generated Property Tests

```python
# Agent writes ONLY this:
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    """
    >>> sqrt(4)
    2.0
    """
    return x ** 0.5

# Invar AUTO-GENERATES (conceptually):
@given(x=st.floats(min_value=0.01, allow_nan=False, allow_infinity=False))
def test_sqrt_property(x):
    result = sqrt(x)
    # @post is automatically verified by deal at runtime
    assert True  # If we get here without ContractError, property holds
```

#### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Parse @pre lambda → Extract constraints                      │
│    @pre(lambda x, y: x > 0 and y >= 0)                         │
│    → x: integers(min_value=1), y: integers(min_value=0)        │
├─────────────────────────────────────────────────────────────────┤
│ 2. Infer types from annotations                                 │
│    def func(x: int, y: float) → x: integers(), y: floats()    │
├─────────────────────────────────────────────────────────────────┤
│ 3. Combine constraints with types                               │
│    → x: integers(min_value=1), y: floats(min_value=0)          │
├─────────────────────────────────────────────────────────────────┤
│ 4. Generate test function dynamically                           │
│    @given(x=..., y=...)                                         │
│    def test_func_property(x, y):                                │
│        func(x, y)  # @post checked by deal at runtime          │
├─────────────────────────────────────────────────────────────────┤
│ 5. Run with Hypothesis                                          │
│    - If @post violated → Hypothesis finds counterexample        │
│    - If no violation → Property verified for 100 examples       │
└─────────────────────────────────────────────────────────────────┘
```

#### Integration with Smart Guard

```bash
# Local development: Skip for speed
invar guard                    # Static + Doctests (fast)

# CI environment: Run property tests
CI=true invar guard            # Static + Doctests + Hypothesis

# Explicit: Force property testing
invar guard --thorough         # Adds Hypothesis property tests

# Full verification
invar guard --prove            # Static + Doctests + Hypothesis + CrossHair
```

**Agent-Native:** No new commands to learn. CI auto-runs property tests.

#### Implementation

##### Phase 1: Core Generator (1 day)

```python
# src/invar/core/property_gen.py

from hypothesis import given, strategies as st
from invar.core.strategies import infer_from_lambda, infer_from_multiple

def generate_property_test(func: Callable) -> Callable | None:
    """
    Generate a Hypothesis property test from @pre/@post contracts.

    Returns None if:
    - No @pre contracts
    - @pre too complex to parse
    - Types not inferrable
    """
    pre_sources = extract_pre_sources(func)
    if not pre_sources:
        return None

    strategies = {}
    for param_name, param_type in get_typed_params(func):
        hint = infer_from_multiple(pre_sources, param_name, param_type)
        strategy = hint_to_strategy(hint, param_type)
        if strategy:
            strategies[param_name] = strategy

    if not strategies:
        return None

    @given(**strategies)
    def property_test(**kwargs):
        # deal's @post will raise ContractError if violated
        func(**kwargs)

    property_test.__name__ = f"test_{func.__name__}_property"
    return property_test
```

##### Phase 2: Guard Integration (0.5 day)

```python
# src/invar/shell/testing.py

def run_property_tests(files: list[Path]) -> Result[dict, str]:
    """Run auto-generated property tests on Core files."""
    try:
        from hypothesis import settings
        from invar.core.property_gen import generate_property_test
    except ImportError:
        return Success({"status": "skipped", "reason": "hypothesis not installed"})

    results = {"passed": 0, "failed": 0, "skipped": 0, "counterexamples": []}

    for file in files:
        for func in find_contracted_functions(file):
            test = generate_property_test(func)
            if test is None:
                results["skipped"] += 1
                continue

            try:
                test()
                results["passed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["counterexamples"].append({
                    "function": func.__name__,
                    "file": str(file),
                    "error": str(e)
                })

    return Success(results)
```

##### Phase 3: Strategy Enhancement (1 day)

Extend `strategies.py` to handle more patterns:

```python
# Additional patterns to support:
EXTENDED_PATTERNS = [
    # String length: len(s) > 0
    (r"len\((\w+)\)\s*>\s*(\d+)", lambda m, p: {"min_size": int(m.group(2)) + 1}),

    # Collection membership: x in [1, 2, 3]
    (r"(\w+)\s+in\s+\[([^\]]+)\]", lambda m, p: {"elements": eval(f"[{m.group(2)}]")}),

    # Type checks: isinstance(x, str)
    (r"isinstance\((\w+),\s*(\w+)\)", lambda m, p: {"type": m.group(2)}),

    # Boolean: x is True
    (r"(\w+)\s+is\s+True", lambda m, p: {"value": True}),
]
```

#### Example: Full Flow

```python
# Developer writes:
@pre(lambda items: len(items) > 0)
@pre(lambda items: all(x >= 0 for x in items))
@post(lambda result: result >= 0)
def average(items: list[float]) -> float:
    """
    >>> average([1, 2, 3])
    2.0
    """
    return sum(items) / len(items)

# invar guard --thorough runs:
# 1. Static analysis ✓
# 2. Doctest: average([1, 2, 3]) == 2.0 ✓
# 3. Auto-generated property test:
#    @given(items=st.lists(st.floats(min_value=0), min_size=1))
#    def test_average_property(items):
#        average(items)  # @post verified by deal
#
#    → Runs 100 random examples
#    → If any fails, Hypothesis reports minimal counterexample
```

#### Why This is Valuable

| Aspect | Without DX-08 | With DX-08 |
|--------|---------------|------------|
| Test writing | Manual @given duplication | Zero extra code |
| Edge case discovery | Manual thinking | Automatic |
| Contract value | Documentation + runtime check | + Property verification |
| CI confidence | Doctests only | + 100 random inputs per function |

#### Research Alignment

- **Clover (2024):** Contracts should uniquely determine implementation → Property tests verify this
- **AlphaCodium:** Test-first improves accuracy → More tests = more accuracy
- **icontract-hypothesis:** Prior art for contract → Hypothesis generation

#### Limitations & Mitigations

| Limitation | Mitigation |
|------------|------------|
| Complex @pre can't be parsed | Fall back to doctest-only, log warning |
| Slow for large codebases | Only run in CI, cache strategies |
| False positives from NaN/Inf | Use `allow_nan=False, allow_infinity=False` |
| @post may have side effects | Only generate for Core (pure) functions |

#### Tasks

```
□ Phase 1: Core Generator (1 day)
  ├── Create src/invar/core/property_gen.py
  ├── Implement generate_property_test()
  ├── Handle common type annotations (int, float, str, list)
  └── Add doctests for the generator itself

□ Phase 2: Guard Integration (0.5 day)
  ├── Add run_property_tests() to testing.py
  ├── Integrate into guard --thorough and CI mode
  ├── Add property test results to JSON output
  └── Update documentation

□ Phase 3: Strategy Enhancement (1 day)
  ├── Extend PATTERNS in strategies.py
  ├── Add collection strategies (list, dict, set)
  ├── Handle Optional types
  └── Add comprehensive doctests

□ Phase 4: deal Integration Research (0.5 day)
  ├── Investigate deal's built-in Hypothesis support
  ├── Consider using @deal.example alongside @given
  └── Document best practices
```

#### Success Metrics

| Metric | Target |
|--------|--------|
| Functions with auto-generated tests | 80% of Core functions |
| Edge cases found by Hypothesis | Track over time |
| CI test coverage | +30% (from property tests) |
| Manual @given tests needed | 0 (all auto-generated) |

---

### DX-09: Self-Violation Prevention (Dogfooding Enforcement)

**Priority:** ★★★★☆ (High impact, prevents regression)
**Effort:** 0.5 day
**Source:** Ultrathink self-reflection on development practices

#### Problem

During Invar development, the developer (AI agent) designed "zero-decision" tools but then bypassed them:

```bash
# Design intent (DX-06):
invar guard                  # Auto-runs doctests, zero decisions

# Actual development behavior:
invar guard --quick          # Manually skipped doctests
python -m doctest file.py    # Then ran doctests separately
```

**Irony:** The designer of "Agent-Native, automatic > manual" used manual overrides.

**Root Causes:**
1. Old habits override new design
2. Speed anxiety (unfounded: difference is only 0.4s)
3. No feedback mechanism to detect self-violation

#### Measured Impact

```
Command              Time     Content
--quick              0.2s     Static only
Default (STANDARD)   0.6s     Static + doctests
                     ----
Difference           0.4s     ← Not worth bypassing
```

#### Solution: Multi-Layer Prevention

##### Layer 1: CLAUDE.md Explicit Guidance

Add explicit rule that makes --quick usage visible as a deliberate exception:

```markdown
## Guard Usage

**Default:** `invar guard` (STANDARD = static + doctests)

**Do NOT use --quick unless:**
- Debugging a specific static analysis issue
- Performance profiling the guard itself
- Explicitly testing --quick behavior

**Why:** Default is only 0.4s slower. Trust the design.
```

##### Layer 2: Usage Telemetry (Optional)

Track verification levels in guard output:

```python
# src/invar/shell/cli.py

def guard(...):
    # Log verification level for visibility
    if verification_level == VerificationLevel.STATIC:
        console.print("[dim]Mode: --quick (static only, doctests skipped)[/dim]")
    elif verification_level == VerificationLevel.STANDARD:
        console.print("[dim]Mode: default (static + doctests)[/dim]")
```

Benefits:
- Makes --quick usage visible
- Developer sees "doctests skipped" message
- Creates friction for unnecessary bypassing

##### Layer 3: Context.md Reflection Prompt

Add to `.invar/context.md`:

```markdown
## Self-Check Questions

Before committing, ask:
- Did I use `--quick`? Was it necessary?
- Did I run `--prove` before major changes?
- Am I trusting Invar's defaults?
```

##### Layer 4: CI Enforcement (Strong)

```yaml
# .github/workflows/test.yml
- name: Guard (must not use --quick in CI)
  run: |
    # CI always runs THOROUGH, no --quick allowed
    invar guard
    if [ "$?" != "0" ]; then
      echo "::error::Guard failed. Fix before merge."
      exit 1
    fi
```

#### Implementation

```python
# src/invar/shell/cli.py - Add visibility message

@app.command("guard")
def guard(
    path: str = typer.Argument(...),
    quick: bool = typer.Option(False, "--quick", help="Static only"),
    ...
):
    # DX-09: Make verification level visible
    level_name = {
        VerificationLevel.STATIC: "[yellow]--quick[/yellow] (static only)",
        VerificationLevel.STANDARD: "default (static + doctests)",
        VerificationLevel.THOROUGH: "--thorough (+ Hypothesis)",
        VerificationLevel.PROVE: "--prove (+ CrossHair)"
    }

    if not agent_mode:
        console.print(f"[dim]Verification: {level_name[verification_level]}[/dim]")
```

#### Why This Works

| Layer | Prevents | Mechanism |
|-------|----------|-----------|
| CLAUDE.md | Unconscious bypass | Explicit rule |
| Telemetry | Hidden --quick | Visible message |
| Reflection | Habit without thinking | Prompt questions |
| CI | Production bypass | Hard enforcement |

#### Key Insight

**The goal is not to prevent --quick usage, but to make it a conscious choice.**

```
Before DX-09:                    After DX-09:
--quick (unconscious habit)  →   --quick + visible "doctests skipped" message
                             →   Developer pauses: "Do I need this?"
                             →   Usually: "No, 0.4s is fine"
```

#### Tasks

```
□ Update CLAUDE.md with explicit --quick guidance
□ Add verification level visibility message to guard
□ Add self-check questions to context.md template
□ Document in INVAR.md
```

#### Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| --quick usage in development | Common | Rare (exceptions only) |
| Doctest failures caught | Sometimes | Always (default runs them) |
| Developer awareness of mode | Low | High (visible message) |

---

### DX-10: Hypothesis Property Testing Integration

**Priority:** ★★★☆☆ (Medium, enables deeper testing)
**Effort:** 2-3 days
**Status:** ✅ Partially Complete (core absorbed by DX-19)
**Depends on:** DX-08 (Contract-Driven Property Testing)

#### Completion Status (2025-12-23)

**What was implemented (via DX-08 + DX-19):**
- ✅ Contract → Hypothesis strategy extraction
- ✅ Auto-generated property tests from @pre/@post
- ✅ Integration into default STANDARD level
- ✅ No separate --property flag needed (Agent-Native: zero decisions)

**What remains (moved to DX-20):**
- ⏳ Strategy caching (avoid repeated parsing)
- ⏳ Complex pattern support (x < y, all(), Union)
- ⏳ Performance profiling (--profile flag)
- ⏳ Selective skip (@skip_property_test decorator)

**See:** [DX-20: Property Testing Enhancements](./2025-12-23-dx-20-property-testing-enhancements.md)

#### Original Background

The original DX-06 design included a THOROUGH level with Hypothesis property testing:

```python
# Original (removed in v3.23)
class VerificationLevel(IntEnum):
    STATIC = 0
    STANDARD = 1
    THOROUGH = 2  # Promised Hypothesis but never implemented
    PROVE = 3
```

This was removed because:
1. It was never implemented
2. CI defaulted to THOROUGH, creating false confidence
3. Agent-Native principle: Don't promise what you can't deliver

#### Original Proposal (Superseded)

~~Add Hypothesis property testing as an optional fourth level:~~

```python
# SUPERSEDED by DX-19: simplified to 2 levels
# Property testing now included in STANDARD by default
class VerificationLevel(IntEnum):
    STATIC = 0    # --static
    STANDARD = 1  # default (includes property tests)
```

#### Implementation Strategy

##### Phase 1: Contract → Strategy Extraction (DX-08)

Leverage existing `strategies.py` to extract Hypothesis strategies from contracts:

```python
@pre(lambda x: x > 0)
@pre(lambda items: len(items) > 0)
def average(x: float, items: list[float]) -> float: ...

# Auto-generates:
@given(x=st.floats(min_value=0, exclude_min=True),
       items=st.lists(st.floats(), min_size=1))
def test_average_property(x, items):
    average(x, items)  # @post verified by deal
```

##### Phase 2: Guard Integration

```bash
invar guard --property   # Run auto-generated property tests
```

##### Phase 3: CI Integration

```yaml
# Optional CI configuration
- name: Property Tests
  run: invar guard --property
```

#### Why Not Include in Current Release

1. **Complexity** - Property test generation requires robust contract parsing
2. **Time cost** - Property tests are slower than doctests
3. **False positives** - Need to handle edge cases (NaN, Inf, etc.)
4. **Value unclear** - Most bugs are caught by doctests + CrossHair

#### When This Becomes Valuable

- Large codebases with many numeric functions
- When doctests don't cover edge cases
- When CrossHair times out on complex contracts

#### Relationship to DX-08

DX-08 focuses on the core infrastructure:
- Contract parsing
- Strategy generation
- Integration with deal

DX-10 focuses on:
- Guard integration
- CI workflow
- Performance optimization

**Recommendation:** Implement DX-08 first, evaluate, then decide on DX-10.

---

## Implementation Roadmap

| Week | Proposals | Effort |
|------|-----------|--------|
| 1 | DX-01 ✅, DX-02 ✅, DX-03 ✅, DX-06 ✅, DX-07 ✅, DX-09 ✅ | 2 days |
| 2 | DX-04, DX-05 | 2 days |
| 3 | DX-08 ✅ | 1 day |
| Future | DX-10 (Additional Hypothesis enhancements) | 1-2 days |

**Completed (2025-12-21):**
- DX-01: Lambda fix templates for param_mismatch
- DX-02: Doctest best practices documentation
- DX-03: exclude_doctest_lines configuration
- DX-06: Smart Guard (static + doctests auto-run)
- DX-07: Integration tests for CLI flags
- DX-09: Self-violation prevention (verification_level in JSON)

**Completed (2025-12-23):**
- DX-08: Contract-driven property testing (`invar guard --thorough`, `invar test`)

**v3.23 Changes:** Simplified to 3 levels (removed unimplemented THOROUGH), added verification_level to Agent JSON.
**v3.25 Changes:** Added THOROUGH level with property testing (DX-08 implementation).

## Success Metrics

| Proposal | Metric | Target |
|----------|--------|--------|
| DX-01 | First-attempt success rate | +20% |
| DX-02 | Doctest dict failures | -90% |
| DX-03 | Config discoverability | Documented |
| DX-04 | Manual fix time | -50% |
| DX-06 | Test command adoption | 100% (via integration) |
| DX-07 | Disconnected features | 0 |
| DX-08 | Auto-generated property tests | 80% Core functions |

---

## Appendix: Session Data

### Features Implemented
1. TTY Auto-detection
2. A1 invar test
3. A2 invar verify
4. C2 @must_use
5. B4 Purity Detection
6. C1 @invariant
7. C3 Contract Composition
8. C4 Strategy Inference
9. C5 @must_close

### Files Created
- `src/invar/decorators.py`
- `src/invar/invariant.py`
- `src/invar/contracts.py`
- `src/invar/resource.py`
- `src/invar/core/must_use.py`
- `src/invar/core/purity_heuristics.py`
- `src/invar/core/strategies.py`
- `src/invar/shell/testing.py`
- `src/invar/shell/init_cmd.py`

### Guard Statistics
- Total runs: ~15
- Errors caught: 5
- Final status: 0 errors, 65 warnings (pre-existing)

### Tool Usage Analysis

| Command | Runs | Notes |
|---------|------|-------|
| `invar guard` | ~15 | Primary verification tool |
| `pytest --doctest-modules` | ~5 | Used instead of `invar test` |
| `invar test` | 0 | Implemented but not adopted |
| `invar verify` | 0 | Implemented but not adopted |

**Key Insight:** New commands implemented in same session weren't integrated into workflow. This validates DX-06: tools must be integrated into primary commands to achieve adoption.

---

*Generated from ultrathink analysis of development session 2025-12-21*
