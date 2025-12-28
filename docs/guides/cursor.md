# Invar + Cursor Integration Guide

[Cursor](https://cursor.com/) is an AI-first IDE with the largest user base among coding agents. This guide shows how to use Invar with Cursor, including its beta hooks feature.

## Quick Start

### 1. Install Invar

```bash
pip install invar-tools
```

### 2. Create `.cursorrules`

Create `.cursorrules` in your project root:

```markdown
# Invar Development Protocol

## Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | Use invar_guard MCP tool — NOT pytest, NOT crosshair |
| **Core** | @pre/@post + doctests, NO I/O imports in core/ |
| **Shell** | Returns Result[T, E] from returns library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```

## USBV Workflow

### 1. UNDERSTAND
- What exactly needs to be done?
- Use invar_sig to see existing contracts
- Read relevant code, understand patterns

### 2. SPECIFY
- Write @pre/@post BEFORE implementation
- Add doctests for expected behavior

### 3. BUILD
- Follow the contracts from SPECIFY
- Run invar_guard frequently

### 4. VALIDATE
- Run invar_guard (full verification)
- Ensure all requirements met

## Verification

ALWAYS use invar_guard instead of pytest:

```
# Good
invar_guard(changed=true)

# Bad - Don't use directly
pytest ...
crosshair ...
```

## Contract Example

```python
from invar_runtime import pre, post

@pre(lambda x: x > 0, "x must be positive")
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    >>> calculate(10)
    100
    """
    return x * x
```
```

### 3. Configure MCP

In Cursor settings, add MCP server configuration:

**Option A: Using uvx**

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

**Option B: Using project venv**

```json
{
  "mcpServers": {
    "invar": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  }
}
```

### 4. (Optional) Configure Hooks

Cursor 1.7+ supports hooks. Create `.cursor/hooks.json`:

```json
{
  "hooks": {
    "beforeShellExecution": {
      "command": "node",
      "args": [".cursor/hooks/check-command.js"],
      "timeout": 5000
    }
  }
}
```

Create `.cursor/hooks/check-command.js`:

```javascript
// Block pytest/crosshair, redirect to invar guard
const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
const command = input.command || '';

const blocked = [
  /^pytest\b/,
  /^python\s+-m\s+pytest\b/,
  /^crosshair\b/,
  /^python\s+-m\s+crosshair\b/
];

for (const pattern of blocked) {
  if (pattern.test(command)) {
    console.log(JSON.stringify({
      decision: "block",
      message: "Use invar_guard MCP tool instead of " + command.split(' ')[0]
    }));
    process.exit(0);
  }
}

console.log(JSON.stringify({ decision: "allow" }));
```

---

## Project Rules (Modern Approach)

Cursor recommends `.cursor/rules/` directory over `.cursorrules`:

### Create Rule Files

```
.cursor/
└── rules/
    ├── invar-core.mdc
    ├── invar-workflow.mdc
    └── invar-verification.mdc
```

### `invar-core.mdc`

```markdown
---
description: Invar core development rules
globs: ["src/**/core/**/*.py"]
alwaysApply: true
---

# Core Module Rules

This is a **core** module. Follow these rules:

1. **Pure functions only** - No I/O operations
2. **Contracts required** - Every public function needs @pre/@post
3. **Doctests required** - Include usage examples
4. **No forbidden imports** - No pathlib, os.path, requests, etc.

## Example

```python
from invar_runtime import pre, post

@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def process(x: int) -> int:
    """
    >>> process(5)
    25
    """
    return x * x
```
```

### `invar-workflow.mdc`

```markdown
---
description: USBV workflow for all Python files
globs: ["**/*.py"]
alwaysApply: false
---

# USBV Workflow

When implementing features:

1. **UNDERSTAND** - Read existing code, use invar_sig
2. **SPECIFY** - Write @pre/@post contracts first
3. **BUILD** - Implement following contracts
4. **VALIDATE** - Run invar_guard
```

### `invar-verification.mdc`

```markdown
---
description: Verification rules
globs: ["**/*.py"]
alwaysApply: true
---

# Verification

**NEVER** use pytest or crosshair directly.
**ALWAYS** use the invar_guard MCP tool.

```
# Correct
invar_guard(changed=true)

# Wrong - will be blocked by hooks
pytest ...
```
```

---

## Feature Mapping

### What Works

| Invar Feature | Cursor Support |
|---------------|----------------|
| USBV Workflow | ✅ Via rules |
| Guard Verification | ✅ Via MCP |
| Sig/Map Tools | ✅ Via MCP |
| Core/Shell Rules | ✅ Via rules |
| pytest Blocking | ⚠️ Via hooks (beta) |

### What's Different

| Claude Code | Cursor Alternative |
|-------------|-------------------|
| Skills (auto-routing) | Not available |
| Hooks (4 types) | Hooks beta (limited) |
| /audit, /guard commands | Direct MCP calls |
| CLAUDE.md | .cursorrules or .cursor/rules/ |

---

## Hooks Deep Dive

### Available Hook Events (Cursor 1.7+)

| Event | Purpose |
|-------|---------|
| `beforeShellExecution` | Before running terminal commands |
| `afterFileEdit` | After AI edits a file |
| `stop` | When session ends |

### pytest Blocking Hook

The hook above blocks pytest. Here's an enhanced version:

```javascript
// .cursor/hooks/check-command.js
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const command = input.command || '';

// Patterns to block
const blocked = [
  { pattern: /^pytest\b/, redirect: 'invar_guard' },
  { pattern: /^python\s+-m\s+pytest\b/, redirect: 'invar_guard' },
  { pattern: /^crosshair\b/, redirect: 'invar_guard' },
  { pattern: /^python\s+-m\s+crosshair\b/, redirect: 'invar_guard' },
];

// Escape hatches
const escapes = [
  /invar_guard/,           // Using invar is fine
  /--collect-only/,        // pytest discovery
  /--fixtures/,            // pytest fixtures list
];

// Check escapes first
for (const escape of escapes) {
  if (escape.test(command)) {
    console.log(JSON.stringify({ decision: "allow" }));
    process.exit(0);
  }
}

// Check blocks
for (const { pattern, redirect } of blocked) {
  if (pattern.test(command)) {
    console.log(JSON.stringify({
      decision: "block",
      message: `⛔ Blocked: Use ${redirect} MCP tool instead.\n` +
               `Invar provides smart verification with contracts.`
    }));
    process.exit(0);
  }
}

console.log(JSON.stringify({ decision: "allow" }));
```

### Auto-Format Hook

Run formatting after AI edits:

```javascript
// .cursor/hooks/post-edit.js
const fs = require('fs');
const { execSync } = require('child_process');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));

if (input.filePath && input.filePath.endsWith('.py')) {
  try {
    execSync(`ruff format "${input.filePath}"`, { stdio: 'inherit' });
    execSync(`ruff check --fix "${input.filePath}"`, { stdio: 'inherit' });
  } catch (e) {
    // Formatting failed, continue anyway
  }
}

console.log(JSON.stringify({ decision: "continue" }));
```

---

## Complete Setup

### Directory Structure

```
your-project/
├── .cursorrules           # Simple rules (or use .cursor/rules/)
├── .cursor/
│   ├── rules/
│   │   ├── invar-core.mdc
│   │   ├── invar-shell.mdc
│   │   └── invar-workflow.mdc
│   └── hooks.json         # Hook configuration
├── src/
│   └── your_package/
│       ├── core/          # Pure logic
│       └── shell/         # I/O operations
└── .invar/
    ├── context.md         # Project state
    └── examples/          # Pattern examples
```

### Full hooks.json

```json
{
  "hooks": {
    "beforeShellExecution": {
      "command": "node",
      "args": [".cursor/hooks/check-command.js"],
      "timeout": 5000
    },
    "afterFileEdit": {
      "command": "node",
      "args": [".cursor/hooks/post-edit.js"],
      "timeout": 10000
    }
  }
}
```

---

## Troubleshooting

### MCP Tools Not Working

1. Check Cursor MCP settings
2. Verify installation: `pip show invar-tools`
3. Test directly: `uvx invar-tools mcp`

### Hooks Not Triggering

1. Ensure Cursor version is 1.7+
2. Check `.cursor/hooks.json` syntax
3. Verify hook scripts are executable
4. Check Cursor console for errors

### Rules Not Applied

1. Use `.cursor/rules/*.mdc` format (recommended)
2. Check `globs` patterns match your files
3. Verify `alwaysApply` setting

### Agent Uses pytest Anyway

1. Enable hooks for blocking
2. Add explicit instruction in rules
3. Start prompts with "Following Invar rules..."

---

## Tips

1. **Use MDC rules** - More organized than single .cursorrules
2. **Enable hooks** - Best experience with command blocking
3. **Be explicit** - "Run invar_guard" not "run tests"
4. **Glob patterns** - Target rules to specific directories

---

## Next Steps

- [Multi-Agent Overview](./multi-agent.md)
- [Cline Integration](./cline.md)
- [Aider Integration](./aider.md)
