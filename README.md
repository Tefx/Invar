# Invar

[![PyPI version](https://badge.fury.io/py/python-invar.svg)](https://badge.fury.io/py/python-invar)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Don't hope AI code is correct. Know it.**

Invar is a framework that helps developers ensure AI-generated code is reliable through contracts, verification, and mechanical checks.

```python
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

## Installation

```bash
pip install python-invar              # Basic (static + doctests)
pip install python-invar[prove]       # + CrossHair symbolic verification
```

---

## Quick Start

```bash
cd your-project
invar init          # Creates INVAR.md, CLAUDE.md, .invar/
invar guard         # Verify code quality
```

**Multi-Agent Support:** `invar init` auto-detects and configures:

| AI Tool | Configuration |
|---------|---------------|
| Claude Code | Creates CLAUDE.md + MCP server |
| Cursor | Adds to .cursorrules |
| Aider | Adds to .aider.conf.yml |
| Others | Add "Follow INVAR.md" to system prompt |

---

## MCP Integration (Claude Code)

For deeper integration with Claude Code, install MCP support:

`invar init` automatically configures `.claude/settings.json`:

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["--from", "python-invar[mcp]", "invar-mcp"]
    }
  }
}
```

> **Note:** If `uv` is not installed, `invar init` will use the Python path instead.

**MCP Tools:**

| Tool | Replaces | Purpose |
|------|----------|---------|
| `invar_guard` | `pytest`, `crosshair` | Smart Guard verification |
| `invar_sig` | Reading entire file | Show contracts and signatures |
| `invar_map` | `grep` for functions | Symbol map with reference counts |

Manual setup: See `.invar/mcp-setup.md` after running `invar init`.

---

## Commands

### Guard (Primary)

```bash
invar guard              # Static + doctests (default)
invar guard --changed    # Only git-modified files
invar guard --static     # Static only (skip doctests)
invar guard --prove      # + CrossHair verification
```

**Flags:**

| Flag | Purpose |
|------|---------|
| `--strict` | Treat warnings as errors |
| `--explain` | Show rule limitations |
| `--agent` | JSON output for AI tools |
| `--pedantic` | Show all rules including off-by-default |

### Other Commands

```bash
invar sig <file>         # Show signatures + contracts
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules
invar test <file>        # Property-based testing (Hypothesis)
invar test --changed     # Test git-modified files
invar verify <file>      # Symbolic verification (CrossHair)
invar verify --changed   # Verify git-modified files
invar update             # Update managed files
```

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

# Purity overrides
purity_pure = ["pandas.DataFrame.groupby"]
purity_impure = ["my_module.cached_lookup"]

# Rule exclusions
[[tool.invar.guard.rule_exclusions]]
pattern = "**/generated/**"
rules = ["*"]

# Severity overrides
[tool.invar.guard.severity_overrides]
redundant_type_contract = "off"
```

---

## Verification Levels

| Level | Command | Checks | When to Use |
|-------|---------|--------|-------------|
| STATIC | `--static` | Rules only | Debugging static analysis |
| STANDARD | (default) | Rules + doctests | Normal development |
| PROVE | `--prove` | + CrossHair | Pre-commit, CI (automatic) |

Pre-commit uses `--prove` by default. Incremental mode makes it fast (~5s first, ~2s cached).

---

## File Ownership

| File | Owner | Edit? |
|------|-------|-------|
| `INVAR.md` | Invar | No (`invar update` manages) |
| `CLAUDE.md` | You | Yes (project config) |
| `.invar/examples/` | Invar | No (reference only) |

---

## Core/Shell Architecture

Invar enforces separation between pure logic and I/O:

| Zone | Requirements | Forbidden |
|------|--------------|-----------|
| **Core** | `@pre`/`@post` contracts, doctests | I/O imports (os, pathlib, requests...) |
| **Shell** | `Result[T, E]` returns | - |

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
| `param_mismatch` | ERROR | Lambda params ≠ function params |

Full list: `invar rules --explain`

---

## Runtime Behavior

Contracts are checked at runtime via [deal](https://github.com/life4/deal).

```bash
# Disable in production
DEAL_DISABLE=1 python app.py
```

---

## Troubleshooting

**Guard is slow:**
- Use `--changed` for incremental checks
- Use `--static` to skip doctests during debugging

**Too many warnings:**
- Add exclusions for generated code
- Override severity for noisy rules

**CrossHair timeout:**
- Some code patterns don't work well with symbolic execution
- Hypothesis fallback runs automatically

---

## Learn More

**In your project** (created by `invar init`):
- `INVAR.md` — Protocol for AI agents
- `CLAUDE.md` — Project configuration
- `.invar/examples/` — Reference patterns

**Documentation:**
- [docs/INVAR-GUIDE.md](./docs/INVAR-GUIDE.md) — Detailed guide
- [docs/VISION.md](./docs/VISION.md) — Design philosophy

---

## License

MIT
