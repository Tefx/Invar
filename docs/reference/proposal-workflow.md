# Proposal Workflow

> **"Think before code. Document decisions."**

This document describes the proposal-driven development workflow used in the Invar project. It's a recommended practice, not a framework requirement.

## Overview

The proposal workflow applies USBV principles at the feature/architecture level:

| USBV Phase | Code Level | Proposal Level |
|------------|------------|----------------|
| **UNDERSTAND** | Read code, understand context | Problem Statement |
| **SPECIFY** | @pre/@post, doctests | Success Criteria |
| **BUILD** | Implement function | Implementation |
| **VALIDATE** | invar guard | Acceptance testing |

**Key insight:** Proposals are feature-level contracts.

## Workflow Steps

```
1. Identify Problem  →  2. Create Proposal  →  3. Discuss/Refine
        ↓                                              ↓
6. Implement  ←  5. Commit Proposal  ←  4. Analyze Dependencies
        ↓
7. Archive (completed/)
```

### 1. Identify Problem

Recognize an issue, inconsistency, or improvement opportunity:
- Documentation drift
- Code duplication
- Missing feature
- Performance issue

### 2. Create Proposal

Create `docs/proposals/DX-XX-name.md`:

```markdown
# DX-XX: Title

> **"One-line philosophy quote"**

**Status:** Draft
**Created:** YYYY-MM-DD
**Effort:** Low/Medium/High
**Risk:** Low/Medium/High

## Problem Statement

What's wrong? Why does it matter?

## Proposed Solution

What's the fix? Options if multiple approaches.

## Implementation Plan

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | First step | Low |
| 2 | Second step | Medium |

## Success Criteria

- [ ] Measurable outcome 1
- [ ] Measurable outcome 2

## Related

- DX-YY: Related proposal
- `path/to/relevant/file.py`
```

### 3. Discuss and Refine

Iterate on the proposal:
- Clarify scope
- Identify edge cases
- Consider alternatives
- Get stakeholder input

### 4. Analyze Dependencies

Update `docs/proposals/index.md`:
- Add to Active Proposals table
- Update Dependency Graph
- Identify parallel execution opportunities

### 5. Commit Proposal

Version control the proposal before implementation:

```bash
git add docs/proposals/DX-XX-*.md docs/proposals/index.md
git commit -m "docs(DX): add DX-XX proposal for <description>"
```

### 6. Implement

Execute the proposal phases:
- Follow the implementation plan
- Update status as you progress
- Handle unexpected issues

### 7. Archive

Move completed proposals:

```bash
mv docs/proposals/DX-XX-name.md docs/proposals/completed/
git commit -m "docs(DX): archive DX-XX as implemented"
```

## Index Structure

Maintain `docs/proposals/index.md` with:

```markdown
## Active Proposals

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-XX | feature-name | Draft | Brief description |

## Archived Proposals

| ID | Name | Status | Description |
|----|------|--------|-------------|
| DX-YY | old-feature | Implemented | What it did |

## Dependency Graph

```
DX-47 (Naming)
    │
    ├── DX-49 (depends on 47)
    │
    └── DX-42 (depends on 47)
```

## Priority Recommendations

| Priority | Proposal | Rationale | Dependencies |
|----------|----------|-----------|--------------|
| Critical | DX-47 | Blocks others | None |
| High | DX-49 | Core infra | DX-47 |
```

## Parallel Execution

Identify independent proposals that can run concurrently:

| Wave | Proposals | Parallel? |
|------|-----------|-----------|
| 0 | DX-48 | Can parallel with Wave 1-2 |
| 1 | DX-47 | Sequential (critical path) |
| 2 | DX-49, DX-42 | Both parallel |

## Status Values

| Status | Meaning |
|--------|---------|
| Draft | Under discussion |
| Approved | Ready for implementation |
| In Progress | Being implemented |
| Implemented | Code complete |
| Superseded | Replaced by another proposal |
| Deferred | Postponed indefinitely |

## When to Use Proposals

**Use proposals for:**
- Multi-file changes
- Architectural decisions
- Breaking changes
- Features requiring discussion

**Skip proposals for:**
- Single-file bug fixes
- Typo corrections
- Obvious refactoring
- Urgent hotfixes

## Value Proposition

| Benefit | Description |
|---------|-------------|
| **Visibility** | All planned work documented |
| **Traceability** | Decisions recorded with rationale |
| **Dependencies** | Clear blocking relationships |
| **Parallelization** | Independent work streams identified |
| **Discussion-first** | Think before code |

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Proposal without implementation | Accumulates debt | Set deadlines or defer |
| Implementation without proposal | No visibility | Retroactive documentation |
| Stale index.md | Misleading status | Update on every change |
| Too granular | Overhead exceeds value | Merge related proposals |

## Integration with USBV

The proposal workflow is USBV applied at a higher level:

```
Code Level:
  UNDERSTAND: Read function context
  SPECIFY: Write @pre/@post
  BUILD: Implement function
  VALIDATE: invar guard

Proposal Level:
  UNDERSTAND: Problem Statement
  SPECIFY: Success Criteria
  BUILD: Implementation phases
  VALIDATE: Acceptance testing
```

This fractal pattern scales from functions to features to architecture.

---

*This workflow is optional. Use it when the coordination benefits outweigh the documentation overhead.*
