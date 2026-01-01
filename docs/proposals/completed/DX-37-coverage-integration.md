# DX-37: Coverage Integration

> **"What you don't test, you don't know."**

**Status:** Done
**Created:** 2025-12-25
**Updated:** 2025-12-27
**Origin:** Extracted from DX-33 Option D
**Effort:** Low (~1 day)
**Risk:** Low
**Decision:** Option A (coverage.py) — scoped to doctest + hypothesis

## Problem Statement

Guard currently verifies code through multiple phases:
- Static analysis (architecture rules)
- Doctests (example-based)
- CrossHair (symbolic execution)
- Hypothesis (property-based)

However, there's no visibility into which code paths are actually exercised. Dead code and untested branches remain invisible until adversarial review finds them.

## Decision: Option A (coverage.py)

After analysis (2025-12-27), Option A was selected:

| Option | Feasibility | Value | Decision |
|--------|-------------|-------|----------|
| A: coverage.py | ✅ High | ⭐⭐⭐ | **Selected** |
| B: AST-based | ⚠️ Medium | ⭐ | Rejected |

### Why Option A

1. **Mature ecosystem** — coverage.py is battle-tested
2. **Accurate tracking** — sys.settrace() provides real execution data
3. **Branch coverage** — Built-in support for `branch=True`
4. **Low maintenance** — No custom implementation to maintain

### Why NOT Option B

1. **Cannot infer execution** — Static analysis can find branches but cannot determine which were executed
2. **High complexity** — Would need to parse test output and reverse-engineer execution paths
3. **Low accuracy** — At best, can only detect "branch exists" not "branch covered"

## Scope Limitation

```
┌─────────────────────────────────────────────────┐
│  Coverage collected for:                        │
│    ✅ Doctests (real execution)                 │
│    ✅ Hypothesis (real execution)               │
│    ❌ CrossHair (symbolic execution - N/A)      │
└─────────────────────────────────────────────────┘
```

**CrossHair limitation:**
- CrossHair runs as a subprocess (`subprocess.run()`)
- Uses symbolic execution (Z3 solver), not line-by-line execution
- coverage.py cannot track subprocess or symbolic execution
- This is a fundamental limitation, not a bug

## Proposed Solution

### CLI Interface

```bash
# Opt-in coverage collection
invar guard --coverage

# With changed files only
invar guard --coverage --changed

# MCP equivalent
invar_guard(coverage=True)
invar_guard(coverage=True, changed=True)
```

### Output Format

```
Coverage Analysis (doctest + hypothesis):
  src/invar/core/parser.py: 94% branch (3 uncovered)
    Line 127: else branch never taken
    Line 203-205: except handler never triggered
  src/invar/core/rules.py: 89% branch (5 uncovered)
    Line 45: elif branch never taken
    Line 112: else branch never taken
    ...

Overall: 91% branch coverage (doctest + hypothesis)

Note: CrossHair uses symbolic execution; coverage not applicable.
```

### JSON Output

```json
{
  "coverage": {
    "enabled": true,
    "phases_tracked": ["doctest", "hypothesis"],
    "phases_excluded": ["crosshair"],
    "overall_branch_coverage": 91.2,
    "files": [
      {
        "path": "src/invar/core/parser.py",
        "branch_coverage": 94.1,
        "uncovered_branches": [
          {"line": 127, "type": "else", "context": "if x > 0:"},
          {"line": 203, "type": "except", "context": "except ValueError:"}
        ]
      }
    ]
  }
}
```

## Implementation Plan

### Phase 1: Infrastructure (2h)

```python
# src/invar/shell/coverage_integration.py
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import coverage as cov_module

@dataclass
class CoverageReport:
    """Coverage data from doctest + hypothesis phases."""
    overall_branch_coverage: float
    files: dict[str, FileCoverage] = field(default_factory=dict)
    phases_tracked: list[str] = field(default_factory=list)

@dataclass
class FileCoverage:
    """Coverage data for a single file."""
    path: str
    branch_coverage: float
    uncovered_branches: list[UncoveredBranch] = field(default_factory=list)

@dataclass
class UncoveredBranch:
    """A branch that was never taken."""
    line: int
    type: str  # "if", "else", "elif", "except", "for", "while"
    context: str  # Source line for context

@contextmanager
def collect_coverage(source_dirs: list[Path]):
    """Context manager for coverage collection."""
    import coverage

    cov = coverage.Coverage(
        branch=True,
        source=[str(d) for d in source_dirs],
        omit=["**/test_*", "**/*_test.py", "**/conftest.py"]
    )

    cov.start()
    try:
        yield cov
    finally:
        cov.stop()
        cov.save()
```

### Phase 2: Doctest Integration (2h)

```python
# In guard_helpers.py
def run_doctests_phase(
    files: list[Path],
    collect_coverage: bool = False
) -> tuple[bool, CoverageReport | None]:
    """Run doctests with optional coverage collection."""

    if not collect_coverage:
        return _run_doctests_basic(files), None

    from invar.shell.coverage_integration import collect_coverage

    source_dirs = list({f.parent for f in files})

    with collect_coverage(source_dirs) as cov:
        passed = _run_doctests_basic(files)

    report = extract_coverage_report(cov, files)
    return passed, report
```

### Phase 3: Hypothesis Integration (2h)

```python
# In guard_helpers.py
def run_hypothesis_phase(
    files: list[Path],
    collect_coverage: bool = False
) -> tuple[bool, CoverageReport | None]:
    """Run Hypothesis tests with optional coverage collection."""

    if not collect_coverage:
        return _run_hypothesis_basic(files), None

    from invar.shell.coverage_integration import collect_coverage

    source_dirs = list({f.parent for f in files})

    with collect_coverage(source_dirs) as cov:
        passed = _run_hypothesis_basic(files)

    report = extract_coverage_report(cov, files)
    return passed, report
```

### Phase 4: Report Merge & Output (1h)

```python
def merge_coverage_reports(
    doctest_report: CoverageReport | None,
    hypothesis_report: CoverageReport | None
) -> CoverageReport:
    """Merge coverage from multiple phases."""
    # Union of covered lines/branches
    # Intersection of uncovered = truly uncovered
    ...

def format_coverage_output(report: CoverageReport) -> str:
    """Format coverage report for CLI output."""
    ...
```

### Phase 5: CLI & MCP Integration (1h)

```python
# In guard.py CLI
@app.command()
def guard(
    path: Path = ...,
    coverage: bool = typer.Option(False, "--coverage", help="Collect branch coverage"),
    ...
):
    ...

# In MCP server
def invar_guard(coverage: bool = False, ...):
    ...
```

## Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
coverage = ["coverage[toml]>=7.0"]

# Or include in dev dependencies
[project.optional-dependencies]
dev = [
    ...,
    "coverage[toml]>=7.0",
]
```

## Configuration

```toml
# invar.toml or pyproject.toml
[tool.invar.guard]
# Coverage is always opt-in via --coverage flag
# No threshold enforcement (visibility only, not enforcement)
```

## Success Criteria

- [x] Decision made: Option A selected
- [x] `invar guard --coverage` collects branch coverage
- [x] Coverage limited to doctest + hypothesis phases
- [x] Clear note that CrossHair is excluded (symbolic execution)
- [x] JSON output includes coverage data
- [x] Performance overhead < 30% when enabled (opt-in only)
- [x] Works with `--changed` flag

## Resolved Questions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Opt-in or always-on? | **Opt-in** | Coverage has 20-30% overhead |
| Minimum threshold? | **None** | Visibility first, no enforcement |
| Track trends? | **Future** | Out of scope for v1 |
| CrossHair coverage? | **Excluded** | Technically impossible |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| coverage.py not installed | Graceful error: "Install coverage for --coverage support" |
| Performance overhead | Opt-in only, clear documentation |
| User expects CrossHair coverage | Clear note in output |

## Effort Estimate

| Task | Time |
|------|------|
| Coverage integration infrastructure | 2h |
| Doctest phase integration | 2h |
| Hypothesis phase integration | 2h |
| Report merge & formatting | 1h |
| CLI & MCP integration | 1h |
| **Total** | **~1 day** |

## Related

- DX-33: Verification Blind Spots Analysis (origin)
- DX-19: Smart Guard verification levels
- coverage.py: https://coverage.readthedocs.io/
