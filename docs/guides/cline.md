# Invar + Cline Integration Guide

[Cline](https://cline.bot/) is an open-source VS Code extension for autonomous coding. This guide shows how to use Invar's verification and workflow with Cline.

## Quick Start

### 1. Install Invar

```bash
pip install invar-tools
```

### 2. Create `.clinerules`

Create `.clinerules` in your project root:

```markdown
# Invar Development Protocol

## Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | Use invar_guard MCP tool — NOT pytest, NOT crosshair |
| **Core** | @pre/@post + doctests, NO I/O imports |
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
- Design decomposition for complex tasks

### 3. BUILD
- Follow the contracts from SPECIFY
- Run invar_guard frequently
- Commit after each logical unit

### 4. VALIDATE
- Run invar_guard (full verification)
- Ensure all requirements met

## Verification

ALWAYS use the invar_guard MCP tool instead of pytest:

```
# Good - Use MCP tool
invar_guard(changed=true)

# Bad - Don't run directly
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

## Plan Mode Mapping

Cline's Plan Mode maps to USBV:

| Cline Mode | USBV Phase |
|------------|------------|
| Plan Mode | UNDERSTAND + SPECIFY |
| Act Mode | BUILD + VALIDATE |

Use Plan Mode for exploration, Act Mode for implementation.
```

### 3. Configure MCP

In VS Code, open Cline settings and add MCP server:

**Option A: Using uvx (recommended)**

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

### 4. Verify Setup

Ask Cline to run verification:

```
Please run invar_guard to verify the code
```

Cline should use the MCP tool and show results.

---

## Feature Mapping

### What Works

| Invar Feature | Cline Support |
|---------------|---------------|
| USBV Workflow | ✅ Via .clinerules |
| Guard Verification | ✅ Via MCP |
| Sig/Map Tools | ✅ Via MCP |
| Core/Shell Rules | ✅ Via .clinerules |
| Context Files | ✅ Agent can read |

### What's Different

| Claude Code | Cline Alternative |
|-------------|-------------------|
| Skills (auto-routing) | Manual workflow or Custom Roles |
| Hooks (pytest block) | Not available - rely on instructions |
| /audit, /guard commands | Direct MCP tool calls |
| Check-In/Final | Include in .clinerules |

### Not Available

- Automatic pytest/crosshair blocking (no hooks)
- Skill-based auto-routing
- Command shortcuts

---

## Plan Mode + USBV

Cline's Plan & Act mode aligns well with USBV:

```
┌─────────────────────────────────────────────┐
│  Plan Mode (Read-Only)                      │
│  ├── UNDERSTAND: Explore codebase           │
│  └── SPECIFY: Design contracts              │
├─────────────────────────────────────────────┤
│  Act Mode (Execute)                         │
│  ├── BUILD: Implement following contracts   │
│  └── VALIDATE: Run invar_guard              │
└─────────────────────────────────────────────┘
```

### Workflow Example

1. **Enter Plan Mode**
   - "Analyze the authentication module"
   - Cline explores without making changes

2. **Design in Plan Mode**
   - "Design contracts for a new login function"
   - Cline proposes @pre/@post without implementing

3. **Switch to Act Mode**
   - "Implement the login function"
   - Cline writes code following contracts

4. **Validate**
   - "Run invar_guard to verify"
   - Cline uses MCP tool

---

## Custom Roles

Create specialized roles for Invar workflow:

### Invar Developer Role

```
You are an Invar-compliant developer. You:
1. Always write @pre/@post contracts before implementation
2. Use invar_guard for verification, never pytest directly
3. Follow Core (pure) / Shell (I/O) separation
4. Include doctests for all public functions
```

### Invar Reviewer Role

```
You are an adversarial code reviewer. You:
1. Challenge whether contracts have semantic value
2. Find bugs, logic errors, edge cases
3. Question every escape hatch
4. Check if code matches contracts
```

---

## Complete .clinerules Template

```markdown
# Invar Development Protocol

## Quick Reference

| Zone | Requirements |
|------|-------------|
| Core | @pre/@post + doctests, pure (no I/O) |
| Shell | Returns Result[T, E] from returns library |

## Workflow: USBV

1. **UNDERSTAND** - What needs to be done? Read existing code.
2. **SPECIFY** - Write contracts FIRST (@pre/@post, doctests)
3. **BUILD** - Implement following contracts
4. **VALIDATE** - Run invar_guard, ensure all passes

## Verification Commands

Use MCP tools:
- `invar_guard(changed=true)` - Verify changed files
- `invar_guard()` - Full verification
- `invar_sig(target="file.py")` - Show signatures
- `invar_map()` - Show symbol map

## Code Patterns

### Core Function (Pure)

```python
from invar_runtime import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: result is not None)
def first_item(items: list[str]) -> str:
    """
    >>> first_item(["a", "b"])
    'a'
    """
    return items[0]
```

### Shell Function (I/O)

```python
from returns.result import Result, Success, Failure

def read_config(path: str) -> Result[Config, str]:
    """Read configuration from file."""
    try:
        data = Path(path).read_text()
        return Success(parse_config(data))
    except Exception as e:
        return Failure(f"Failed to read {path}: {e}")
```

## Plan Mode Usage

- Use Plan Mode for UNDERSTAND and SPECIFY phases
- Use Act Mode for BUILD and VALIDATE phases
- Always verify with invar_guard before completing

## Don'ts

- Don't use pytest directly (use invar_guard)
- Don't put I/O in core/ directory
- Don't skip contracts on public functions
- Don't use bare exceptions in shell code
```

---

## Troubleshooting

### MCP Tools Not Available

1. Check Cline MCP configuration
2. Verify invar-tools is installed: `pip show invar-tools`
3. Test MCP server: `uvx invar-tools mcp`

### Cline Ignores .clinerules

1. Ensure file is in project root
2. Check file name is exactly `.clinerules`
3. Restart VS Code / Cline extension

### Cline Uses pytest Instead of Guard

Add explicit instruction to .clinerules:

```markdown
## IMPORTANT

NEVER run pytest or crosshair directly.
ALWAYS use the invar_guard MCP tool for verification.
```

### Guard Reports Missing Dependencies

```bash
# Ensure project dependencies are available
pip install -e ".[dev]"

# Or configure PYTHONPATH
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
```

---

## Tips

1. **Use Plan Mode liberally** - It's perfect for UNDERSTAND/SPECIFY
2. **Be explicit about verification** - Ask "run invar_guard" not "test"
3. **Reference the rules** - "Following .clinerules, implement..."
4. **Check MCP first** - Ensure tools work before starting

---

## Next Steps

- [Multi-Agent Overview](./multi-agent.md)
- [Cursor Integration](./cursor.md)
- [Aider Integration](./aider.md)
