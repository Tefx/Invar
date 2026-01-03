# DX-78: MCP Protocol Sync & TypeScript Support

**Status:** Draft (Revised)
**Created:** 2026-01-03
**Revised:** 2026-01-03
**Priority:** P0 (Phase A), P1 (Phase B/C)
**Source:** Paralex project feedback analysis

## Executive Summary

Feedback from Paralex (TypeScript) project revealed:

1. **Protocol mismatch:** MCP instructions contradict INVAR.md v5.0
2. **Documentation error:** Language matrix says TypeScript sig/map don't exist — **they do!**
3. **Enhancement needed:** Existing TS tools lack Zod detection and method signatures

**Key discovery:** `invar sig` and `invar map` already support TypeScript (LX-06). Phase C is about **enhancement**, not building from scratch.

---

## Part 1: Problem Analysis

### 1.1 Issue Catalog (Revised)

| ID | Category | Severity | Issue | Status |
|----|----------|----------|-------|--------|
| #1 | Protocol | Critical | MCP "Session Start" contradicts v5.0 "Check-In" | Open |
| #2 | Protocol | Critical | MCP says "MUST run guard first", v5.0 says "Do NOT" | Open |
| #3 | Docs | High | Language matrix incorrectly says TS sig/map unavailable | Open |
| #4 | Tooling | Medium | TS sig misses method signatures | Open |
| #5 | Tooling | Medium | TS sig/map don't detect Zod schemas | Open |
| #6 | Tooling | Low | TS map has no reference counting | Open |

### 1.2 Key Discovery: TypeScript Tools Already Exist!

```python
# src/invar/shell/commands/perception.py

# Line 48-49: Map supports TypeScript
if project_language == "typescript":
    return _run_map_typescript(path, top_n, json_output)

# Line 82-84: Sig supports TypeScript
if suffix in (".ts", ".tsx"):
    return _run_sig_typescript(content, file_path, symbol_name, json_output)
```

**Current capabilities (LX-06):**
- `invar sig file.ts` — Extracts function/class signatures ✅
- `invar map` (in TS project) — Lists symbols by kind ✅
- Zod schema detection — ❌
- Method signatures in classes — ❌
- Reference counting — ❌

### 1.3 Root Cause: MCP Not Synced to v5.0

**Location:** `src/invar/mcp/server.py` lines 40-49

**Current (outdated):**
```markdown
### Session Start (REQUIRED)
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

---

## Part 2: Proposed Solutions

### 2.1 Phase A: MCP Protocol Sync (P0)

**File:** `src/invar/mcp/server.py`

**Changes:**

1. Replace "Session Start" with "Check-In":

```python
# Before (lines 40-49):
### Session Start (REQUIRED)
Before writing ANY code, you MUST execute:
1. `invar_guard(changed=true)` — Check existing violations
2. `invar_map(top=10)` — Understand code structure

# After:
### Check-In (REQUIRED)
Your first message MUST display:
✓ Check-In: [project] | [branch] | [clean/dirty]

**Actions:** Read `.invar/context.md`, then show status.
**Do NOT run guard at Check-In.**

Run guard only when:
- Entering VALIDATE phase
- User requests verification
- After making code changes
```

2. Update "Task Completion" section (line 94):

```python
# Before:
- Session Start executed (invar_guard + invar_map)

# After:
- Check-In displayed
```

**Effort:** 1 hour

---

### 2.2 Phase A: Fix Language Support Matrix (P0)

**Files:** README.md, MCP instructions

**Current (incorrect):**
```markdown
| `invar_sig` | ✅ Full | ⚠️ Limited | TS: Type signatures via LSP |
| `invar_map` | ✅ Full | ❌ N/A | Python symbol analysis only |
```

**Corrected:**
```markdown
## Tool × Language Support

| Tool | Python | TypeScript | Notes |
|------|--------|------------|-------|
| `invar_guard` | ✅ Full | ⚠️ Partial | TS: tsc + eslint + vitest |
| `invar_sig` | ✅ Full | ✅ Basic | TS: Regex parser (LX-06) |
| `invar_map` | ✅ Full | ✅ Basic | TS: Symbol list, no ref counts |
| `invar_doc_*` | ✅ Full | ✅ Full | Language-agnostic |

### TypeScript Limitations

- **sig:** Function/class signatures only (no method details)
- **map:** No reference counting (symbol list only)
- **guard:** Static rules only, no @pre/@post contracts

### Planned Enhancements (Phase C)

- Zod schema detection
- Method signatures in classes
- Import/export relationship tracking
```

**Effort:** 1 hour

---

### 2.3 Phase B: Error Message Improvement (P1)

**File:** `src/invar/shell/commands/perception.py`

**Current (line 216):**
```python
return Failure("No TypeScript symbols found (files may be empty...)")
```

**Proposed:**
```python
return Failure("""No TypeScript symbols found.

Possible causes:
- Files contain only type definitions (no functions/classes)
- Files are empty or contain only comments

Available tools for TypeScript:
- invar_doc_* — Document navigation (full support)
- invar_sig <file.ts> — Extract signatures from specific file
- invar_guard — Static verification (tsc + eslint)
""")
```

**Effort:** 30 minutes

---

### 2.4 Phase B: TypeScript Examples (P1)

**File:** `.invar/examples/typescript-patterns.md`

**Content outline:**
1. Available tools for TypeScript
2. Zod schema as contracts (concept)
3. neverthrow Result<T, E> for Shell
4. Guard verification (tsc + eslint)
5. Document-first workflow

**Effort:** 2 hours

---

### 2.5 Phase C: TypeScript Tool Enhancements (P1)

#### C1: Add Method Signature Extraction

**File:** `src/invar/core/ts_sig_parser.py`

**Current output:**
```
class: AuthService
  export class AuthService
```

**Enhanced output:**
```
class: AuthService
  export class AuthService
  └─ constructor(config: AuthConfig)
  └─ async login(credentials: Credentials): Promise<Result<Session, AuthError>>
```

**Implementation:** Extend regex patterns to capture method signatures.

**Effort:** 3 hours

#### C2: Add Zod Schema Detection

**File:** `src/invar/core/ts_sig_parser.py`

**Detection heuristics:**
```typescript
// Pattern 1: Variable assignment
const userSchema = z.object({ ... })  // Detect "Schema" suffix

// Pattern 2: Export
export const CreateUserSchema = z.object({ ... })

// Pattern 3: Type inference
type User = z.infer<typeof userSchema>  // Link to schema
```

**Output:**
```
schema: userSchema
  z.object({ name: z.string(), email: z.string().email() })
  └─ infers: User (line 15)
```

**Effort:** 4 hours

#### C3: Add Import Tracking (Optional)

**File:** `src/invar/shell/commands/perception.py`

**Current:** Symbol list only
**Enhanced:** Track which files import each symbol

```
Symbol Map (src/)
  AuthService    class    src/auth/service.ts:10
    imported by: src/routes/login.ts, src/middleware/auth.ts
```

**Note:** This is NOT reference counting (no usage analysis). Just import statements.

**Effort:** 4 hours

---

## Part 3: Implementation Plan

| Phase | Task | Priority | Effort | Deliverable |
|-------|------|----------|--------|-------------|
| A | Sync MCP to v5.0 | P0 | 1h | v1.11.1 |
| A | Fix language matrix | P0 | 1h | v1.11.1 |
| B | Improve error messages | P1 | 30m | v1.11.2 |
| B | TypeScript examples | P1 | 2h | v1.11.2 |
| C | Method signatures | P1 | 3h | v1.12.0 |
| C | Zod detection | P1 | 4h | v1.12.0 |
| C | Import tracking | P2 | 4h | v1.12.0 |

**Phase A:** 2 hours — Ship immediately
**Phase B:** 2.5 hours — Ship this week
**Phase C:** 11 hours — Separate PR

**Total:** ~15.5 hours (down from 25.5h — no new tools needed!)

---

## Part 4: Technical Details

### 4.1 Current TypeScript Parser (ts_sig_parser.py)

**Approach:** Regex-based parsing
**Pros:** Pure Python, no dependencies, fast
**Cons:** Limited accuracy, can't handle complex syntax

**Current capabilities:**
```python
# Detected:
- export function name(params): ReturnType
- export class ClassName
- export interface InterfaceName
- export type TypeName = ...
- export const CONSTANT = ...

# Not detected:
- Method signatures inside classes
- Zod schema patterns
- Private/protected members
```

### 4.2 Why Not tree-sitter?

| Factor | Regex (Current) | tree-sitter |
|--------|-----------------|-------------|
| Dependencies | None | C compiler required |
| uvx install | ✅ Works | ⚠️ May break |
| Accuracy | 80% | 95% |
| Maintenance | Low | Medium |

**Decision:** Enhance regex parser for now. Consider tree-sitter if accuracy becomes critical.

### 4.3 Why Not LSP?

| Factor | Regex | LSP (typescript-language-server) |
|--------|-------|----------------------------------|
| Dependencies | None | Node.js + npm |
| Startup time | ~10ms | ~500ms |
| Accuracy | 80% | 100% |
| Cross-file refs | ❌ | ✅ |

**Decision:** LSP is better but requires Node.js. Keep as future option (LX-10?).

---

## Part 5: Acceptance Criteria

### Phase A (P0) — Must Ship Immediately
- [ ] MCP server.py uses Check-In, not Session Start
- [ ] MCP server.py does NOT require guard at startup
- [ ] Language matrix correctly shows TS sig/map as "Basic"
- [ ] README updated with accurate tool support

### Phase B (P1) — This Week
- [ ] Error messages guide users to available tools
- [ ] TypeScript examples document exists
- [ ] USBV checkpoints in MCP (optional)

### Phase C (P1) — Separate PR
- [ ] `invar sig` shows method signatures for TS classes
- [ ] `invar sig` detects Zod schemas (by naming convention)
- [ ] `invar map` shows import relationships (optional)

---

## Part 6: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regex parser misses edge cases | Medium | Document limitations clearly |
| Zod detection false positives | Low | Use strict naming conventions |
| Breaking existing behavior | Low | Additive changes only |

---

## Part 7: Alternatives Considered

### A1: Build New Tools with tree-sitter
- **Rejected:** TypeScript tools already exist (LX-06)
- **Rejected:** tree-sitter adds native dependencies

### A2: Use LSP for Full Semantic Analysis
- **Deferred:** Requires Node.js runtime
- **Future:** Consider for LX-10 if accuracy demands increase

### A3: Don't Enhance, Just Fix Docs
- **Partial:** Phase A+B take this approach
- **Rejected for C:** Agent experience still suboptimal without method sigs

---

## Appendix: Source Documents

1. `/Users/tefx/Projects/paralex/docs/feedback/invar-typescript-ux-feedback.md`
2. `/Users/tefx/Projects/paralex/docs/feedback/invar-comprehensive-analysis.md`

---

## Appendix: Existing TypeScript Support (LX-06)

**Files:**
- `src/invar/core/ts_sig_parser.py` — Signature extraction
- `src/invar/core/ts_parsers.py` — tsc/eslint/vitest output parsing
- `src/invar/shell/prove/guard_ts.py` — TypeScript guard orchestration
- `src/invar/shell/commands/perception.py` — sig/map CLI integration

**Test:**
```bash
# Already works!
invar sig path/to/file.ts
invar map  # (in TypeScript project)
```

---

## Document History

- **2026-01-03**: Initial draft from Paralex feedback
- **2026-01-03**: Merged TypeScript sig/map as Phase C
- **2026-01-03**: **Major revision** — Discovered TS tools already exist (LX-06)
  - Reduced scope from 25.5h to 15.5h
  - Phase C: Enhancement, not new build
  - Removed tree-sitter approach (unnecessary)
  - Fixed language matrix accuracy
