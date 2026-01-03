# DX-78: MCP Protocol Sync & Multi-Language Support

**Status:** Draft
**Created:** 2026-01-03
**Priority:** P0 (Critical)
**Source:** Paralex project feedback analysis

## Executive Summary

Two feedback documents from the Paralex project (TypeScript) revealed critical issues with Invar's MCP server instructions and multi-language support. The MCP server provides outdated "Session Start" protocol that contradicts INVAR.md v5.0 "Check-In" protocol, causing unpredictable agent behavior.

---

## Part 1: Problem Analysis

### 1.1 Issue Catalog (12 issues, 2 root causes)

| ID | Category | Severity | Issue |
|----|----------|----------|-------|
| #1 | Protocol | Critical | MCP "Session Start" contradicts v5.0 "Check-In" |
| #2 | Protocol | Critical | MCP says "MUST run guard first", v5.0 says "Do NOT" |
| #3 | Language | Critical | `invar_map` error causes agent to skip ALL tools |
| #4 | Protocol | High | USBV workflow not enforced in MCP |
| #5 | Protocol | High | No Check-In/Final pair enforcement |
| #6 | Tooling | High | Guard usage instructions outdated |
| #7 | Language | Medium | No language support matrix |
| #8 | Language | Medium | TypeScript examples missing |
| #9 | Language | Medium | Zod patterns don't match TS idioms |
| #10 | Cognitive | Medium | Too many tools to learn at once |
| #11 | Docs | Low | Scattered documentation |
| #12 | Docs | Low | No quick-start for non-Python |

### 1.2 Root Cause Analysis

#### Root Cause 1: MCP Server Not Synced to v5.0

**Current MCP instructions (outdated):**
```markdown
## Session Start (REQUIRED)
Before writing ANY code, you MUST execute:
1. `invar_guard(changed=true)` — Check existing violations
2. `invar_map(top=10)` — Understand code structure
```

**INVAR.md v5.0 (current):**
```markdown
## Check-In
Your first message MUST display:
✓ Check-In: [project] | [branch] | [clean/dirty]

Actions: Read `.invar/context.md`, then show status.
Do NOT run guard at Check-In.
```

**Impact:** Agent receives contradictory instructions, behavior unpredictable.

#### Root Cause 2: Python-Centric Design Without Declaration

**Current `invar_map` error:**
```
No Python files found in /path/to/project
```

**Agent's (incorrect) inference:**
```
"Invar tools are not usable for this TypeScript project"
→ Skip ALL invar_* tools, including document tools
```

**Reality:** `invar_doc_*` tools are language-agnostic and fully functional.

---

## Part 2: Proposed Solutions

### 2.1 P0: Sync MCP Server to v5.0 Protocol

**File:** `src/invar/templates/mcp-instructions.md` (or equivalent)

**Changes:**

1. Remove "Session Start" section entirely
2. Add "Check-In" section matching INVAR.md v5.0:

```markdown
## Check-In (REQUIRED)

Your first message MUST display:
✓ Check-In: [project] | [branch] | [clean/dirty]

**Actions:** Read `.invar/context.md`, then show status.
**Do NOT run guard at Check-In.**

Run guard only when:
- Entering VALIDATE phase
- User requests verification
- After making code changes
```

3. Update tool usage table to remove mandatory guard-first:

```markdown
### Tool Usage (Session Start)

| Step | Tool | When |
|------|------|------|
| 1 | Read `.invar/context.md` | Always first |
| 2 | `invar_map` | If exploring codebase |
| 3 | `invar_guard` | Only in VALIDATE phase |
```

**Effort:** 1 hour

---

### 2.2 P0: Add Language Support Matrix

**Files:** README.md, MCP instructions

**Content:**

```markdown
## Tool × Language Support

| Tool | Python | TypeScript | Notes |
|------|--------|------------|-------|
| `invar_guard` | ✅ Full | ⚠️ Partial | TS: Static rules only, no contract verification |
| `invar_sig` | ✅ Full | ⚠️ Limited | TS: Type signatures via LSP |
| `invar_map` | ✅ Full | ❌ N/A | Python symbol analysis only |
| `invar_doc_*` | ✅ Full | ✅ Full | Language-agnostic markdown tools |

### TypeScript Projects

Use these tools:
- `invar_doc_*` — Document navigation (fully supported)
- `invar_guard` — Static rule checking (architecture only)
- `invar_sig` — Type signatures (limited, via LSP)

Skip these tools:
- `invar_map` — Python-only
```

**Effort:** 1 hour

---

### 2.3 P1: Improve `invar_map` Error Message

**File:** `src/invar/shell/commands/map.py`

**Current:**
```python
if not python_files:
    return "No Python files found in {path}"
```

**Proposed:**
```python
if not python_files:
    return """No Python files found in {path}.

Note: invar_map analyzes Python symbols only.

For TypeScript/other projects, these tools are available:
- invar_doc_* — Document navigation (fully supported)
- invar_sig — Type signatures (limited, via LSP)
- invar_guard — Static architecture rules
"""
```

**Effort:** 30 minutes

---

### 2.4 P1: Add TypeScript Examples

**File:** New `.invar/examples/typescript-patterns.md`

**Content outline:**
1. Zod schema as contracts
2. neverthrow Result<T, E> for Shell
3. Guard static rules (no @pre/@post)
4. Document-first workflow

**Effort:** 2 hours

---

### 2.5 P2: USBV Enforcement in MCP

**File:** MCP instructions

**Add workflow checkpoints:**
```markdown
## USBV Workflow (MANDATORY)

When implementing features, you MUST follow:

1. **UNDERSTAND** — Read context, analyze requirements
2. **SPECIFY** — Write contracts/types BEFORE code
3. **BUILD** — Implement following specifications
4. **VALIDATE** — Run `invar_guard`, verify completeness

**Violation check:** Before writing ANY implementation code:
- "Have I shown the contract/type for THIS function?"
- "Have I completed SPECIFY phase?"
```

**Effort:** 1 hour

---

## Part 3: Implementation Plan

| Phase | Tasks | Priority | Effort |
|-------|-------|----------|--------|
| A | Sync MCP to v5.0 protocol | P0 | 1h |
| A | Add language support matrix | P0 | 1h |
| B | Improve `invar_map` error message | P1 | 30m |
| B | Add TypeScript examples | P1 | 2h |
| C | Add USBV enforcement | P2 | 1h |

**Total:** ~5.5 hours

---

## Part 4: Open Questions

### Q1: Should we implement `invar_sig` for TypeScript?

**Current state:** Limited TypeScript support via LSP

**Options:**
| Option | Pros | Cons |
|--------|------|------|
| A: LSP-only (current) | No new code | Limited functionality |
| B: TypeScript parser | Full signatures, Zod detection | 8-16h effort, maintenance |
| C: tree-sitter | Fast, multi-language | Learning curve, less semantic |

**Recommendation:** Defer to separate proposal (LX-10?)

### Q2: Should we implement `invar_map` for TypeScript?

**Current state:** Python-only

**Options:**
| Option | Pros | Cons |
|--------|------|------|
| A: Skip (current) | No effort | TS users lack orientation tool |
| B: TypeScript parser | Full support | 16-24h effort |
| C: LSP symbols | Uses existing infra | May miss some patterns |

**Recommendation:** Defer to separate proposal (LX-10?)

---

## Part 5: Acceptance Criteria

### Phase A (P0)
- [ ] MCP instructions match INVAR.md v5.0 Check-In protocol
- [ ] Language support matrix in README and MCP
- [ ] No "Session Start" or "MUST run guard first" in MCP

### Phase B (P1)
- [ ] `invar_map` provides helpful message for non-Python projects
- [ ] TypeScript examples document exists

### Phase C (P2)
- [ ] USBV checkpoints in MCP instructions

---

## Part 6: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing users depend on old MCP | Medium | Version note in changelog |
| TypeScript users expect full support | Medium | Clear matrix + "partial" labels |
| Protocol changes confuse agents | Low | Single source of truth (INVAR.md) |

---

## Appendix: Source Documents

1. `/Users/tefx/Projects/paralex/docs/feedback/invar-typescript-ux-feedback.md`
2. `/Users/tefx/Projects/paralex/docs/feedback/invar-comprehensive-analysis.md`

---

## Document History

- **2026-01-03**: Initial draft from Paralex feedback analysis
