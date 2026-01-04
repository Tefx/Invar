# LX-06: TypeScript Tooling Support

**Status:** Complete ✅ (Phase 1-3), Phase 4 Optional
**Priority:** High
**Category:** Language/Agent eXtensions
**Created:** 2025-12-31
**Updated:** 2026-01-01
**Based on:** LX-05 (language-agnostic protocol)
**Depends on:** LX-05 Phase 1-3 (templates) ✅
**Appendix:** [Guard Implementation Comparison](LX-06-appendix-guard-comparison.md)

## Executive Summary

Implement TypeScript verification tooling using a **hybrid architecture**: Python orchestration with targeted Node.js components for capabilities that cannot be achieved via subprocess parsing.

**Core insight:** Invar tools serve AI agents, not human IDE users. Design decisions prioritize structured output, actionable guidance, and deterministic behavior over real-time feedback and IDE integration.

**Architecture Decision:** Approach A (Python Orchestration) + Targeted B Components

| Approach | Development Cost | Functionality | Recommendation |
|----------|------------------|---------------|----------------|
| Pure A (subprocess only) | 10 days | 85% | MVP baseline |
| Hybrid A+B (selected) | 18 days | 96% | **Recommended** |
| Pure B (native TS) | 25+ days | 98% | Overkill for agent use |

---

## Problem Statement

### Current State After LX-05

| Layer | Python | TypeScript |
|-------|--------|------------|
| Protocol (INVAR.md) | ✅ Full | ✅ Full |
| Examples | ✅ contracts.py, core_shell.py, functional.py | ✅ contracts.ts, core_shell.ts, functional.ts |
| Templates | ✅ Jinja composition | ✅ Jinja composition |
| Language Detection | ✅ pyproject.toml | ✅ tsconfig.json |
| **`invar guard`** | ✅ 4-layer verification | ❌ **Not implemented** |
| **`invar sig`** | ✅ Python AST | ❌ **Not implemented** |
| **`invar map`** | ✅ Symbol discovery | ❌ **Not implemented** |
| **MCP Tools** | ✅ invar_guard, invar_sig, invar_map | ❌ **Python-only** |

### Impact on Agent Workflow

Without TypeScript tooling, agents cannot autonomously verify TypeScript code:

```
# Python project: Full automation
Agent: invar_guard() → JSON output → parse → fix issues → repeat

# TypeScript project: Blocked
Agent: invar_guard() → "Unsupported language" → cannot proceed
```

---

## Architecture Decision

### Why Hybrid A+B?

**Pure Approach A Limitations:**

| Capability | Subprocess Parsing | Impact on Agent |
|------------|-------------------|-----------------|
| Property test counterexamples | ⚠️ String only | Cannot understand failure cause |
| Cross-file type tracing | ❌ Impossible | Misses contract relationships |
| Contract quality assessment | ❌ Impossible | Cannot evaluate contract value |
| Incremental analysis | ⚠️ File-hash only | Slow for large projects |

**Hybrid Solution:** Keep Python orchestration, add targeted Node components for specific capabilities.

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python Layer (invar-tools) — Orchestration & Output                    │
├─────────────────────────────────────────────────────────────────────────┤
│  invar guard --language=typescript                                      │
│    ├── tsc --noEmit --pretty false    → parse stdout                   │
│    ├── eslint --format json           → parse JSON                     │
│    ├── vitest --reporter json         → parse JSON                     │
│    ├── @invar/fc-runner --json        → parse JSON  [Node component]   │
│    └── @invar/ts-analyzer --json      → parse JSON  [Node component]   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Node Layer (optional npm packages) — Targeted Capabilities             │
├─────────────────────────────────────────────────────────────────────────┤
│  @invar/quick-check    (~100 LOC) — Pre-commit fast verification       │
│  @invar/ts-analyzer    (~300 LOC) — TypeScript Compiler API analysis   │
│  @invar/fc-runner      (~200 LOC) — fast-check programmatic control    │
│  @invar/eslint-plugin  (~400 LOC) — Invar-specific ESLint rules        │
│  @invar/vitest-reporter(~200 LOC) — Doctest coverage reporting         │
│  @invar/daemon         (~500 LOC) — Shared Node process [Phase 4]      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Graceful Degradation

```python
def run_typescript_guard(path: str) -> GuardResult:
    results = []

    # Always available (subprocess)
    results.append(run_tsc(path))
    results.append(run_eslint(path))
    results.append(run_vitest(path))

    # Enhanced if available (Node components)
    try:
        results.append(run_ts_analyzer(path))  # Deep contract analysis
        results.append(run_fc_runner(path))     # Rich property test output
    except ToolNotInstalled as e:
        # Graceful degradation with suggestion
        results.append(BasicResult(
            status="skipped",
            suggestion=f"Install {e.package} for enhanced analysis"
        ))

    return aggregate(results)
```

---

## Agent-Centric Design

### What Agents Need

| Requirement | Priority | Implementation |
|-------------|----------|----------------|
| Structured JSON output | ⭐⭐⭐⭐⭐ | All tools output JSON |
| Precise locations (file:line:col) | ⭐⭐⭐⭐⭐ | Unified fix format |
| Actionable repair code | ⭐⭐⭐⭐⭐ | Include code snippets |
| Causal failure explanation | ⭐⭐⭐⭐ | Why failed, not just what |
| Contract quality assessment | ⭐⭐⭐⭐ | strong/medium/weak/useless |
| Confidence level | ⭐⭐⭐⭐ | "tested" vs "proven" |
| Impact analysis | ⭐⭐⭐ | What files affected by change |

### What Agents Do NOT Need

| Feature | Reason |
|---------|--------|
| IDE integration | Agents don't use IDEs |
| Real-time feedback | Agents call tools explicitly |
| Quick Fix UI | Agents write fixes themselves |
| Watch mode | Agents trigger verification |
| Hover information | Agents read code directly |

---

## Output Format (Agent-Optimized)

### Unified Guard Output

```json
{
  "version": "2.0",
  "language": "typescript",
  "status": "failed",
  "summary": {
    "errors": 2,
    "warnings": 1,
    "files_checked": 15
  },

  "static": {
    "tsc": { "passed": true, "errors": 0 },
    "eslint": { "passed": false, "errors": 2, "warnings": 1 }
  },

  "tests": {
    "passed": true,
    "total": 25,
    "failed": 0,
    "doctests": { "covered": 12, "total": 15, "percent": 80.0 }
  },

  "property_tests": {
    "status": "failed",
    "confidence": "statistical",
    "failures": [{
      "name": "discounted price is non-negative",
      "counterexample": {
        "values": { "price": 0, "discount": 1.0000000000000002 },
        "shrunk": true,
        "shrink_steps": 23
      },
      "analysis": {
        "failed_assertion": "result >= 0",
        "actual": -2.22e-16,
        "root_cause": "floating_point_precision",
        "suggested_fix": "Use Math.max(0, result) or round to fixed decimals"
      }
    }]
  },

  "contracts": {
    "coverage": 80.0,
    "quality": {
      "strong": 7,
      "medium": 2,
      "weak": 1,
      "useless": 0
    },
    "blind_spots": [{
      "function": "processPayment",
      "file": "src/payment.ts",
      "line": 78,
      "risk": "critical",
      "reason": "Handles money with no validation",
      "suggested_schema": "z.object({ amount: z.number().positive().max(1000000) })"
    }]
  },

  "fixes": [{
    "id": "FIX-001",
    "priority": "high",
    "issue": {
      "type": "missing_validation",
      "message": "Parameter 'input' has Zod type but no .parse() call",
      "location": { "file": "src/api/users.ts", "line": 42, "column": 5 }
    },
    "repair": {
      "action": "insert",
      "target": { "file": "src/api/users.ts", "line": 43 },
      "code": "const validated = CreateUserSchema.parse(input);",
      "explanation": "Add Zod validation at function entry"
    }
  }]
}
```

### Contract Analysis Output

```json
{
  "functions": [{
    "name": "createUser",
    "file": "src/api/users.ts",
    "line": 42,
    "contract_status": "complete",
    "params": [{
      "name": "input",
      "type": "CreateUserInput",
      "has_contract": true,
      "contract_source": {
        "schema": "CreateUserSchema",
        "file": "src/schemas/user.ts",
        "line": 10,
        "trace_chain": ["CreateUserInput", "z.infer<typeof CreateUserSchema>"]
      },
      "quality": {
        "score": "strong",
        "has_type_constraint": true,
        "has_value_constraint": true,
        "has_boundary_constraint": true
      }
    }],
    "validation": {
      "has_runtime_check": true,
      "check_locations": [{ "method": "parse", "line": 44 }]
    }
  }]
}
```

---

## Node Components Specification

### @invar/quick-check (P0 — Pre-commit)

**Purpose:** Fast pre-commit verification (<1s)

**Why needed:** Python orchestration has ~5s cold start; unacceptable for git hooks.

```bash
# Usage
npx @invar/quick-check src/

# Output
{
  "passed": true,
  "duration_ms": 450,
  "checks": {
    "tsc": { "passed": true, "cached": true },
    "eslint": { "passed": true, "cached": true }
  }
}
```

**Implementation:** ~100 LOC, uses tsc --incremental and eslint --cache.

### @invar/ts-analyzer (P1 — Contract Analysis)

**Purpose:** Deep contract analysis using TypeScript Compiler API

**Why needed:** tree-sitter cannot trace types across files or resolve `z.infer<typeof T>`.

```bash
# Usage
npx @invar/ts-analyzer --json src/

# Capabilities
- Cross-file type tracing
- z.infer<T> resolution
- Contract quality assessment
- Dependency graph for impact analysis
- Blind spot detection
```

**Implementation:** ~300 LOC, uses TypeScript Compiler API.

### @invar/fc-runner (P1 — Property Tests)

**Purpose:** Programmatic fast-check control with rich failure analysis

**Why needed:** vitest JSON output lacks counterexample details, shrinking info, and causal analysis.

```bash
# Usage
npx @invar/fc-runner --json --seed 12345 --num-runs 100 src/

# Output includes
- Typed counterexamples (not just strings)
- Shrinking path and step count
- Root cause classification
- Suggested fix based on failure pattern
```

**Implementation:** ~200 LOC, wraps fast-check programmatic API.

### @invar/eslint-plugin (P1 — Static Rules)

**Purpose:** Invar-specific ESLint rules for prevention (not just detection)

**Rules:**

| Rule | Description |
|------|-------------|
| `@invar/require-schema-validation` | Zod-typed params must have .parse() |
| `@invar/no-io-in-core` | Forbid I/O imports in /core/ |
| `@invar/shell-result-type` | Shell functions must return Result<T, E> |
| `@invar/no-any-in-schema` | Forbid z.any() in schemas |
| `@invar/require-jsdoc-example` | Exported functions need @example |

**Implementation:** ~400 LOC.

### @invar/vitest-reporter (P2 — Doctest Coverage)

**Purpose:** Track doctest coverage and correlate with contracts

**Why needed:** Standard vitest JSON doesn't distinguish doctests from regular tests.

```json
{
  "doctest_coverage": {
    "functions_with_examples": 12,
    "functions_total": 15,
    "percent": 80.0,
    "uncovered": ["deleteUser", "processPayment"]
  }
}
```

**Implementation:** ~200 LOC, custom vitest reporter.

### @invar/daemon (P4 — Performance)

**Purpose:** Shared Node process to eliminate cold start overhead

**Why needed:** Multiple subprocess spawns add ~2-3s overhead.

**Architecture:**

```
Python ←→ Unix Socket ←→ @invar/daemon
                            ├── Cached TypeScript Program
                            ├── Cached ESLint instance
                            └── Persistent fast-check runner
```

**Performance impact:** Subsequent calls 200ms → 50ms

**Implementation:** ~500 LOC, Unix socket server with JSON protocol.

---

## Environment Isolation Strategy

### Problem: Node.js Root Directory Pollution

Node.js projects typically pollute root directories with many config files:

```
# Typical Node.js project root (polluted)
├── package.json
├── package-lock.json
├── node_modules/           # Hundreds of MB
├── tsconfig.json
├── .eslintrc.js
├── .prettierrc
├── vitest.config.ts
└── ...
```

Invar is a Python project. We don't want Node artifacts in the root.

### Solution: Subdirectory Isolation

All TypeScript/Node.js development happens in an isolated `typescript/` subdirectory:

```
invar/                          # Python project root (CLEAN)
├── pyproject.toml
├── src/invar/
├── runtime/
├── tests/
├── docs/
└── typescript/                 # TS isolation zone
    ├── .gitignore              # node_modules, dist
    ├── package.json            # pnpm workspace root
    ├── pnpm-lock.yaml
    ├── pnpm-workspace.yaml
    ├── tsconfig.base.json
    └── packages/
        ├── quick-check/
        │   ├── package.json
        │   ├── tsconfig.json
        │   └── src/
        ├── ts-analyzer/
        ├── fc-runner/
        ├── eslint-plugin/
        └── vitest-reporter/
```

### Root Directory Impact: Zero

```diff
  invar/
  ├── .gitignore
  ├── pyproject.toml
  ├── CLAUDE.md
  ├── INVAR.md
  ├── src/
  ├── runtime/
  ├── tests/
  ├── docs/
+ └── typescript/              # Only addition (self-contained)
```

### .gitignore Configuration

```gitignore
# TypeScript isolation
typescript/node_modules/
typescript/**/dist/
typescript/**/*.tsbuildinfo
```

### Development Workflow

```bash
# Python development (root directory)
cd invar
pip install -e ".[dev]"
invar guard

# TypeScript development (isolated subdirectory)
cd typescript
pnpm install
pnpm build
pnpm test

# Publish npm packages
cd typescript
pnpm -r publish
```

### CI/CD Separation

```yaml
# .github/workflows/python.yml
name: Python CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[dev]"
      - run: invar guard

# .github/workflows/typescript.yml
name: TypeScript CI
on:
  push:
    paths: ['typescript/**']
jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: typescript
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm build
      - run: pnpm test
```

### Python ↔ TypeScript Integration
### Python ↔ TypeScript Integration

Python calls TypeScript tools via 3-tier discovery with graceful degradation:

```python
# src/invar/shell/prove/guard_ts.py

def _get_invar_package_cmd(package_name: str, project_path: Path) -> list[str]:
    """Get command to run an @invar/* package.
    
    Priority order:
    1. Embedded tools (pip install invar-tools includes these)
    2. Local development (typescript/packages/*/dist/ in Invar repo)
    3. npx fallback (if published to npm)
    """
    # Priority 1: Embedded tools (from pip install)
    try:
        from invar.node_tools import get_tool_path
        if embedded := get_tool_path(package_name):
            return ["node", str(embedded)]
    except ImportError:
        pass  # node_tools module not available
    
    # Priority 2: Local development setup
    local_cli = project_path / f"typescript/packages/{package_name}/dist/cli.js"
    if local_cli.exists():
        return ["node", str(local_cli)]
    
    # Priority 3: npx fallback
    return ["npx", f"@invar/{package_name}"]

def run_eslint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run ESLint with @invar/eslint-plugin rules."""
    try:
        cmd = _get_invar_package_cmd("eslint-plugin", project_path)
        cmd.append(str(project_path))
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        violations = []
        try:
            eslint_output = json.loads(result.stdout)
            for file_result in eslint_output:
                for msg in file_result.get("messages", []):
                    violations.append(TypeScriptViolation(...))
        except json.JSONDecodeError:
            if result.returncode != 0 and result.stderr:
                return Failure(f"ESLint error: {result.stderr[:200]}")
        
        return Success(violations)
    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
```

**Key Benefits:**
- **Zero-config for users:** Embedded tools work out-of-the-box after `pip install invar-tools`
- **Development-friendly:** Local dev setup auto-detected in Invar repo
- **Graceful degradation:** Falls back to npx if embedded tools not available

### Benefits

| Aspect | Result |
|--------|--------|
| Root directory | ✅ Zero pollution |
| Version sync | ✅ Single repo, easy coordination |
| Development | ✅ Clear separation of concerns |
| CI/CD | ✅ Independent pipelines |
| npm publishing | ✅ Standard workflow from `typescript/` |

---

## Implementation Plan

### Phase 1: MVP — Python Orchestration (10 days)

**Goal:** `invar guard` works on TypeScript projects via subprocess.

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | TypeScript guard orchestrator | `guard_ts.py` with tsc/eslint/vitest |
| 3 | Language dispatch | `detect_language()` integration |
| 4-5 | Output parsing | tsc, eslint, vitest JSON parsers |
| 6-7 | MCP integration | `invar_guard` works for TypeScript |
| 8 | Sig TypeScript (basic) | tree-sitter based extraction |
| 9 | Map TypeScript | File discovery, reference counting |
| 10 | Integration tests | End-to-end verification |

**Deliverables:**
- `invar guard` detects TypeScript, runs verification
- `invar sig file.ts` shows basic contract info
- `invar map` includes TypeScript files
- MCP tools work for TypeScript

### Phase 2: Core Enhancement — Node Components (8 days)

**Goal:** Add targeted Node components for capabilities subprocess can't provide.

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | @invar/quick-check | Pre-commit fast verification |
| 3-5 | @invar/ts-analyzer | TypeScript Compiler API analysis |
| 6-7 | @invar/fc-runner | fast-check programmatic wrapper |
| 8 | @invar/eslint-plugin (basic) | 2-3 core rules |

**Deliverables:**
- Pre-commit < 1s
- Cross-file contract tracing
- Rich property test failure analysis
- Core ESLint rules

### Phase 3: Agent Optimization (5 days)

**Goal:** Enhance output for agent consumption.

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Causal failure analysis | Root cause + suggested fix |
| 2 | Contract quality scoring | strong/medium/weak/useless |
| 3 | Repair code generation | Actionable code snippets |
| 4 | Impact analysis | Change → affected files |
| 5 | Blind spot detection | High-risk unvalidated code |

**Deliverables:**
- Agent-optimized JSON output v2.0
- All fix suggestions include code
- Contract quality assessment

### Phase 4: Performance Optimization (As Needed)

**Goal:** Optimize for large projects and frequent calls.

| Task | Trigger | Deliverable |
|------|---------|-------------|
| @invar/daemon | Users report >3s overhead | Shared Node process |
| Incremental cache | Large projects slow | File-hash based caching |
| Parallel execution | Many files | Concurrent subprocess |

---

## File Structure

### Complete Project Layout

```
invar/                              # Project root (Python-focused, CLEAN)
├── pyproject.toml
├── CLAUDE.md
├── INVAR.md
├── .gitignore                      # Includes typescript/node_modules
│
├── src/invar/                      # Python source
│   ├── shell/
│   │   ├── prove/
│   │   │   ├── guard_ts.py         # TypeScript guard orchestrator
│   │   │   ├── perception_ts.py    # Sig TypeScript (tree-sitter)
│   │   │   └── output_parsers.py   # tsc/eslint/vitest parsers
│   │   └── commands/
│   │       └── guard.py            # Language dispatch
│   ├── core/
│   │   ├── extraction_ts.py        # Zod schema extraction
│   │   └── references_ts.py        # TypeScript reference counting
│   └── mcp/
│       └── tools.py                # Language-aware MCP tools
│
├── runtime/                        # invar-runtime package
├── tests/                          # Python tests
├── docs/
│
└── typescript/                     # ══════ ISOLATED TS ZONE ══════
    ├── .gitignore                  # node_modules, dist, *.tsbuildinfo
    ├── package.json                # pnpm workspace root
    ├── pnpm-lock.yaml
    ├── pnpm-workspace.yaml
    ├── tsconfig.base.json          # Shared TS config
    ├── vitest.workspace.ts         # Shared test config
    │
    └── packages/
        ├── quick-check/            # @invar/quick-check
        │   ├── package.json
        │   ├── tsconfig.json
        │   └── src/
        │       └── index.ts        # Fast pre-commit check
        │
        ├── ts-analyzer/            # @invar/ts-analyzer
        │   ├── package.json
        │   ├── tsconfig.json
        │   └── src/
        │       ├── index.ts        # CLI entry
        │       ├── analyzer.ts     # TypeScript Compiler API
        │       └── quality.ts      # Contract quality scoring
        │
        ├── fc-runner/              # @invar/fc-runner
        │   ├── package.json
        │   ├── tsconfig.json
        │   └── src/
        │       ├── index.ts        # CLI entry
        │       ├── runner.ts       # fast-check wrapper
        │       └── analysis.ts     # Failure analysis
        │
        ├── eslint-plugin/          # @invar/eslint-plugin
        │   ├── package.json
        │   ├── tsconfig.json
        │   └── src/
        │       ├── index.ts        # Plugin entry
        │       └── rules/          # Individual rules
        │
        └── vitest-reporter/        # @invar/vitest-reporter
            ├── package.json
            ├── tsconfig.json
            └── src/
                └── index.ts        # Custom reporter
```

### pnpm Workspace Configuration

```yaml
# typescript/pnpm-workspace.yaml
packages:
  - 'packages/*'
```

```json
// typescript/package.json
{
  "name": "@invar/monorepo",
  "private": true,
  "scripts": {
    "build": "pnpm -r build",
    "test": "vitest run",
    "lint": "eslint packages/*/src",
    "publish:all": "pnpm -r publish --access public"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.56.0"
  }
}
```

---

## User Installation

### Minimal (MVP)

```bash
pip install invar-tools
# TypeScript verification works via subprocess
# No additional npm packages needed
```

### Enhanced (Full Features)

```bash
pip install invar-tools

# Optional: Enhanced analysis
npm install -D @invar/ts-analyzer @invar/fc-runner @invar/eslint-plugin

# Optional: Fast pre-commit
npm install -D @invar/quick-check
```

### Convenience Script

```bash
# One command to install all optional packages
npx @invar/setup typescript
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_guard_ts.py

def test_tsc_output_parsing():
    """TSC errors parsed correctly."""
    output = "src/core/calc.ts(42,5): error TS2345: Type mismatch"
    result = parse_tsc_output(output)
    assert result.errors == 1
    assert result.fixes[0].line == 42

def test_eslint_json_parsing():
    """ESLint JSON parsed correctly."""
    # ...

def test_graceful_degradation():
    """Missing Node components don't crash guard."""
    # ...
```

### Integration Tests

```python
# tests/integration/test_guard_ts.py

def test_full_typescript_project(tmp_path):
    """Guard runs complete verification on TypeScript project."""
    setup_typescript_project(tmp_path)
    result = run_guard(tmp_path)
    assert result["status"] in ("passed", "failed")
    assert "static" in result
    assert "tests" in result
```

### Node Component Tests

```typescript
// packages/ts-analyzer/tests/analyzer.test.ts

test('traces z.infer across files', async () => {
  const result = await analyze(fixtureProject);
  const func = result.functions.find(f => f.name === 'createUser');
  expect(func.params[0].contract_source.trace_chain).toContain('z.infer');
});
```

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Node not installed | High | Medium | Clear error message, fallback to basic |
| npm packages not installed | Medium | High | Graceful degradation with suggestions |
| TypeScript version conflicts | Medium | Medium | Support TS 4.9+ |
| ESLint version conflicts | Medium | Medium | Support ESLint 8 and 9 |
| Performance (subprocess overhead) | Low | Medium | Phase 4 daemon if needed |
| tree-sitter accuracy limits | Low | Medium | @invar/ts-analyzer for deep analysis |

---

## Success Criteria

### Phase 1 (MVP) ✅ Complete

- [x] `invar guard` runs on TypeScript project
- [x] MCP `invar_guard` works for TypeScript
- [x] `invar sig file.ts` shows basic signatures
- [x] `invar map` includes TypeScript files
- [x] Unified JSON output format

**Implementation Notes:**
- Regex-based signature extraction (tree-sitter planned for Phase 2)
- Graceful degradation when Node.js tools unavailable
- 23 integration tests covering all TypeScript tooling

### Phase 2 (Core Enhancement) ✅ Complete

- [x] Pre-commit < 1s with @invar/quick-check
- [x] Cross-file contract tracing works
- [x] Property test failures include causal analysis
- [x] @invar/eslint-plugin implemented (5 rules)

**Implementation Notes:**
- pnpm monorepo in `typescript/` subdirectory
- 4 packages: quick-check, ts-analyzer, fc-runner, eslint-plugin
- Python integration with graceful degradation
- esbuild bundling for standalone CJS distribution
- Embedded in Python wheel via `scripts/embed_node_tools.py`
- npm publish available for users who prefer npm installation

### Phase 3 (Agent Optimization) ✅ Complete

- [x] All fixes include repair code snippets
- [x] Contract quality assessment (strong/medium/weak/useless)
- [x] Blind spot detection for high-risk code
- [x] Impact analysis for changed files
- [x] v2.0 JSON format integrated into guard command

**Implementation Notes:**
- v2.0 JSON format with `contracts.quality` and `contracts.coverage`
- ESLint rules have `hasSuggestions: true` with auto-fix code
- ts-analyzer provides contract quality scoring via TypeScript Compiler API
- `buildDependencyGraph()` and `analyzeImpact()` for change impact
- Guard command dispatches to TypeScript handler and uses v2.0 format
- Embedded tools tested and working (ts-analyzer ~220KB bundled)

### Acceptance Test

```bash
# Agent workflow simulation
$ invar guard --json
{
  "status": "failed",
  "fixes": [{
    "id": "FIX-001",
    "repair": {
      "code": "const validated = UserSchema.parse(input);",
      "explanation": "Add validation"
    }
  }]
}

# Agent applies fix, re-runs
$ invar guard --json
{
  "status": "passed",
  "contracts": {
    "quality": { "strong": 8, "medium": 2 }
  }
}
```

---

## Timeline Summary

| Phase | Duration | Cumulative | Key Deliverable |
|-------|----------|------------|-----------------|
| Phase 1: MVP | 10 days | 10 days | TypeScript guard works |
| Phase 2: Core Enhancement | 8 days | 18 days | Node components |
| Phase 3: Agent Optimization | 5 days | 23 days | Agent-friendly output |
| Phase 4: Performance | As needed | — | Daemon optimization |

---

## Appendices

- [Appendix A: Guard Implementation Comparison](LX-06-appendix-guard-comparison.md) — Detailed analysis of Python orchestration vs native TypeScript approaches

---

## References

- LX-05: Language-Agnostic Protocol Extraction
- [TypeScript Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)
- [tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript)
- [Zod](https://zod.dev/)
- [fast-check](https://fast-check.dev/)
- [vitest](https://vitest.dev/)
- [neverthrow](https://github.com/supermacro/neverthrow)

---

*LX-06 v3: Hybrid architecture with agent-centric design and isolated TypeScript environment. Completes TypeScript tooling story started by LX-05.*
