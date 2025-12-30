<p align="center">
  <img src="docs/logo.svg" alt="Invar Logo" width="128" height="128">
</p>

<h1 align="center">Invar</h1>

<p align="center">
  <strong>From AI-generated to AI-engineered code.</strong>
</p>

<p align="center">
Invar brings decades of software engineering best practices to AI-assisted development.<br>
Through automated verification, structured workflows, and proven design patterns,<br>
agents write code that's correct by construction—not by accident.
</p>

<p align="center">
  <a href="https://badge.fury.io/py/invar-tools"><img src="https://badge.fury.io/py/invar-tools.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-Apache%202.0%20%2B%20GPL--3.0-blue.svg" alt="License"></a>
</p>

<p align="center">
  <a href="#why-invar"><img src="https://img.shields.io/badge/🤖_Dogfooding-Invar's_code_is_100%25_AI--generated_and_AI--verified_using_itself-8A2BE2?style=for-the-badge" alt="Dogfooding"></a>
</p>

### What It Looks Like

An AI agent, guided by Invar, writes code with formal contracts and built-in tests:

```python
from invar_runtime import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def average(items: list[float]) -> float:
    """
    Calculate the average of a non-empty list.

    >>> average([1.0, 2.0, 3.0])
    2.0
    >>> average([10.0])
    10.0
    """
    return sum(items) / len(items)
```

Invar's Guard automatically verifies the code—the agent sees results and fixes issues without human intervention:

```
$ invar guard
Invar Guard Report
========================================
No violations found.
----------------------------------------
Files checked: 1 | Errors: 0 | Warnings: 0
Contract coverage: 100% (1/1 functions)

Code Health: 100% ████████████████████ (Excellent)
✓ Doctests passed
✓ CrossHair: no counterexamples found
✓ Hypothesis: property tests passed
----------------------------------------
Guard passed.
```

---

## 🚀 Quick Start

### 📦 Two Packages, Different Purposes

```
┌───────────────────────────────────────────────────────────────────┐
│  Your Project                                                     │
│  ├── pyproject.toml                                               │
│  │   └── dependencies = ["invar-runtime"]  ← Ships with code      │
│  │                                                                │
│  └── Development (never enters production)                        │
│      └── uvx invar-tools guard  ← Guides agents                   │
└───────────────────────────────────────────────────────────────────┘
```

| Package | Purpose | Install |
|---------|---------|---------|
| **invar-runtime** | Runtime contracts. Add to your project dependencies. | `pip install invar-runtime` |
| **invar-tools** | Development tools. Guides agents during development. | `uvx invar-tools <cmd>` |

**Why uvx?** Always uses latest version, doesn't pollute project dependencies, auto-detects your project's venv.

### 🎯 Setup

```bash
cd your-project

# Interactive mode - choose what to install
uvx invar-tools init

# Or quick setup for Claude Code (skip prompts)
uvx invar-tools init --claude

# Add runtime contracts to your project
pip install invar-runtime
```

**Safe and idempotent** — Run `invar init` anytime. It always **merges** with existing files, preserving your content.

> 💡 **After `claude /init`?** Just run `invar init` again to restore Invar configuration.

### 💬 Example Interaction

**You say:**
> "Add a function that calculates compound interest with validation"

**Agent responds (automatically guided by Invar):**

```
✓ Check-In: my-project | main | clean

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First, I'll define the contract:

@pre(lambda principal, rate, years: principal > 0 and rate >= 0 and years > 0)
@post(lambda result: result >= principal)
def compound_interest(principal: float, rate: float, years: int) -> float:
    ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → VALIDATE (4/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$ invar guard --changed
WARN: missing doctest example (compound_interest)

[Agent adds doctest, re-runs guard]

$ invar guard --changed
Guard passed. (1 file, 0 errors)

✓ Final: guard PASS | 0 errors, 0 warnings
```

**Key insight:** The agent verifies and fixes automatically. You review the result, not the process.

---

## Why Invar?

### ⚠️ The Problem: Unconstrained AI = Unpredictable Quality

Without guardrails, AI-generated code has systematic risks:
- **No specification** → Agent guesses intent, misses edge cases
- **No feedback loop** → Errors accumulate undetected
- **No workflow** → Jumps to implementation, skips validation
- **No separation** → I/O mixed with logic, code becomes untestable

Invar addresses each from the ground up.

### ✅ Solution 1: Contracts as Specification

Contracts (`@pre`/`@post`) turn vague intent into verifiable specifications:

```python
# Without contracts: "calculate average" is ambiguous
def average(items):
    return sum(items) / len(items)  # What if empty? What's the return type?

# With contracts: specification is explicit and verifiable
@pre(lambda items: len(items) > 0)      # Precondition: non-empty input
@post(lambda result: result >= 0)        # Postcondition: non-negative output
def average(items: list[float]) -> float:
    """
    >>> average([1.0, 2.0, 3.0])
    2.0
    """
    return sum(items) / len(items)
```

**Benefits:**
- Agent knows exactly what to implement
- Edge cases are explicit in the contract
- Verification is automatic, not manual review

### ✅ Solution 2: Multi-Layer Verification

Guard provides fast feedback. Agent sees errors, fixes immediately:

| Layer | Tool | Speed | What It Catches |
|-------|------|-------|-----------------|
| **Static** | Guard rules | ~0.5s | Architecture violations, missing contracts |
| **Doctest** | pytest | ~2s | Example correctness |
| **Property** | Hypothesis | ~10s | Edge cases via random inputs |
| **Symbolic** | CrossHair | ~30s | Mathematical proof of contracts |

```
┌──────────┐   ┌───────────┐   ┌───────────┐   ┌────────────┐
│ ⚡ Static │ → │ 🧪 Doctest│ → │ 🎲 Property│ → │ 🔬 Symbolic│
│   ~0.5s  │   │   ~2s     │   │   ~10s    │   │   ~30s     │
└──────────┘   └───────────┘   └───────────┘   └────────────┘
```

```
Agent writes code
       ↓
   invar guard  ←──────┐
       ↓               │
   Error found?        │
       ↓ Yes           │
   Agent fixes ────────┘
       ↓ No
   Done ✓
```

### ✅ Solution 3: Workflow Discipline

The USBV workflow forces "specify before implement":

```
🔍 Understand  →  📝 Specify  →  🔨 Build  →  ✓ Validate
      │              │              │            │
   Context        Contracts        Code        Guard
```

Skill routing ensures agents enter through the correct workflow:

| User Intent | Skill Invoked | Behavior |
|-------------|---------------|----------|
| "why does X fail?" | `/investigate` | Research only, no code changes |
| "should we use A or B?" | `/propose` | Present options with trade-offs |
| "add feature X" | `/develop` | Full USBV workflow |
| (after develop) | `/review` | Adversarial review with fix loop |

### ✅ Solution 4: Architecture Constraints

| Pattern | Enforcement | Benefit |
|---------|-------------|---------|
| **Core/Shell** | Guard blocks I/O imports in Core | 100% testable business logic |
| **Result[T, E]** | Guard warns if Shell returns bare values | Explicit error handling |

### 🔮 Future: Quality Guidance (DX-61)

Beyond "correct or not"—Invar will suggest improvements:

```
SUGGEST: 3 string parameters in 'find_symbol'
  → Consider NewType for semantic clarity
```

From gatekeeper to mentor.

---

## 🏗️ Core Concepts

### Core/Shell Architecture

Separate pure logic from I/O for maximum testability:

| Zone | Location | Requirements |
|------|----------|--------------|
| **Core** | `**/core/**` | `@pre`/`@post` contracts, doctests, no I/O imports |
| **Shell** | `**/shell/**` | `Result[T, E]` return types |

```
┌─────────────────────────────────────────────┐
│  🐚 Shell (I/O Layer)                       │
│  load_config, save_result, fetch_data       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  💎 Core (Pure Logic)                       │
│  parse_config, validate, calculate          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼ Result[T, E]
```

```python
# Core: Pure, testable, provable
def parse_config(content: str) -> Config:
    return Config.parse(content)

# Shell: Handles I/O, returns Result
def load_config(path: Path) -> Result[Config, str]:
    try:
        return Success(parse_config(path.read_text()))
    except FileNotFoundError:
        return Failure(f"Not found: {path}")
```

### Session Protocol

Clear boundaries for every AI session:

| Phase | Format | Purpose |
|-------|--------|---------|
| **Start** | `✓ Check-In: project \| branch \| status` | Context visibility |
| **End** | `✓ Final: guard PASS \| 0 errors` | Verification proof |

### Intellectual Heritage

**Foundational Theory:**
Design-by-Contract (Meyer, 1986) ·
Functional Core/Imperative Shell (Bernhardt) ·
Property-Based Testing (QuickCheck, 2000) ·
Symbolic Execution (King, 1976)

**Inspired By:**
Eiffel · Dafny · Idris · Haskell

**AI Programming Research:**
AlphaCodium · Parsel · Reflexion · Clover

**Dependencies:**
[deal](https://github.com/life4/deal) ·
[returns](https://github.com/dry-python/returns) ·
[CrossHair](https://github.com/pschanely/CrossHair) ·
[Hypothesis](https://hypothesis.readthedocs.io/)

---

## 🖥️ Agent Support

| Agent | Status | Setup |
|-------|--------|-------|
| **Claude Code** | ✅ Full | `invar init` → select Claude Code |
| **Pi / Cursor** | 🚧 In progress | `invar init` → select Other, include `AGENT.md` in prompt |
| **Other** | 📝 Manual | `invar init` → select Other, include `AGENT.md` in prompt |

### Claude Code (Full Experience)

All features auto-configured:
- MCP tools (`invar_guard`, `invar_sig`, `invar_map`)
- Workflow skills (`/develop`, `/review`, `/investigate`, `/propose`)
- Claude Code hooks (tool guidance, verification reminders)
- Pre-commit hooks

### Pi / Cursor (In Progress)

Currently available:
- Protocol document (INVAR.md)
- CLI verification (`invar guard`)
- Pre-commit hooks
- MCP server (manual configuration)

### Other Editors (Manual)

1. Run `invar init` → select "Other (AGENT.md)"
2. Include generated `AGENT.md` in your agent's prompt
3. Configure MCP server if supported
4. Use CLI commands (`invar guard`) for verification

---

## 📂 What Gets Installed

`invar init` creates (select in interactive mode):

| File/Directory | Purpose | Category |
|----------------|---------|----------|
| `INVAR.md` | Protocol for AI agents | Required |
| `.invar/` | Config, context, examples | Required |
| `.pre-commit-config.yaml` | Verification before commit | Optional |
| `src/core/`, `src/shell/` | Recommended structure | Optional |
| `CLAUDE.md` | Agent instructions | Claude Code |
| `.claude/skills/` | Workflow automation | Claude Code |
| `.claude/commands/` | User commands (/audit, /guard) | Claude Code |
| `.claude/hooks/` | Tool guidance | Claude Code |
| `.mcp.json` | MCP server config | Claude Code |
| `AGENT.md` | Universal agent instructions | Other agents |

**Note:** If `pyproject.toml` exists, Guard configuration goes there as `[tool.invar.guard]` instead of `.invar/config.toml`.

**Recommended structure:**

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] returns)
```

---

## ⚙️ Configuration

```toml
# pyproject.toml

[tool.invar.guard]
# Option 1: Explicit paths
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]

# Option 2: Pattern matching (for existing projects)
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**"]

# Option 3: Auto-detection (when no paths/patterns specified)
# - Default paths: src/core, core, src/shell, shell
# - Content analysis: @pre/@post → Core, Result → Shell

# Size limits
max_file_lines = 500
max_function_lines = 50

# Requirements
require_contracts = true
require_doctests = true
```

### 🚪 Escape Hatches

For code that intentionally breaks rules:

```toml
# Exclude entire directories
[[tool.invar.guard.rule_exclusions]]
pattern = "**/generated/**"
rules = ["*"]

# Exclude specific rules for specific files
[[tool.invar.guard.rule_exclusions]]
pattern = "**/legacy_api.py"
rules = ["missing_contract", "shell_result"]
```

---

## 🔧 Tool Reference

### CLI Commands

| Command | Purpose |
|---------|---------|
| `invar guard` | Full verification (static + doctest + property + symbolic) |
| `invar guard --changed` | Only git-modified files |
| `invar guard --static` | Static analysis only (~0.5s) |
| `invar init` | Initialize or update project (interactive) |
| `invar init --claude` | Quick setup for Claude Code |
| `invar uninstall` | Remove Invar from project (preserves user content) |
| `invar sig <file>` | Show signatures and contracts |
| `invar map` | Symbol map with reference counts |
| `invar rules` | List all rules |
| `invar test` | Property-based tests (Hypothesis) |
| `invar verify` | Symbolic verification (CrossHair) |
| `invar hooks` | Manage Claude Code hooks |

### MCP Tools

| Tool | Purpose |
|------|---------|
| `invar_guard` | Smart multi-layer verification |
| `invar_sig` | Extract signatures and contracts |
| `invar_map` | Symbol map with reference counts |

---

## 📚 Learn More

**Created by `invar init`:**
- `INVAR.md` — Protocol v5.0
- `.invar/examples/` — Reference patterns

**Documentation:**
- [Vision & Philosophy](./docs/vision.md)
- [Technical Design](./docs/design.md)

---

## 📄 License

| Component | License | Notes |
|-----------|---------|-------|
| **invar-runtime** | [Apache-2.0](LICENSE) | Use freely in any project |
| **invar-tools** | [GPL-3.0](LICENSE-GPL) | Improvements must be shared |
| **Documentation** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) | Share with attribution |

See [NOTICE](NOTICE) for third-party licenses.
