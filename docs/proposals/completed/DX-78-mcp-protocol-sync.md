# DX-78: MCP Protocol Sync & TypeScript Support

**Status:** Implemented
**Created:** 2026-01-03
**Revised:** 2026-01-03
**Priority:** P0 (Phase A), P1 (Phase B/C)
**Source:** Paralex project feedback analysis

## Executive Summary

Feedback from Paralex (TypeScript) project revealed:

1. **Protocol mismatch:** MCP instructions contradict INVAR.md v5.0
2. **Documentation error:** Language matrix incorrectly says TypeScript sig/map unavailable
3. **Enhancement needed:** Existing TS tools need accuracy upgrade + new `refs` command

**Key decisions:**
- TypeScript: Use TS Compiler API (single-shot, no orphan process risk)
- Python: Use jedi directly (no Serena dependency)
- Default to accurate mode (1-2s acceptable for CLI/MCP tools)

---

## Part 1: Problem Analysis

### 1.1 Issue Catalog

| ID | Category | Severity | Issue | Status |
|----|----------|----------|-------|--------|
| #1 | Protocol | Critical | MCP "Session Start" contradicts v5.0 "Check-In" | Open |
| #2 | Protocol | Critical | MCP says "MUST run guard first", v5.0 says "Do NOT" | Open |
| #3 | Docs | High | Language matrix incorrectly says TS sig/map unavailable | Open |
| #4 | Tooling | Medium | TS sig uses regex (80% accuracy) | Open |
| #5 | Tooling | Medium | No `invar refs` command | Open |
| #6 | Tooling | Low | TS map has no reference counting | Open |

### 1.2 Key Discovery: TypeScript Tools Already Exist

```python
# src/invar/shell/commands/perception.py (LX-06)
if project_language == "typescript":
    return _run_map_typescript(path, top_n, json_output)
```

**Current:** Regex-based, 80% accuracy
**Target:** TS Compiler API, 100% accuracy

### 1.3 Root Cause: MCP Not Synced to v5.0

**Location:** `src/invar/mcp/server.py` lines 40-49

---

## Part 2: Proposed Solutions

### 2.1 Phase A: MCP Protocol Sync (P0)

**File:** `src/invar/mcp/server.py`

**Replace lines 40-49:**

```markdown
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

**Update line 94 (Task Completion):**
```markdown
- Check-In displayed  # was: Session Start executed
```

**Effort:** 1 hour

---

### 2.2 Phase A: Fix Language Support Matrix (P0)

**Files:** README.md, MCP instructions

```markdown
## Tool × Language Support

| Tool | Python | TypeScript | Notes |
|------|--------|------------|-------|
| `invar_guard` | ✅ Full | ⚠️ Partial | TS: tsc + eslint + vitest |
| `invar_sig` | ✅ Full | ✅ Full | TS: TS Compiler API |
| `invar_map` | ✅ Full | ✅ Full | TS: With reference counts |
| `invar_refs` | ✅ Full | ✅ Full | Cross-file reference finding |
| `invar_doc_*` | ✅ Full | ✅ Full | Language-agnostic |

### TypeScript Notes
- Requires Node.js + TypeScript (most TS projects have these)
- Falls back to regex parser if Node.js unavailable
```

**Effort:** 1 hour

---

### 2.3 Phase B: Error Message & Examples (P1)

**Improved error (perception.py):**
```python
return Failure("""No TypeScript symbols found.

Available tools:
- invar sig <file.ts> — Extract signatures
- invar refs <file.ts>::Symbol — Find references
- invar_doc_* — Document navigation
- invar_guard — Static verification
""")
```

**New file:** `.invar/examples/typescript-patterns.md`

**Effort:** 2.5 hours

---

### 2.4 Phase C: TypeScript Compiler Integration (P1)

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    invar sig/map/refs                        │
├─────────────────────────────────────────────────────────────┤
│  TypeScript                      │  Python                  │
│  ────────────────────────────────│  ────────────────────    │
│  Single-shot subprocess          │  Direct library call     │
│  ┌─────────────────────────┐     │  ┌──────────────────┐   │
│  │  node ts-query.js       │     │  │  import jedi     │   │
│  │  - No persistent process│     │  │  - No subprocess │   │
│  │  - No orphan risk       │     │  │  - Fast          │   │
│  │  - 1-2s per query       │     │  │  - 95% accuracy  │   │
│  │  - 100% accuracy        │     │  └──────────────────┘   │
│  └─────────────────────────┘     │                          │
└─────────────────────────────────────────────────────────────┘
```

#### C1: ts-query.js (TypeScript Side)

**File:** `src/invar/node_tools/ts-query.js`

```javascript
#!/usr/bin/env node
const ts = require('typescript');
const fs = require('fs');

// Load project
const configPath = ts.findConfigFile('.', ts.sys.fileExists);
const config = ts.readConfigFile(configPath, ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, '.');
const program = ts.createProgram(parsed.fileNames, parsed.options);
const checker = program.getTypeChecker();

// Parse query from argv
const query = JSON.parse(process.argv[2]);

switch (query.command) {
    case 'sig':
        outputSignatures(query.file);
        break;
    case 'map':
        outputSymbolMap(query.path, query.top);
        break;
    case 'refs':
        outputReferences(query.file, query.line, query.column);
        break;
}

function outputSignatures(filePath) {
    const sourceFile = program.getSourceFile(filePath);
    const symbols = [];

    ts.forEachChild(sourceFile, node => {
        if (ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node)) {
            const symbol = checker.getSymbolAtLocation(node.name);
            const type = checker.getTypeOfSymbolAtLocation(symbol, node);
            symbols.push({
                name: node.name.getText(),
                kind: ts.SyntaxKind[node.kind],
                signature: checker.typeToString(type),
                line: sourceFile.getLineAndCharacterOfPosition(node.pos).line + 1,
                // For classes, include methods
                members: getMembers(node, checker)
            });
        }
    });

    console.log(JSON.stringify({ file: filePath, symbols }));
}

function outputReferences(filePath, line, column) {
    // Use TypeScript language service for find references
    const languageService = createLanguageService(program);
    const refs = languageService.findReferences(filePath, positionAt(line, column));
    console.log(JSON.stringify(refs));
}

process.exit(0);  // Clean exit, no orphan
```

**Effort:** 5 hours

#### C2: Python Wrapper

**File:** `src/invar/shell/ts_compiler.py`

```python
"""TypeScript Compiler API wrapper (single-shot, no orphan process)."""

import subprocess
import json
from pathlib import Path
from returns.result import Result, Success, Failure

def query_typescript(
    project_root: Path,
    command: str,
    **params
) -> Result[dict, str]:
    """Run ts-query.js and return parsed result.

    Single-shot subprocess: starts, runs query, exits.
    No persistent process, no orphan risk.
    """
    query = {"command": command, **params}

    try:
        result = subprocess.run(
            ["node", "ts-query.js", json.dumps(query)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30  # Safety timeout
        )

        if result.returncode != 0:
            return Failure(f"ts-query failed: {result.stderr}")

        return Success(json.loads(result.stdout))

    except subprocess.TimeoutExpired:
        return Failure("TypeScript query timed out (30s)")
    except FileNotFoundError:
        return Failure("Node.js not found. Install Node.js to use TypeScript tools.")
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON from ts-query: {e}")


def run_sig_typescript(file_path: Path) -> Result[dict, str]:
    """Get signatures for TypeScript file."""
    project_root = find_tsconfig_root(file_path)
    return query_typescript(project_root, "sig", file=str(file_path))


def run_map_typescript(path: Path, top_n: int) -> Result[dict, str]:
    """Get symbol map with reference counts."""
    return query_typescript(path, "map", path=str(path), top=top_n)


def run_refs_typescript(file_path: Path, line: int, col: int) -> Result[list, str]:
    """Find all references to symbol at position."""
    project_root = find_tsconfig_root(file_path)
    return query_typescript(
        project_root, "refs",
        file=str(file_path), line=line, column=col
    )
```

**Effort:** 3 hours

#### C3: Python refs (jedi)

**File:** `src/invar/core/py_refs.py`

```python
"""Python reference finding using jedi (no Serena dependency)."""

from dataclasses import dataclass
from pathlib import Path
from returns.result import Result, Success, Failure
import jedi  # Required dependency of invar-tools


@dataclass
class Reference:
    """A reference to a symbol."""
    file: Path
    line: int
    column: int
    context: str


def find_references(
    file_path: Path,
    line: int,
    column: int,
    project_root: Path | None = None
) -> Result[list[Reference], str]:
    """Find all references to symbol at position using jedi.

    Args:
        file_path: File containing the symbol
        line: 1-based line number
        column: 0-based column number
        project_root: Project root for cross-file resolution

    Returns:
        List of references or error message

    >>> refs = find_references(Path("test.py"), 1, 0)
    """
    try:
        source = file_path.read_text()

        project = None
        if project_root:
            project = jedi.Project(path=str(project_root))

        script = jedi.Script(source, path=str(file_path), project=project)
        refs = script.get_references(line, column)

        return Success([
            Reference(
                file=Path(ref.module_path) if ref.module_path else file_path,
                line=ref.line,
                column=ref.column,
                context=ref.get_line_code().strip() if ref.get_line_code() else ""
            )
            for ref in refs
            if ref.module_path  # Exclude builtins
        ])

    except Exception as e:
        return Failure(f"jedi error: {e}")
```

**Effort:** 2 hours

#### C4: CLI Command `invar refs`

**File:** `src/invar/shell/commands/perception.py` (extend)

```python
@app.command()
def refs(
    target: str = Argument(..., help="file.py::symbol or file.ts::symbol"),
    json_output: bool = Option(False, "--json", help="JSON output"),
) -> None:
    """Find all references to a symbol.

    Examples:
        invar refs src/auth.py::AuthService
        invar refs src/auth.ts::validateToken
    """
    file_path, symbol_name = parse_target(target)

    # Find symbol position
    line, col = find_symbol_position(file_path, symbol_name)

    if file_path.suffix in (".ts", ".tsx"):
        result = run_refs_typescript(file_path, line, col)
    else:
        result = run_refs_python(file_path, line, col)

    # Output handling...
```

**Effort:** 2 hours

---

## Part 3: Implementation Plan

| Phase | Task | Priority | Effort | Deliverable |
|-------|------|----------|--------|-------------|
| **A** | Sync MCP to v5.0 | P0 | 1h | v1.11.1 |
| **A** | Fix language matrix | P0 | 1h | v1.11.1 |
| **B** | Error messages | P1 | 0.5h | v1.11.2 |
| **B** | TypeScript examples | P1 | 2h | v1.11.2 |
| **C** | ts-query.js | P1 | 5h | v1.12.0 |
| **C** | Python wrapper | P1 | 3h | v1.12.0 |
| **C** | invar sig TS rewrite | P1 | 2h | v1.12.0 |
| **C** | invar map TS rewrite | P1 | 2h | v1.12.0 |
| **C** | invar refs (Python, jedi) | P1 | 2h | v1.12.0 |
| **C** | invar refs (TypeScript) | P1 | 2h | v1.12.0 |
| **C** | Testing | P1 | 3h | v1.12.0 |
| **C** | Documentation | P1 | 2h | v1.12.0 |

**Phase A:** 2 hours — Ship immediately as v1.11.1
**Phase B:** 2.5 hours — Ship this week as v1.11.2
**Phase C:** 21 hours — Ship as v1.12.0

**Total:** ~25.5 hours

---

## Part 4: Technical Details

### 4.1 Process Model Comparison

| Approach | Orphan Risk | Speed | Accuracy |
|----------|-------------|-------|----------|
| Persistent LSP | **High** | 50ms | 100% |
| **Single-shot (chosen)** | **None** | 1-2s | 100% |
| Regex only | None | 10ms | 80% |

**Decision:** Single-shot subprocess (ts-query.js)
- Process starts, runs query, exits
- No connection management
- No orphan process risk
- 1-2s latency acceptable for CLI/MCP tools

### 4.2 Dependency Strategy

**TypeScript:**
- Requires: Node.js + TypeScript (standard in TS projects)
- Falls back to regex if unavailable

**Python refs:**
- jedi as required dependency of invar-tools
- No fallback needed

**pyproject.toml:**
```toml
[project]
dependencies = [
    # ... existing deps
    "jedi>=0.19",
]
```

### 4.3 Why Not Serena for Python?

| Aspect | jedi direct | Serena |
|--------|-------------|--------|
| Dependency | jedi only | Serena + LSP |
| Process | None | LSP server |
| Speed | ~100ms | ~500ms startup |
| Maintenance | jedi (stable) | Serena updates |

**Decision:** jedi direct — simpler, no process management

### 4.4 Fallback Strategy

```python
def run_sig_typescript(file_path: Path) -> Result:
    if has_node() and has_typescript():
        return run_ts_compiler_sig(file_path)  # 100% accuracy

    console.print("[yellow]Node.js not found, using regex parser[/yellow]")
    return run_regex_sig(file_path)  # 80% accuracy
```

---

## Part 5: Acceptance Criteria

### Phase A (P0) — v1.11.1
- [ ] MCP server.py uses Check-In, not Session Start
- [ ] MCP server.py does NOT require guard at startup
- [ ] Language matrix shows correct TS support

### Phase B (P1) — v1.11.2
- [ ] Error messages guide to available tools
- [ ] TypeScript examples document exists

### Phase C (P1) — v1.12.0
- [ ] `invar sig file.ts` uses TS Compiler API (100% accuracy)
- [ ] `invar sig file.ts` shows method signatures in classes
- [ ] `invar map` shows reference counts for TypeScript
- [ ] `invar refs file.py::symbol` works (jedi)
- [ ] `invar refs file.ts::symbol` works (TS Compiler)
- [ ] Graceful fallback to regex when Node.js unavailable (TypeScript only)

---

## Part 6: Deliverables

### New Commands

```bash
# Find all references (new)
invar refs src/auth.py::AuthService
invar refs src/auth.ts::validateToken

# Enhanced (TS Compiler API)
invar sig src/auth.ts      # Now includes method signatures
invar map                  # Now includes reference counts for TS
```

### New Files

```
src/invar/
├── node_tools/
│   └── ts-query.js           # TS Compiler API wrapper
├── core/
│   └── py_refs.py            # Python refs using jedi
└── shell/
    └── ts_compiler.py        # Python → ts-query.js bridge
```

### Output Examples

**invar sig (TypeScript, enhanced):**
```
class: AuthService
  export class AuthService
  ├─ constructor(config: AuthConfig)
  ├─ async login(credentials: Credentials): Promise<Result<Session, AuthError>>
  └─ validateToken(token: string): Result<User, AuthError>
```

**invar refs:**
```
AuthService (src/auth/service.ts:10)
  Referenced by:
    src/routes/login.ts:15      import { AuthService }
    src/routes/login.ts:28      const auth = new AuthService()
    src/middleware/auth.ts:5    import { AuthService }
    src/middleware/auth.ts:12   AuthService.validate(token)

  Total: 4 references in 2 files
```

---

## Part 7: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| ts-query.js errors | Medium | Comprehensive error handling |
| Node.js not installed | Low | Fallback to regex + clear message |
| Large project slowness | Low | 30s timeout, can optimize later |
| jedi adds ~5MB to package | Low | Acceptable for refs functionality |

---

## Appendix: Existing Code (LX-06)

**Files to modify:**
- `src/invar/shell/commands/perception.py` — sig/map dispatch
- `src/invar/core/ts_sig_parser.py` — Keep as fallback

**Files to add:**
- `src/invar/node_tools/ts-query.js` — TS Compiler wrapper
- `src/invar/shell/ts_compiler.py` — Python bridge
- `src/invar/core/py_refs.py` — jedi wrapper

---

## Document History

- **2026-01-03**: Initial draft from Paralex feedback
- **2026-01-03**: Merged TypeScript sig/map as Phase C
- **2026-01-03**: Discovered TS tools already exist (LX-06)
- **2026-01-03**: **v2 revision:**
  - Changed to TS Compiler API (single-shot, no orphan risk)
  - Added `invar refs` for both Python and TypeScript
  - Python uses jedi directly (no Serena dependency)
  - Default to accurate mode (1-2s acceptable)
  - Updated effort: 25.5h total
