# LX-09: Legacy Project Onboarding

**Status:** Draft
**Created:** 2026-01-03
**Dependencies:** LX-05 (Language-agnostic protocol)

## Executive Summary

The `/invar-onboard` skill helps existing projects adopt Invar patterns. With recent additions (--mcp-only, document tools, type checking layer), the skill needs updates to reflect two migration paths: lightweight (MCP only) vs. full framework adoption.

**Priority**: Medium
**Effort**: 2 hours (skill update only)

---

## Part 1: Current State

### 1.1 What Works

✅ **Comprehensive assessment** - Deep project analysis (architecture, patterns, risks)
✅ **Language adapters** - Python and TypeScript pattern guides
✅ **Phased roadmap** - Foundation → Core → Shell → Contracts → Validation
✅ **Human checkpoint** - User confirmation before planning phase

### 1.2 Gaps (Post-1.11.0)

#### G1: Missing Lightweight Path (--mcp-only)

**Context**: v1.11.0 added `invar init --mcp-only` for MCP tools without framework adoption.

**Problem**: Skill assumes all projects want full migration (Core/Shell architecture).

**Impact**: Users unaware of lightweight option, over-committed to full migration.

**Evidence**:
```markdown
# README.md says:
## Legacy Project Migration
### Quick Start: MCP Tools Only  ← Added in v1.11.0

# But /invar-onboard says:
Phase 3: PLAN → Full migration roadmap only
```

---

#### G2: No Type Checking Assessment

**Context**: v1.11.0 clarified mypy/tsc as foundational layer before Guard.

**Problem**: Skill doesn't detect or recommend type checker setup.

**Impact**: Users may adopt Invar without type checking, missing 50% of value.

**Evidence**:
```markdown
# Skill detects:
- Error handling (Result vs throw)
- Validation (Zod / Pydantic)

# Skill SHOULD detect:
- Type checking (mypy / tsc / none)
```

---

#### G3: No Document Tools Discovery

**Context**: v1.11.0 added 7 MCP document tools (invar_doc_toc, etc.).

**Problem**: Skill doesn't mention document tools as lightweight onboarding benefit.

**Impact**: Users unaware that --mcp-only provides immediate value via doc tools.

---

## Part 2: Proposed Enhancements

### 2.1 Add Migration Strategy Decision (Priority: High)

**Goal**: Present two paths in Phase 2 DISCUSS.

**Implementation:**

Add to Phase 2 DISCUSS, before "4. Confirmation":

```markdown
### 3.5 Migration Strategy Decision

**🎯 Recommended: Start Lightweight**

```bash
invar init --mcp-only
```

Benefits:
- Zero framework commitment
- Immediate value: Document tools (invar_doc_toc, invar_doc_read)
- Code navigation: invar_sig, invar_map
- Basic verification: invar_guard (minimal rules)

Evaluation period: 1-2 weeks

**⚙️ Alternative: Full Migration Now**

Commitment:
- {total_days} days estimated effort
- Core/Shell architecture refactoring
- Contract coverage: @pre/@post or Zod schemas
- Full Guard verification

Prerequisites:
- [ ] Type checker configured (mypy/tsc)
- [ ] E2E test coverage > 80%
- [ ] Result library installed

**Which approach?** [Lightweight (recommended) / Full migration]
```

**Workflow change**:

```
Phase 2: DISCUSS
  ├─ User chooses "Lightweight"
  │  └─ Phase 4: Lightweight Setup (new) → Exit
  │
  └─ User chooses "Full migration"
     └─ Phase 3: PLAN (existing) → Roadmap
```

---

### 2.2 Add Phase 4: Lightweight Setup (Priority: High)

**Goal**: Provide quick-start guide for --mcp-only path.

**Implementation:**

New phase (only executed if user chose "Lightweight"):

```markdown
### Phase 4: Lightweight Setup

**Only if user chose "Lightweight" in Phase 2**

#### Step 1: Install MCP Tools

```bash
invar init --mcp-only
```

Creates: `.mcp.json` only (no INVAR.md, CLAUDE.md, Core/Shell structure)

#### Step 2: Verify Agent Access

Agent now has access to:
- `invar_doc_toc` - View document structure
- `invar_doc_read` - Read specific sections
- `invar_doc_find` - Search sections by pattern
- `invar_sig` - Show function signatures and contracts
- `invar_map` - Symbol map with reference counts
- `invar_guard` - Basic verification (minimal rules for non-Invar projects)

#### Step 3: Quick Wins

**Week 1: Document Navigation**
```
Agent: "What's in the design doc?"
You: Use invar_doc_toc to see structure
```

**Week 2: Code Exploration**
```
Agent: "Where is the authentication logic?"
You: Use invar_sig and invar_map
```

#### Step 4: Evaluation

After 1-2 weeks:
- Does lightweight mode provide enough value? → Done ✅
- Need more (contracts, verification)? → Re-run `/invar-onboard` for full migration

**Output:** `docs/invar-lightweight-quickstart.md`

**Next Steps:**
- Use tools for 1-2 weeks
- If satisfied → Done
- If need contracts/verification → `/invar-onboard` (full migration path)
```

---

### 2.3 Add Type Checker Detection (Priority: Medium)

**Goal**: Detect and recommend type checker setup.

**Phase 1 ASSESS changes:**

```markdown
Step 3: Pattern Detection
├── Error handling (throw / Result / error return)
├── Validation (Zod / Pydantic / manual)
├── Type checking (mypy / tsc / none)  ← New
├── Dependency injection
└── Logging/monitoring patterns
```

**Assessment Report changes:**

```markdown
## 3. Pattern Analysis

| Dimension | Current | Invar Target | Gap |
|-----------|---------|--------------|-----|
| Type Checking | {mypy/tsc/none} | mypy (Python) / tsc (TypeScript) configured | {gap} |
| Error Handling | {current_error} | Result[T, E] / Result<T, E> | {gap_error} |
| Validation | {current_validation} | @pre/@post / Zod | {gap_validation} |
```

**Prerequisites update:**

```markdown
### 6.2 Prerequisites

- [ ] **Type checker configured**
  - Python: `pip install mypy`, add to `.pre-commit-config.yaml`
  - TypeScript: `tsc` configured in `tsconfig.json`
- [ ] E2E test coverage > 80% for critical paths
- [ ] Result library installed (neverthrow / returns)
- [ ] Error type hierarchy defined
```

**Recommendations update:**

```markdown
### 6.1 Suggested Approach

**⚠️ Critical: Type Checking First**

{if no type checker detected}
Before adopting Invar, configure type checking:
- Python: Install mypy, enable strict mode
- TypeScript: Configure tsc with strict settings

Invar contracts complement (not replace) type checking.
Type checking = foundational layer
Guard = semantic verification layer
```

---

### 2.4 Update Lightweight Messaging (Priority: Low)

**Goal**: Emphasize document tools as immediate value.

**Phase 2 DISCUSS changes:**

```markdown
### 1. Summary Display

**Lightweight Path Benefits:**
- Document tools: Navigate 100+ page specs instantly
- Code navigation: Understand unfamiliar codebase quickly
- Basic verification: Catch common issues without contracts

**Full Migration Benefits:**
- Architecture enforcement: Core/Shell separation
- Contract verification: @pre/@post guarantees
- Multi-layer testing: Doctest + Property + Symbolic
```

---

## Part 3: Implementation Plan

### Phase A: Skill Update (2 hours)

| Task | Files | Effort |
|------|-------|--------|
| Add Section 3.5 to Phase 2 | `SKILL.md` line 120-150 | 30 min |
| Add Phase 4: Lightweight Setup | `SKILL.md` after line 206 | 30 min |
| Add type checker detection | `SKILL.md` line 69-73 | 15 min |
| Update assessment template | `SKILL.md` line 258-264 | 15 min |
| Update recommendations | `SKILL.md` line 289-297 | 15 min |
| Update template files | `src/invar/templates/onboard/` | 15 min |

**Total**: ~2 hours

### Phase B: Documentation Sync (30 min)

| Task | Files | Effort |
|------|-------|--------|
| Update README migration section | Already done (v1.11.0) | - |
| Verify consistency | Cross-check SKILL.md vs README.md | 30 min |

---

## Part 4: Acceptance Criteria

### 4.1 Phase A Success

**Lightweight Path:**
- [ ] User presented with "Lightweight vs Full" decision in Phase 2
- [ ] Choosing "Lightweight" executes Phase 4 (quick setup)
- [ ] Phase 4 outputs `docs/invar-lightweight-quickstart.md`
- [ ] Phase 4 mentions document tools, sig, map, guard

**Type Checker:**
- [ ] Assessment detects mypy/tsc presence
- [ ] Report shows type checking gap if missing
- [ ] Prerequisites include type checker setup

**Full Migration:**
- [ ] Existing workflow unchanged
- [ ] Prerequisites now include type checker
- [ ] Recommendations mention type checking layer

### 4.2 Consistency Validation

**Cross-document check:**
- [ ] README.md migration section matches SKILL.md workflow
- [ ] Both mention --mcp-only as lightweight option
- [ ] Both position full migration as optional upgrade

---

## Part 5: Risk Assessment

### 5.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase 4 output quality | Low | Use README quick-start as template |
| Type checker detection fragile | Medium | Use simple file existence (mypy.ini, tsconfig.json) |
| User confusion (two paths) | Low | Clear decision table with recommendations |

### 5.2 Adoption Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users skip lightweight, over-commit | Medium | Mark "Lightweight" as "(recommended)" |
| Users expect --mcp-only to work without agent | Low | Clear messaging: "Agent gets access to..." |

---

## Part 6: Success Indicators

**Quantitative:**
- [ ] 50%+ of /invar-onboard users choose lightweight path first
- [ ] Zero issues filed about "skill doesn't mention --mcp-only"

**Qualitative:**
- [ ] User feedback: "Lightweight path helped me evaluate before committing"
- [ ] User feedback: "Type checker reminder prevented bad setup"

---

## Appendix A: Files to Update

### A.1 Skill Definition

**File**: `.claude/skills/invar-onboard/SKILL.md`

**Changes**:
1. Phase 2, before line 143: Add "3.5 Migration Strategy Decision"
2. After Phase 3 (line 206): Add "Phase 4: Lightweight Setup"
3. Phase 1, line 69-73: Add type checking to pattern detection
4. Assessment template, line 258-264: Add type checking row
5. Prerequisites, line 293-296: Add type checker item
6. Recommendations, line 289-291: Add type checking emphasis

### A.2 Template Files (Optional)

**File**: `src/invar/templates/onboard/assessment.md.jinja`

**Changes**: Add type_checking variable to template

**File**: `src/invar/templates/onboard/roadmap.md.jinja`

**Changes**: N/A (lightweight path outputs simple guide, not roadmap)

---

## Document History

- **2026-01-03**: Initial draft based on v1.11.0 feature additions
