# Smart Verification Routing

> **"Right tool for the right code, automatically."**

## Quick Reference

Invar automatically selects the best verification tool for each file:

| Code Type | Detection | Verification Tool | Guarantee |
|-----------|-----------|-------------------|-----------|
| Core (pure Python) | No C extension imports | CrossHair | Mathematical proof |
| Core (C extensions) | `numpy`, `pandas`, etc. | Hypothesis | Property testing |
| Shell | Path or Result usage | Doctests only | Behavioral |

**Zero configuration.** Invar detects imports and routes automatically.

## How It Works

### 1. File Classification

When `invar guard` runs, each file is classified:

```
File Classification Flow:

┌──────────────────────────────────────────────────────────────┐
│                     Input: Python File                       │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Scan imports for C extensions│
            │  (numpy, pandas, torch, etc.) │
            └──────────────┬───────────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
    ┌────────────────┐         ┌─────────────────┐
    │ Has C extension│         │ Pure Python     │
    │ → Hypothesis   │         │ → CrossHair     │
    └────────────────┘         └─────────────────┘
```

### 2. Incompatible Libraries

These libraries cannot be symbolically executed by CrossHair:

```python
# C/Fortran Extensions (no symbolic execution possible)
"numpy", "pandas", "scipy", "sklearn", "torch", "tensorflow"

# Image Processing (C backends)
"cv2", "PIL", "pillow", "skimage"

# Network I/O (non-deterministic)
"requests", "aiohttp", "httpx"

# System Calls (side effects)
"subprocess", "multiprocessing"

# Databases (I/O operations)
"sqlalchemy", "psycopg2", "pymongo"
```

### 3. Routing Decision

```python
from invar.core.verification_routing import select_verification_tool

# Pure Python with contracts → CrossHair (can prove correctness)
select_verification_tool("@pre(lambda x: x > 0)\ndef foo(x): pass", has_contracts=True)
# → VerificationTool.CROSSHAIR

# C extension code → Hypothesis (CrossHair would timeout)
select_verification_tool("import numpy\n@pre(...)\ndef bar(): pass", has_contracts=True)
# → VerificationTool.HYPOTHESIS

# No contracts → Skip (nothing to verify)
select_verification_tool("def baz(): pass", has_contracts=False)
# → VerificationTool.SKIP
```

## Why Smart Routing?

### Problem: Wasted Time

Before DX-22:
```
CrossHair attempt on numpy code → 10s timeout → Hypothesis fallback → 2s
Total: 12 seconds wasted
```

### Solution: Proactive Detection

After DX-22:
```
Detect numpy import → Direct to Hypothesis → 2s
Total: 2 seconds, no wasted attempts
```

### Performance Impact

| Scenario | Before DX-22 | After DX-22 |
|----------|--------------|-------------|
| Pure Python | ~5s | ~5s |
| C extension (1 file) | ~12s | ~2s |
| Mixed project (10 files, 3 with numpy) | ~41s | ~17s |

## De-duplicated Statistics

DX-22 provides clear statistics distinguishing proof from testing:

```
Verification breakdown:
  ✓ Proven (CrossHair): 130 functions
  ✓ Tested (Hypothesis): 19 functions
    (C-extension routing: 3 files)
  ✓ Doctests: 88 passed
  Proof coverage: 87%
```

**Proof coverage** = percentage of verifiable code proven by CrossHair (mathematical guarantee).

## Configuration

No configuration needed. Smart routing is automatic.

If you need to force a specific tool:

```python
# Force Hypothesis for a file that CrossHair struggles with
# Add to imports (even if not used)
import subprocess  # @invar:routing hint

# Or add a comment
# @invar:force hypothesis
```

## API Reference

### `has_incompatible_imports(source: str) -> bool`

Check if source contains C extension imports.

```python
>>> from invar.core.verification_routing import has_incompatible_imports
>>> has_incompatible_imports("import numpy")
True
>>> has_incompatible_imports("import json")
False
```

### `get_incompatible_imports(source: str) -> set[str]`

Get the set of incompatible libraries found.

```python
>>> from invar.core.verification_routing import get_incompatible_imports
>>> get_incompatible_imports("import numpy\nfrom pandas import DataFrame")
{'numpy', 'pandas'}
```

### `select_verification_tool(source: str, has_contracts: bool) -> VerificationTool`

Select the appropriate verification tool.

```python
>>> from invar.core.verification_routing import select_verification_tool, VerificationTool
>>> select_verification_tool("import numpy", has_contracts=True)
<VerificationTool.HYPOTHESIS: 'hypothesis'>
```

## See Also

- [Verification Overview](./README.md) - Full verification pipeline
- [DX-22 Proposal](../../proposals/DX-22-verification-strategy.md) - Design history
- [CrossHair vs Hypothesis](./crosshair-vs-hypothesis.md) - Tool comparison
