# LX-06 Appendix: Guard Implementation Comparison

**Purpose:** Deep analysis of implementation approaches for TypeScript guard.
**Decision:** Hybrid A+B (Python Orchestration + Targeted Node Components)
**Updated:** 2025-12-31

---

## Two Approaches Overview

### Approach A: Python Orchestration (Subprocess)

```
┌─────────────────────────────────────────────────────────────┐
│                    Python (invar-tools)                      │
├─────────────────────────────────────────────────────────────┤
│  invar guard                                                 │
│    ├── detect_language(path) → "typescript"                 │
│    ├── TypeScriptGuard.run()                                │
│    │     ├── subprocess.run(["npx", "tsc", "--noEmit"])     │
│    │     ├── subprocess.run(["npx", "eslint", "."])         │
│    │     ├── subprocess.run(["npx", "vitest", "run"])       │
│    │     └── aggregate_results()                            │
│    └── output_agent(result) → JSON                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Node.js (user project)                    │
├─────────────────────────────────────────────────────────────┤
│  tsc, eslint, vitest (called via subprocess)                │
└─────────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- Python controls orchestration, Node executes verification
- Parse stdout/stderr from Node tools
- Unified output format regardless of underlying tools
- Single `pip install invar-tools` provides all functionality

### Approach B: Native TypeScript Package

```
┌─────────────────────────────────────────────────────────────┐
│                    Node.js (@invar/tools)                    │
├─────────────────────────────────────────────────────────────┤
│  invar-guard (npx)                                          │
│    ├── detectLanguage(path) → "typescript"                  │
│    ├── runTsc()                                             │
│    ├── runEslint()                                          │
│    ├── runVitest()                                          │
│    └── outputAgent(result) → JSON                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python (invar-tools)                      │
├─────────────────────────────────────────────────────────────┤
│  invar guard                                                 │
│    ├── detect_language(path) → "typescript"                 │
│    ├── subprocess.run(["npx", "@invar/guard"])              │
│    └── passthrough output                                   │
│                                                             │
│  OR                                                         │
│                                                             │
│  MCP server calls @invar/guard directly                     │
└─────────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- TypeScript has its own complete tool implementation
- Python is thin wrapper or MCP just invokes npm package
- Better TypeScript ecosystem integration
- Requires `npm install @invar/tools` + `pip install invar-tools`

---

## Detailed Comparison Matrix

### 1. Development Complexity

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **New code** | ~500 LOC Python | ~2000 LOC TypeScript + ~200 LOC Python |
| **Languages to maintain** | 1 (Python) | 2 (Python + TypeScript) |
| **Build systems** | pyproject.toml only | pyproject.toml + package.json + tsconfig.json |
| **CI/CD** | Existing GitHub Actions | New npm publish workflow |
| **Testing** | pytest only | pytest + vitest |
| **Release coordination** | Single version | Two versions to sync |

**Winner: Approach A** — Significantly simpler to develop and maintain.

### 2. Runtime Dependencies

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **User install (Python project)** | `pip install invar-tools` | `pip install invar-tools` |
| **User install (TS project)** | `pip install invar-tools` (Node required for subprocess) | `pip install invar-tools` + `npm install @invar/tools` |
| **Node.js required** | Yes (for subprocess) | Yes (native) |
| **Global vs local** | Uses project's npx | Needs global or project install |

**Winner: Approach A** — Single package install, Node only needed at runtime.

### 3. Output Parsing Reliability

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **tsc output** | Parse stdout (structured with --pretty false) | Native API access |
| **ESLint output** | Parse JSON (--format json) | Native API access |
| **vitest output** | Parse JSON (--reporter json) | Native API access |
| **Error handling** | Must handle format changes | Direct access to errors |
| **Edge cases** | May miss non-standard output | Full control |

**Winner: Approach B** — More reliable, no parsing fragility.

### 4. Performance

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **Cold start** | Python + Node subprocess spawn | Node only |
| **Per-tool overhead** | 3 subprocess spawns (tsc, eslint, vitest) | Direct API calls |
| **Parallel execution** | Python ProcessPoolExecutor + Node | Node native async |
| **Memory** | Python + Node processes | Node only |

**Measurement (estimated for 100-file project):**

| Metric | Approach A | Approach B |
|--------|------------|------------|
| Cold start | ~2s | ~1s |
| Full verification | ~15s | ~12s |
| Incremental (1 file) | ~5s | ~3s |

**Winner: Approach B** — 20-40% faster, especially for incremental checks.

### 5. TypeScript Ecosystem Integration

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **ESLint plugin** | Separate npm package | Same package, direct integration |
| **vitest plugin** | Separate config | Same package, bundled |
| **TypeScript compiler API** | Subprocess only | Direct access for advanced analysis |
| **IDE integration** | Via subprocess | Native VSCode extension possible |
| **Monorepo support** | Limited (cwd-based) | Workspace-aware |

**Winner: Approach B** — Much better ecosystem integration.

### 6. MCP Integration

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **MCP server language** | Python (existing) | Python (calls npm) or Node (new server) |
| **Tool registration** | Same as Python tools | Additional dispatch logic |
| **Output format** | Unified by Python | Need format agreement |
| **Error propagation** | Python handles all | Cross-language error handling |

```python
# Approach A: Python MCP server
async def _run_guard(args):
    if language == "typescript":
        return TypeScriptGuard().run(path, args)  # Python orchestration
    else:
        return PythonGuard().run(path, args)

# Approach B: Python MCP calls Node
async def _run_guard(args):
    if language == "typescript":
        result = subprocess.run(["npx", "@invar/guard", "--json"])
        return parse_output(result.stdout)
```

**Winner: Approach A** — Simpler MCP integration, unified codebase.

### 7. Maintenance Burden

| Aspect | Approach A (Python) | Approach B (Native TS) |
|--------|---------------------|------------------------|
| **Bug reports** | Single issue tracker | Split across repos? |
| **Version compatibility** | Python version matrix | Python + Node version matrix |
| **Breaking changes** | tsc/eslint/vitest output format | Same, plus internal API |
| **Documentation** | Python docs only | Python + TypeScript docs |
| **Community PRs** | Python contributors | Need TS contributors too |

**Winner: Approach A** — Significantly lower maintenance burden.

### 8. Feature Parity with Python Guard

| Feature | Python Guard | Approach A | Approach B |
|---------|--------------|------------|------------|
| Static analysis | ✅ rules.py | ✅ Parse ESLint | ✅ ESLint API |
| Doctests | ✅ pytest | ✅ vitest @example | ✅ vitest API |
| Property tests | ✅ Hypothesis | ⚠️ fast-check (manual) | ✅ fast-check integration |
| Symbolic | ✅ CrossHair | ❌ No TS equivalent | ❌ No TS equivalent |
| Contract detection | ✅ AST | ⚠️ tree-sitter | ✅ TS compiler API |
| Incremental | ✅ git diff | ✅ git diff | ✅ git diff + TS incremental |
| Caching | ✅ file hash | ⚠️ Limited | ✅ Full TypeScript cache |

**Winner: Approach B** — Better feature parity, especially for advanced features.

---

## Decision Analysis

### Why Choose Approach A (Current Recommendation)

1. **MVP Speed**
   - 10 days vs 20+ days implementation
   - Can iterate faster on feedback

2. **Single Codebase**
   - All logic in Python
   - Easier to understand and debug
   - Consistent coding standards

3. **Lower Risk**
   - Known technology (subprocess)
   - No npm package publishing learning curve
   - No TypeScript build tooling complexity

4. **User Simplicity**
   - `pip install invar-tools` works for all projects
   - No additional `npm install` step
   - Same CLI regardless of project type

5. **MCP Consistency**
   - Python MCP server unchanged
   - Same tool signatures
   - Unified output format

### When Approach B Becomes Better

| Trigger | When | Why Switch |
|---------|------|------------|
| **Performance** | Users report >5s overhead | Native is 40% faster |
| **ESLint plugin** | Need custom rules | Plugin must be npm package |
| **IDE integration** | VSCode extension requested | Needs TS codebase |
| **Monorepo support** | Enterprise adoption | Workspace-aware tooling |
| **Community growth** | >100 TS users | Worth the investment |

### Hybrid Path

Start with Approach A, migrate specific components to B as needed:

```
Phase 1: Approach A (MVP)
├── Python orchestration
├── Subprocess calls to npx
└── Parse output

Phase 2: ESLint Plugin (Approach B component)
├── @invar/eslint-plugin as npm package
├── Python guard calls existing ESLint + plugin
└── Best of both worlds

Phase 3: Full Native (if needed)
├── @invar/tools npm package
├── Python as thin wrapper
└── Full ecosystem integration
```

---

## Output Format Agreement

Regardless of approach, unified output format is critical:

```json
{
  "status": "passed" | "failed",
  "language": "python" | "typescript",
  "static": {
    "passed": true,
    "errors": 0,
    "warnings": 2
  },
  "tests": {
    "passed": true,
    "total": 15,
    "failed": 0
  },
  "property_tests": {
    "status": "passed" | "skipped" | "failed",
    "reason": "..."
  },
  "fixes": [
    {
      "file": "src/core/calc.ts",
      "line": 42,
      "rule": "missing_zod_schema",
      "severity": "error",
      "message": "Function 'calculate' has no Zod schema validation"
    }
  ],
  "summary": {
    "files_checked": 10,
    "errors": 0,
    "warnings": 2
  }
}
```

This format must be identical for both Python and TypeScript guards, enabling:
- Unified MCP tool response
- Consistent agent parsing
- Same UI/output formatting

---

## Subprocess Parsing Strategy (Approach A)

### tsc Output Parsing

```python
def parse_tsc_output(stdout: str, stderr: str) -> StaticResult:
    """Parse TypeScript compiler output.

    tsc formats:
    - Default: "file.ts(line,col): error TSxxxx: message"
    - --pretty false: Same but no colors
    """
    errors = []
    pattern = r"(.+)\((\d+),(\d+)\): (error|warning) (TS\d+): (.+)"

    for line in stdout.split("\n"):
        match = re.match(pattern, line)
        if match:
            file, line_num, col, severity, code, message = match.groups()
            errors.append(Fix(
                file=file,
                line=int(line_num),
                rule=f"typescript_{code.lower()}",
                severity="error" if severity == "error" else "warning",
                message=message,
            ))

    return StaticResult(
        passed=len([e for e in errors if e.severity == "error"]) == 0,
        errors=len([e for e in errors if e.severity == "error"]),
        warnings=len([e for e in errors if e.severity == "warning"]),
        fixes=errors,
    )
```

### ESLint JSON Parsing

```python
def parse_eslint_output(stdout: str) -> StaticResult:
    """Parse ESLint JSON output.

    Run with: npx eslint . --format json
    """
    try:
        results = json.loads(stdout)
    except json.JSONDecodeError:
        return StaticResult(passed=False, errors=1, warnings=0,
                          fixes=[Fix(file="", line=0, rule="eslint_parse_error",
                                    severity="error", message="Failed to parse ESLint output")])

    fixes = []
    for file_result in results:
        for msg in file_result.get("messages", []):
            fixes.append(Fix(
                file=file_result["filePath"],
                line=msg.get("line", 0),
                rule=msg.get("ruleId", "unknown"),
                severity="error" if msg.get("severity") == 2 else "warning",
                message=msg.get("message", ""),
            ))

    error_count = sum(1 for f in fixes if f.severity == "error")
    warning_count = sum(1 for f in fixes if f.severity == "warning")

    return StaticResult(
        passed=error_count == 0,
        errors=error_count,
        warnings=warning_count,
        fixes=fixes,
    )
```

### vitest JSON Parsing

```python
def parse_vitest_output(stdout: str) -> TestResult:
    """Parse vitest JSON reporter output.

    Run with: npx vitest run --reporter=json
    """
    try:
        results = json.loads(stdout)
    except json.JSONDecodeError:
        return TestResult(passed=False, total=0, failed=1)

    test_results = results.get("testResults", [])
    total = sum(len(tr.get("assertionResults", [])) for tr in test_results)
    failed = sum(
        1 for tr in test_results
        for ar in tr.get("assertionResults", [])
        if ar.get("status") == "failed"
    )

    return TestResult(
        passed=failed == 0,
        total=total,
        failed=failed,
    )
```

---

## Conclusion

**Recommended: Approach A (Python Orchestration)**

| Criterion | Weight | A | B | Weighted A | Weighted B |
|-----------|--------|---|---|------------|------------|
| Development speed | 25% | 9 | 4 | 2.25 | 1.00 |
| Maintenance burden | 20% | 8 | 4 | 1.60 | 0.80 |
| User simplicity | 20% | 9 | 6 | 1.80 | 1.20 |
| Feature parity | 15% | 6 | 9 | 0.90 | 1.35 |
| Performance | 10% | 6 | 8 | 0.60 | 0.80 |
| Ecosystem integration | 10% | 4 | 9 | 0.40 | 0.90 |
| **Total** | 100% | | | **7.55** | **6.05** |

**Approach A wins** for MVP phase. Re-evaluate after:
- 6 months of usage data
- Community feedback on performance
- ESLint plugin requirements materialize

---

## References

- [TypeScript Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)
- [ESLint Node.js API](https://eslint.org/docs/latest/integrate/nodejs-api)
- [vitest Node API](https://vitest.dev/advanced/api.html)
- [tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript)

---

## Appendix: Hybrid Approach (Final Decision)

After deeper analysis, we adopt a **Hybrid A+B** approach:

### Architecture

```
Python Orchestration (Approach A)
├── tsc, eslint, vitest via subprocess
├── Output parsing for structured JSON
└── Unified CLI and MCP interface

+ Targeted Node Components (Approach B elements)
├── @invar/quick-check     — Fast pre-commit (<1s)
├── @invar/ts-analyzer     — TypeScript Compiler API
├── @invar/fc-runner       — fast-check programmatic control
└── @invar/eslint-plugin   — Invar-specific rules
```

### Why Hybrid Wins

| Dimension | Pure A | Pure B | Hybrid A+B |
|-----------|--------|--------|------------|
| Dev cost | 10 days | 25 days | 18 days |
| Functionality | 85% | 98% | 96% |
| Maintenance | Low | High | Medium |
| User install | Simple | Complex | Simple + optional |

### Agent-Centric Perspective

Key insight: Invar tools serve AI agents, not IDE users.

**Agents need:**
- Structured JSON output
- Actionable repair code
- Causal failure explanation
- Contract quality assessment

**Agents don't need:**
- IDE integration
- Real-time feedback
- Quick Fix UI
- Watch mode

This shifts the evaluation: IDE-related features (where Pure B excels) have zero weight.

### Remaining Gaps (4%)

| Gap | Size | Solvable? |
|-----|------|-----------|
| Symbolic execution | 1% | No (language limitation) |
| Complex causal analysis | 1% | Partially (heuristics) |
| Edge case repairs | 1% | Partially (patterns) |
| Deep type inference | 1% | Yes (with @invar/ts-analyzer) |

The 96% coverage is sufficient for agent use cases.

---

*This appendix supports the LX-06 v2 proposal decision rationale.*
