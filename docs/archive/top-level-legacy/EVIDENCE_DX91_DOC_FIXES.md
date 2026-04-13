# DX-91 Release Readiness Blocker Remediation Report
## Evidence: fix-doc-runtime-proposal-index-blockers

**Timestamp:** 2026-03-14
**Step ID:** dx91-release-readiness.fix-doc-runtime-proposal-index-blockers
**Agent:** doc-reviewer

---

## Blocker Mapping (B1 + B2 Remediation)

### B1: Active docs exposing retired pre-DX-91 workflow guidance
**Status:** RESOLVED

| File | Status | Changes Applied |
|------|--------|-----------------|
| README.md | Fixed | Removed Check-In/Final ceremony section → "Verification Status"; updated agent support links |
| docs/guides/pi.md | Archived | Added archive header; removed .claude/skills refs; removed USBV ceremony; added historical notes |
| docs/guides/cursor.md | Fixed | Removed USBV workflow refs; removed hooks documentation (historical only); added historical note |
| docs/guides/continue.md | Fixed | Removed USBV workflow refs; removed skills/Check-In/Final refs; added historical note |
| docs/guides/cline.md | Fixed | Removed USBV workflow refs; removed Check-In/Final refs; simplified to 3-phase; added historical note |
| .invar/context.md | Fixed | Updated workflow description; removed 4-phase references; updated quick rule check |
| .invar/project-additions.md | Fixed | Added contracts-first rule; no retired surface references |

### B2: Proposal-index active status drift
**Status:** RESOLVED

| File | Status | Changes Applied |
|------|--------|-----------------|
| docs/proposals/index.md | Fixed | Updated Cross-Reference table to mark all corrected surfaces as Active; removed stale update-needed markings |

---

## Active vs Archive Classification (Post-Fix)

| Document | Classification | Rationale |
|----------|----------------|-----------|
| README.md | **Active** | Updated to DX-91 Python-only workflow; historical notes clearly marked |
| docs/guides/pi.md | **Archive** | Archive header added; historical notes for all retired features |
| docs/guides/cursor.md | **Active** | Updated to DX-91 MCP-only workflow; historical notes clearly marked |
| docs/guides/continue.md | **Active** | Updated to DX-91 MCP-only workflow; historical notes clearly marked |
| docs/guides/cline.md | **Active** | Updated to DX-91 MCP-only workflow; historical notes clearly marked |
| .invar/context.md | **Active** | Updated to DX-91 workflow; no retired command references |
| .invar/project-additions.md | **Active** | Updated to DX-91 workflow; no retired command references |
| docs/proposals/index.md | **Active** | Accurate status classification for all docs |
| docs/reference/workflow/usbv.md | **Archive** (unchanged) | Already marked as archive |
| docs/AGENTS.md | **Archive** (unchanged) | Already marked as archive |

---

## Sibling Search Results (Verification)

### Retired Terms Search Coverage
**Command:** `rg "USBV|Check-In|Final:|\.claude/skills|\.cursor/rules|invar update[^-]|four-phase" --type md`

| Location | Matches | Classification |
|----------|---------|----------------|
| docs/proposals/index.md | 3 | **Expected** - Historical reference table, properly marked |
| README.md | 2 | **Expected** - Historical note reference |
| docs/guides/cline.md | 1 | **Expected** - Historical note reference |
| docs/guides/continue.md | 1 | **Expected** - Historical note reference |
| docs/guides/cursor.md | 1 | **Expected** - Historical note reference |
| docs/guides/pi.md | 2 | **Expected** - Historical note reference |
| tests/fixtures/ | N/A | **Exempt** - Test fixture data (expected) |
| src/invar/templates/ | N/A | **Exempt** - Template source files |
| docs/reference/ | N/A | **Expected** - Archive documentation |
| docs/proposals/completed/ | N/A | **Expected** - Archive proposals |
| docs/testing/ | N/A | **Expected** - Historical test reports |

**Active Release Surfaces Clean:** All active docs (README, guides, .invar/*) now either:
1. Present current DX-91 guidance (Python-only, MCP-based, contracts-first)
2. Include explicit historical notes marking retired features as non-active

---

## Residual Risks

| Risk | Mitigation | Status |
|------|------------|--------|
| Archive/history content may still contain retired terms | **Accepted** - Archive content is intentionally non-active, clearly marked | ACCEPTED |
| Template files retain historical protocol | **Accepted** - Source templates are managed separately from release-facing docs | ACCEPTED |
| Test fixtures contain v1 context samples | **Accepted** - Test fixtures verify migration behavior | ACCEPTED |
| CLAUDE.md header references workflow | **Expected** - The header block itself is the managed surface (not the content) | ACCEPTED |

---

## Git Evidence

**Commit Range:** (pending commit)

**Files Changed:**
- README.md
- docs/guides/pi.md
- docs/guides/cursor.md
- docs/guides/continue.md
- docs/guides/cline.md
- .invar/context.md
- .invar/project-additions.md
- docs/proposals/index.md

**Change Summary:**
- Total lines changed: ~800 lines removed/rewritten
- Primary focus: Retired USBV ceremony, skills/hooks references, Check-In/Final protocol
- New pattern: Historical notes explicitly mark retired features as non-active

---

## Gate Readiness

**B1 Resolution:** All active docs now present DX-91 Python-only workflow; historical content clearly marked as archive
**B2 Resolution:** Proposal index accurately reflects post-fix repo state
**Sibling Search:** Confirms no remaining retired workflow guidance in active release-facing surfaces

**Status:** READY FOR RETEST
