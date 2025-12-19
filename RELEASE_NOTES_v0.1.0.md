# Invar v0.1.0 - Initial Release

**AI-native software engineering framework with design-by-contract**

## Installation

```bash
pip install python-invar
```

## What is Invar?

Invar provides structure for AI-assisted development by enforcing:

- **Core/Shell Architecture** - Separate pure logic from I/O operations
- **Design-by-Contract** - `@pre`/`@post` contracts on Core functions
- **Size Limits** - Files < 500 lines, Functions < 50 lines
- **Purity Checks** - No I/O imports or impure calls in Core

## Quick Start

```bash
# Initialize in your project
invar init

# Check architecture rules
invar guard

# Only check modified files
invar guard --changed

# Get detailed explanations
invar guard --explain
```

## Commands

| Command | Description |
|---------|-------------|
| `invar guard` | Check project against architecture rules |
| `invar guard --changed` | Check only git-modified files |
| `invar guard --explain` | Show detailed rule explanations |
| `invar guard --agent` | JSON output for AI agents |
| `invar init` | Initialize Invar in a project |
| `invar map` | Generate symbol map with reference counts |
| `invar sig <file>` | Extract signatures from a file |
| `invar rules` | List all rules with metadata |

## Features

### Agent-Native Design

Invar is built for AI coding agents, not just humans:

- **Always-on hints** - Every violation includes actionable guidance
- **Lambda skeletons** - Contract templates with correct parameter names
- **INSPECT section** - Shows file context in `--changed` mode
- **JSON output** - `--agent` mode for machine-parseable results
- **INVAR_MODE=agent** - Auto-detect agent context

### Guard Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `file_size` | ERROR | File exceeds 500 lines |
| `function_size` | WARNING | Function exceeds 50 lines |
| `missing_contract` | WARNING | Core function without `@pre`/`@post` |
| `empty_contract` | WARNING | Contract is always true (`lambda: True`) |
| `param_mismatch` | ERROR | `@pre` lambda params ≠ function params |
| `forbidden_import` | ERROR | I/O imports in Core |
| `shell_result` | WARNING | Shell function not returning `Result[T, E]` |

### Configuration

```toml
# pyproject.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
max_file_lines = 500
max_function_lines = 50
strict_pure = true
```

## Requirements

- Python 3.11+
- Dependencies: typer, rich, pydantic, deal, returns

## Documentation

- [INVAR.md](./INVAR.md) - Protocol for AI agents (90 lines, compressed)
- [docs/VISION.md](./docs/VISION.md) - Design philosophy
- [docs/DESIGN.md](./docs/DESIGN.md) - Technical architecture

## License

MIT

---

*"Trade structure for safety."* - The Invar Protocol v3.17
