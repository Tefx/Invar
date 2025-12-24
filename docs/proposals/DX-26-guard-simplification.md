# DX-26: Guard Command Simplification

**Status:** Implemented
**Created:** 2025-12-24
**Implemented:** 2025-12-24
**Principle:** Agent-Native, Zero Backward Compatibility Concerns

## Problem

The `invar guard` command has accumulated complexity:
- 9 CLI parameters with overlapping purposes
- 3 JSON output modes (`--json`, `--agent`, auto-detect)
- Redundant commands (`invar test`, `invar verify`)
- Dead code from removed features (`--prove`, `--thorough`)
- MCP uses wrong output mode (missing verification details)
- **`status` field inconsistent with exit code** (critical bug)

## Current State

### CLI Parameters (9)
```
path              # Project root
--strict          # Warnings as errors
--no-strict-pure  # Disable purity checks
--pedantic        # Show off-by-default rules
--explain         # Detailed explanations
--changed         # Git-modified files only
--agent           # JSON with fix instructions
--json            # Simple JSON
--static          # Skip runtime tests
```

### MCP Parameters (3)
```
path     # default: "."
changed  # default: True
strict   # default: False
```

### Issues Found

| Issue | Impact | Severity |
|-------|--------|----------|
| `status` doesn't reflect runtime test results | Agent sees "passed" but exit code is 1 | **Critical** |
| MCP uses `--json` instead of `--agent` | Missing verification_level, test results, fix instructions | **High** |
| `output_json()` missing runtime test results | Agent can't see doctest/crosshair/hypothesis results | **High** |
| Property test failures not actionable | Seed message without file/function context, no reproduction command | **High** |
| Rich output shows "Guard passed" then "Doctests failed" | Confusing mixed signals | Medium |
| `--json` vs `--agent` confusion | When would agent want simple JSON? | Medium |
| `--no-strict-pure` double negative | Confusing semantics | Low |
| `--pedantic` rarely used | Agents don't need off-by-default rules | Low |
| `invar test` / `invar verify` redundant | `guard` already runs both | Low |
| `detect_verification_context()` dead code | Always returns STANDARD | Low |

### Critical Bug: `status` vs Exit Code Mismatch

```
┌─────────────────────────────────────────────────────────────────┐
│                   Current Failure Logic                         │
├─────────────────────────────────────────────────────────────────┤
│  GuardReport.passed = (errors == 0)     # Static only!          │
│                                                                  │
│  Exit Code Logic:                                                │
│    static_exit_code = 1 if errors > 0 else 0                    │
│    all_passed = doctest AND crosshair AND property              │
│    final_exit = static_exit_code if all_passed else 1           │
└─────────────────────────────────────────────────────────────────┘

Scenario: Static passes, Doctests fail
  - report.passed = True       ← Wrong!
  - output["status"] = "passed" ← Wrong!
  - Exit code = 1              ← Correct
```

**Agent sees:** `{"status": "passed", "doctest": {"passed": false}}`
**Exit code:** 1

This forces agents to manually combine fields to determine true status.

### Issue: Property Test Failure Output Not Actionable

Current property test failure output:
```
✗ Property tests failed (1 functions)
  deal.PostContractError: expected post(-1 is None or isinstance(-1, float)) ...
  You can add @seed(336048909179393285647920446708996038674) to this test to reproduce this failure.
```

**Problems:**

| Issue | Impact |
|-------|--------|
| "this test" undefined | Which file? Which function? |
| No file path context | Agent can't locate the failure |
| Seed not parsed | Not a structured field for reproduction |
| Counterexample values not extracted | `PropertyTestResult.counterexample` always None |
| No reproduction command | Agent must guess how to use seed |

**Root cause:** `run_property_test()` returns `PropertyTestResult(error=str(e))` - raw exception string.

**Code locations:**
- `property_gen.py:27` - `counterexample` field defined but never populated
- `property_gen.py:374,392` - Error captured as `str(e)`
- `guard_helpers.py:282-283` - Raw error printed without parsing

## Proposal

### 1. Fix Status/Exit Code Consistency

**Add combined status calculation:**

```python
def get_combined_status(
    report: GuardReport,
    strict: bool,
    doctest_passed: bool,
    crosshair_passed: bool,
    property_passed: bool,
) -> str:
    """Calculate true guard status including all test phases."""
    if report.errors > 0:
        return "failed"
    if strict and report.warnings > 0:
        return "failed"
    if not doctest_passed:
        return "failed"
    if not crosshair_passed:
        return "failed"
    if not property_passed:
        return "failed"
    return "passed"
```

**Update all output functions:**

```python
# Before
output = {
    "status": "passed" if report.passed else "failed",  # Static only
    ...
}

# After
output = {
    "status": combined_status,  # All tests combined
    "static": {"passed": report.errors == 0, "errors": report.errors, "warnings": report.warnings},
    "doctest": {"passed": doctest_passed, ...},
    "crosshair": {...},
    "property_tests": {...},
}
```

### 2. Unified Output Mode

**Remove:** `--json`, `--agent`

**Add:** `--human` (force human-readable output)

**Behavior:**
```
TTY detected     → Human-readable (Rich)
Non-TTY detected → Full JSON (agent-optimized)
--human flag     → Force human-readable (for testing/debugging)
```

**Delete `output_json()`** - always use full agent format for JSON.

```python
# Before (confusing)
if json_output:
    output_json(report)           # Simple JSON, missing runtime results
elif agent or _detect_agent_mode():
    output_agent(report, ...)     # Full JSON
else:
    output_rich(report, ...)      # Human

# After (clear)
if human_flag or sys.stdout.isatty():
    output_rich(report, ...)      # Human
else:
    output_agent(report, ...)     # Full JSON (always complete)
```

### 3. Fix Rich Output Order

**Before (confusing):**
```
Guard passed.          ← Static result first (misleading)
✗ Doctests failed      ← Runtime result after
```

**After (clear):**
```
Static analysis: ✓ 0 errors, 3 warnings
Doctests: ✗ failed
CrossHair: ✓ verified (42 files)
Property tests: ✓ passed (151/151)
────────────────────────────────────
Guard failed.          ← Combined conclusion last
```

### 4. Remove Redundant Commands

**Delete:** `invar test`, `invar verify`

**Keep:** `invar guard` (single entry point)

**Rationale:**
- `guard` already runs static + doctests + CrossHair + Hypothesis
- Separate commands violate Agent-Native (zero decisions)
- Usage data: `invar guard` ~100%, `invar test/verify` ~0%

### 5. Simplify Flags

**Before (9):**
```
path, --strict, --no-strict-pure, --pedantic, --explain,
--changed, --agent, --json, --static
```

**After (5):**
```
path        # Project path (positional)
--changed   # Git-modified files only
--strict    # Warnings as errors
--static    # Skip runtime tests (debug mode)
--human     # Force human-readable output (testing)
```

**Removed:**
| Flag | Reason |
|------|--------|
| `--no-strict-pure` | If purity checks wrong, fix the checks |
| `--pedantic` | Agents don't need off-by-default rules |
| `--explain` | Verbosity should be per-output-mode, not flag |
| `--agent` | Replaced by auto-detect |
| `--json` | Replaced by auto-detect |

### 6. Fix MCP

**Before:**
```python
cmd.append("--json")  # Wrong: simple JSON, missing info
```

**After:**
```python
# No output flag needed - non-TTY auto-detects to full JSON
```

### 7. Clean Dead Code

**Remove:**
- `output_json()` function (merge into `output_agent()`)
- `detect_verification_context()` - always returns STANDARD
- `VerificationLevel` comments about `--thorough`
- `invar test` command and `test_cmd.py`
- `invar verify` command
- `INVAR_MODE=agent` env check (non-TTY sufficient)
- `_detect_agent_mode()` function (inline the TTY check)

**Update:**
- Documentation references to `--prove` (removed in DX-19)
- MCP instructions to reflect simplified interface

### 8. Fix Property Test Failure Output

**Goal:** Make property test failures actionable with structured reproduction info.

**Changes to `PropertyTestResult`:**

```python
@dataclass
class PropertyTestResult:
    function_name: str
    file_path: str | None = None      # NEW: Where the function lives
    passed: bool = True
    examples_run: int = 0
    counterexample: dict[str, Any] | None = None  # POPULATE: Actual values
    seed: int | None = None           # NEW: Extracted from Hypothesis
    error: str | None = None
```

**Parse Hypothesis output in `run_property_test()`:**

```python
def _parse_hypothesis_error(e: Exception, func: Callable) -> tuple[dict, int | None]:
    """Extract counterexample and seed from Hypothesis failure."""
    error_str = str(e)

    # Extract seed: @seed(12345...)
    seed_match = re.search(r"@seed\((\d+)\)", error_str)
    seed = int(seed_match.group(1)) if seed_match else None

    # Extract counterexample from deal.PostContractError
    # Format: "where x=1, y='foo'" or function call args
    counterexample = _extract_counterexample(error_str)

    return counterexample, seed
```

**Human-readable output (Rich):**

```
✗ Property tests failed (1 function)
  src/invar/core/parser.py::parse_contract
    Counterexample: x=-1, y=None
    Seed: 336048909179393285647920446708996038674
    Reproduce: invar test src/invar/core/parser.py --function parse_contract --seed 336048909179393285647920446708996038674
```

**Agent JSON output:**

```json
{
  "property_tests": {
    "status": "failed",
    "functions_tested": 151,
    "functions_passed": 150,
    "functions_failed": 1,
    "failures": [
      {
        "file": "src/invar/core/parser.py",
        "function": "parse_contract",
        "counterexample": {"x": -1, "y": null},
        "seed": 336048909179393285647920446708996038674,
        "error": "PostContractError: expected post(...)",
        "reproduction": "invar test src/invar/core/parser.py --function parse_contract --seed 336048909179393285647920446708996038674"
      }
    ]
  }
}
```

**Add `--function` and `--seed` to `invar test`:**

```bash
invar test <file>                    # Test all contracted functions
invar test <file> --function <name>  # Test specific function
invar test <file> --seed <value>     # Reproduce with seed
```

## Resulting Interface

### CLI
```bash
invar guard [path]           # Full verification (default)
invar guard --changed        # Git-modified files only (common)
invar guard --static         # Static only (debug)
invar guard --strict         # Warnings as errors (CI)
invar guard --human          # Force human output (testing)
```

### MCP
```python
invar_guard(
    path=".",
    changed=True,   # Default True (agent's common case)
    strict=False,
)
# Output: Always full JSON with all verification details
```

### Output Modes

| Context | Output |
|---------|--------|
| Terminal (TTY) | Rich human-readable |
| Pipe/redirect (non-TTY) | Full agent JSON |
| `--human` flag | Rich human-readable |

### Agent JSON Schema (Updated)

```json
{
  "status": "passed",
  "verification_level": "standard",
  "static": {
    "passed": true,
    "errors": 0,
    "warnings": 3,
    "infos": 0
  },
  "doctest": {
    "passed": true,
    "output": ""
  },
  "crosshair": {
    "status": "verified",
    "verified": ["file1.py", "file2.py"],
    "skipped": ["file3.py"],
    "failed": []
  },
  "property_tests": {
    "status": "passed",
    "functions_tested": 151,
    "functions_passed": 151,
    "functions_failed": 0,
    "total_examples": 7000
  },
  "violations": [...],
  "fixes": [...]
}
```

**Key change:** Top-level `status` now reflects ALL test phases, not just static.

### Human Output (Updated)

```
Invar Guard Report
========================================
(changed-only mode)

src/invar/core/parser.py
  WARN :25 Function 'parse_source' has no @post contract
    → Add: @post(lambda result: result is None or isinstance(result, FileInfo))

────────────────────────────────────────
Static: ✓ 0 errors, 1 warning
Doctests: ✓ passed
CrossHair: ✓ verified (19 files)
Property tests: ✓ passed (151/151)
────────────────────────────────────────
Guard passed.
```

## Implementation

### Phase 1: Fix Critical Bug (Immediate)
1. Add `get_combined_status()` function
2. Update `output_agent()` to use combined status
3. Update `output_rich()` to show phases then conclusion
4. Remove `--json` from MCP server

### Phase 2: Simplify Output
1. Delete `output_json()` function
2. Merge into `output_agent()` with full details
3. Add `--human` flag
4. Remove `--json`, `--agent` flags

### Phase 3: Simplify Flags
1. Remove `--pedantic`, `--explain`, `--no-strict-pure`
2. Update help text

### Phase 4: Remove Dead Code
1. Delete `invar test`, `invar verify` commands
2. Delete `detect_verification_context()`
3. Delete `_detect_agent_mode()` (inline TTY check)
4. Clean up `VerificationLevel` comments

### Phase 5: Property Test Output
1. Add `file_path`, `seed` fields to `PropertyTestResult`
2. Parse Hypothesis error to extract counterexample and seed
3. Update `run_property_test()` to populate structured fields
4. Update human output to show `file::function` format with reproduction command
5. Update agent JSON with `failures` array containing structured info
6. Add `--function` and `--seed` flags to `invar test`

### Phase 6: Documentation
1. Update CLAUDE.md
2. Update context.md (remove `--prove` references)
3. Update MCP instructions

## Migration

**Not needed** - this is a breaking change proposal with no backward compatibility.

For projects that might use old flags:
- `--json` → remove (auto-detect)
- `--agent` → remove (auto-detect)
- `--prove` → remove (merged into default)
- `--pedantic` → remove (rarely used)
- `--explain` → remove (use `--human` if needed)
- `--no-strict-pure` → configure in `pyproject.toml` if needed

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| CLI flags | 9 | 5 |
| Output modes | 3 | 2 (auto) |
| Commands | 5 | 3 |
| Output logic lines | ~50 | ~20 |
| Status/exit consistency | No | Yes |

## Files to Modify

| File | Changes |
|------|---------|
| `core/models.py` | Keep `passed` property for backward compat |
| `core/formatter.py` | Update `format_guard_agent()` to accept combined status |
| `core/property_gen.py` | Add `file_path`, `seed` to `PropertyTestResult`; parse error for counterexample |
| `shell/cli.py` | Calculate combined status, pass to output functions |
| `shell/guard_output.py` | Delete `output_json()`, update `output_rich()` order |
| `shell/guard_helpers.py` | Update property test output format with structured failures |
| `shell/property_tests.py` | Pass file path to `run_property_test()`; format reproduction commands |
| `shell/test_cmd.py` | Add `--function`, `--seed` flags (keep for reproduction); or delete if guard handles all |
| `shell/testing.py` | Remove `detect_verification_context()` |
| `mcp/server.py` | Remove `--json` flag |

## Decision

- [ ] Approved
- [ ] Rejected
- [ ] Needs revision
