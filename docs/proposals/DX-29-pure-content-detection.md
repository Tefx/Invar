# DX-29: Pure Content Detection

**Status:** Proposed
**Created:** 2024-12-24
**Relates to:** DX-22 (Verification Strategy)

## Problem

The current module classification system uses three mechanisms:
1. **Path-based**: Files in `src/core/` are Core, `src/shell/` are Shell
2. **Pattern-based**: Glob patterns for custom project structures
3. **Content-based**: AST analysis of imports, decorators, and types

This creates several issues:

### Issue 1: Path Detection is Fragile
Files not in standard paths fall through to content detection, which may give incorrect results. Example: a library module with I/O imports but no contracts gets classified as Shell even though it's a utility.

### Issue 2: Entry Point False Positives
The entry point detection uses partial pattern matching that can trigger on unrelated code:
```python
# This triggers entry_point_too_thick because .get() matches router.get pattern
_INVAR_CHECK = os.environ.get("INVAR_CHECK", "1") == "1"

def invariant(condition: bool, message: str = "") -> None:  # Flagged!
```

### Issue 3: No Explicit Override
When auto-detection fails, users must add `@invar:allow` markers to suppress errors rather than correctly classifying the module.

## Proposed Solution

### Part 1: Explicit Module Markers (Immediate)

Add `# @invar:module <type>` marker support for explicit module classification:

```python
# @invar:module core
"""This file is Core despite not being in a /core/ path."""

from typing import Any

def pure_transform(data: Any) -> Any:
    """Pure function - no I/O, no side effects."""
    return data
```

```python
# @invar:module shell
"""This file is Shell - handles I/O operations."""

from pathlib import Path
from returns.result import Result, Success, Failure

def read_config(path: Path) -> Result[dict, str]:
    ...
```

```python
# @invar:module skip
"""This file is excluded from Core/Shell checks."""
```

**Priority order:**
1. Explicit `# @invar:module` marker (highest)
2. Pattern-based classification (config)
3. Path-based classification (convention)
4. Content-based auto-detection (fallback)

### Part 2: Deprecate Path/Pattern Config (Future)

Once `@invar:module` is stable, deprecate path/pattern config:

```toml
# pyproject.toml - deprecated
[tool.invar.guard]
core_paths = ["src/core"]     # Deprecated: use @invar:module
shell_paths = ["src/shell"]   # Deprecated: use @invar:module
```

New projects would rely entirely on:
1. Convention (`/core/` and `/shell/` in path)
2. Content detection
3. Explicit markers for edge cases

### Part 3: Improve Entry Point Detection (Future)

Fix the false positive in entry point detection by using AST-based decorator matching instead of string pattern matching:

```python
# Current (string matching - fragile)
if f".{base}(" in context:  # Matches os.environ.get()!
    return True

# Proposed (AST-based - precise)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for decorator in node.decorator_list:
            if _is_framework_decorator(decorator):
                return True
```

## Implementation Plan

### Phase 1: Add @invar:module Marker (This PR)
- [ ] Add `INVAR_MODULE_PATTERN` regex to `entry_points.py`
- [ ] Add `get_module_marker(source: str) -> ModuleType | None` function
- [ ] Update `auto_detect_module_type()` to check marker first
- [ ] Add documentation and examples

### Phase 2: Improve Entry Point Detection (Future PR)
- [ ] Refactor `_has_entry_decorator()` to use AST
- [ ] Remove partial pattern matching
- [ ] Remove workaround markers from `invariant.py`

### Phase 3: Deprecate Config-Based Classification (v1.0)
- [ ] Add deprecation warnings for `core_paths`/`shell_paths` config
- [ ] Update documentation for pure content detection
- [ ] Remove deprecated config in v2.0

## Benefits

1. **Explicit is Better**: Developers can explicitly declare intent
2. **Self-Documenting**: Module type is visible in the file header
3. **No Configuration**: Works without pyproject.toml entries
4. **Portable**: Module classification travels with the file
5. **Simpler Rules**: Reduces need for pattern/path configuration

## Backward Compatibility

- Path/pattern classification continues to work
- Existing projects unchanged
- Marker is opt-in for edge cases
- Gradual migration path

## Related Work

- DX-22: Established the content-based detection foundation
- DX-23: Entry point detection and exemptions
- `@shell:entry` marker: Precedent for file-level markers
