# USBV Reference Inventory for DX-91 Cleanup

**Generated:** 2026-03-18
**Purpose:** Categorize every USBV reference for DX-91 removal scope

---

## Classification Legend

| Category | Definition | Action |
|----------|------------|--------|
| **ACTIVE** | Generates content or influences runtime | **MUST remove/replace** |
| **ARCHIVED** | Historical reference with archive banner | Keep with banner |
| **HISTORICAL** | Proposals, completed docs, past discussions | Keep as-is |

---

## ACTIVE References (MUST Remove/Replace)

### src/invar/templates/ — Template Files (Runtime Generation)

These files generate content that agents read at runtime. All USBV references will influence agent behavior.

| File | Line | Content | Context | Removal Notes |
|------|------|---------|---------|---------------|
| `CLAUDE.md.template` | 9 | `\| **Flow** \| USBV: Understand → Specify → Build → Validate \|` | Critical Rules table | Replace with contracts-first workflow |
| `CLAUDE.md.template` | 16 | `includes Check-In, USBV workflow, and Task Completion requirements` | Protocol reference | Remove USBV mention |
| `CLAUDE.md.template` | 95 | `Use \`INVAR.md\` USBV guidance as the canonical workflow reference` | Visible Workflow section | Replace with contracts-first guidance |
| `context.md.template` | 15 | `### USBV Workflow` | Key Rules section | Remove section |
| `context.md.template` | 35 | `- Am I following USBV workflow?` | Self-Reminder checklist | Remove from checklist |
| `manifest.toml` | 5 | `workflow = "USBV"` | Template manifest | Remove workflow key entirely |
| `config/AGENT.md.jinja` | 13 | `\| **Flow** \| USBV: Understand → Specify → Build → Validate \|` | Critical Rules table | Replace |
| `config/AGENT.md.jinja` | 38 | `Follow [INVAR.md](./INVAR.md) — includes Check-In, USBV workflow, and Task Completion` | Protocol reference | Remove USBV mention |
| `config/AGENT.md.jinja` | 104 | `## USBV Workflow` | Section header | Remove entire section (lines 104-156) |
| `config/context.md.jinja` | 19 | `### USBV Workflow` | Key Rules section | Remove |
| `config/context.md.jinja` | 40 | `\| Implement a feature \| \`INVAR.md#usbv-workflow\` \|` | Task Router table | Remove row |
| `config/context.md.jinja` | 57 | `- Am I following USBV workflow?` | Quick check | Remove |
| `config/context.md.jinja` | 86 | `- Checking USBV workflow details` | Documentation reference | Remove |
| `protocol/universal/completion.md` | 68 | `*Protocol v5.0 — USBV workflow (DX-32)*` | Footer attribution | Replace with DX-91 reference |
| `protocol/universal/usbv.md` | **ENTIRE FILE** | `## USBV Workflow` | Template file | **DELETE FILE** |
| `mcp/server.py` | 54 | `- Entering VALIDATE phase of USBV workflow` | INVAR_INSTRUCTIONS comment | Remove line |
| `core/inspect.py` | 2 | `File inspection for USBV Understand step (Phase 9.2 P14)` | Module docstring | Remove USBV reference |

**Template Files Summary:** 18 references across 6 files (including 1 entire file to delete)

---

## ARCHIVED References (Keep with Banner)

These files already have archive banners and should be preserved as historical documentation.

| File | Status | Banner Present |
|------|--------|----------------|
| `docs/reference/workflow/usbv.md` | **ARCHIVED** | Yes (line 1) |
| `docs/guides/multi-agent.md` | **ARCHIVED** | Yes (line 3) |
| `docs/guides/pi.md` | **ARCHIVED** | Yes (line 78) |
| `docs/guides/aider.md` | **ARCHIVED** | Yes (line 28) |
| `docs/guides/cursor.md` | **ARCHIVED** | Yes (line 213) |
| `docs/guides/continue.md` | **ARCHIVED** | Yes (line 295) |

---

## HISTORICAL References (Keep As-Is)

### docs/proposals/ — Design Proposals

These are historical proposals documenting design decisions. They should be preserved as-is for historical reference.

| File | Count | Notes |
|------|-------|-------|
| `LX-01-multi-language-feasibility.md` | 8 | Historical feasibility analysis |
| `LX-11-cursor-support.md` | 3 | Historical IDE expansion proposal |
| `LX-17-haskell-elm-feasibility.md` | 18 | Historical language exploration |
| `LX-17-implementation-matrix.md` | 13 | Implementation matrix |
| `DX-91-generated-file-contracts.md` | 1 | References removed workflows |
| `DX-91-claude-md-draft.md` | 1 | Draft document |
| `DX-91-simplification.md` | 5 | **Main DX-91 proposal** — defines removal |
| `DX-60-structured-rules-ssot.md` | 2 | Historical rules proposal |
| `DX-61-functional-pattern-guidance.md` | 2 | Historical pattern guidance |
| `DX-79-invar-usage-feedback.md` | 1 | Historical feedback proposal |
| `DX-85-opencode-support.md` | 1 | Historical OpenCode proposal |
| `proposals/index.md` | 4 | Index with historical notes |
| `completed/DX-32-workflow-iteration.md` | 12 | Historical USBV introduction |
| `completed/DX-34-review-cycle.md` | 3 | Historical review cycle |
| `completed/DX-35-workflow-phase-separation.md` | 8 | Historical phase separation |
| `completed/DX-36-documentation-restructuring.md` | 7 | Historical restructure |
| `completed/DX-39-workflow-efficiency.md` | 6 | Historical efficiency work |
| `completed/DX-42-workflow-auto-routing.md` | 1 | Historical auto-routing |
| `completed/DX-46-documentation-audit.md` | 2 | Historical audit |
| `completed/DX-49-protocol-distribution-unification.md` | 7 | Historical protocol work |
| `completed/DX-51-workflow-phase-visibility.md` | 4 | Historical visibility |
| `completed/DX-54-agent-native-context-management.md` | 3 | Historical context management |
| `completed/DX-57-claude-code-hooks.md` | 4 | Historical hooks work |
| `completed/DX-58-document-structure-optimization.md` | 4 | Historical structure work |
| `completed/DX-67-explicit-skill-invocation.md` | 6 | Historical skill invocation |
| `completed/DX-74-experiment-report.md` | 1 | Historical experiment |
| `completed/DX-75-attention-aware-framework.md` | 6 | Historical attention framework |
| `completed/LX-02-agent-portability-analysis.md` | 7 | Historical portability analysis |
| `completed/LX-04-pi-agent-support.md` | 4 | Historical Pi support |
| `completed/LX-05-language-agnostic-protocol.md` | 12 | Historical language work |
| `completed/LX-07-extension-skills.md` | 2 | Historical extension skills |

### docs/reference/ — Reference Documentation

| File | Count | Notes |
|------|-------|-------|
| `workflow/index.md` | 2 | Already has archive marker for USBV |
| `workflow/session-start.md` | 1 | Historical reference |
| `contracts/doctests.md` | 1 | Historical reference |
| `contracts/index.md` | 1 | Historical reference |
| `contracts/completeness.md` | 1 | Historical reference |
| `agent-information-hierarchy.md` | 1 | Historical reference |
| `documentation.md` | 1 | Historical reference |

### docs/ — Other Documentation

| File | Count | Notes |
|------|-------|-------|
| `design.md` | 2 | Historical design decisions |
| `diagrams.md` | 2 | Historical diagrams |
| `vision.md` | 1 | Vision with strikethrough |
| `history/feedback/feedback-memo.md` | 1 | Historical memo |
| `history/feedback/index.md` | 1 | Historical index |
| `history/feedback/compliance-analysis.md` | 1 | Historical analysis |
| `testing/v1.5.0-test-report.md` | 1 | Historical test report |
| `testing/v1.5.0-workflow-compliance.md` | 3 | Historical compliance |
| `index.html` | 1 | Historical landing page |
| `agents.md` | 1 | Historical agent roles |

---

## Verification Commands

```bash
# Verify ACTIVE references (must be cleaned)
rg -n 'USBV|usbv' src/invar/

# Verify ARCHIVED references (must have banner)
rg -l 'USBV|usbv' docs/reference/workflow/ docs/guides/
# Each should have "> **ARCHIVE:" or "> **DX-91:" marker

# Verify HISTORICAL references (no action needed)
rg -c 'USBV|usbv' docs/proposals/ | wc -l
# Expected: ~50 files (proposals are preserved)

# Verify complete inventory
rg -n 'USBV|usbv' --type md --type py --type toml src/invar/ docs/
# All hits should be categorized above
```

---

## Summary Statistics

| Category | Files | References | Action |
|----------|-------|------------|--------|
| ACTIVE | 6 | 18 | Remove/Replace |
| ARCHIVED | 6 | ~10 | Keep (banner present) |
| HISTORICAL | ~50 | ~150 | Keep (proposals/docs) |

---

## Known Locations Verification

From the step description, these locations were expected:

| Known Location | Found? | Category | Notes |
|----------------|--------|----------|-------|
| `src/invar/templates/CLAUDE.md.template` (3 refs) | ✅ Yes | ACTIVE | 3 references |
| `src/invar/templates/context.md.template` (2 refs) | ✅ Yes | ACTIVE | 2 references |
| `src/invar/templates/manifest.toml` (1 ref) | ✅ Yes | ACTIVE | 1 reference |
| `src/invar/templates/config/AGENT.md.jinja` (3 refs) | ✅ Yes | ACTIVE | 3 references |
| `src/invar/templates/config/context.md.jinja` (4 refs) | ✅ Yes | ACTIVE | 4 references |
| `src/invar/templates/protocol/universal/completion.md` (1 ref) | ✅ Yes | ACTIVE | 1 reference |
| `src/invar/templates/protocol/universal/usbv.md` | ✅ Yes | ACTIVE | **Entire file** (DELETE) |
| `src/invar/mcp/server.py` line 54 | ✅ Yes | ACTIVE | 1 reference |
| `src/invar/core/inspect.py` line 2 | ✅ Yes | ACTIVE | 1 reference |
| `docs/*.md` many references | ✅ Yes | HISTORICAL/ARCHIVED | Properly categorized |

**All known locations verified.** Additional references found in `docs/` proper directory (not listed in known locations) are all HISTORICAL or ARCHIVED.

---

## Next Steps (For DX-91 Implementation)

1. **Delete files:**
   - `src/invar/templates/protocol/universal/usbv.md`

2. **Edit ACTIVE template files:**
   - Replace USBV workflow with "contracts before code" in all 5 template files
   - Remove `workflow` key from `manifest.toml`
   - Update module docstring in `core/inspect.py`

3. **Verify no runtime impact:**
   - Run tests after template modifications
   - Check that `invar init` produces DX-91 compliant output

4. **No changes needed:**
   - All `docs/proposals/` files (historical)
   - All `docs/history/` files (historical)
   - All `docs/testing/` files (historical)
   - Archive-bannered files in `docs/guides/` and `docs/reference/`