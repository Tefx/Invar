# LX-08: Extension Skills — Future Candidates

**Status:** Deferred
**Priority:** Low
**Category:** Language/Agent eXtensions
**Created:** 2026-01-01
**Depends on:** LX-07 (Extension Skills Architecture)

## Purpose

This proposal documents extension skill candidates that are **deferred** for future consideration. These skills were evaluated during LX-07 planning but ranked lower priority due to:
- Overlap with existing tools
- Lower frequency of use
- Higher implementation complexity
- Language/framework specificity

## Deferred Skills

### T2: Nice to Have

| Skill | Purpose | Defer Reason |
|-------|---------|--------------|
| `/document` | Code documentation generation | Many existing tools (JSDoc, Sphinx, etc.) |
| `/complexity` | Complexity analysis | Overlaps with Guard's size rules |
| `/changelog` | Changelog generation | conventional-changelog exists |
| `/onboard` | New member onboarding guide | Valuable but low frequency |
| `/pr-review` | PR review assistance | Overlaps with `/review` |

### T3: Situational

| Skill | Purpose | Defer Reason |
|-------|---------|--------------|
| `/migrate` | Framework/version migration | Low frequency, high complexity |
| `/perf` | Performance analysis | Language-specific, hard to generalize |
| `/spec` | Requirement spec generation | Overlaps with `/propose` |
| `/design` | Architecture design | Overlaps with `/propose` |
| `/secrets` | Credentials scanning | Tools exist (git-secrets, truffleHog) |
| `/dependency` | Dependency vulnerability check | npm audit, pip-audit exist |

### T4: Not Recommended

| Skill | Purpose | Skip Reason |
|-------|---------|-------------|
| `/convert` | Code conversion (JS→TS) | Language-specific, tools exist |
| `/scaffold` | Project scaffolding | Framework-specific (CRA, Vite, etc.) |
| `/estimate` | Effort estimation | Too subjective for AI |

## Potential Future Promotion

Skills may be promoted to LX-07 if:
1. User demand demonstrates high value
2. Existing tools prove inadequate
3. Implementation becomes simpler

## Evaluation Criteria Used

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Universality | 25% | Cross-language/framework |
| Independence | 20% | Works without Invar |
| Value × Frequency | 30% | Impact × usage rate |
| Differentiation | 15% | Gap from existing tools |
| Complexity | 10% | Implementation effort (inverse) |

---

*Deferred from LX-07 — Extension Skills Architecture*
