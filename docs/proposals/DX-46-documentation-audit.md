# DX-46: Documentation Audit (docs/ Directory)

> **"Documentation that contradicts code is worse than no documentation."**

**Status:** Draft
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Effort:** Low-Medium
**Risk:** Low

## Scope Change

**Original scope:** Audit all documentation (INVAR.md, CLAUDE.md, sections/, docs/)

**Updated scope:** Audit docs/ directory only

**Reason:** DX-49 (Protocol Distribution Unification) now handles:
- INVAR.md → unified single version from templates/
- CLAUDE.md → generated from templates with user regions
- sections/ → deleted, merged into templates/skills/

**Remaining:** docs/ directory audit and `invar check-docs` command.

## Problem Statement

With protocol updates (USBV, workflow skills, v5.0), docs/ may contain outdated content:

| Document | Lines | Concern |
|----------|-------|---------|
| docs/reference/*.md | ~1500 | May reference ICIDIV, old CLI flags |
| docs/design.md | ~300 | Architecture diagrams may be stale |
| docs/vision.md | ~200 | Should still be valid |
| docs/guide.md | ? | May have outdated examples |

## Audit Scope

### In Scope (This Proposal)

```
docs/
├── reference/           # Primary target
│   ├── workflow/        # USBV content check
│   ├── architecture/    # Core/Shell diagrams
│   ├── verification/    # Guard behavior
│   └── contracts/       # @pre/@post syntax
├── design.md            # Architecture overview
├── vision.md            # Philosophy (likely stable)
├── guide.md             # User guide
└── history/             # Historical docs (preserve as-is)
```

### Out of Scope (Handled by DX-49)

- INVAR.md
- CLAUDE.md
- sections/*.md
- .claude/skills/*.md

## Stale Content Detection

### Keyword Patterns

```python
STALE_PATTERNS = [
    r"ICIDIV",                    # Old workflow name → USBV
    r"v[34]\.\d+",                # Old version numbers → v5.0
    r"--prove",                   # Old CLI flag → guard default
    r"invar prove",               # Old command → guard
    r"--thorough",                # Removed flag
    r"Check-In:.*invar guard",    # Old Check-In format
]

EXCLUDE_PATHS = [
    "docs/history/",              # Historical docs preserved
    "docs/proposals/completed/",  # Archived proposals preserved
]
```

### Command: `invar check-docs`

```bash
$ invar check-docs

Scanning docs/ for stale content...

⚠️ Potentially stale content:

docs/reference/workflow/session-start.md:42
  Found: "ICIDIV workflow"
  Suggest: Replace with "USBV workflow"

docs/design.md:15
  Found: "v4.2"
  Suggest: Update to "v5.0"

docs/reference/verification/index.md:78
  Found: "--prove flag"
  Suggest: Remove (now default in guard)

Found 3 issues in 3 files.
Skipped: docs/history/ (preserved), docs/proposals/completed/ (archived)
```

## Implementation Plan

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | Implement `invar check-docs` command | Low |
| 2 | Run audit on docs/reference/ | Low |
| 3 | Fix critical issues | Low |
| 4 | Add TODO markers to non-critical | Low |
| 5 | Integrate into CI (optional) | Low |

### Phase 1: check-docs Command

```python
# src/invar/shell/check_docs.py

def check_docs(docs_path: Path) -> list[Issue]:
    """Scan docs for stale content patterns."""
    issues = []

    for md_file in docs_path.rglob("*.md"):
        # Skip excluded paths
        if any(ex in str(md_file) for ex in EXCLUDE_PATHS):
            continue

        content = md_file.read_text()
        for pattern, suggestion in STALE_PATTERNS.items():
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count("\n") + 1
                issues.append(Issue(
                    file=md_file,
                    line=line_num,
                    found=match.group(),
                    suggestion=suggestion
                ))

    return issues
```

### Phase 2-4: Manual Audit

Priority order:
1. **docs/reference/workflow/** — Most likely to have USBV changes
2. **docs/design.md** — Version number, architecture diagrams
3. **docs/reference/verification/** — Guard behavior changes
4. **docs/guide.md** — User-facing examples

### Phase 5: CI Integration (Optional)

```yaml
# .github/workflows/docs-check.yml
- name: Check documentation freshness
  run: invar check-docs --strict
```

## History Directory Policy

```
docs/history/
├── protocol-evolution.md    # v3.5 → v3.6 changes (preserve)
├── feedback/                # Historical feedback (preserve)
└── index.md                 # Already has staleness warning
```

**Policy:** Historical docs preserved as-is. The existing warning banner is sufficient:

```markdown
> These documents may reference outdated concepts (e.g., ICIDIV workflow, v3.x protocol).
```

## Success Criteria

- [ ] `invar check-docs` command implemented
- [ ] docs/reference/ audited for USBV consistency
- [ ] Version numbers updated to v5.0
- [ ] No ICIDIV references in active docs (excluding history/)
- [ ] CLI examples match current commands

## Related Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-49 | Handles INVAR.md, CLAUDE.md, sections/ — this proposal is complementary |
| DX-24 | Created mechanism docs — this proposal audits them |
| DX-45 | Superseded by DX-49 |
