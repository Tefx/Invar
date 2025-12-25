# DX-46: Documentation Audit and Sync

> **"Documentation that contradicts code is worse than no documentation."**

**Status:** Draft
**Created:** 2025-12-25
**Effort:** Medium
**Risk:** Low

## Problem Statement

With the new framework (USBV, workflow skills, etc.), existing documentation may be outdated:

| Document | Concern |
|----------|---------|
| INVAR.md | May still reference ICIDIV instead of USBV |
| CLAUDE.md | May have outdated workflow instructions |
| docs/reference/ | DX-24 said 100% complete, but may not reflect USBV |
| docs/design.md | May reference old architecture |
| docs/vision.md | Philosophy should still be valid |
| GitHub Pages | May not reflect current structure |

**Symptom:** Agent and user confusion when docs contradict actual behavior.

## Proposed Audit

### Phase 1: Inventory

| Document | Lines | Last Updated | Check Needed |
|----------|-------|--------------|--------------|
| INVAR.md | ~200 | 2025-12-25 | ✅ Recent |
| CLAUDE.md | ~50 | 2025-12-25 | ✅ Recent |
| sections/develop.md | ~100 | 2025-12-25 | ✅ Recent |
| sections/investigate.md | ~50 | 2025-12-25 | ✅ Recent |
| sections/propose.md | ~50 | 2025-12-25 | ✅ Recent |
| sections/review.md | ~50 | 2025-12-25 | ✅ Recent |
| docs/reference/*.md | ~1500 | 2025-12-24 | ⚠️ Pre-USBV |
| docs/design.md | ~300 | ? | ❓ Unknown |
| docs/vision.md | ~200 | ? | ❓ Unknown |
| docs/agents.md | ~150 | ? | ❓ Unknown |
| README.md | ~100 | ? | ❓ Unknown |

### Phase 2: Specific Checks

#### INVAR.md / CLAUDE.md
- [ ] USBV workflow correctly described
- [ ] Check-In/Final format current
- [ ] Workflow skill references accurate
- [ ] No ICIDIV references remain

#### docs/reference/
- [ ] workflow/usbv.md → USBV content current
- [ ] workflow/session-start.md → Check-In format current
- [ ] architecture/index.md → Core/Shell still accurate
- [ ] verification/index.md → Guard behavior current
- [ ] contracts/pre-post.md → Contract system current

#### docs/design.md
- [ ] Architecture diagrams current
- [ ] Version number updated
- [ ] No stale section references

#### docs/vision.md
- [ ] Philosophy still applies
- [ ] No contradictions with current implementation

### Phase 3: Keyword Search

Automated check for potentially stale content:

```python
STALE_PATTERNS = [
    r"ICIDIV",                    # Old workflow name
    r"v3\.\d+",                   # Old version numbers
    r"v4\.\d+",                   # Old version numbers
    r"--prove",                   # Old CLI flag
    r"invar prove",               # Old command
    r"Check-In:.*invar guard",    # Old Check-In format
]

def find_stale_content(docs_path: Path) -> list[tuple[Path, str, int]]:
    """Find potentially stale content in docs."""
    issues = []
    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text()
        for pattern in STALE_PATTERNS:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count("\n") + 1
                issues.append((md_file, match.group(), line_num))
    return issues
```

### Phase 4: Resolution Options

#### Option A: Incremental Update

Update each document as issues are found:

```
1. Run keyword search
2. Review flagged locations
3. Update one document at a time
4. Verify with invar guard
```

**Effort:** Medium (spread over time)
**Risk:** Low

#### Option B: Comprehensive Rewrite

Systematically rewrite all documentation:

```
1. Create doc spec from current code
2. Regenerate all docs from spec
3. Review and adjust
4. Replace old docs
```

**Effort:** High
**Risk:** Medium (may lose valuable context)

#### Option C: Hybrid (Recommended)

```
1. Run automated stale content check
2. Update critical docs immediately (INVAR.md, CLAUDE.md)
3. Add TODO markers to non-critical docs
4. Schedule incremental updates
```

## Implementation Plan

| Phase | Action | Effort | Priority |
|-------|--------|--------|----------|
| 1 | Run stale content check | Low | **High** |
| 2 | Fix critical issues in INVAR.md, CLAUDE.md | Low | **High** |
| 3 | Update docs/reference/workflow/ | Medium | Medium |
| 4 | Review docs/design.md | Low | Low |
| 5 | Add `invar check-docs` command | Medium | Low |

### Quick Win: Stale Content Check

```bash
$ invar check-docs

Scanning documentation for stale content...

⚠️ Potentially stale content found:

docs/reference/workflow/usbv.md:1
  "# USBV: The Four-Phase Development Workflow"
  → ✅ Already updated

docs/design.md:15
  "Version: v5.0"
  → ✅ Already updated

docs/reference/verification/index.md:42
  "Run `invar guard`"
  → ✅ Already updated

Found 3 potential issues in 3 files.
```

## Success Criteria

- [ ] No ICIDIV references in active documentation
- [ ] Version numbers consistent
- [ ] CLI examples match current commands
- [ ] Check-In/Final format consistent

## Open Questions

1. Should we add doc version tracking?
2. Should `invar check-docs` be part of CI?
3. How to handle historical docs (proposals)?

## Related

- DX-24: Mechanism Documentation (created the mechanism docs)
- DX-45: Template Consistency (related sync problem)
- docs/reference/: Primary audit target
