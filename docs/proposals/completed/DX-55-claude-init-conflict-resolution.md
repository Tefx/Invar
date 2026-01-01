# DX-55: Claude /init Conflict Resolution

**Status:** ✅ Complete
**Created:** 2025-12-27
**Updated:** 2025-12-27
**Test Report:** [DX-55-test-report.md](../test-reports/DX-55-test-report.md)
**Problem:** Running Claude `/init` after `invar init` destroys Invar configuration

## Problem Statement

### Scenario

```
1. User runs: invar init
   → Creates CLAUDE.md with <!--invar:managed-->, <!--invar:project-->, <!--invar:user--> regions
   → Creates .claude/skills/, .mcp.json, etc.

2. Time passes...

3. User runs: claude /init (or clicks "Initialize" in Claude Code)
   → Claude overwrites CLAUDE.md with fresh project analysis
   → All Invar regions lost ❌
```

### Impact

| File | Consequence |
|------|-------------|
| `CLAUDE.md` | All Invar regions destroyed |
| `.claude/skills/` | May be overwritten or conflicted |
| `.mcp.json` | May be overwritten |
| `INVAR.md` | Protected by pre-commit (safe) |
| `.invar/` | Not touched by Claude (safe) |

### Why This Happens

1. Claude `/init` doesn't know about Invar's region markers
2. Invar doesn't protect CLAUDE.md like it protects INVAR.md
3. No mechanism to merge content from both tools

## Design Goals

1. **Detection**: Recognize when CLAUDE.md has been overwritten
2. **Recovery**: Restore Invar regions without losing Claude's content
3. **Simplicity**: One command that always does the right thing
4. **Idempotent**: Safe to run multiple times

---

## Key Design Decision: Unified Idempotent Command

### Problem with Two Commands

Current design has `invar init` and `invar update` as separate commands:

| User Scenario | Correct Command | User Confusion |
|---------------|-----------------|----------------|
| New project | `init` | None |
| After `claude /init` | `update`? `init`? | Which one? |
| After Invar upgrade | `update` | Maybe `init`? |
| Not sure of state | ??? | Decision paralysis |

This violates Invar's own principles:
- **DX-54**: Reduce agent decisions
- **DX-06**: Zero-decision tools
- **Lesson #11**: Agent-Native means no choices

### Solution: Merge into Idempotent `invar init`

**One command that always works:**

```
invar init
│
├─ Not initialized?
│   └─ Full setup (create all files)
│
├─ Already initialized?
│   ├─ CLAUDE.md intact? → Update managed regions only
│   ├─ CLAUDE.md partial? → Clean + rebuild
│   ├─ CLAUDE.md missing regions? → Smart merge
│   └─ CLAUDE.md absent? → Create new
│
└─ Check version, update if needed
```

**Backwards Compatibility:**
- `invar update` becomes an alias for `invar init`
- Existing scripts continue to work

---

## Detailed Design

### Phase 1: Unified Command Architecture

#### 1.1 State Detection

```python
def detect_project_state(project_path: Path) -> ProjectState:
    """
    Detect Invar initialization state.

    Returns:
        ProjectState with:
        - initialized: bool
        - claude_md_state: "intact" | "partial" | "missing" | "absent"
        - version: str | None
        - needs_update: bool
    """
    invar_md = project_path / "INVAR.md"
    invar_dir = project_path / ".invar"
    claude_md = project_path / "CLAUDE.md"

    initialized = invar_md.exists() and invar_dir.exists()

    return ProjectState(
        initialized=initialized,
        claude_md_state=detect_claude_md_state(claude_md),
        version=extract_version(invar_md) if initialized else None,
        needs_update=check_version_outdated(...)
    )


def detect_claude_md_state(path: Path) -> Literal["intact", "partial", "missing", "absent"]:
    """
    Detect the state of CLAUDE.md Invar regions.

    Returns:
        "intact": All regions present and properly closed
        "partial": Some regions missing or malformed (corruption)
        "missing": File exists but no Invar regions (overwritten)
        "absent": File doesn't exist
    """
    if not path.exists():
        return "absent"

    content = path.read_text()

    # Check for proper region structure
    has_managed_open = "<!--invar:managed" in content
    has_managed_close = "<!--/invar:managed-->" in content
    has_user_open = "<!--invar:user-->" in content
    has_user_close = "<!--/invar:user-->" in content

    if all([has_managed_open, has_managed_close, has_user_open, has_user_close]):
        return "intact"
    elif any([has_managed_open, has_managed_close, has_user_open, has_user_close]):
        return "partial"  # Some markers but not all
    else:
        return "missing"  # No Invar markers at all
```

#### 1.2 Unified Command Logic

```python
@app.command()
def init(
    path: Path = Path("."),
    check: bool = False,      # Preview mode
    force: bool = False,      # Update even if current
    reset: bool = False,      # Dangerous: discard user content
    claude: bool = False,     # Also run claude /init first
):
    """
    Initialize or update Invar configuration.

    This command is idempotent - safe to run multiple times.
    It detects current state and does the right thing:

    - New project: Full setup
    - Existing project: Update managed regions, preserve user content
    - Corrupted/overwritten: Smart recovery with content preservation
    """
    state = detect_project_state(path)

    if check:
        return report_what_would_change(state)

    if reset:
        if not confirm("This will DELETE all user customizations. Continue?"):
            return
        return full_reset(path)

    if not state.initialized:
        return full_init(path, claude=claude)

    # Already initialized - handle various states
    match state.claude_md_state:
        case "intact":
            if state.needs_update or force:
                return update_managed_regions(path)
            else:
                console.print("✓ Invar configured (no changes needed)")

        case "partial":
            return clean_and_rebuild(path)

        case "missing":
            return smart_merge(path)

        case "absent":
            return create_claude_md(path)
```

#### 1.3 Output Examples

```bash
# First time initialization
$ invar init
✓ Initialized Invar v5.0
  Created: INVAR.md, CLAUDE.md, .invar/, .claude/skills/

⚠ Note: If you run 'claude /init' later, just run 'invar init' again.

# Already initialized, up to date
$ invar init
✓ Invar v5.0 configured (no changes needed)

# Already initialized, needs version update
$ invar init
✓ Updated Invar v5.0
  Refreshed: CLAUDE.md (managed section)
  Refreshed: .claude/skills/* (skill sections)
  Preserved: All user content

# After claude /init overwrote CLAUDE.md
$ invar init
✓ Recovered Invar v5.0
  Restored: CLAUDE.md regions
  Preserved: Claude analysis → user section

  Review the merged content in CLAUDE.md

# Partial corruption detected
$ invar init
✓ Repaired Invar v5.0
  Fixed: CLAUDE.md (malformed regions)
  Recovered: User content from corrupted file

# Preview mode
$ invar init --check
Would update:
  - CLAUDE.md (managed section v4.0 → v5.0)
  - .claude/skills/develop/SKILL.md (refresh)

Run 'invar init' to apply.
```

### Phase 2: Smart Merge Implementation

#### 2.1 Merge Strategy by State

```python
@pre(lambda content: isinstance(content, str))
@post(lambda result: is_valid_region_structure(result))
def merge_claude_md(
    existing_content: str,
    managed_template: str,
    project_additions: str | None = None,
    state: Literal["intact", "partial", "missing"]
) -> str:
    """
    Smart merge based on detected state.
    """
    match state:
        case "intact":
            # Just update managed, preserve user exactly
            existing_user = extract_region(existing_content, "user")
            return build_claude_md(managed_template, project_additions, existing_user)

        case "partial":
            # Corruption: try to salvage user content
            existing_user = try_extract_region(existing_content, "user")
            non_invar = strip_invar_markers(existing_content)

            if existing_user:
                # Found user region, check for extra content outside
                extra = get_content_outside_regions(existing_content)
                combined = existing_user
                if extra.strip():
                    combined += f"\n\n## Recovered Content\n\n{extra}"
            else:
                # No user region found, treat cleaned content as user
                combined = f"## Recovered Content\n\n{non_invar}"

            return build_claude_md(managed_template, project_additions, combined)

        case "missing":
            # No Invar markers at all - treat entire file as user content
            user_content = format_preserved_content(existing_content)
            return build_claude_md(managed_template, project_additions, user_content)


def format_preserved_content(content: str) -> str:
    """Format preserved content with review markers."""
    return f"""<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
<!-- Merge date: {date.today().isoformat()} -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

{content}

<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->"""


def strip_invar_markers(content: str) -> str:
    """Remove all Invar region markers, keeping content."""
    import re
    # Remove all <!--invar:xxx--> and <!--/invar:xxx--> markers
    cleaned = re.sub(r'<!--/?invar:\w+[^>]*-->', '', content)
    # Clean up excessive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def is_valid_region_structure(content: str) -> bool:
    """Validate that all regions are properly opened and closed."""
    import re
    opens = re.findall(r'<!--invar:(\w+)', content)
    closes = re.findall(r'<!--/invar:(\w+)', content)
    return opens == closes  # Order and count must match
```

#### 2.2 Visual Merge Result

```
Before (Claude-generated or corrupted):
┌─────────────────────────────────────┐
│ # Project Guide                     │
│ <!--invar:managed-->                │  ← Partial marker (no close)
│ This project uses Python 3.12...   │
│ Key files: src/main.py, tests/...  │
│                                     │
│ ## Architecture                     │
│ [Claude's analysis]                 │
└─────────────────────────────────────┘

After (Cleaned and merged):
┌─────────────────────────────────────┐
│ <!--invar:managed version="5.0"-->  │
│ # Project Development Guide         │
│ [Fresh Invar managed content]       │
│ <!--/invar:managed-->               │
│                                     │
│ <!--invar:project-->                │
│ <!--/invar:project-->               │
│                                     │
│ <!--invar:user-->                   │
│ <!-- MERGED CONTENT ... -->         │
│ ## Recovered Content                │
│                                     │
│ # Project Guide                     │  ← Original preserved
│ This project uses Python 3.12...   │
│ ...                                 │
│ <!-- END MERGED CONTENT -->         │
│ <!--/invar:user-->                  │
└─────────────────────────────────────┘
```

### Phase 3: Backwards Compatibility

#### 3.1 Update as Alias

```python
@app.command()
def update(
    path: Path = Path("."),
    check: bool = False,
    force: bool = False,
):
    """
    Alias for 'invar init'.

    Maintained for backwards compatibility.
    Both commands are now idempotent and do the same thing.
    """
    console.print("[dim]Note: 'update' is now an alias for 'init'[/dim]")
    return init(path=path, check=check, force=force)
```

#### 3.2 Deprecation Timeline

| Phase | Behavior |
|-------|----------|
| v5.1 | `update` works, shows note |
| v6.0 | `update` shows deprecation warning |
| v7.0 | `update` removed (optional) |

### Phase 4: Pre-commit Protection (Optional)

```yaml
# .pre-commit-config.yaml
- id: invar-claude-md-regions
  name: CLAUDE.md Region Check
  entry: bash -c 'if [ -f CLAUDE.md ] && ! grep -q "<!--invar:managed-->" CLAUDE.md; then echo "⚠ CLAUDE.md missing Invar regions. Run: invar init"; exit 1; fi'
  language: system
  files: ^CLAUDE\.md$
  pass_filenames: false
```

### Phase 5: Skills Directory Handling

Same logic applies to `.claude/skills/`:

```python
def handle_skills(skills_dir: Path, force: bool = False) -> list[str]:
    """
    Check and update skill files.

    Returns list of actions taken.
    """
    actions = []
    for skill_name in ["develop", "review", "investigate", "propose"]:
        skill_file = skills_dir / skill_name / "SKILL.md"

        if not skill_file.exists():
            create_skill(skill_file, skill_name)
            actions.append(f"Created: {skill_file}")

        elif "<!--invar:skill-->" not in skill_file.read_text():
            # Missing markers - merge with template
            merge_skill(skill_file, skill_name)
            actions.append(f"Recovered: {skill_file}")

        elif force or skill_outdated(skill_file):
            update_skill(skill_file, skill_name)
            actions.append(f"Updated: {skill_file}")

    return actions
```

---

## Command Reference

### `invar init`

```
Usage: invar init [OPTIONS] [PATH]

Initialize or update Invar configuration (idempotent).

Arguments:
  PATH    Project directory [default: .]

Options:
  --check    Preview changes without applying
  --force    Update even if already current
  --reset    Dangerous: discard all user content
  --claude   Run 'claude /init' first, then setup Invar
  --help     Show this message
```

### Behavior Matrix

| State | --check | Default | --force | --reset |
|-------|---------|---------|---------|---------|
| Not initialized | Report | Full setup | Full setup | Full setup |
| Intact + current | Report nothing | No changes | Refresh | Full reset |
| Intact + outdated | Report updates | Update managed | Update managed | Full reset |
| Partial | Report repair | Clean + rebuild | Clean + rebuild | Full reset |
| Missing regions | Report merge | Smart merge | Smart merge | Full reset |

---

## Implementation Plan

| Phase | Scope | Effort | Priority |
|-------|-------|--------|----------|
| 1 | Unified command + state detection | Medium | High |
| 2 | Smart merge (all states) | Medium | High |
| 3 | Backwards compat (update alias) | Low | High |
| 4 | Pre-commit hook | Low | Medium |
| 5 | Skills handling | Low | Medium |

**Recommended order:** 1 → 2 → 3 → 4 → 5

---

## Success Criteria

1. **Single Command**: `invar init` handles all scenarios
2. **Idempotent**: Safe to run multiple times
3. **No Data Loss**: User content always preserved
4. **Clear Output**: User knows what happened
5. **Backwards Compatible**: `invar update` still works

---

## Testing Requirements

### Test Environment Setup

Create isolated test environments to avoid affecting real projects:

```bash
# Create temporary test directory
TEST_DIR=$(mktemp -d)
cd $TEST_DIR

# Initialize git (required for some Invar features)
git init
echo "*.pyc" > .gitignore
git add .gitignore && git commit -m "init"

# Create minimal Python project structure
mkdir -p src/myproject
echo 'print("hello")' > src/myproject/__init__.py
echo '[project]\nname = "myproject"' > pyproject.toml
```

### Test Scenarios Matrix

| # | Scenario | Initial State | Action | Expected Result |
|---|----------|---------------|--------|-----------------|
| **A. Fresh Project** |
| A1 | New project, no files | Empty | `invar init` | Full setup created |
| A2 | New project with existing CLAUDE.md | CLAUDE.md (no regions) | `invar init` | Merge, preserve content |
| A3 | Run init twice | After A1 | `invar init` | No changes, success message |
| **B. Intact State** |
| B1 | All regions present, current version | Intact | `invar init` | No changes |
| B2 | All regions present, outdated version | Intact (v4.0) | `invar init` | Update managed only |
| B3 | User content in user region | Intact + user content | `invar init` | Preserve user content exactly |
| B4 | Force update | Intact + current | `invar init --force` | Refresh managed |
| **C. Partial State (Corruption)** |
| C1 | Missing close tag | `<!--invar:managed-->` only | `invar init` | Repair, recover content |
| C2 | Missing open tag | `<!--/invar:managed-->` only | `invar init` | Repair, recover content |
| C3 | Nested regions (invalid) | Malformed nesting | `invar init` | Clean + rebuild |
| C4 | User region only | `<!--invar:user-->` but no managed | `invar init` | Add managed, preserve user |
| **D. Missing State (Overwritten)** |
| D1 | Claude /init overwrote | Claude-generated content | `invar init` | Merge, move to user section |
| D2 | Manual edit removed regions | Plain markdown | `invar init` | Merge, preserve as user |
| D3 | Empty file | Empty CLAUDE.md | `invar init` | Create fresh regions |
| **E. Absent State** |
| E1 | CLAUDE.md deleted | No CLAUDE.md | `invar init` | Create new file |
| E2 | .invar/ deleted | Missing .invar/ | `invar init` | Recreate directory |
| **F. Skills Handling** |
| F1 | Skills intact | All skills with markers | `invar init` | No changes |
| F2 | Skill missing markers | Skill without `<!--invar:skill-->` | `invar init` | Recover skill |
| F3 | Skill deleted | Missing skill file | `invar init` | Recreate skill |
| F4 | Extensions preserved | Skill with user extensions | `invar init` | Preserve extensions |
| **G. Edge Cases** |
| G1 | Very large CLAUDE.md | 10000+ lines | `invar init` | Handle without timeout |
| G2 | Binary content in file | Non-UTF8 content | `invar init` | Graceful error |
| G3 | Read-only file | Permission denied | `invar init` | Clear error message |
| G4 | Concurrent modification | File changes during merge | `invar init` | Atomic write |
| **H. Backwards Compatibility** |
| H1 | `invar update` command | Any state | `invar update` | Same as `invar init` |
| H2 | `--check` flag | Any state | `invar init --check` | Preview, no changes |
| H3 | `--reset` flag | Intact + user content | `invar init --reset` | Confirm, then reset |

### Test Execution Script

```bash
#!/bin/bash
# test_dx55.sh - Comprehensive DX-55 test suite

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
RESULTS=""

run_test() {
    local name="$1"
    local setup="$2"
    local command="$3"
    local verify="$4"

    echo -n "Testing $name... "

    # Create isolated environment
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    mkdir -p src/myproject
    echo '[project]\nname = "test"' > pyproject.toml

    # Run setup
    eval "$setup" 2>/dev/null || true

    # Run command
    if eval "$command" 2>&1; then
        # Verify result
        if eval "$verify" 2>/dev/null; then
            echo -e "${GREEN}PASS${NC}"
            ((PASS++))
            RESULTS+="✅ $name\n"
        else
            echo -e "${RED}FAIL${NC} (verification)"
            ((FAIL++))
            RESULTS+="❌ $name (verification failed)\n"
        fi
    else
        echo -e "${RED}FAIL${NC} (command error)"
        ((FAIL++))
        RESULTS+="❌ $name (command error)\n"
    fi

    # Cleanup
    rm -rf "$TEST_DIR"
}

# A1: Fresh project
run_test "A1: Fresh project" \
    "" \
    "invar init" \
    "test -f INVAR.md && test -f CLAUDE.md && test -d .invar"

# A3: Idempotent
run_test "A3: Idempotent" \
    "invar init" \
    "invar init" \
    "grep -q 'no changes' /dev/stdin || true"

# B3: Preserve user content
run_test "B3: Preserve user content" \
    "invar init && sed -i 's|<!--/invar:user-->|MY_CUSTOM_CONTENT\n<!--/invar:user-->|' CLAUDE.md" \
    "invar init --force" \
    "grep -q 'MY_CUSTOM_CONTENT' CLAUDE.md"

# D1: Claude /init recovery
run_test "D1: Claude /init recovery" \
    "invar init && echo '# Claude Generated\nProject analysis here' > CLAUDE.md" \
    "invar init" \
    "grep -q 'invar:managed' CLAUDE.md && grep -q 'Project analysis' CLAUDE.md"

# H1: Backwards compat
run_test "H1: invar update alias" \
    "invar init" \
    "invar update" \
    "test -f CLAUDE.md"

# Summary
echo ""
echo "=============================="
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "=============================="
echo -e "$RESULTS"

exit $FAIL
```

### Test Report Format

After implementation, generate a test report:

```markdown
# DX-55 Test Report

**Date:** YYYY-MM-DD
**Version:** X.Y.Z
**Tester:** [Agent/Human]

## Environment

- OS: [macOS/Linux/Windows]
- Python: [version]
- Invar: [version]

## Results Summary

| Category | Pass | Fail | Skip |
|----------|------|------|------|
| A. Fresh Project | X | 0 | 0 |
| B. Intact State | X | 0 | 0 |
| C. Partial State | X | 0 | 0 |
| D. Missing State | X | 0 | 0 |
| E. Absent State | X | 0 | 0 |
| F. Skills Handling | X | 0 | 0 |
| G. Edge Cases | X | 0 | 0 |
| H. Backwards Compat | X | 0 | 0 |
| **Total** | **XX** | **0** | **0** |

## Detailed Results

### A. Fresh Project

| Test | Result | Notes |
|------|--------|-------|
| A1 | ✅ PASS | |
| A2 | ✅ PASS | |
| A3 | ✅ PASS | |

### B. Intact State

...

## Content Preservation Verification

For each merge scenario, verify content integrity:

| Scenario | Original Content | After Merge | Preserved? |
|----------|------------------|-------------|------------|
| D1 | `# Claude Generated\n...` | In user section | ✅ |
| ... | | | |

## Regression Check

Verify existing functionality not broken:

- [ ] `invar guard` works normally
- [ ] `invar sig` works normally
- [ ] `invar map` works normally
- [ ] Pre-commit hooks work normally
- [ ] MCP server works normally

## Performance

| Scenario | Time | Acceptable? |
|----------|------|-------------|
| Fresh init | < 2s | ✅ |
| Large file merge (10K lines) | < 5s | ✅ |
| Idempotent (no changes) | < 0.5s | ✅ |

## Issues Found

| # | Severity | Description | Resolution |
|---|----------|-------------|------------|
| 1 | ... | ... | ... |

## Conclusion

- [ ] All tests pass
- [ ] No data loss in any scenario
- [ ] Performance acceptable
- [ ] Ready for release
```

### Test Acceptance Criteria

Before marking DX-55 as complete:

1. **100% Scenario Coverage**: All scenarios in matrix tested
2. **Zero Data Loss**: No test loses user content
3. **Idempotent Verified**: Running twice produces same result
4. **Edge Cases Handled**: All edge cases pass or fail gracefully
5. **Performance Acceptable**: No operation > 5 seconds
6. **Regression Free**: Existing functionality unaffected

---

## Alternative Approaches Considered

### A: Keep Two Commands

Keep `init` and `update` separate.

**Pros:** Semantic clarity
**Cons:** User confusion, decision burden

**Decision:** Rejected - violates zero-decision principle

### B: Separate Files

Use `INVAR-CLAUDE.md` instead of modifying `CLAUDE.md`.

**Pros:** No conflict possible
**Cons:** Fragmented configuration

**Decision:** Rejected - fragmentation worse than merge

### C: Claude /init Integration

Modify Claude Code to recognize Invar regions.

**Pros:** Perfect integration
**Cons:** Out of our control

**Decision:** Not feasible

---

## References

- DX-49: Protocol distribution unification (region architecture)
- DX-54: Agent native context management (CLAUDE.md structure)
- DX-06: Smart Guard (zero-decision tools)
- Lesson #11: Agent-Native means no unnecessary choices
- Lesson #19: Enforcement timing matters
