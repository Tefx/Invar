# DX-46: Documentation Audit (docs/ Directory)

> **"Documentation that contradicts code is worse than no documentation."**

**Status:** Draft
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Effort:** Medium
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

### Problem 1: Stale Content

With protocol updates (USBV, workflow skills, v5.0), docs/ may contain outdated content:

| Document | Lines | Concern |
|----------|-------|---------|
| docs/reference/*.md | ~1500 | May reference ICIDIV, old CLI flags |
| docs/design.md | ~300 | Architecture diagrams may be stale |
| docs/vision.md | ~200 | Should still be valid |
| docs/guide.md | ? | May have outdated examples |

### Problem 2: Completeness Gaps

Documentation may be missing critical design rationale:

| Gap Type | Risk | Example |
|----------|------|---------|
| **Undocumented decisions** | Future devs repeat mistakes | Why Core forbids I/O? |
| **Missing rationale** | Changes break invariants | Why @pre before @post? |
| **Implicit knowledge** | Knowledge loss on team change | Why two packages? |
| **Code-doc drift** | Features exist without docs | New rules undocumented |

**Key questions for completeness audit:**
1. Can a new developer understand WHY, not just WHAT?
2. Are all design decisions traceable to rationale?
3. Do lessons learned flow back into docs?
4. Is `.invar/context.md` the only place for decisions?

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
| 2 | Run stale content audit on docs/reference/ | Low |
| 3 | Fix critical staleness issues | Low |
| 4 | **Completeness audit** (deep review) | Medium |
| 5 | Fill documentation gaps | Medium |
| 6 | Integrate into CI (optional) | Low |

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

### Phase 4: Completeness Audit (Deep Review)

Systematic review to identify undocumented designs and rationale:

**Audit Checklist:**

| Area | Questions | Source of Truth |
|------|-----------|-----------------|
| **Architecture** | Why Core/Shell? Why no I/O in Core? | docs/design.md |
| **Verification** | Why 4 layers? Why CrossHair + Hypothesis? | docs/reference/verification/ |
| **Contracts** | Why @pre before @post? Contract completeness? | docs/reference/contracts/ |
| **Workflow** | Why USBV? Why Check-In/Final? | docs/reference/workflow/ |
| **Package Split** | Why two packages? Why Apache + GPL? | README, context.md |
| **Rules** | Why each rule exists? Severity rationale? | docs/reference/rules/ |
| **Lessons** | Are context.md lessons in permanent docs? | .invar/context.md → docs/ |

**Audit Process:**

1. **Inventory:** List all design decisions in code (comments, markers, structure)
2. **Cross-reference:** Check if each decision has documentation
3. **Gap analysis:** Identify missing rationale
4. **Priority:** Rank gaps by impact (onboarding friction, mistake risk)

**Expected Gaps (Hypotheses):**

- DX proposal rationale not in permanent docs (only in proposals/)
- Lesson learned (#1-#28) not consolidated into reference docs
- Rule severity choices undocumented
- Package split rationale only in context.md

### Phase 5: Fill Documentation Gaps

Create or update documentation for identified gaps:

| Gap | Action | Target |
|-----|--------|--------|
| Architecture rationale | Expand docs/design.md | "Why Core/Shell" section |
| Verification layers | Add rationale to docs/reference/verification/ | "Why 4 layers" section |
| Lessons consolidation | Extract permanent lessons to docs/ | docs/reference/lessons.md |
| Package split | Add to README or docs/guide.md | "Package Architecture" section |
| Rule rationale | Add to docs/reference/rules/ | Per-rule "Why" sections |

**Principle:** Each design decision should be findable by searching docs/, not require reading context.md or proposals/.

### Phase 6: CI Integration (Optional)

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

### Staleness Audit
- [ ] `invar check-docs` command implemented
- [ ] docs/reference/ audited for USBV consistency
- [ ] Version numbers updated to v5.0
- [ ] No ICIDIV references in active docs (excluding history/)
- [ ] CLI examples match current commands

### Completeness Audit
- [ ] All architecture decisions documented with rationale
- [ ] Verification layer choices explained (why 4 layers)
- [ ] Rule severity rationale documented
- [ ] Package split rationale in permanent docs (not just context.md)
- [ ] Lessons #1-#28 consolidated into reference docs
- [ ] New developer can understand "why" without reading context.md

## Related Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-49 | Handles INVAR.md, CLAUDE.md, sections/ — this proposal is complementary |
| DX-24 | Created mechanism docs — this proposal audits them |
| DX-45 | Superseded by DX-49 |
