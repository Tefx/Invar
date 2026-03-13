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

### Tool × Language Support

| Tool | Python | Notes |
|------|--------|-------|
| `invar guard` | ✅ Full | Static + doctest + CrossHair + Hypothesis |
| `invar sig` | ✅ Full | Signatures + contracts |
| `invar map` | ✅ Full | Symbol map + reference counts |
| `invar refs` | ✅ Full | Cross-file reference finding |
| `invar doc *` | ✅ Full | Language-agnostic docs tools |

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

# Initialize DX-91 managed files
uvx invar-tools init

# Optional: target a different instruction file
uvx invar-tools init --file AGENTS.md

# Optional: preview migration/write plan without changes
uvx invar-tools init --preview

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
Startup status: my-project | main | clean

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase: Design (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First, I'll define the contract:

@pre(lambda principal, rate, years: principal > 0 and rate >= 0 and years > 0)
@post(lambda result: result >= principal)
def compound_interest(principal: float, rate: float, years: int) -> float:
    ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase: Validate (4/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$ invar guard --changed
WARN: missing doctest example (compound_interest)

[Agent adds doctest, re-runs guard]

$ invar guard --changed
Guard passed. (1 file, 0 errors)

Final guard status: PASS | 0 errors, 0 warnings
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
# Without contracts: ambiguous
def average(items):
    return sum(items) / len(items)
    # What if empty? Return type?

# With contracts: explicit
@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
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

Guard provides fast feedback **on top of standard type checking**. Agent sees errors, fixes immediately:

| Layer | Tool | Speed | What It Catches |
|-------|------|-------|-----------------|
| **Type Check** | mypy | ~1s | Type errors, missing annotations |
| **Static** | Guard rules | ~0.5s | Architecture violations, missing contracts |
| **Doctest** | pytest | ~2s | Example correctness |
| **Property** | Hypothesis | ~10s | Edge cases via random inputs |
| **Symbolic** | CrossHair | ~30s | Mathematical proof of contracts |

<sup>* Requires separate installation: `pip install mypy`</sup>

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

Contracts before implementation — the single required rule per [DX-91](./docs/proposals/DX-91-simplification.md):

```
📝 Specify  →  🔨 Build  →  ✓ Validate
     │              │            │
 Contracts        Code        Guard
```

Guard enforces outcomes, not ceremony. The essential intent: specify with `@pre`/`@post` before implementing.

### ✅ Solution 4: Architecture Constraints

| Pattern | Enforcement | Benefit |
|---------|-------------|---------|
| **Core/Shell** | Guard blocks I/O imports in Core | 100% testable business logic |
| **Result[T, E]** | Guard warns if Shell returns bare values | Explicit error handling |

### 🔮 Future: Quality Guidance

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
| **Start** | `✓ Check-In: project | branch | clean/dirty` | Context visibility |
| **End** | `✓ Final: guard PASS | 0 errors` | Verification proof |

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
| **Claude Code** | ✅ Full | `invar init` |
| **[Pi](https://shittycodingagent.ai/)** | ✅ MCP | `invar init`, then add MCP config manually |
| **Cursor** | ✅ MCP | `invar init`, then add MCP config manually |
| **Other** | 📝 Manual | `invar init`, then include `CLAUDE.md`/`INVAR.md` in your prompt flow |

> **See also:** ~~[Multi-Agent Guide](./docs/guides/multi-agent.md)~~ — *simplified per [DX-91](./docs/proposals/DX-91-simplification.md)*. See INVAR.md for agent-agnostic protocol.

### Claude Code (Full Experience)

All features auto-configured:
- MCP tools (`invar_guard`, `invar_sig`, `invar_map`)
- ~~Workflow modes (implement, review, investigate, propose)~~ — *simplified per [DX-91](./docs/proposals/DX-91-simplification.md)*
- Pre-commit hooks

### [Pi](https://shittycodingagent.ai/) (MCP Support)

Pi can use the same Invar MCP server and protocol docs:
- Configure MCP as described in the Other Editors flow
- Keep `CLAUDE.md` and `INVAR.md` as the project protocol source
- Use CLI verification (`invar guard`) when MCP is unavailable

### Cursor (MCP + Rules)

Cursor users get full verification via MCP:
- MCP tools (`invar_guard`, `invar_sig`, `invar_map`)
- .cursor/rules/ for workflow guidance
- Pre-commit hooks

> See [Cursor Guide](./docs/guides/cursor.md) for detailed setup.

### Other Editors (Manual)

1. Run `invar init`
2. Include generated `CLAUDE.md` and `INVAR.md` in your agent's prompt flow
3. Configure MCP server if supported
4. Use CLI commands (`invar guard`) for verification

---

## 📂 What Gets Installed

`invar init` writes this DX-91 minimal generated surface:

| File/Directory | Purpose | Category |
|----------------|---------|----------|
| `CLAUDE.md` | Agent guidance with managed Invar block | Required |
| `INVAR.md` | Protocol for AI agents | Required |
| `.pre-commit-config.yaml` | Verification hook config merged by init | Required |

<sup>* mypy hook included in `.pre-commit-config.yaml` but requires: `pip install mypy`</sup>

Not generated by fresh DX-91 init: `.invar/context.md`, `.mcp.json`, `.claude/commands/`, skills/hooks scaffolds.

**Note:** Guard reads config from `pyproject.toml` (`[tool.invar.guard]`) or `invar.toml` (`[guard]`). `.invar/config.toml` is deprecated.

**Recommended structure:**

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] returns)
```

---

## 🔄 Legacy Project Migration

### Quick Start: MCP Tools Only

For projects that want Invar's MCP tools **without adopting the framework**:

```bash
uvx invar-tools init
```

This writes DX-91 managed files (`CLAUDE.md`, `INVAR.md`, `.pre-commit-config.yaml`) and migrates legacy assets when detected. Your AI agent gets access to:
- **Document tools** (`invar_doc_toc`, `invar_doc_read`, etc.)
- **Code navigation** (`invar_sig`, `invar_map`)
- **Basic verification** (`invar_guard` with minimal rules)

### Language Support

The onboarding workflow examples include Python pattern guides:

```python
# Error handling: returns library
from returns.result import Result, Success, Failure

def get_user(id: str) -> Result[User, NotFoundError]:
    user = db.find(id)
    if not user:
        return Failure(NotFoundError(f"User {id}"))
    return Success(user)

# Contracts: invar_runtime
from invar_runtime import pre, post

@pre(lambda amount: amount > 0)
@post(lambda result: result >= 0)
def calculate_tax(amount: float) -> float:
    return amount * 0.1
```

Historical extension-skill workflows (`invar skill ...`, `/invar-onboard`) are archived in
`docs/proposals/completed/LX-07-extension-skills.md` and are not part of the DX-91 runtime command surface.

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

# Timeouts (seconds)
timeout_doctest = 60           # Doctest execution timeout
timeout_crosshair = 300        # CrossHair total timeout
timeout_crosshair_per_condition = 30  # Per-function timeout
timeout_hypothesis = 300       # Hypothesis total timeout

# Excluded paths (not checked by guard)
exclude_paths = ["tests", "scripts", ".venv", "node_modules", "dist", "build"]
```

### Pattern Detection (DX-61)

Guard can suggest functional programming patterns to improve code quality:

```toml
[tool.invar.guard]
# Minimum confidence for suggestions (low | medium | high)
pattern_min_confidence = "medium"

# Priority levels to include (P0 = core, P1 = extended)
pattern_priorities = ["P0"]

# Patterns to exclude from suggestions
pattern_exclude = []
```

Available patterns: `NewType`, `Validation`, `NonEmpty`, `Literal`, `ExhaustiveMatch`, `SmartConstructor`, `StructuredError`

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
| `invar guard --coverage` | Collect branch coverage from tests |
| `invar init` | Initialize or migrate DX-91 managed files |
| `invar init <path>` | Initialize or migrate DX-91 managed files |
| `invar init --file AGENTS.md` | Write managed block to a non-default target file |
| `invar init --preview` | Show migration/create plan without writing |
| `invar sig <file>` | Show signatures and contracts |
| `invar map` | Symbol map with reference counts |
| `invar refs <file>::<symbol>` | Find all references to a symbol |
| `invar doc toc <file>` | View document structure (headings) |
| `invar doc read <file> <section>` | Read specific section by slug/fuzzy/index |
| `invar doc find <pattern> <files>` | Search sections by title pattern |
| `invar doc replace <file> <section>` | Replace section content |
| `invar doc insert <file> <anchor>` | Insert content relative to section |
| `invar doc delete <file> <section>` | Delete section |
| `invar rules` | List all rules with severity |
| `invar mcp` | Start MCP server for Claude Code |
| `invar dev` | Developer commands for Invar project development |
| `invar version` | Show version info |

### MCP Tools

| Tool | Purpose |
|------|---------|
| `invar_guard` | Smart multi-layer verification |
| `invar_sig` | Extract signatures and contracts |
| `invar_map` | Symbol map with reference counts |
| `invar_doc_toc` | Extract document structure (TOC) |
| `invar_doc_read` | Read specific section |
| `invar_doc_read_many` | Read multiple sections (batch) |
| `invar_doc_find` | Search sections by title pattern |
| `invar_doc_replace` | Replace section content |
| `invar_doc_insert` | Insert content relative to section |
| `invar_doc_delete` | Delete section |

---

## 📚 Learn More

**Created by `invar init`:**
- `CLAUDE.md` — Managed Invar block merged with project guidance
- `INVAR.md` — Protocol v5.0
- `.pre-commit-config.yaml` — Guard hook configuration

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
