# Invar

[![PyPI version](https://badge.fury.io/py/invar-tools.svg)](https://badge.fury.io/py/invar-tools)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0%20%2B%20GPL--3.0-blue.svg)](#license)

> **Don't hope AI code is correct. Know it.**

Invar is a verification framework for AI-assisted development. It provides contracts, verification, and a structured workflow methodology.

```python
from invar_runtime import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def average(items: list[float]) -> float:
    """
    >>> average([1, 2, 3])
    2.0
    """
    return sum(items) / len(items)
```

---

## Experience Tiers

| Platform | Experience | Features |
|----------|------------|----------|
| **Claude Code** | Full | USBV workflow + skill automation + MCP integration |
| **Cursor/Windsurf** | Basic | INVAR.md protocol + CLI verification |
| **Other editors** | Minimal | CLI verification tools only |

**Why tiers?** The skill system (`/develop`, `/review`, etc.) requires Claude Code's sub-agent capabilities. Other editors receive the protocol document and CLI tools.

---

## Installation

### Two Packages, Different Purposes

```
┌─────────────────────────────────────────────────────────────────┐
│  Your Project                                                   │
│  ├── src/                                                       │
│  │   └── from invar_runtime import pre, post  ← Runtime        │
│  │                                                              │
│  └── Development (not shipped with your code)                   │
│      └── uvx invar-tools guard  ← Tools                         │
└─────────────────────────────────────────────────────────────────┘
```

| Package | Install | Purpose |
|---------|---------|---------|
| **invar-tools** | `uvx invar-tools <cmd>` | Development: verification, init, MCP server |
| **invar-runtime** | `pip install invar-runtime` | Production: add to your project's dependencies |

### Quick Install

```bash
# Development tools (recommended: use without installing)
uvx invar-tools guard
uvx invar-tools init --claude

# Runtime contracts (add to your project)
pip install invar-runtime
```

---

## Quick Start

```bash
# 1. Initialize your project
cd your-project
uvx invar-tools init --claude    # Full experience (Claude Code)
uvx invar-tools init             # Basic experience (other editors)

# 2. Write code with AI (AI follows INVAR.md protocol)

# 3. Verify code quality
uvx invar-tools guard            # Runs static analysis + doctests + property tests
```

---

## The USBV Workflow

AI agents follow a four-phase development cycle:

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│ Understand│ → │  Specify  │ → │   Build   │ → │ Validate  │
│           │    │           │    │           │    │           │
│ Intent    │    │ @pre/@post│    │ Implement │    │ invar     │
│ Inspect   │    │ Doctests  │    │ leaves    │    │ guard     │
│ Constraints    │ Design    │    │ first     │    │           │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
```

**Key insight:** Specify contracts BEFORE implementation. The contract becomes the specification.

See [INVAR.md](./INVAR.md) for complete protocol.

---

## Session Protocol

Every AI session follows this format:

**First message (Check-In):**
```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

**Last message (Final):**
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

These markers ensure the AI verifies code at session boundaries.

---

## Core/Shell Architecture

Invar enforces separation between pure logic and I/O:

| Zone | Requirements | Forbidden |
|------|--------------|-----------|
| **Core** (`**/core/**`) | `@pre`/`@post` contracts, doctests | I/O imports (os, pathlib, requests...) |
| **Shell** (`**/shell/**`) | `Result[T, E]` returns | - |

```python
# Core: Pure logic, receives data
def parse_config(content: str) -> Config:
    return Config.parse(content)

# Shell: Handles I/O, returns Result
def load_config(path: Path) -> Result[Config, str]:
    content = path.read_text()
    return Success(parse_config(content))
```

---

## Commands

### Guard (Primary)

```bash
invar guard              # Full verification (static + doctests + property tests)
invar guard --changed    # Only git-modified files
invar guard --static     # Static analysis only (~0.5s)
```

**Flags:**

| Flag | Purpose |
|------|---------|
| `--strict` | Treat warnings as errors |
| `--explain` | Show rule explanations |
| `--agent` | JSON output for AI tools |

### Other Commands

```bash
invar sig <file>         # Show signatures + contracts
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules
invar update             # Update managed files
```

---

## Workflow Skills (Claude Code)

`invar init --claude` creates workflow skills in `.claude/skills/`:

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `/investigate` | "why", "explain", vague tasks | Exploration, no code changes |
| `/propose` | "should we", "compare" | Decision facilitation with options |
| `/develop` | "add", "fix", "implement" | USBV implementation workflow |
| `/review` | After develop, `review_suggested` | Adversarial review with fix loop |

**Note:** Skills are Claude Code exclusive. Other editors use INVAR.md protocol directly.

---

## Configuration

### pyproject.toml

```toml
[tool.invar.guard]
# Directory classification
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]

# Or use patterns for existing projects
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**"]

# Size limits
max_file_lines = 500
max_function_lines = 50

# Contract requirements
require_contracts = true
require_doctests = true

# Doctest-heavy code
exclude_doctest_lines = true

# Rule exclusions
[[tool.invar.guard.rule_exclusions]]
pattern = "**/generated/**"
rules = ["*"]
```

---

## Rules Reference

| Rule | Severity | What It Checks |
|------|----------|----------------|
| `file_size` | ERROR | File > max lines |
| `function_size` | WARN | Function > max lines |
| `missing_contract` | ERROR | Core function lacks @pre/@post |
| `missing_doctest` | WARN | Contracted function lacks doctest |
| `forbidden_import` | ERROR | I/O import in Core |
| `shell_result` | WARN | Shell function not returning Result |
| `empty_contract` | ERROR | Contract is `lambda: True` |

Full list: `invar rules --explain`

---

## MCP Integration (Claude Code)

`invar init --claude` automatically configures MCP:

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

**MCP Tools:**

| Tool | Replaces | Purpose |
|------|----------|---------|
| `invar_guard` | `pytest`, `crosshair` | Smart verification |
| `invar_sig` | Reading entire files | Show contracts and signatures |
| `invar_map` | `grep` for functions | Symbol map with reference counts |

---

## Platform Support

| Feature | Claude Code | Cursor/Windsurf | Others |
|---------|-------------|-----------------|--------|
| Smart Guard CLI | ✅ | ✅ | ✅ |
| INVAR.md protocol | ✅ | ✅ | ✅ |
| MCP integration | ✅ | ❌ | ❌ |
| Workflow skills | ✅ | ❌ | ❌ |
| Sub-agent review | ✅ | ❌ | ❌ |

**Claude Code** provides the full experience with automated workflow and independent review.

**Other editors** receive the protocol and CLI tools. Workflow adherence is manual.

---

## File Ownership

| File | Owner | Edit? |
|------|-------|-------|
| `INVAR.md` | Invar | No (`invar update` manages) |
| `CLAUDE.md` | You | Yes (project config) |
| `.claude/skills/` | You | Yes (customize workflows) |

---

## Runtime Behavior

Contracts are checked at runtime via [deal](https://github.com/life4/deal).

```bash
# Disable in production for performance
DEAL_DISABLE=1 python app.py
```

---

## Learn More

**In your project** (created by `invar init`):
- `INVAR.md` — Protocol v5.0 for AI agents
- `CLAUDE.md` — Project configuration
- `.invar/examples/` — Reference patterns

**Documentation:**
- [docs/vision.md](./docs/vision.md) — Design philosophy
- [docs/design.md](./docs/design.md) — Technical architecture
- [GitHub Pages](https://tefx.github.io/Invar/) — Visual overview

---

## License

| Component | License | Purpose |
|-----------|---------|---------|
| **invar-runtime** | [Apache-2.0](LICENSE) | Runtime contracts - use freely |
| **invar-tools** | [GPL-3.0](LICENSE-GPL) | CLI tools - improvements shared |
| **Documentation** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) | Share with attribution |

See [NOTICE](NOTICE) for third-party licenses.
