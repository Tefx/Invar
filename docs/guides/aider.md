# Invar + Aider Integration Guide

[Aider](https://aider.chat/) is a terminal-based AI pair programmer with Git-aware editing. Its built-in auto-lint feature makes it uniquely suited for Invar integration.

## Quick Start

### 1. Install Both Tools

```bash
# Install Aider
pip install aider-chat

# Install Invar
pip install invar-tools
```

### 2. Create CONVENTIONS.md

Aider uses `CONVENTIONS.md` as persistent project memory. Create it in your project root:

```markdown
# Invar Development Conventions

## Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | Run `invar guard` for verification |
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
- Run `invar sig <file>` to see existing contracts
- Read relevant code, understand patterns

### 2. SPECIFY
- Write @pre/@post BEFORE implementation
- Add doctests for expected behavior

### 3. BUILD
- Follow the contracts from SPECIFY
- Run `invar guard --changed` frequently

### 4. VALIDATE
- Run `invar guard` (full verification)
- Ensure all requirements met

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

## Core Module Rules

Files in `core/` must:
- Be pure (no I/O operations)
- Have @pre/@post on all public functions
- Include doctests
- Not import: pathlib, os, requests, subprocess, etc.

## Shell Module Rules

Files in `shell/` must:
- Return Result[T, E] for fallible operations
- Handle errors explicitly
- Use dependency injection for testability
```

### 3. Configure Auto-Lint with Invar

This is where Aider shines! It can automatically run verification after each change:

```bash
# Run Aider with Invar verification
aider --lint-cmd "invar guard --changed" --auto-lint
```

Or add to `.aider.conf.yml`:

```yaml
# .aider.conf.yml
lint-cmd: invar guard --changed
auto-lint: true
auto-commits: true
```

Now Aider will:
1. Make code changes
2. Automatically run `invar guard --changed`
3. If verification fails, show errors to the LLM
4. LLM fixes the issues
5. Repeat until passing

---

## Configuration Options

### Basic Config (.aider.conf.yml)

```yaml
# Model settings
model: claude-sonnet-4-20250514

# Invar integration
lint-cmd: invar guard --changed
auto-lint: true

# Git integration
auto-commits: true
attribute-author: true
attribute-committer: true

# Display
dark-mode: true
show-diffs: true
```

### Full Invar Integration

```yaml
# .aider.conf.yml

# Verification
lint-cmd: invar guard --changed
auto-lint: true

# Additional checks (optional)
test-cmd: invar guard
auto-test: false  # Run manually with /test

# Conventions file
read: CONVENTIONS.md

# Git
auto-commits: true

# Performance
cache-prompts: true
```

### Environment Variables

```bash
# .env or shell
export AIDER_LINT_CMD="invar guard --changed"
export AIDER_AUTO_LINT=true
```

---

## Workflow

### Daily Usage

```bash
# Start Aider with Invar
aider --lint-cmd "invar guard --changed" --auto-lint

# Or if configured in .aider.conf.yml
aider
```

### Session Example

```
$ aider
Aider v0.x.x
Model: claude-sonnet-4-20250514
Loaded CONVENTIONS.md

> Add a function to validate email addresses in core/validation.py

# Aider writes code with @pre/@post...
# Aider runs: invar guard --changed
# If errors, Aider sees them and fixes
# If passes, Aider commits

> /lint
# Manually trigger verification

> /test
# Run full verification if configured
```

### Using Invar Tools Directly

```bash
# In Aider, prefix with !
> !invar sig src/core/validation.py
> !invar map
> !invar guard
```

---

## Feature Mapping

### What Works

| Invar Feature | Aider Support |
|---------------|---------------|
| USBV Workflow | ✅ Via CONVENTIONS.md |
| Guard Verification | ✅ Via auto-lint |
| Sig/Map Tools | ✅ Via ! commands |
| Core/Shell Rules | ✅ Via CONVENTIONS.md |
| Auto-fix on Failure | ✅ Built-in! |

### What's Different

| Claude Code | Aider Alternative |
|-------------|-------------------|
| MCP tools | CLI commands (!) |
| Skills (auto-routing) | Manual workflow |
| Hooks | auto-lint built-in |
| CLAUDE.md | CONVENTIONS.md |

### Unique Aider Advantage

**Auto-lint feedback loop:**

```
Change → Verify → Fail → Fix → Verify → Pass
         ↑                      │
         └──────────────────────┘
```

This is automatic! No manual intervention needed.

---

## Advanced Configuration

### Multiple Verification Steps

```yaml
# .aider.conf.yml
lint-cmd: |
  ruff check --fix . &&
  ruff format . &&
  invar guard --changed
auto-lint: true
```

### Conditional Verification

```bash
#!/bin/bash
# scripts/verify.sh

# Only run if Python files changed
if git diff --name-only HEAD | grep -q '\.py$'; then
    invar guard --changed
fi
```

```yaml
# .aider.conf.yml
lint-cmd: ./scripts/verify.sh
```

### Pre-commit Style

```yaml
# .aider.conf.yml
lint-cmd: |
  # Format first
  ruff format . 2>/dev/null || true
  ruff check --fix . 2>/dev/null || true
  # Then verify
  invar guard --changed
```

---

## Complete Setup

### Directory Structure

```
your-project/
├── .aider.conf.yml        # Aider configuration
├── .aiderignore           # Files to ignore
├── .env                   # API keys
├── CONVENTIONS.md         # Invar rules (Aider reads this)
├── src/
│   └── your_package/
│       ├── core/          # Pure logic
│       └── shell/         # I/O operations
└── .invar/
    ├── context.md         # Project state
    └── examples/          # Pattern examples
```

### .aiderignore

```
# Don't include in context
.venv/
__pycache__/
*.pyc
.git/
.invar/cache/
node_modules/
```

### Full CONVENTIONS.md

```markdown
# Project Development Conventions

## Invar Protocol

This project follows the Invar development protocol.

### Architecture

| Directory | Purpose | Requirements |
|-----------|---------|--------------|
| `src/*/core/` | Pure logic | @pre/@post, doctests, no I/O |
| `src/*/shell/` | I/O operations | Result[T, E] returns |

### USBV Workflow

1. **UNDERSTAND** - Analyze requirements, read existing code
2. **SPECIFY** - Write contracts (@pre/@post) before implementation
3. **BUILD** - Implement following the contracts
4. **VALIDATE** - Run `invar guard` to verify

### Code Patterns

#### Core Function

```python
from invar_runtime import pre, post

@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    Calculate square.

    >>> calculate(5)
    25
    """
    return x * x
```

#### Shell Function

```python
from returns.result import Result, Success, Failure
from pathlib import Path

def read_file(path: str) -> Result[str, str]:
    """Read file contents."""
    try:
        return Success(Path(path).read_text())
    except Exception as e:
        return Failure(f"Failed: {e}")
```

### Verification

The project uses `invar guard` for verification. This is configured
as the auto-lint command, so verification runs automatically after
each change.

To manually verify:
```bash
invar guard           # Full verification
invar guard --changed # Only changed files
invar sig <file>      # Show signatures
invar map             # Show symbol map
```

### Common Issues

1. **Missing contracts**: Add @pre/@post to public functions
2. **I/O in core**: Move file/network operations to shell/
3. **Missing Result**: Shell functions must return Result[T, E]
4. **No doctests**: Add usage examples to docstrings
```

---

## Troubleshooting

### Invar Not Found

```bash
# Install in same environment
pip install invar-tools

# Or use full path
lint-cmd: /path/to/.venv/bin/invar guard --changed
```

### Auto-lint Not Running

1. Check `.aider.conf.yml` syntax
2. Verify `auto-lint: true` is set
3. Ensure `lint-cmd` is valid
4. Test command manually: `invar guard --changed`

### Verification Too Slow

```yaml
# Only check changed files
lint-cmd: invar guard --changed

# Or skip CrossHair for speed
lint-cmd: invar guard --changed --no-prove
```

### CONVENTIONS.md Not Loaded

```bash
# Explicitly load
aider --read CONVENTIONS.md

# Or add to config
read: CONVENTIONS.md
```

---

## Tips

1. **Use auto-lint** - It's Aider's killer feature for Invar
2. **Keep CONVENTIONS.md focused** - It's loaded into context
3. **Use `!` for tools** - `!invar sig file.py` works great
4. **Trust the loop** - Let Aider fix verification failures

---

## Command Reference

| Aider Command | Purpose |
|---------------|---------|
| `/lint` | Run verification manually |
| `/test` | Run test command |
| `!invar guard` | Run guard directly |
| `!invar sig <file>` | Show signatures |
| `!invar map` | Show symbol map |
| `/read CONVENTIONS.md` | Reload conventions |

---

## Next Steps

- [Multi-Agent Overview](./multi-agent.md)
- [Cline Integration](./cline.md)
- [Cursor Integration](./cursor.md)
