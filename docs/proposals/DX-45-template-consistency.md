# DX-45: Template Consistency

> **"Single source of truth, multiple destinations."**

**Status:** Draft
**Created:** 2025-12-25
**Effort:** Low-Medium
**Risk:** Low

## Problem Statement

The project has multiple copies of similar content that can drift apart:

```
/Users/tefx/Projects/Invar/
├── CLAUDE.md                    ← Project uses this (evolving)
├── INVAR.md                     ← Project uses this (evolving)
├── .claude/skills/              ← Project uses these (evolving)
│
├── src/invar/templates/         ← Distribution templates (may lag)
│   ├── CLAUDE.md.template
│   ├── INVAR.md.template
│   └── skills/
│
└── invar init --claude          ← Installs from templates/
```

**Symptom:** User needs to manually remind agent to check consistency.

**Root Cause:** No automated mechanism to detect or prevent drift.

## Proposed Solutions

### Option A: Pre-commit Hook (Recommended)

Add hook that compares project files with templates:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: invar-template-sync
        name: Check template consistency
        entry: python scripts/check_template_sync.py
        language: python
        files: ^(CLAUDE\.md|INVAR\.md|\.claude/skills/)
        pass_filenames: false
```

**Implementation:**

```python
# scripts/check_template_sync.py

import difflib
from pathlib import Path

SYNC_PAIRS = [
    ("CLAUDE.md", "src/invar/templates/CLAUDE.md.template"),
    ("INVAR.md", "src/invar/templates/INVAR.md.template"),
    (".claude/skills/develop/SKILL.md", "src/invar/templates/skills/develop/SKILL.md"),
    (".claude/skills/investigate/SKILL.md", "src/invar/templates/skills/investigate/SKILL.md"),
    (".claude/skills/propose/SKILL.md", "src/invar/templates/skills/propose/SKILL.md"),
    (".claude/skills/review/SKILL.md", "src/invar/templates/skills/review/SKILL.md"),
]

def check_sync():
    """Compare project files with templates, report differences."""
    diffs = []

    for project_file, template_file in SYNC_PAIRS:
        project_path = Path(project_file)
        template_path = Path(template_file)

        if not project_path.exists() or not template_path.exists():
            continue

        project_content = project_path.read_text()
        template_content = template_path.read_text()

        # Allow template variables like {{project_name}}
        template_content = expand_template_vars(template_content)

        if project_content != template_content:
            diff = list(difflib.unified_diff(
                template_content.splitlines(),
                project_content.splitlines(),
                fromfile=template_file,
                tofile=project_file,
                lineterm=""
            ))
            diffs.append((project_file, diff))

    if diffs:
        print("❌ Template sync check failed!")
        for file, diff in diffs:
            print(f"\n{file}:")
            print("\n".join(diff[:20]))  # First 20 lines
        return 1

    print("✅ Templates in sync")
    return 0
```

**Pros:**
- Automatic enforcement on every commit
- Clear error messages
- Blocks commits until resolved

**Cons:**
- Requires pre-commit setup
- May block legitimate project-specific changes

### Option B: CI Check

Add GitHub Actions workflow:

```yaml
# .github/workflows/template-sync.yml
name: Template Sync Check

on:
  push:
    paths:
      - 'CLAUDE.md'
      - 'INVAR.md'
      - '.claude/skills/**'
      - 'src/invar/templates/**'

jobs:
  check-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check template sync
        run: python scripts/check_template_sync.py
```

**Pros:**
- Works in CI without local setup
- Non-blocking (warning only)

**Cons:**
- Discovers drift after commit, not before
- Requires PR review to catch

### Option C: CLI Command (`invar check-sync`)

Add command for on-demand checking:

```bash
$ invar check-sync

Checking template consistency...

✅ CLAUDE.md ↔ templates/CLAUDE.md.template: In sync
❌ INVAR.md ↔ templates/INVAR.md.template: 3 differences
   Line 45: Protocol version mismatch (v5.0 vs v4.9)
   Line 120-125: Missing workflow section

✅ .claude/skills/develop/SKILL.md: In sync
✅ .claude/skills/investigate/SKILL.md: In sync

Summary: 1 file(s) out of sync

To sync templates from project:
  invar sync-templates --from-project

To sync project from templates:
  invar sync-templates --from-templates
```

**Pros:**
- User-controlled
- Can sync in either direction
- No CI/pre-commit dependency

**Cons:**
- Relies on user remembering to run
- May be forgotten

### Option D: Single Source Generation

Generate both project files and templates from a common source:

```
src/invar/specs/
├── claude.yaml     ← Common specification
├── invar.yaml
└── skills/
    ├── develop.yaml
    └── ...

$ invar generate-docs

Generated:
  → CLAUDE.md (for this project)
  → src/invar/templates/CLAUDE.md.template (for distribution)
```

**Pros:**
- True single source of truth
- Impossible for drift to occur

**Cons:**
- High implementation effort
- Requires spec format design
- Less flexible for project-specific content

### Option E: Hybrid (Recommended)

Combine Options A + C:

1. **Pre-commit hook** — Catches drift before commit
2. **`invar check-sync` command** — On-demand verification
3. **`invar sync-templates` command** — Easy resolution

```bash
# Development workflow
$ git commit -m "Update INVAR.md"
Template sync check... ❌ FAILED

Templates out of sync:
  INVAR.md differs from templates/INVAR.md.template

Options:
  1. invar sync-templates --from-project  (copy changes to templates)
  2. invar sync-templates --from-templates (revert to template)
  3. git commit --no-verify (skip check, not recommended)
```

## Configuration

Allow certain sections to differ:

```toml
# pyproject.toml
[tool.invar.sync]
# Files to check
check_files = [
    "CLAUDE.md",
    "INVAR.md",
    ".claude/skills/**/*.md"
]

# Sections allowed to differ (regex)
allowed_differences = [
    "^## Project-Specific.*?(?=^## |$)",  # Project-specific section
    "^<!--.*?-->",                         # Comments
]

# Direction for auto-sync
sync_direction = "project-to-template"  # or "template-to-project"
```

## Implementation Plan

| Phase | Feature | Effort |
|-------|---------|--------|
| 1 | `invar check-sync` command | Low |
| 2 | `invar sync-templates` command | Low |
| 3 | Pre-commit hook | Low |
| 4 | Configuration options | Medium |

## Success Criteria

- [ ] Drift detected before commit
- [ ] Clear error messages with resolution options
- [ ] Easy sync command
- [ ] Project-specific sections preserved

## Open Questions

1. Which files should be checked? All skills or just core ones?
2. Should sync be bidirectional or one-direction only?
3. How to handle project-specific customizations?

## Related

- DX-43: Cross-Platform Distribution (templates are part of distribution)
- `src/invar/templates/`: Current template location
