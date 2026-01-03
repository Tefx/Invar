# LX-11: Cursor IDE Support

**Status:** Draft
**Created:** 2026-01-04
**Updated:** 2026-01-04
**Priority:** High (Largest user base among coding agents)

## Executive Summary

Implement native Cursor IDE support with `invar init --cursor`, generating complete configuration including MDC rules with glob patterns, 6-type hooks system (surpassing Claude Code's 4), and commands system. Cursor's hooks enable automatic verification superior to Claude Code.

**Key Insight:** Cursor's `afterFileEdit` hook enables automatic guard execution after every AI edit—a capability Claude Code lacks.

---

## Problem Statement

### Current State

- ✅ Manual integration documented in `docs/guides/cursor.md`
- ❌ No `invar init --cursor` automation
- ❌ Users must manually create ~11 configuration files
- ❌ Hooks require JavaScript expertise

### User Pain Points

1. **Manual Setup Burden** — 11 files to create manually
2. **Hook Complexity** — Requires Node.js knowledge
3. **MDC Format** — Unfamiliar YAML frontmatter + globs
4. **No Verification Loop** — Unlike Aider's lint-cmd

### Why Cursor Matters

| Metric | Value |
|--------|-------|
| User Base | Largest among AI coding agents |
| Hooks Support | 6 types (vs Claude's 4) |
| Rules System | MDC with glob patterns |
| MCP Support | Native |

---

## Solution Design

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Rules (MDC Format)                                │
│  ───────────────────────────────────────────────────────────│
│  .cursor/rules/                                             │
│  ├── invar-core.mdc        (globs: src/**/core/**/*.py)     │
│  ├── invar-shell.mdc       (globs: src/**/shell/**/*.py)    │
│  └── invar-workflow.mdc    (globs: **/*.py)                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Hooks (Automatic Enforcement)                     │
│  ───────────────────────────────────────────────────────────│
│  beforeShellExecution  → Block pytest/crosshair             │
│  afterFileEdit         → Auto-run guard (UNIQUE!)           │
│  stop                  → Final verification                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Commands (Skills Alternative)                     │
│  ───────────────────────────────────────────────────────────│
│  /invar-develop   → USBV workflow guide                     │
│  /invar-review    → Adversarial review checklist            │
│  /invar-guard     → Manual verification trigger             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
project/
├── .cursorrules                    # Simple rules (backward compat)
├── .cursor/
│   ├── rules/                      # MDC rules (recommended)
│   │   ├── invar-core.mdc          # Core layer enforcement
│   │   ├── invar-shell.mdc         # Shell layer enforcement
│   │   └── invar-workflow.mdc      # USBV workflow
│   ├── commands/                   # Skills alternative
│   │   ├── invar-develop.md        # /invar-develop
│   │   ├── invar-review.md         # /invar-review
│   │   └── invar-guard.md          # /invar-guard
│   ├── hooks/                      # Enforcement scripts
│   │   ├── block-pytest.js         # beforeShellExecution
│   │   ├── auto-guard.js           # afterFileEdit
│   │   └── final-check.js          # stop
│   ├── hooks.json                  # Hook configuration
│   └── mcp-setup.md                # MCP setup guide
└── .invar/
    ├── context.md                  # Project context
    └── examples/                   # Pattern examples
```

---

## MDC Rules Design

### Core Layer Rule

```markdown
---
description: Invar Core module rules - pure functions with contracts
globs: ["src/**/core/**/*.py", "**/core/**/*.py"]
alwaysApply: true
---

# Core Module Rules

You are editing a **Core** module. These rules are MANDATORY:

## Requirements

1. **Pure Functions Only**
   - NO I/O operations (file, network, database)
   - NO side effects
   - Deterministic output for same input

2. **Contracts Required**
   ```python
   from invar_runtime import pre, post

   @pre(lambda x: x > 0)
   @post(lambda result: result >= 0)
   def calculate(x: int) -> int:
       ...
   ```

3. **Doctests Required**
   ```python
   def calculate(x: int) -> int:
       """
       >>> calculate(5)
       25
       """
   ```

4. **Forbidden Imports**
   - ❌ pathlib, os, os.path
   - ❌ requests, urllib, httpx
   - ❌ subprocess, shutil
```

**Key Feature:** `globs` pattern automatically applies rule to Core directories only.

### Shell Layer Rule

```markdown
---
description: Invar Shell module rules - I/O with Result types
globs: ["src/**/shell/**/*.py", "**/shell/**/*.py"]
alwaysApply: true
---

# Shell Module Rules

You are editing a **Shell** module. These rules are MANDATORY:

1. **Result Return Type**
   ```python
   from returns.result import Result, Success, Failure

   def read_config(path: str) -> Result[Config, str]:
       try:
           data = Path(path).read_text()
           return Success(parse_config(data))
       except Exception as e:
           return Failure(f"Failed: {e}")
   ```

2. **No Contracts Required**
   - Shell functions don't need @pre/@post
   - Result type provides error handling
```

---

## Hooks Implementation

### Hook Configuration

```json
{
  "hooks": {
    "beforeShellExecution": {
      "command": "node",
      "args": [".cursor/hooks/block-pytest.js"],
      "timeout": 5000
    },
    "afterFileEdit": {
      "command": "node",
      "args": [".cursor/hooks/auto-guard.js"],
      "timeout": 30000
    },
    "stop": {
      "command": "node",
      "args": [".cursor/hooks/final-check.js"],
      "timeout": 60000
    }
  }
}
```

### Hook 1: pytest Blocker

**Purpose:** Prevent direct pytest/crosshair usage, redirect to invar_guard

```javascript
// .cursor/hooks/block-pytest.js
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const command = input.command || '';

const BLOCKED = [
  /^pytest\b/,
  /^python\s+-m\s+pytest\b/,
  /^crosshair\b/,
];

for (const pattern of BLOCKED) {
  if (pattern.test(command)) {
    console.log(JSON.stringify({
      decision: "block",
      message: "⛔ Use invar_guard MCP tool instead"
    }));
    process.exit(0);
  }
}

console.log(JSON.stringify({ decision: "allow" }));
```

### Hook 2: Auto Guard (UNIQUE CAPABILITY)

**Purpose:** Automatically run guard after AI edits Python files

```javascript
// .cursor/hooks/auto-guard.js
const fs = require('fs');
const { execSync } = require('child_process');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const filePath = input.filePath || '';

if (!filePath.endsWith('.py')) {
  console.log(JSON.stringify({ decision: 'continue' }));
  process.exit(0);
}

try {
  const result = execSync(`invar guard "${filePath}" --human`, {
    encoding: 'utf-8',
    timeout: 25000
  });

  if (result.includes('FAIL')) {
    console.log(JSON.stringify({
      decision: 'continue',
      message: `⚠️ Invar Guard found issues:\n${result}`
    }));
  } else {
    console.log(JSON.stringify({
      decision: 'continue',
      message: `✓ Guard OK`
    }));
  }
} catch (error) {
  console.log(JSON.stringify({
    decision: 'continue',
    message: `⚠️ Guard check failed: ${error.message}`
  }));
}
```

**Why This Matters:** This is automatic verification without user intervention—superior to Claude Code's manual approach.

### Hook 3: Final Check

**Purpose:** Run full verification when session ends

```javascript
// .cursor/hooks/final-check.js
const { execSync } = require('child_process');

try {
  const result = execSync('invar guard --changed --human', {
    encoding: 'utf-8',
    timeout: 55000
  });

  if (result.includes('FAIL')) {
    console.log(JSON.stringify({
      decision: 'continue',
      message: `⚠️ Final: guard FAIL\n${result}`
    }));
  } else {
    console.log(JSON.stringify({
      decision: 'continue',
      message: `✓ Final: guard PASS`
    }));
  }
} catch (error) {
  console.log(JSON.stringify({
    decision: 'continue',
    message: `⚠️ Final check skipped`
  }));
}
```

---

## Commands Design (Skills Alternative)

Cursor doesn't support SKILL.md auto-routing, but has Commands system triggered via `/command`.

### Command 1: Development Workflow

```markdown
<!-- .cursor/commands/invar-develop.md -->
# Invar Development Mode

Follow USBV workflow strictly:

## Phase 1: UNDERSTAND
1. Read user's request
2. Use `invar_sig` to see existing code
3. Identify Core vs Shell

## Phase 2: SPECIFY
1. Write @pre/@post contracts FIRST
2. Add doctests
3. Show contracts before implementing

## Phase 3: BUILD
1. Implement following contracts
2. Run `invar_guard(changed=true)` after each file

## Phase 4: VALIDATE
1. Run `invar_guard()` for full verification
2. Report: `✓ Final: guard PASS`

Start by understanding the task.
```

### Command 2: Code Review

```markdown
<!-- .cursor/commands/invar-review.md -->
# Adversarial Code Review

Code is GUILTY until proven INNOCENT.

## Review Checklist

### A. Contract Semantic Value
- [ ] @pre constrains inputs beyond types?
- [ ] @post verifies meaningful properties?

### B. Doctest Coverage
- [ ] Normal, boundary, error cases?

### C. Core/Shell Separation
- [ ] I/O isolated in Shell?
- [ ] Core modules pure?

## Output Format
```
### Critical Issues (must fix)
| Line | Issue | Fix |
```

Run `invar_guard()` after review.
```

---

## Comparison with Other Agents

### vs Claude Code

| Feature | Claude Code | Cursor (This Proposal) | Winner |
|---------|-------------|------------------------|--------|
| Rules Format | CLAUDE.md | MDC + globs | **Cursor** |
| Skills/Commands | Auto-routing | Manual `/cmd` | Claude |
| Hooks | 4 types | **6 types** | **Cursor** |
| pytest Block | PreToolUse | beforeShellExecution | Equal |
| Auto Verify | ❌ | ✅ **afterFileEdit** | **Cursor** |
| Final Check | ❌ | ✅ **stop** | **Cursor** |
| MCP | Project .mcp.json | Global config | Claude |

**Key Advantage:** `afterFileEdit` hook enables automatic verification after every AI edit—Claude Code requires manual triggering.

### vs Aider

| Feature | Aider | Cursor |
|---------|-------|--------|
| Auto Verify | ✅ lint-cmd | ✅ afterFileEdit hook |
| Skills | ❌ | Commands (manual) |
| MCP | ⚠️ Community | ✅ Native |
| Plan Mode | ❌ | ❌ |

### vs Cline

| Feature | Cline | Cursor |
|---------|-------|--------|
| Rules | .clinerules | MDC + globs |
| Hooks | ❌ | ✅ 6 types |
| Commands | ❌ | ✅ |
| Plan Mode | ✅ | ❌ |

---

## Implementation Plan

### Phase A: Templates (1 day)

| Task | File | Lines |
|------|------|-------|
| Simple rules | `.cursorrules.jinja` | ~100 |
| Core MDC | `rules/invar-core.mdc.jinja` | ~80 |
| Shell MDC | `rules/invar-shell.mdc.jinja` | ~60 |
| Workflow MDC | `rules/invar-workflow.mdc.jinja` | ~50 |

### Phase B: Hooks (1 day)

| Task | File | Lines |
|------|------|-------|
| Hook config | `hooks.json` | ~15 |
| pytest blocker | `hooks/block-pytest.js` | ~40 |
| Auto guard | `hooks/auto-guard.js` | ~50 |
| Final check | `hooks/final-check.js` | ~40 |

### Phase C: Commands (0.5 day)

| Task | File | Lines |
|------|------|-------|
| Develop | `commands/invar-develop.md` | ~60 |
| Review | `commands/invar-review.md` | ~50 |
| Guard | `commands/invar-guard.md` | ~30 |

### Phase D: Integration (0.5 day)

| Task | File | Changes |
|------|------|---------|
| Init flag | `init.py` | `--cursor` option |
| Manifest | `manifest.toml` | File mappings |
| Docs | `cursor.md` | Update guide |

**Total:** ~3 days

---

## Manifest Configuration

```toml
# templates/manifest.toml

[agents.cursor]
creates = [
    ".cursorrules",
    ".cursor/rules/invar-core.mdc",
    ".cursor/rules/invar-shell.mdc",
    ".cursor/rules/invar-workflow.mdc",
    ".cursor/commands/invar-develop.md",
    ".cursor/commands/invar-review.md",
    ".cursor/commands/invar-guard.md",
    ".cursor/hooks.json",
    ".cursor/hooks/block-pytest.js",
    ".cursor/hooks/auto-guard.js",
    ".cursor/hooks/final-check.js",
    ".cursor/mcp-setup.md",
]

skip = [".cursor/mcp.json"]  # User-global, provide docs only
```

---

## Success Criteria

### Must Have

- [ ] `invar init --cursor` creates all 11 files
- [ ] MDC rules enforce Core/Shell separation via globs
- [ ] beforeShellExecution blocks pytest/crosshair
- [ ] afterFileEdit runs guard automatically
- [ ] stop hook runs final verification
- [ ] Commands accessible via `/invar-*`

### Nice to Have

- [ ] MCP auto-detection and configuration
- [ ] Hook error handling and recovery
- [ ] Progress feedback during hook execution

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hooks beta status | May change | Provide non-hook fallback in docs |
| Node.js dependency | Setup friction | Check and guide installation |
| MCP global config | Manual setup | Clear mcp-setup.md guide |
| Auto-guard slowdown | Workflow interruption | Make it opt-in via hook config |

---

## Future Enhancements

### Phase 2 (Optional)

1. **Smart Auto-Guard**
   - Only run on significant changes (>10 lines)
   - Skip on whitespace-only edits
   - Debounce rapid edits

2. **beforeMCPExecution Governance**
   - Audit invar_guard calls
   - Log verification history

3. **MCP Auto-Configuration**
   - Detect uvx availability
   - Auto-add to global MCP settings

---

## References

### External

- [Cursor Hooks Deep Dive](https://blog.gitbutler.com/cursor-hooks-deep-dive)
- [Cursor 1.7 Release](https://www.infoq.com/news/2025/10/cursor-hooks/)
- [MCP Governance](https://www.mintmcp.com/blog/mcp-governance-cursor-hooks)
- [Cursor Docs: Commands](https://cursor.com/docs/agent/chat/commands)

### Internal

- [LX-02: Agent Portability Analysis](completed/LX-02-agent-portability-analysis.md)
- [LX-04: Multi-Agent Framework (Pi)](LX-04-pi-agent-support.md)
- [DX-69: Project Uninstall](completed/DX-69-project-uninstall.md)
- [docs/guides/cursor.md](../guides/cursor.md)

---

## Decision Log

### 2026-01-04: Initial Proposal

**Decision:** Prioritize Cursor over Aider/Cline/Antigravity

**Rationale:**
1. Largest user base among AI coding agents
2. 6-type hooks system (most comprehensive)
3. afterFileEdit enables automatic verification
4. MDC globs naturally support Core/Shell separation

**Trade-offs:**
- No Skills auto-routing (use Commands instead)
- MCP is global not project-level
- Requires Node.js for hooks

**Alternative Considered:** Implement Aider first (simpler, no hooks)

**Why Rejected:** Cursor's hooks provide superior enforcement and automation
