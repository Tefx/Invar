# DX-56: Template Sync Unification

**Status:** Complete
**Created:** 2025-12-27
**Updated:** 2025-12-27
**Dependencies:** DX-49 (SSOT), DX-55 (Idempotent Init)
**Test Report:** [DX-56-test-report.md](../test-reports/DX-56-test-report.md)

## Problem Statement

### Current State

Three commands handle template synchronization with **overlapping but inconsistent** behavior:

```
┌─────────────────────────────────────────────────────────────────┐
│  invar init     │  invar update   │  invar sync-self            │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ For users       │ Alias for init  │ For Invar developers only   │
│ CLI syntax      │ CLI syntax      │ MCP syntax                  │
│ DX-55 4-state   │ DX-55 4-state   │ Simple region replace       │
│ From manifest   │ From manifest   │ HARDCODED file list         │
│ No project inj. │ No project inj. │ project-additions.md        │
│ --check         │ --check         │ --dry-run                   │
│ --force/--reset │ --force         │ (none)                      │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### Problems Identified

#### 1. Manifest Underutilization

`manifest.toml` already defines command behaviors, but `sync_self.py` ignores it:

```toml
# manifest.toml - already exists but unused by sync-self
[commands.sync_self]
syntax = "mcp"
inject_project_additions = true
```

```python
# sync_self.py - hardcoded instead of reading manifest
fully_managed = [("INVAR.md", "protocol/INVAR.md")]
sync_files = [
    ("CLAUDE.md", ...),
    (".claude/skills/develop/SKILL.md", ...),
    # ... hardcoded list
]
```

**Risk:** If init adds new files to manifest, sync-self won't pick them up → **divergence**.

#### 2. Region Schemes Duplicated

```python
# sync_self.py - duplicates what manifest defines
REGION_SCHEMES = {
    "managed": ("managed", "user"),
    "skill": ("skill", "extensions"),
}
```

```toml
# manifest.toml - already defines regions
[regions."CLAUDE.md"]
managed = { action = "overwrite" }
user = { action = "preserve" }

[regions.".claude/skills/*/SKILL.md"]
skill = { action = "overwrite" }
extensions = { action = "preserve" }
```

#### 3. Project Additions Limited to Invar

`project-additions.md` is a powerful feature for project-specific customization:

```toml
[regions."CLAUDE.md"]
project = { action = "inject", source = ".invar/project-additions.md" }
```

But only `sync-self` uses it. User projects cannot benefit from this pattern.

#### 4. Merge Logic Divergence

| Command | Merge Logic | States Handled |
|---------|-------------|----------------|
| init | DX-55 smart merge | intact, partial, missing, absent |
| sync-self | Simple region replace | regions present only |

If CLAUDE.md is corrupted in Invar repo, sync-self won't recover it properly.

#### 5. CLI Inconsistency

| Flag | init | update | sync-self |
|------|------|--------|-----------|
| Preview | `--check` | `--check` | `--dry-run` |
| Force refresh | `--force` | `--force` | (none) |
| Reset user content | `--reset` | (none) | (none) |

#### 6. Cryptic Naming

`sync-self` doesn't communicate its purpose:
- What is "self"?
- Why would I sync it?
- Is it for me?

Better: `invar dev sync` or `invar internal-sync`

---

## Proposed Solution

### Phase 1: Configuration-Driven sync-self (Low Risk)

**Goal:** Make sync-self read from manifest instead of hardcoding.

```python
# Before (sync_self.py)
fully_managed = [("INVAR.md", "protocol/INVAR.md")]
sync_files = [("CLAUDE.md", ...), ...]

# After
manifest = load_manifest(templates_dir).unwrap()
sync_config = manifest["commands"]["sync_self"]
fully_managed = get_fully_managed_files(manifest)
sync_files = get_partially_managed_files(manifest)
```

**Benefits:**
- Single source of truth (manifest.toml)
- No divergence between init and sync-self
- Easier to add new template files

### Phase 2: Unified Sync Engine (Medium Effort)

**Goal:** Share core sync logic between init and sync-self.

```python
# New: template_sync.py
def sync_templates(
    path: Path,
    syntax: Literal["cli", "mcp"] = "cli",
    inject_project_additions: bool = False,
    merge_strategy: Literal["smart", "simple"] = "smart",
) -> Result[SyncReport, str]:
    """Unified template sync engine.

    Used by both `invar init` and `invar sync-self`.
    """
    ...

# init.py becomes thin wrapper
def init(...):
    result = sync_templates(path, syntax="cli", ...)

# sync_self.py becomes thin wrapper
def sync_self(...):
    result = sync_templates(path, syntax="mcp", inject_project_additions=True)
```

**Benefits:**
- DX-55 smart merge for all commands
- Consistent behavior
- Reduced code duplication (~150 lines)

### Phase 3: Project Additions for All (Optional)

**Goal:** Enable project-specific customization for user projects.

```bash
# User creates their custom project rules
echo "## My Team Rules" > .invar/project-additions.md
echo "- Use async/await for I/O" >> .invar/project-additions.md

# invar init injects into CLAUDE.md project region
invar init --force
```

**Use Cases:**
- Team coding conventions
- Project-specific architecture rules
- Custom verification requirements

### Phase 4: CLI Cleanup (Low Risk)

#### 4a. Rename sync-self

```bash
# Before
invar sync-self

# After
invar dev sync
```

Implementation: Add `dev` subcommand group.

#### 4b. Unify Flags

```bash
# All commands use same flags
--check     # Preview changes (not --dry-run)
--force     # Update even if current
--reset     # Discard user content (with confirmation)
```

### Phase 5: New Diagnostic Commands (Optional)

```bash
# Show what's different from templates
invar template diff

# Validate template syntax
invar template validate

# Show template variables
invar template vars
```

---

## Implementation Plan

### Wave 1: Foundation (Low Risk)

| Task | Effort | Risk |
|------|--------|------|
| 1.1 sync-self reads from manifest | 2h | Low |
| 1.2 Share region scheme from manifest | 1h | Low |
| 1.3 Unify --check/--dry-run flags | 30m | Low |

### Wave 2: Unification (Medium Risk)

| Task | Effort | Risk |
|------|--------|------|
| 2.1 Create unified sync engine | 4h | Medium |
| 2.2 Migrate init to use engine | 2h | Medium |
| 2.3 Migrate sync-self to use engine | 2h | Medium |
| 2.4 Add --force to sync-self | 30m | Low |

### Wave 3: Enhancement (Optional)

| Task | Effort | Risk |
|------|--------|------|
| 3.1 Project additions for user projects | 2h | Low |
| 3.2 Rename to `invar dev sync` | 1h | Low |
| 3.3 Add `invar template diff` | 3h | Low |

---

## Decision Points

### D1: Keep sync-self or merge into init?

**Option A: Keep Separate (Recommended)**
- Clear separation of concerns
- Different audiences (users vs developers)
- No flag pollution in init

**Option B: Merge with `--internal` flag**
- Fewer commands
- But adds complexity to init
- Confusing for users

**Recommendation:** Keep separate, share engine internally.

### D2: Project additions for all projects?

**Option A: Enable for all (Recommended)**
- Powerful customization
- Already implemented, just needs exposure
- `.invar/project-additions.md` → CLAUDE.md project region

**Option B: Invar-only**
- Simpler
- But wastes existing capability

**Recommendation:** Enable for all projects.

### D3: CLI namespace?

**Option A: Flat (`invar sync-self` → `invar dev-sync`)**
- Minimal change
- But growing command list

**Option B: Hierarchical (`invar dev sync`)**
- Better organization
- Room for `invar dev template-diff`, etc.
- Standard CLI pattern

**Recommendation:** Hierarchical namespace.

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Hardcoded file lists | 2 (sync-self) | 0 |
| Duplicated region schemes | 2 locations | 1 (manifest) |
| Flag consistency | 60% | 100% |
| Lines in sync_self.py | 274 | ~50 (thin wrapper) |
| DX-55 coverage | init only | init + sync-self |

---

## Testing Requirements

### Regression Tests

- [ ] init creates all expected files
- [ ] sync-self creates all expected files
- [ ] Both handle 4 CLAUDE.md states (DX-55)
- [ ] Project additions injected correctly
- [ ] MCP syntax used for Invar project
- [ ] CLI syntax used for user projects

### New Tests

- [ ] Manifest change → both commands pick up
- [ ] --force works for sync-self
- [ ] --check and --dry-run produce same output

---

## Appendix: Current vs Proposed Architecture

### Current

```
┌─────────────┐     ┌─────────────┐
│   init.py   │     │sync_self.py │
│  (400 lines)│     │ (274 lines) │
├─────────────┤     ├─────────────┤
│ DX-55 merge │     │Simple merge │
│ From manifest│    │ Hardcoded   │
│ CLI syntax  │     │ MCP syntax  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│       template_engine.py        │
│  generate_from_manifest()       │
│  render_template_file()         │
└─────────────────────────────────┘
```

### Proposed

```
┌─────────────┐     ┌─────────────┐
│   init.py   │     │ dev/sync.py │
│  (100 lines)│     │  (50 lines) │
│ thin wrapper│     │thin wrapper │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│       template_sync.py          │
│  sync_templates()               │
│  - DX-55 smart merge            │
│  - Manifest-driven              │
│  - Syntax switching             │
│  - Project additions injection  │
└──────┬──────┘────────────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│       template_engine.py        │
│  (unchanged, lower-level)       │
└─────────────────────────────────┘
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking sync-self for Invar devs | Low | High | Comprehensive testing |
| Init regression | Low | High | DX-55 test suite |
| Manifest format changes | Low | Medium | Version in manifest |
| CLI breaking change (rename) | N/A | Low | Alias for 1 version |

---

## Detailed Implementation Plan

### Step 1: Create Unified Sync Engine (`template_sync.py`)

**File:** `src/invar/shell/commands/template_sync.py`

```python
@dataclass
class SyncConfig:
    """Configuration for template sync operation."""
    syntax: Literal["cli", "mcp"] = "cli"
    inject_project_additions: bool = False
    force: bool = False
    check: bool = False  # Preview only
    reset: bool = False  # Discard user content

@dataclass
class SyncReport:
    """Result of sync operation."""
    created: list[str]
    updated: list[str]
    skipped: list[str]
    errors: list[str]

def sync_templates(path: Path, config: SyncConfig) -> Result[SyncReport, str]:
    """Unified template sync engine.

    Handles:
    1. State detection (DX-55: intact/partial/missing/absent)
    2. Manifest-driven file list
    3. Region-based updates (managed/user/project)
    4. Syntax switching (CLI vs MCP)
    5. Project additions injection
    """
```

### Step 2: Manifest Extensions

**File:** `src/invar/templates/manifest.toml`

Add file categorization for sync engine:

```toml
[sync]
# Files that are fully managed (overwrite completely)
fully_managed = [
    "INVAR.md",
    ".invar/examples/",
]

# Files with region-based updates
region_managed = [
    "CLAUDE.md",
    ".claude/skills/*/SKILL.md",
]

# Files created once, never updated
create_only = [
    ".invar/context.md",
    ".pre-commit-config.yaml",
    ".claude/commands/",
]
```

### Step 3: Refactor Commands

**init.py** becomes thin wrapper:
```python
def init(...):
    config = SyncConfig(
        syntax="cli",
        inject_project_additions=has_project_additions(path),
        force=force,
        check=check,
        reset=reset,
    )
    result = sync_templates(path, config)
    # Handle MCP config, hooks, etc.
```

**dev/sync.py** (renamed from sync_self.py):
```python
def sync(...):
    if not is_invar_project(path):
        raise error
    config = SyncConfig(
        syntax="mcp",
        inject_project_additions=True,
        force=force,
        check=check,
    )
    result = sync_templates(path, config)
```

### Step 4: CLI Structure

```
invar/
├── init          # Main command (uses sync engine)
├── update        # Alias for init
├── dev/          # Developer commands (new group)
│   └── sync      # Invar project sync (renamed from sync-self)
└── template/     # Template diagnostics (optional)
    ├── diff      # Show differences
    └── vars      # Show variables
```

### Step 5: Test Matrix

| Scenario | init | dev sync | Expected |
|----------|------|----------|----------|
| Fresh project | ✓ | N/A | All files created |
| Invar project | N/A | ✓ | MCP syntax, project additions |
| CLAUDE.md intact | ✓ | ✓ | Update managed only |
| CLAUDE.md partial | ✓ | ✓ | DX-55 recovery |
| CLAUDE.md missing | ✓ | ✓ | Merge as preserved |
| CLAUDE.md absent | ✓ | ✓ | Create fresh |
| --force | ✓ | ✓ | Refresh managed |
| --check | ✓ | ✓ | Preview only |
| project-additions | ✓ | ✓ | Inject into project region |

---

## Implementation Progress

### Completed
- [x] Analysis of current implementation
- [x] Detailed implementation plan
- [x] Create template_sync.py engine
- [x] Manifest extensions for sync config
- [x] Refactor sync_self.py to thin wrapper
- [x] Refactor init.py to use sync engine
- [x] CLI restructure (`invar dev sync`)
- [x] Test suite (16 unit tests)
- [x] Isolated subagent testing (4 scenarios)
- [x] Test report generated

### Files Changed
- `src/invar/core/sync_helpers.py` - Created (pure logic)
- `src/invar/shell/commands/template_sync.py` - Created (sync engine)
- `src/invar/shell/commands/sync_self.py` - Refactored (~110 lines)
- `src/invar/shell/commands/init.py` - Refactored (uses sync engine)
- `src/invar/shell/commands/guard.py` - Added dev subcommand
- `src/invar/templates/manifest.toml` - Added sync config
- `tests/integration/test_dx56_sync.py` - Created (16 tests)

---

## References

- DX-49: Protocol Distribution Unification (SSOT)
- DX-55: Claude Init Conflict Resolution
- manifest.toml: Template configuration
