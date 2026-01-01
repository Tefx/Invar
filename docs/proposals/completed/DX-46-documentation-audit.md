# DX-46: Documentation Audit (Revised)

> **"Documentation that contradicts code is worse than no documentation."**

**Status:** ✅ Complete
**Created:** 2025-12-25
**Completed:** 2025-12-26
**Effort:** Low (Phase 1) + Medium (Phase 2)
**Risk:** Low

## Scope

**In scope:** docs/ directory audit + completeness review
**Out of scope:** INVAR.md, CLAUDE.md, skills/ (handled by DX-49 templates)

## Revised Phase Structure

| Phase | Content | Effort | Priority |
|-------|---------|--------|----------|
| **Phase 1** | Fix stale references | 10 min | High |
| **Phase 2** | Completeness audit + Lessons review | 4-8 hours | Medium |
| **Phase 3** | CI check (optional) | 30 min | Low |
| ~~Skipped~~ | ~~`invar check-docs` command~~ | — | — |

### Why No `invar check-docs` Command

- Problem scale is small (2 stale refs found)
- Problem frequency is low (only on major version upgrades)
- grep achieves same result:
  ```bash
  grep -rn "ICIDIV\|v[34]\.[0-9]" docs/ --include="*.md" |
    grep -v "history/" | grep -v "proposals/"
  ```

---

## Phase 1: Fix Stale References

**Immediate action (10 min):**

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `docs/design.md` | 1045 | "INVAR.md v4.0" | → v5.0 |
| `docs/reference/workflow/session-start.md` | 212 | "v3.27" | → v5.0 |

**Exclusions (preserved as-is):**
- `docs/history/` — Historical docs with warning banner
- `docs/proposals/completed/` — Archived proposals

---

## Phase 2: Completeness Audit

### 2.1 Lessons Applicability Review

**Important:** Lessons #1-#28 in context.md may be based on old approaches. Each must be evaluated:

| Category | Judgment Criteria |
|----------|-------------------|
| ✅ Still applicable | Core insight remains valid |
| ⚠️ Partially applicable | Update to reflect current state |
| ❌ Obsolete | Problem solved or approach changed |

**Key changes to consider:**

| Old | New | Affected Lessons |
|-----|-----|------------------|
| ICIDIV | USBV (DX-32) | Workflow-related |
| --prove flag | Default in guard (DX-19) | Verification-related |
| 4 verification levels | 2 levels | Level-related |
| Manual workflow switch | DX-42 auto-routing | Transition-related |
| sections/ | skills/ (DX-49) | Structure-related |

### 2.2 Documentation Gaps Audit

| Area | Questions | Source of Truth |
|------|-----------|-----------------|
| **Architecture** | Why Core/Shell? Why no I/O in Core? | docs/design.md |
| **Verification** | Why 4 layers? Why CrossHair + Hypothesis? | docs/reference/verification/ |
| **Rules** | Severity rationale for each rule? | docs/reference/rules/ |
| **Workflow** | Why USBV? Why Check-In/Final? | docs/reference/workflow/ |
| **Package Split** | Why two packages? Why Apache + GPL? | README, context.md |

### 2.3 Integration to Permanent Docs

```
Step 1: Classify each Lesson
├── ✅ Applicable → Integrate to docs/
├── ⚠️ Partial → Update then integrate
└── ❌ Obsolete → Mark as historical or remove

Step 2: Update context.md
├── Keep applicable Lessons
├── Update partial ones
└── Remove or mark obsolete ones

Step 3: Integrate to permanent docs
├── docs/reference/lessons.md (new) or
└── Distribute to relevant reference docs
```

---

## Phase 3: CI Check (Optional)

Simple grep in CI to prevent regression:

```yaml
# .github/workflows/docs-check.yml
- name: Check for stale docs
  run: |
    if grep -rn "ICIDIV\|v[34]\.[0-9]" docs/ --include="*.md" |
       grep -v "history/" | grep -v "proposals/" | grep -q .; then
      echo "::warning::Stale documentation found"
    fi
```

---

## Success Criteria

### Phase 1 ✅
- [x] No v3.x/v4.x references in active docs/ (excluding history/)

### Phase 2 ✅
- [x] Each Lesson (#1-#28) classified (26 applicable, 2 updated)
- [x] Lesson #26 updated with resolution note
- [x] Created crosshair-vs-hypothesis.md (fixed broken link)
- [x] Design decisions have "why" documentation
- [x] context.md remains concise (current relevant content only)

### Phase 3 (Skipped)
- [ ] CI check prevents regression — Low priority, grep sufficient

---

## Related

| Proposal | Relationship |
|----------|--------------|
| DX-49 | Handles INVAR.md, CLAUDE.md, skills/ — this proposal is complementary |
| DX-24 | Created mechanism docs — this proposal audits them |
