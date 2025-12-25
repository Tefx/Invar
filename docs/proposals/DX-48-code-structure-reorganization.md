# DX-48: Code Structure Reorganization

> **"Related code should live together."**

**Status:** Complete (Phase 1 + DX-48b-lite)
**Created:** 2025-12-26
**Effort:** Phase 1: Low | DX-48b-lite: Low
**Risk:** Phase 1: Very Low | DX-48b-lite: Low
**Breaking:** No (internal imports only, public API unchanged)

---

## Scope Split Decision (2025-12-26)

After review, this proposal was split and partially executed:

| Phase | Scope | Status | Rationale |
|-------|-------|--------|-----------|
| **DX-48a** | Delete dead code (~664 lines) | ✅ Complete | Low risk, high value |
| **DX-48b-lite** | shell/commands/ + shell/prove/ only | ✅ Complete | Low risk, clear benefit |
| **DX-48b-full** | Full core/ restructuring | Deferred | High risk, moderate value |

**Why DX-48b-lite instead of full restructuring?**
- Only restructured shell/ (10 files), left core/ flat (27 files)
- No file merges (highest risk part of original proposal)
- ~40 import updates vs ~160 in full proposal
- 45 minutes vs 3-4 hours

---

## Problem Statement

The `src/invar/` package has grown organically to 64 files across core/ and shell/ directories. While the Core/Shell architectural separation is correct, several issues have emerged:

### Issue 1: Dead Code (614 lines)

```
src/invar/contracts.py      # 153 lines - duplicates runtime
src/invar/decorators.py     # 95 lines  - duplicates runtime
src/invar/invariant.py      # 59 lines  - duplicates runtime
src/invar/resource.py       # ~50 lines - duplicates runtime
deprecated/                  # 307 lines - obsolete package
```

These files are not imported anywhere—`src/invar/__init__.py` re-exports directly from `invar_runtime`.

### Issue 2: Scattered Related Modules

**prove-related (4 files in shell/):**
```
prove.py           # CrossHair verification
prove_fallback.py  # Hypothesis fallback
prove_cache.py     # Caching
prove_accept.py    # Accept mechanism
```

**format-related (3 files in core/):**
```
formatter.py          # Output formatting
format_specs.py       # Format specifications
format_strategies.py  # Format strategies
```

**guard-related (2 files in shell/):**
```
guard_helpers.py   # Helper functions
guard_output.py    # Output handling
```

### Issue 3: Inconsistent Naming

| File | Pattern | Issue |
|------|---------|-------|
| `init_cmd.py` | `*_cmd.py` | ✓ Consistent |
| `update_cmd.py` | `*_cmd.py` | ✓ Consistent |
| `test_cmd.py` | `*_cmd.py` | ✓ Consistent |
| `mutate_cmd.py` | `*_cmd.py` | ✓ Consistent |
| `cli.py` | — | ✗ Should be `guard_cmd.py` or in commands/ |

### Issue 4: Flat Directory Bloat

- `core/` has 27 Python files at top level
- `shell/` has 21 Python files at top level
- Finding related functionality requires scanning many files

---

## Proposed Solution

### Principle: Group by Feature, Not by Type

Reorganize modules into logical subdirectories while maintaining Core/Shell separation.

### Target Structure

```
src/invar/
├── __init__.py                    # Re-exports from invar_runtime only
│
├── core/                          # Pure logic (no I/O)
│   ├── __init__.py
│   ├── models.py                  # Data models
│   ├── parser.py                  # Source parsing
│   ├── rules.py                   # Rule checking (imports from subdirs)
│   ├── suggestions.py             # Fix suggestions
│   ├── utils.py                   # Utilities
│   │
│   ├── analysis/                  # Code analysis
│   │   ├── __init__.py
│   │   ├── contracts.py           # ← core/contracts.py
│   │   ├── purity.py              # ← core/purity.py + purity_heuristics.py
│   │   ├── shell.py               # ← core/shell_analysis.py + shell_architecture.py
│   │   ├── entry_points.py        # ← core/entry_points.py
│   │   ├── extraction.py          # ← core/extraction.py
│   │   ├── references.py          # ← core/references.py + inspect.py
│   │   ├── lambda_helpers.py      # ← core/lambda_helpers.py
│   │   └── tautology.py           # ← core/tautology.py
│   │
│   ├── format/                    # Output formatting
│   │   ├── __init__.py
│   │   ├── output.py              # ← core/formatter.py
│   │   ├── specs.py               # ← core/format_specs.py
│   │   └── strategies.py          # ← core/format_strategies.py
│   │
│   └── verify/                    # Verification logic
│       ├── __init__.py
│       ├── routing.py             # ← core/verification_routing.py
│       ├── strategies.py          # ← core/strategies.py
│       ├── property_gen.py        # ← core/property_gen.py
│       ├── hypothesis.py          # ← core/hypothesis_strategies.py
│       ├── timeout.py             # ← core/timeout_inference.py
│       ├── must_use.py            # ← core/must_use.py
│       ├── review_trigger.py      # ← core/review_trigger.py
│       └── rule_meta.py           # ← core/rule_meta.py
│
├── shell/                         # I/O operations (Result[T, E])
│   ├── __init__.py
│   ├── config.py                  # Configuration loading
│   ├── fs.py                      # Filesystem operations
│   ├── git.py                     # Git operations
│   ├── templates.py               # Template operations
│   ├── testing.py                 # Test running
│   ├── mutation.py                # Mutation testing
│   ├── property_tests.py          # Property test execution
│   ├── mcp_config.py              # MCP configuration
│   │
│   ├── commands/                  # CLI commands
│   │   ├── __init__.py            # Typer app definition
│   │   ├── guard.py               # ← shell/cli.py (guard command)
│   │   ├── init.py                # ← shell/init_cmd.py
│   │   ├── update.py              # ← shell/update_cmd.py
│   │   ├── test.py                # ← shell/test_cmd.py
│   │   ├── mutate.py              # ← shell/mutate_cmd.py
│   │   └── perception.py          # ← shell/perception.py (map/sig)
│   │
│   ├── guard/                     # Guard helpers
│   │   ├── __init__.py
│   │   ├── helpers.py             # ← shell/guard_helpers.py
│   │   └── output.py              # ← shell/guard_output.py
│   │
│   └── prove/                     # Verification execution
│       ├── __init__.py
│       ├── crosshair.py           # ← shell/prove.py
│       ├── hypothesis.py          # ← shell/prove_fallback.py
│       ├── cache.py               # ← shell/prove_cache.py
│       └── accept.py              # ← shell/prove_accept.py
│
├── mcp/                           # MCP server (unchanged)
│   ├── __init__.py
│   ├── __main__.py
│   └── server.py
│
└── templates/                     # Template files (unchanged)
    └── ...
```

---

## Detailed Changes

### Phase 1: Delete Dead Code

| File | Lines | Action |
|------|-------|--------|
| `src/invar/contracts.py` | 153 | Delete |
| `src/invar/decorators.py` | 95 | Delete |
| `src/invar/invariant.py` | 59 | Delete |
| `src/invar/resource.py` | ~50 | Delete |
| `deprecated/` | 307 | Delete directory |

**Total:** -664 lines

### Phase 2: Create Subdirectory Structure

```bash
# core/ subdirectories
mkdir -p src/invar/core/{analysis,format,verify}

# shell/ subdirectories
mkdir -p src/invar/shell/{commands,guard,prove}

# Create __init__.py files
touch src/invar/core/{analysis,format,verify}/__init__.py
touch src/invar/shell/{commands,guard,prove}/__init__.py
```

### Phase 3: Move and Rename Files

#### core/analysis/ (8 files)

| From | To | Notes |
|------|-----|-------|
| `core/contracts.py` | `core/analysis/contracts.py` | — |
| `core/purity.py` | `core/analysis/purity.py` | Merge with purity_heuristics.py |
| `core/purity_heuristics.py` | (merged) | — |
| `core/shell_analysis.py` | `core/analysis/shell.py` | Merge with shell_architecture.py |
| `core/shell_architecture.py` | (merged) | — |
| `core/entry_points.py` | `core/analysis/entry_points.py` | — |
| `core/extraction.py` | `core/analysis/extraction.py` | — |
| `core/references.py` | `core/analysis/references.py` | Merge with inspect.py |
| `core/inspect.py` | (merged) | — |
| `core/lambda_helpers.py` | `core/analysis/lambda_helpers.py` | — |
| `core/tautology.py` | `core/analysis/tautology.py` | — |

#### core/format/ (3 files)

| From | To |
|------|-----|
| `core/formatter.py` | `core/format/output.py` |
| `core/format_specs.py` | `core/format/specs.py` |
| `core/format_strategies.py` | `core/format/strategies.py` |

#### core/verify/ (8 files)

| From | To |
|------|-----|
| `core/verification_routing.py` | `core/verify/routing.py` |
| `core/strategies.py` | `core/verify/strategies.py` |
| `core/property_gen.py` | `core/verify/property_gen.py` |
| `core/hypothesis_strategies.py` | `core/verify/hypothesis.py` |
| `core/timeout_inference.py` | `core/verify/timeout.py` |
| `core/must_use.py` | `core/verify/must_use.py` |
| `core/review_trigger.py` | `core/verify/review_trigger.py` |
| `core/rule_meta.py` | `core/verify/rule_meta.py` |

#### shell/commands/ (6 files)

| From | To |
|------|-----|
| `shell/cli.py` | `shell/commands/guard.py` |
| `shell/init_cmd.py` | `shell/commands/init.py` |
| `shell/update_cmd.py` | `shell/commands/update.py` |
| `shell/test_cmd.py` | `shell/commands/test.py` |
| `shell/mutate_cmd.py` | `shell/commands/mutate.py` |
| `shell/perception.py` | `shell/commands/perception.py` |

#### shell/guard/ (2 files)

| From | To |
|------|-----|
| `shell/guard_helpers.py` | `shell/guard/helpers.py` |
| `shell/guard_output.py` | `shell/guard/output.py` |

#### shell/prove/ (4 files)

| From | To |
|------|-----|
| `shell/prove.py` | `shell/prove/crosshair.py` |
| `shell/prove_fallback.py` | `shell/prove/hypothesis.py` |
| `shell/prove_cache.py` | `shell/prove/cache.py` |
| `shell/prove_accept.py` | `shell/prove/accept.py` |

### Phase 4: Merge Related Modules

#### Merge 1: purity.py + purity_heuristics.py → analysis/purity.py

```python
# analysis/purity.py
# Combine both modules, purity_heuristics becomes internal functions
```

#### Merge 2: shell_analysis.py + shell_architecture.py → analysis/shell.py

```python
# analysis/shell.py
# Both analyze shell code patterns, natural to combine
```

#### Merge 3: references.py + inspect.py → analysis/references.py

```python
# analysis/references.py
# Both deal with symbol references and inspection
```

### Phase 5: Update All Imports

Use automated refactoring to update all import statements:

```python
# Before
from invar.core.formatter import format_guard_agent
from invar.shell.cli import guard

# After
from invar.core.format.output import format_guard_agent
from invar.shell.commands.guard import guard
```

### Phase 6: Update __init__.py Files

Each subdirectory's `__init__.py` should re-export public symbols:

```python
# core/analysis/__init__.py
from invar.core.analysis.contracts import (
    check_contracts,
    check_empty_contracts,
    # ...
)
from invar.core.analysis.purity import (
    check_impure_calls,
    check_internal_imports,
    # ...
)
# ... etc
```

---

## File Count Changes

| Directory | Before | After | Change |
|-----------|--------|-------|--------|
| `core/` top-level | 27 | 6 | -21 |
| `core/analysis/` | 0 | 8 | +8 |
| `core/format/` | 0 | 3 | +3 |
| `core/verify/` | 0 | 8 | +8 |
| `shell/` top-level | 21 | 9 | -12 |
| `shell/commands/` | 0 | 6 | +6 |
| `shell/guard/` | 0 | 2 | +2 |
| `shell/prove/` | 0 | 4 | +4 |
| Root dead code | 4 | 0 | -4 |
| `deprecated/` | 3 | 0 | -3 |
| **Total files** | **64** | **~55** | **-9** |

---

## Import Path Migration

### Automated Migration Script

```python
#!/usr/bin/env python3
"""Migrate imports to new structure."""

MIGRATIONS = {
    # core/analysis/
    "from invar.core.contracts import": "from invar.core.analysis.contracts import",
    "from invar.core.purity import": "from invar.core.analysis.purity import",
    "from invar.core.shell_analysis import": "from invar.core.analysis.shell import",
    "from invar.core.shell_architecture import": "from invar.core.analysis.shell import",
    "from invar.core.entry_points import": "from invar.core.analysis.entry_points import",
    "from invar.core.extraction import": "from invar.core.analysis.extraction import",
    "from invar.core.references import": "from invar.core.analysis.references import",
    "from invar.core.inspect import": "from invar.core.analysis.references import",
    "from invar.core.lambda_helpers import": "from invar.core.analysis.lambda_helpers import",
    "from invar.core.tautology import": "from invar.core.analysis.tautology import",

    # core/format/
    "from invar.core.formatter import": "from invar.core.format.output import",
    "from invar.core.format_specs import": "from invar.core.format.specs import",
    "from invar.core.format_strategies import": "from invar.core.format.strategies import",

    # core/verify/
    "from invar.core.verification_routing import": "from invar.core.verify.routing import",
    "from invar.core.strategies import": "from invar.core.verify.strategies import",
    "from invar.core.property_gen import": "from invar.core.verify.property_gen import",
    "from invar.core.hypothesis_strategies import": "from invar.core.verify.hypothesis import",
    "from invar.core.timeout_inference import": "from invar.core.verify.timeout import",
    "from invar.core.must_use import": "from invar.core.verify.must_use import",
    "from invar.core.review_trigger import": "from invar.core.verify.review_trigger import",
    "from invar.core.rule_meta import": "from invar.core.verify.rule_meta import",

    # shell/commands/
    "from invar.shell.cli import": "from invar.shell.commands.guard import",
    "from invar.shell.init_cmd import": "from invar.shell.commands.init import",
    "from invar.shell.update_cmd import": "from invar.shell.commands.update import",
    "from invar.shell.test_cmd import": "from invar.shell.commands.test import",
    "from invar.shell.mutate_cmd import": "from invar.shell.commands.mutate import",
    "from invar.shell.perception import": "from invar.shell.commands.perception import",

    # shell/guard/
    "from invar.shell.guard_helpers import": "from invar.shell.guard.helpers import",
    "from invar.shell.guard_output import": "from invar.shell.guard.output import",

    # shell/prove/
    "from invar.shell.prove import": "from invar.shell.prove.crosshair import",
    "from invar.shell.prove_fallback import": "from invar.shell.prove.hypothesis import",
    "from invar.shell.prove_cache import": "from invar.shell.prove.cache import",
    "from invar.shell.prove_accept import": "from invar.shell.prove.accept import",
}
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Broken imports | High | High | Automated migration script + invar guard |
| Circular imports | Medium | Medium | Careful __init__.py design |
| MCP server breaks | Low | High | mcp/ directory unchanged |
| Template breaks | Low | Medium | templates/ directory unchanged |
| Test failures | Medium | Medium | Run full test suite after each phase |

---

## Implementation Plan

| Phase | Description | Effort | Verification |
|-------|-------------|--------|--------------|
| 1 | Delete dead code | 5 min | `invar guard` |
| 2 | Create subdirectories | 5 min | — |
| 3 | Move files (no merges) | 30 min | `invar guard` |
| 4 | Update imports | 30 min | `invar guard` + tests |
| 5 | Merge related modules | 1 hour | `invar guard` + tests |
| 6 | Update __init__.py exports | 30 min | `invar guard` + tests |
| 7 | Final verification | 15 min | Full test suite |

**Total estimated time:** 3-4 hours

---

## Success Criteria

### Phase 1 (DX-48a) - Complete

- [x] All dead code removed (-664 lines)
- [x] Misleading docstrings fixed (reference `invar_runtime` not `invar.decorators`)
- [x] `invar guard` passes
- [x] All tests pass

### DX-48b-lite - Complete

- [x] CLI commands grouped in `shell/commands/`
- [x] Prove modules grouped in `shell/prove/`
- [x] Consistent naming (`cli.py` → `guard.py`, `*_cmd.py` → `*.py`)
- [x] Entry points updated (`pyproject.toml`, MCP server)
- [x] `invar guard` passes (0 errors)
- [x] CLI commands work (`invar guard`, `invar map`, `invar sig`)

### DX-48b-full - Deferred

- [ ] core/ subdirectories (analysis/, format/, verify/)
- [ ] File merges (purity, shell_analysis, references)

---

## Alternatives Considered

### Option A: Minimal Cleanup (Dead Code Only)

Just delete dead code, keep flat structure.

- **Pros:** Low risk, fast
- **Cons:** Doesn't address organization issues

### Option B: This Proposal (Moderate Restructuring)

Group related modules, merge small files.

- **Pros:** Better organization, maintainability
- **Cons:** Import path changes

### Option C: Full Restructuring

Deeper hierarchy, more aggressive merging.

- **Pros:** Maximum organization
- **Cons:** Higher risk, more work

**Decision:** Option B balances improvement with risk.

---

## Related

- DX-21: Two-package architecture (established current structure)
- DX-22: Core/Shell separation (architectural foundation)

---

## Open Questions

1. Should `core/rules.py` stay at top level or move to `core/verify/`?
2. Should we add `py.typed` marker to subdirectories?
3. Should `__init__.py` files re-export all public symbols?
