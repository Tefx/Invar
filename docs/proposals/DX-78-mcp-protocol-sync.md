# DX-78: MCP Protocol Sync & TypeScript Support

**Status:** Draft
**Created:** 2026-01-03
**Priority:** P0 (Critical) for Phase A/B, P1 for Phase C
**Source:** Paralex project feedback analysis

## Executive Summary

Two feedback documents from the Paralex project (TypeScript) revealed critical issues with Invar's MCP server instructions and TypeScript support. This proposal addresses:

1. **Phase A (P0):** MCP server provides outdated "Session Start" protocol contradicting INVAR.md v5.0 "Check-In"
2. **Phase B (P1):** Missing TypeScript documentation and examples
3. **Phase C (P1):** Agents lack code navigation tools for TypeScript (no IDE = blind)

**Key insight:** Agents don't have IDE access. Without `invar_sig` and `invar_map` for TypeScript, agents cannot navigate TS codebases effectively.

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
| B | Add USBV enforcement | P1 | 1h |
| C | TypeScript `invar_sig` (tree-sitter) | P1 | 8h |
| C | TypeScript `invar_map` (tree-sitter) | P1 | 8h |
| C | Zod schema detection | P2 | 4h |

**Phase A+B:** ~5.5 hours (quick fixes + docs)
**Phase C:** ~20 hours (TypeScript symbol tools)
**Total:** ~25.5 hours

---

## Part 4: TypeScript Symbol Tools (Phase C)

### 4.1 Why Agent Needs sig/map

**Key insight:** Agents don't have IDE access. They can't:
- Hover to see type signatures
- "Go to Definition"
- Browse code structure visually

Without sig/map, TypeScript agents are **blind**:

```
Current flow (broken):
Agent → invar_map → "No Python files" → Skip ALL tools → Blind grep/read

With TypeScript sig/map:
Agent → invar_map → Symbol list + refs → Locate key files
Agent → invar_sig → Type signatures + Zod → Understand interfaces
```

### 4.2 Value Assessment (Agent Perspective)

| Feature | Agent Value | Reason |
|---------|-------------|--------|
| Symbol list | 🔴 Critical | Only way to "see" code structure |
| Reference counts | 🔴 Critical | Identify core vs edge modules |
| Type signatures | 🔴 Critical | No hover, no IDE hints |
| Zod schemas | 🟡 High | Contracts for TypeScript |
| Export graph | 🟡 High | Module dependencies |

### 4.3 Implementation Approach

**Recommended: tree-sitter**

| Aspect | tree-sitter | LSP | TS Compiler API |
|--------|-------------|-----|-----------------|
| Speed | ✅ ~10ms | ❌ ~500ms startup | ❌ ~1s |
| Dependencies | ✅ Python only | ❌ Node.js | ❌ Node.js |
| Multi-language | ✅ Go, Rust, etc. | ❌ Per-language | ❌ TS only |
| Semantic depth | ⚠️ AST only | ✅ Full | ✅ Full |

**Trade-off:** tree-sitter lacks cross-file type resolution, but sufficient for:
- Function/class signatures (explicit types)
- Export/import relationships
- Symbol listing with locations

### 4.4 Scope

#### `invar_sig` for TypeScript

```typescript
// Input: src/auth/validator.ts

// Output:
export function validateToken(token: string): Result<User, AuthError>
  @zod: tokenSchema (line 15)

export class AuthService
  constructor(config: AuthConfig)
  async login(credentials: Credentials): Promise<Result<Session, AuthError>>
    @zod: credentialsSchema (line 42)
```

**Features:**
- Function/method signatures with types
- Class structure (properties, methods)
- Zod schema associations (by naming convention or JSDoc)
- Export visibility

#### `invar_map` for TypeScript

```typescript
// Output:
Symbol Map (src/)
  AuthService          class    src/auth/service.ts:10    refs: 15
  validateToken        function src/auth/validator.ts:5   refs: 8
  UserRepository       class    src/data/user.ts:20       refs: 12
  ...

Top 10 by references (entry points likely)
```

**Features:**
- Symbol enumeration (functions, classes, types)
- Reference counting (within-file + import tracking)
- Sorted by importance

### 4.5 Effort Estimate

| Task | Effort | Notes |
|------|--------|-------|
| tree-sitter setup | 2h | py-tree-sitter + TypeScript grammar |
| `invar_sig` TS parser | 6h | Signatures, classes, Zod detection |
| `invar_map` TS parser | 6h | Symbols, imports, ref counting |
| Integration + tests | 4h | MCP tools, CLI |
| Documentation | 2h | Examples, language matrix update |

**Total Phase C:** ~20 hours

---

## Part 5: Acceptance Criteria

### Phase A (P0) — Quick Fixes
- [ ] MCP instructions match INVAR.md v5.0 Check-In protocol
- [ ] Language support matrix in README and MCP
- [ ] No "Session Start" or "MUST run guard first" in MCP

### Phase B (P1) — Documentation
- [ ] `invar_map` provides helpful message for non-Python projects
- [ ] TypeScript examples document exists
- [ ] USBV checkpoints in MCP instructions

### Phase C (P1) — TypeScript Symbol Tools
- [ ] `invar_sig` parses TypeScript files and shows signatures
- [ ] `invar_sig` detects Zod schemas and associates with functions
- [ ] `invar_map` lists TypeScript symbols with reference counts
- [ ] `invar_map` tracks import/export relationships
- [ ] MCP tools expose TypeScript sig/map functionality
- [ ] Language support matrix updated: sig/map → ✅ Full for TypeScript

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
- **2026-01-03**: Merged TypeScript sig/map tools as Phase C (agent perspective: no IDE = blind)
