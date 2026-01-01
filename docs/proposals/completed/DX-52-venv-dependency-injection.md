# DX-52: Virtual Environment Dependency Injection

> **"One install, all projects."**

**Status:** ✅ Complete
**Created:** 2025-12-27
**Effort:** Medium (~1-2 days)
**Risk:** Low
**Priority:** High (blocks uvx adoption for real projects)

## Problem Statement

When using `uvx invar-tools` (the recommended zero-install approach), verification phases that require importing project code fail because the uvx environment lacks project dependencies.

### Current Behavior

```bash
# User's project structure
my-project/
├── .venv/                    # Has numpy, pandas, etc.
├── src/
│   └── math_utils.py         # imports numpy
└── .mcp.json                 # Uses uvx invar-tools mcp
```

```python
# my-project/src/math_utils.py
import numpy as np  # Project dependency

@pre(lambda arr: len(arr) > 0)
def mean(arr: list[float]) -> float:
    """
    >>> mean([1, 2, 3])
    2.0
    """
    return np.mean(arr)
```

When Claude calls `invar_guard`:

| Phase | Result | Reason |
|-------|--------|--------|
| Static Analysis | ✅ PASS | Only reads files, no import |
| Doctests | ❌ FAIL | `ModuleNotFoundError: numpy` |
| Property Tests | ❌ FAIL | Same reason |
| CrossHair | ❌ FAIL | Same reason |

### Root Cause

```
uvx invar-tools guard
    │
    └── uvx creates isolated environment
            │
            ├── Has: pytest, hypothesis, crosshair (invar deps)
            └── Missing: numpy, pandas, django (project deps)
                    │
                    └── subprocess.run([sys.executable, "-m", "pytest", ...])
                            │
                            └── pytest imports project code
                                    │
                                    └── project code: import numpy
                                            │
                                            └── FAIL: numpy not in uvx env
```

### Why Invar's Own Tests Pass

Invar's project dependencies ARE invar-tools dependencies (pytest, hypothesis, etc.), so there's no gap. This masked the problem during development.

## Solution Options Analysis

### Option A: Wrapper Script Launcher

```bash
# ~/.local/bin/invar-mcp-launcher
#!/bin/bash
for venv in .venv venv; do
    VENV_PYTHON="${PWD}/${venv}/bin/python"
    if "${VENV_PYTHON}" -c "import invar" 2>/dev/null; then
        exec "${VENV_PYTHON}" -m invar.mcp "$@"
    fi
done
exec uvx invar-tools mcp "$@"
```

| Pros | Cons |
|------|------|
| ✅ Clear logic | ❌ Requires manual install of launcher |
| ✅ Perfect isolation | ❌ Windows needs separate .bat/.ps1 |
| ✅ Zero Python overhead | ❌ User must know PATH setup |

**Verdict:** Too much user friction.

---

### Option B: MCP Server Re-spawn

```python
# In run_server()
project_python = detect_project_python_with_invar()
if project_python and project_python != sys.executable:
    os.execv(project_python, [project_python, "-m", "invar.mcp"])
```

| Pros | Cons |
|------|------|
| ✅ User-invisible | ❌ Extra subprocess check at startup |
| ✅ No configuration | ❌ execv behaves differently on Windows |
| ✅ Auto-adapts | ❌ Old project invar version issues |

**Verdict:** Good for Phase 2, but complex.

---

### Option C: Smart `invar init`

```python
def generate_smart_mcp_config():
    if project_has_invar():
        return {"command": project_python, "args": ["-m", "invar.mcp"]}
    else:
        return {"command": "uvx", "args": ["invar-tools", "mcp"]}
```

| Pros | Cons |
|------|------|
| ✅ One-time config | ❌ Needs re-init after pip install |
| ✅ Transparent config | ❌ User may forget to update |
| ✅ No runtime overhead | ❌ State change requires action |

**Verdict:** Good supplement, not primary solution.

---

### Option D: PYTHONPATH Injection (Selected for Phase 1)

```python
env["PYTHONPATH"] = project_site_packages
subprocess.run([sys.executable, ...], env=env)
```

| Pros | Cons |
|------|------|
| ✅ Simplest implementation | ⚠️ Potential dependency conflicts |
| ✅ Zero user action | ⚠️ Python version mismatch risk |
| ✅ 100% backward compatible | ⚠️ C extension compatibility |
| ✅ Covers 90% use cases | - |

**Verdict:** Best for Phase 1 - immediate solution.

---

### Option E: Hybrid with Auto-Upgrade (Future)

Combines D (immediate) + B (when project has invar) + C (upgrade prompt).

```
Phase 1: PYTHONPATH injection (works immediately)
    │
    └── Detect project has invar installed?
            │
            ├── No → Continue with PYTHONPATH
            └── Yes → Prompt: "Run 'invar config mcp --upgrade' for better compatibility"
```

**Verdict:** Best long-term solution.

---

## Decision Matrix

| Option | Complexity | UX | Compatibility | Phase |
|--------|------------|-----|---------------|-------|
| A: Wrapper | Low | Poor | Good | Rejected |
| B: Re-spawn | Medium | Good | Medium | Phase 2 |
| C: Smart Init | Low | Medium | Good | Supplement |
| **D: PYTHONPATH** | **Low** | **Good** | **Medium** | **Phase 1** |
| E: Hybrid | Medium | Best | Good | Future |

## Proposed Solution: Phased Implementation

### Phase 1: PYTHONPATH Injection (This Proposal)

Immediate fix with minimal changes.

#### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  uvx Python (sys.executable)                                     │
│                                                                  │
│  subprocess.run(                                                 │
│    [sys.executable, "-m", "pytest", ...],                        │
│    env={"PYTHONPATH": project_site_packages}  ← INJECT          │
│  )                                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Child Process (pytest/crosshair/hypothesis)                     │
│                                                                  │
│  sys.path = [                                                    │
│    PYTHONPATH: /project/.venv/lib/python3.11/site-packages,     │
│    uvx site-packages: ~/.cache/uv/.../site-packages,            │
│  ]                                                               │
│                                                                  │
│  Can now import:                                                 │
│    ✓ pytest (from uvx)                                           │
│    ✓ numpy (from project venv via PYTHONPATH)                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### Implementation

**New file: `src/invar/shell/subprocess_env.py`**

```python
"""Subprocess environment preparation with PYTHONPATH injection.

DX-52: Enable uvx-based invar to access project dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path

from deal import post


@post(lambda result: result is None or result.exists())
def detect_project_venv(cwd: Path) -> Path | None:
    """
    Detect project's virtual environment.

    Searches for common venv directory names with pyvenv.cfg marker.

    Args:
        cwd: Current working directory (project root)

    Returns:
        Path to venv directory, or None if not found

    Examples:
        >>> from pathlib import Path
        >>> detect_project_venv(Path("/nonexistent")) is None
        True
    """
    venv_names = [".venv", "venv", ".env", "env"]

    for name in venv_names:
        venv_path = cwd / name
        if (venv_path / "pyvenv.cfg").exists():
            return venv_path

    return None


@post(lambda result: result is None or result.exists())
def find_site_packages(venv_path: Path) -> Path | None:
    """
    Find site-packages directory within a venv.

    Handles both Unix and Windows layouts.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to site-packages, or None if not found

    Examples:
        >>> # Unix: .venv/lib/python3.11/site-packages
        >>> # Windows: .venv/Lib/site-packages
    """
    if not venv_path.exists():
        return None

    # Unix layout: lib/pythonX.Y/site-packages
    lib_path = venv_path / "lib"
    if lib_path.exists():
        for python_dir in lib_path.glob("python*"):
            site_packages = python_dir / "site-packages"
            if site_packages.exists():
                return site_packages

    # Windows layout: Lib/site-packages
    lib_path_win = venv_path / "Lib" / "site-packages"
    if lib_path_win.exists():
        return lib_path_win

    return None


def build_subprocess_env(cwd: Path | None = None) -> dict[str, str]:
    """
    Build environment dict with project's site-packages in PYTHONPATH.

    This enables uvx-based invar to import project dependencies
    when running doctests, property tests, and CrossHair.

    Args:
        cwd: Project root directory (defaults to current directory)

    Returns:
        Environment dict suitable for subprocess.run(env=...)

    Examples:
        >>> env = build_subprocess_env()
        >>> isinstance(env, dict)
        True
        >>> "PATH" in env  # Inherits from current env
        True
    """
    env = os.environ.copy()
    project_root = cwd or Path.cwd()

    venv = detect_project_venv(project_root)
    if venv is None:
        return env

    site_packages = find_site_packages(venv)
    if site_packages is None:
        return env

    # Prepend to PYTHONPATH
    current = env.get("PYTHONPATH", "")
    separator = ";" if os.name == "nt" else ":"
    if current:
        env["PYTHONPATH"] = f"{site_packages}{separator}{current}"
    else:
        env["PYTHONPATH"] = str(site_packages)

    return env
```

**Integration points (3 files):**

```python
# src/invar/shell/testing.py
from .subprocess_env import build_subprocess_env

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=timeout,
    env=build_subprocess_env(),  # ← ADD
)

# src/invar/shell/property_tests.py
# Similar change

# src/invar/shell/prove.py
# Similar change
```

### Phase 2: Smart Re-spawn (Future DX)

When project has invar installed, automatically use project Python via `os.execv()`.

#### Why Re-spawn Eliminates Risk

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1 Risk: Python Version Mismatch                          │
│                                                                  │
│  uvx Python 3.12 runs pytest                                     │
│       │                                                          │
│       └── imports numpy from PYTHONPATH                          │
│               │                                                  │
│               └── numpy.so compiled for Python 3.11              │
│                       │                                          │
│                       └── ABI mismatch → FAIL                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Phase 2 Solution: Process Replacement                           │
│                                                                  │
│  uvx invar-tools mcp                                             │
│       │                                                          │
│       ▼                                                          │
│  detect_project_python_with_invar()                              │
│       │                                                          │
│       └── Found: /project/.venv/bin/python (has invar)           │
│               │                                                  │
│               ▼                                                  │
│       os.execv("/project/.venv/bin/python", ["-m", "invar.mcp"]) │
│               │                                                  │
│               └── Process REPLACED (same PID, new Python)        │
│                       │                                          │
│                       ▼                                          │
│               MCP Server now runs with project Python 3.11       │
│                       │                                          │
│                       └── pytest uses Python 3.11                │
│                               │                                  │
│                               └── numpy.so matches → SUCCESS     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Implementation

```python
# src/invar/shell/subprocess_env.py (extend Phase 1 module)

def detect_project_python_with_invar(cwd: Path) -> Path | None:
    """
    Detect project Python that has invar installed.

    Args:
        cwd: Project root directory

    Returns:
        Path to Python executable if invar is installed, None otherwise

    Examples:
        >>> detect_project_python_with_invar(Path("/no-venv")) is None
        True
    """
    venv = detect_project_venv(cwd)
    if venv is None:
        return None

    # Find Python executable
    python_path = venv / "bin" / "python"  # Unix
    if not python_path.exists():
        python_path = venv / "Scripts" / "python.exe"  # Windows
    if not python_path.exists():
        return None

    # Check if invar is installed
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import invar"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return python_path
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


# src/invar/mcp/server.py
def run_server():
    """MCP server entry point with auto-respawn."""
    cwd = Path.cwd()

    # Phase 2: Check for project Python with invar
    project_python = detect_project_python_with_invar(cwd)

    if project_python and str(project_python) != sys.executable:
        # Re-spawn with project Python (has both invar AND project deps)
        # execv replaces current process, does not return
        os.execv(
            str(project_python),
            [str(project_python), "-m", "invar.mcp"]
        )

    # Phase 1 fallback: Continue with uvx + PYTHONPATH injection
    asyncio.run(main())
```

#### Phase 1 + Phase 2 Flow

```
Claude Code starts MCP: uvx invar-tools mcp
         │
         ▼
    ┌──────────────────────┐
    │ Project has invar?   │
    └──────────────────────┘
         │
    ┌────┴────┐
    │         │
   YES        NO
    │         │
    ▼         ▼
  Phase 2    Phase 1
  (execv)   (PYTHONPATH)
    │         │
    ▼         ▼
  Perfect    Pure Python OK
  compat     C ext may fail
```

### Phase 3: Smart Upgrade Prompt (Future DX)

Show upgrade prompt **only when Python version mismatch detected**.

#### Trigger Logic

```python
# src/invar/shell/subprocess_env.py

def get_venv_python_version(venv_path: Path) -> tuple[int, int] | None:
    """
    Read Python version from venv's pyvenv.cfg.

    Avoids spawning a subprocess by parsing the config file directly.

    Examples:
        >>> # pyvenv.cfg contains: version = 3.11.5
        >>> get_venv_python_version(Path(".venv"))
        (3, 11)
    """
    cfg_path = venv_path / "pyvenv.cfg"
    if not cfg_path.exists():
        return None

    for line in cfg_path.read_text().splitlines():
        if line.startswith("version"):
            # version = 3.11.5
            version_str = line.split("=")[1].strip()
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]))

    return None


def check_version_mismatch(cwd: Path) -> tuple[bool, str]:
    """
    Check if Python versions mismatch between venv and current interpreter.

    Returns:
        (is_mismatched, warning_message)
    """
    venv = detect_project_venv(cwd)
    if venv is None:
        return (False, "")

    venv_version = get_venv_python_version(venv)
    if venv_version is None:
        return (False, "")

    current_version = (sys.version_info.major, sys.version_info.minor)

    if venv_version != current_version:
        msg = f"""
⚠ Python version mismatch detected
  Project venv: {venv_version[0]}.{venv_version[1]}
  uvx invar:    {current_version[0]}.{current_version[1]}

  C extension modules (numpy, pandas, etc.) may fail to load.

  To fix, install invar in your project:
    pip install invar-tools

  This enables automatic Python version matching.
"""
        return (True, msg)

    return (False, "")
```

#### Prompt Frequency Control

```python
def should_suppress_prompt(project_root: Path) -> bool:
    """
    Check if upgrade prompt should be suppressed.

    Strategies:
    - Per-project daily limit (avoid spam)
    - User can permanently disable via .invar/no-upgrade-prompt
    """
    # Permanent disable
    if (project_root / ".invar" / "no-upgrade-prompt").exists():
        return True

    # Daily limit per project
    marker = project_root / ".invar" / ".last-upgrade-prompt"
    if marker.exists():
        from datetime import datetime, timedelta
        last_time = datetime.fromtimestamp(marker.stat().st_mtime)
        if datetime.now() - last_time < timedelta(days=1):
            return True

    # Update marker
    marker.parent.mkdir(exist_ok=True)
    marker.touch()
    return False


def maybe_show_upgrade_prompt(project_root: Path, console) -> None:
    """Show upgrade prompt if conditions are met."""
    is_mismatched, msg = check_version_mismatch(project_root)

    if not is_mismatched:
        return  # Versions match, no prompt needed

    if should_suppress_prompt(project_root):
        return  # Already prompted recently

    console.print(msg)
```

#### When Prompt Appears

| Condition | Prompt? | Reason |
|-----------|---------|--------|
| No venv found | ❌ | Nothing to compare |
| Versions match (3.11 = 3.11) | ❌ | No risk |
| Versions mismatch (3.11 ≠ 3.12) | ✅ | C extension risk |
| Already prompted today | ❌ | Avoid spam |
| `.invar/no-upgrade-prompt` exists | ❌ | User disabled |

#### User Experience

```bash
$ uvx invar-tools guard
✓ Static analysis passed
✓ Doctests passed

⚠ Python version mismatch detected
  Project venv: 3.11
  uvx invar:    3.12

  C extension modules (numpy, pandas, etc.) may fail to load.

  To fix, install invar in your project:
    pip install invar-tools

  This enables automatic Python version matching.
```

After installing invar in project:
```bash
$ uvx invar-tools guard
# (MCP auto-respawns with project Python via Phase 2)
✓ Static analysis passed
✓ Doctests passed
# No warning - versions now match
```

## Edge Cases

### 1. No Venv Found

- Static analysis: Works
- Doctests: May fail (with clear error message)
- Recommendation: Suggest creating venv

### 2. Non-Standard Venv Name

```toml
[tool.invar]
venv_path = "my_custom_venv"
```

### 3. Dependency Version Conflicts

```
Project: requests==2.25
uvx invar: requests==2.31
```

**Behavior:** PYTHONPATH is searched first, so project version wins.

**Risk:** If invar uses a feature from 2.31, it might break.

**Mitigation:** Invar's core deps (rich, returns, deal) are unlikely to conflict with user projects.

### 4. Python Version Mismatch

```
Project venv: Python 3.11
uvx: Python 3.12
```

**Risk:** C extensions compiled for 3.11 may not load in 3.12.

**Mitigation:**
- Pure Python packages work fine
- Add version check warning
- Phase 2 (re-spawn) eliminates this issue

### 5. Windows Path Separator

```python
separator = ";" if os.name == "nt" else ":"
env["PYTHONPATH"] = f"{site_packages}{separator}{current}"
```

## Configuration

```toml
# pyproject.toml
[tool.invar]
# Override venv detection (default: auto-detect)
venv_path = ".venv"

# Disable PYTHONPATH injection (default: true)
inject_pythonpath = true
```

## Success Criteria

### Phase 1

- [ ] `uvx invar-tools guard` works on projects with dependencies
- [ ] Automatic venv detection (`.venv`, `venv`, `.env`, `env`)
- [ ] Cross-platform (Unix + Windows)
- [ ] Graceful degradation when no venv found
- [ ] No breaking changes to existing behavior
- [ ] Documentation updated

### Phase 2

- [ ] Auto-respawn with project Python when invar is installed
- [ ] `os.execv()` works correctly on Unix and Windows
- [ ] No respawn loop (detect already-respawned state)
- [ ] Handles invar version mismatch gracefully

### Phase 3

- [ ] Python version mismatch detection works
- [ ] Prompt appears only when mismatch detected
- [ ] Daily frequency limit prevents spam
- [ ] User can permanently disable via `.invar/no-upgrade-prompt`

## Testing Strategy

### Manual Test

```bash
# 1. Create test project
mkdir /tmp/test-project && cd /tmp/test-project
python -m venv .venv
source .venv/bin/activate
pip install numpy invar-runtime

# 2. Create test file with numpy dependency
cat > math_utils.py << 'EOF'
import numpy as np
from invar_runtime import pre, post

@pre(lambda arr: len(arr) > 0)
@post(lambda result: result >= 0)
def mean(arr: list[float]) -> float:
    """
    >>> mean([1.0, 2.0, 3.0])
    2.0
    """
    return float(np.mean(arr))
EOF

# 3. Test (BEFORE fix: fails, AFTER fix: passes)
deactivate
uvx invar-tools guard math_utils.py
```

### Automated Tests

```python
# tests/test_subprocess_env.py
def test_detect_venv_standard_names():
    """Test detection of .venv, venv, .env, env."""

def test_detect_venv_not_found():
    """Test graceful handling when no venv exists."""

def test_find_site_packages_unix():
    """Test lib/pythonX.Y/site-packages layout."""

def test_find_site_packages_windows():
    """Test Lib/site-packages layout."""

def test_build_env_preserves_existing():
    """Test that existing env vars are preserved."""

def test_pythonpath_prepended():
    """Test that project packages have priority."""
```

## Effort Estimate

### Phase 1 (PYTHONPATH Injection)

| Task | Time |
|------|------|
| subprocess_env.py module | 2h |
| Integration (3 files) | 1h |
| Tests | 2h |
| Documentation | 1h |
| Manual testing | 1h |
| **Total** | **~7h** |

### Phase 2 (Smart Re-spawn)

| Task | Time |
|------|------|
| detect_project_python_with_invar() | 1h |
| MCP server entry point modification | 1h |
| Windows compatibility (execv behavior) | 2h |
| Tests | 2h |
| **Total** | **~6h** |

### Phase 3 (Upgrade Prompt)

| Task | Time |
|------|------|
| Version detection from pyvenv.cfg | 1h |
| Prompt frequency control | 1h |
| Integration with guard output | 1h |
| Tests | 1h |
| **Total** | **~4h** |

### Overall

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1 | ~7h | **High** (blocks uvx adoption) |
| Phase 2 | ~6h | Medium (eliminates C ext risk) |
| Phase 3 | ~4h | Low (UX improvement) |

## Implementation Order

```
Phase 1 → Ship → Gather feedback → Phase 2 + 3
```

Phase 1 can be shipped independently. Phases 2 and 3 can be combined in a follow-up release.

## Related

- DX-37: Coverage Integration (also uses subprocess)
- DX-16: Agent Tool Enforcement (MCP architecture)
- DX-21B: MCP configuration detection
