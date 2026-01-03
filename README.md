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

<table>
<tr>
<th>Python</th>
<th>TypeScript</th>
</tr>
<tr>
<td>

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

</td>
<td>

```typescript
import { z } from 'zod';

const ItemsSchema = z.array(z.number()).min(1);

/**
 * Calculate the average of a non-empty list.
 * @pre items.length > 0
 * @post result >= 0
 *
 * @example
 * average([1.0, 2.0, 3.0]) // => 2.0
 * average([10.0])          // => 10.0
 */
function average(items: number[]): number {
  ItemsSchema.parse(items); // Runtime validation
  return items.reduce((a, b) => a + b) / items.length;
}
```

</td>
</tr>
</table>

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

| Tool | Python | TypeScript | Notes |
|------|--------|------------|-------|
| `invar guard` | ✅ Full | ⚠️ Partial | TS: tsc + eslint + vitest |
| `invar sig` | ✅ Full | ✅ Full | TS: TS Compiler API |
| `invar map` | ✅ Full | ✅ Full | TS: With reference counts |
| `invar refs` | ✅ Full | ✅ Full | Cross-file reference finding |
| `invar doc *` | ✅ Full | ✅ Full | Language-agnostic |

**TypeScript Notes:**
- Requires Node.js + TypeScript (most TS projects have these)
- Falls back to regex parser if Node.js unavailable

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

# Or quick setup (skip prompts)
uvx invar-tools init --claude    # Claude Code only
uvx invar-tools init --pi        # Pi only
uvx invar-tools init --claude --pi  # Both agents (DX-81)
uvx invar-tools init --mcp-only  # MCP tools only (legacy projects)

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

Contracts (`@pre`/`@post` in Python, Zod schemas in TypeScript) turn vague intent into verifiable specifications:

<table>
<tr>
<th>Python</th>
<th>TypeScript</th>
</tr>
<tr>
<td>

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

</td>
<td>

```typescript
// Without contracts: ambiguous
function average(items) {
  return items.reduce((a,b) => a+b) / items.length;
  // What if empty? Return type?
}

// With contracts: explicit
const ItemsSchema = z.array(z.number()).min(1);

/** @post result >= 0 */
function average(items: number[]): number {
  ItemsSchema.parse(items); // Precondition
  const result = items.reduce((a,b) => a+b) / items.length;
  console.assert(result >= 0); // Postcondition
  return result;
}
```

</td>
</tr>
</table>

**Benefits:**
- Agent knows exactly what to implement
- Edge cases are explicit in the contract
- Verification is automatic, not manual review

### ✅ Solution 2: Multi-Layer Verification

Guard provides fast feedback **on top of standard type checking**. Agent sees errors, fixes immediately:

| Layer | Tool | Speed | What It Catches |
|-------|------|-------|-----------------|
| **Type Check*** | mypy (Python) / tsc (TypeScript) | ~1s | Type errors, missing annotations |
| **Static** | Guard rules | ~0.5s | Architecture violations, missing contracts |
| **Doctest** | pytest / vitest | ~2s | Example correctness |
| **Property** | Hypothesis / fast-check | ~10s | Edge cases via random inputs |
| **Symbolic** | CrossHair / (TS: N/A) | ~30s | Mathematical proof of contracts |

<sup>* Requires separate installation: `pip install mypy` or configure TypeScript in your project</sup>

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

<table>
<tr>
<th>Python</th>
<th>TypeScript</th>
</tr>
<tr>
<td>

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

</td>
<td>

```typescript
// Core: Pure, testable, provable
function parseConfig(content: string): Config {
  return ConfigSchema.parse(JSON.parse(content));
}

// Shell: Handles I/O, returns ResultAsync
function loadConfig(path: string): ResultAsync<Config, ConfigError> {
  return ResultAsync.fromPromise(
    fs.readFile(path, 'utf-8'),
    () => ({ type: 'NOT_FOUND', path })
  ).map(parseConfig);
}
```

</td>
</tr>
</table>

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
| **Claude Code** | ✅ Full | `invar init --claude` |
| **[Pi](https://shittycodingagent.ai/)** | ✅ Full | `invar init --pi` |
| **Multi-Agent** | ✅ Full | `invar init --claude --pi` (DX-81) |
| **Cursor** | ✅ MCP | `invar init` → select Other, add MCP config |
| **Other** | 📝 Manual | `invar init` → select Other, include `AGENT.md` in prompt |

> **See also:** [Multi-Agent Guide](./docs/guides/multi-agent.md) for detailed integration instructions.

### Claude Code (Full Experience)

All features auto-configured:
- MCP tools (`invar_guard`, `invar_sig`, `invar_map`)
- Workflow skills (`/develop`, `/review`, `/investigate`, `/propose`)
- Claude Code hooks (tool guidance, verification reminders)
- Pre-commit hooks

### [Pi](https://shittycodingagent.ai/) (Full Support)

Pi reads CLAUDE.md and .claude/skills/ directly, sharing configuration with Claude Code:
- **Same instruction file** — CLAUDE.md (no separate AGENT.md needed)
- **Same workflow skills** — .claude/skills/ work in Pi
- **Pi-specific hooks** — .pi/hooks/invar.ts for pytest blocking and protocol refresh
- **Protocol injection** — Long conversation support via `pi.send()`
- Pre-commit hooks

### Cursor (MCP + Rules)

Cursor users get full verification via MCP:
- MCP tools (`invar_guard`, `invar_sig`, `invar_map`)
- .cursor/rules/ for USBV workflow guidance
- Hooks (beta) for pytest blocking
- Pre-commit hooks

> See [Cursor Guide](./docs/guides/cursor.md) for detailed setup.

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
| `.pre-commit-config.yaml` | Verification before commit (Ruff, mypy*, Guard) | Optional |
| `src/core/`, `src/shell/` | Recommended structure | Optional |
| `CLAUDE.md` | Agent instructions | Claude Code |
| `.claude/skills/` | Workflow + extension skills | Claude Code |
| `.claude/commands/` | User commands (/audit, /guard) | Claude Code |
| `.claude/hooks/` | Tool guidance | Claude Code |
| `.mcp.json` | MCP server config | Claude Code |
| `AGENT.md` | Universal agent instructions | Other agents |

<sup>* mypy hook included in `.pre-commit-config.yaml` but requires: `pip install mypy`</sup>

**Note:** If `pyproject.toml` exists, Guard configuration goes there as `[tool.invar.guard]` instead of `.invar/config.toml`.

**Recommended structure:**

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] returns)
```

---

## 🧩 Extension Skills

Beyond the core workflow skills (`/develop`, `/review`, `/investigate`, `/propose`), Invar provides optional extension skills for specialized tasks:

| Skill | Purpose | Install |
|-------|---------|---------|
| `/security` | OWASP Top 10 security audit | `invar skill add security` |
| `/acceptance` | Requirements acceptance review | `invar skill add acceptance` |
| `/invar-onboard` | Legacy project migration | `invar skill add invar-onboard` |

### Managing Skills

```bash
invar skill list                    # List available/installed skills
invar skill add security            # Install (or update) a skill
invar skill remove security         # Remove a skill
invar skill remove security --force # Force remove (even with custom extensions)
```

**Idempotent:** `invar skill add` works for both install and update. User customizations in the `<!--invar:extensions-->` region are preserved on update.

### Custom Extensions

Each skill has an extensions region where you can add project-specific customizations:

```markdown
<!--invar:extensions-->
## Project-Specific Security Checks

- [ ] Check for hardcoded AWS credentials in config/
- [ ] Verify JWT secret rotation policy
<!--/invar:extensions-->
```

These customizations are preserved when updating skills via `invar skill add`.

---

## 🔄 Legacy Project Migration

### Quick Start: MCP Tools Only

For projects that want Invar's MCP tools **without adopting the framework**:

```bash
uvx invar-tools init --mcp-only
```

This creates only `.mcp.json` — no INVAR.md, CLAUDE.md, or Core/Shell structure. Your AI agent gets access to:
- **Document tools** (`invar_doc_toc`, `invar_doc_read`, etc.)
- **Code navigation** (`invar_sig`, `invar_map`)
- **Basic verification** (`invar_guard` with minimal rules)

### Full Adoption: `/invar-onboard`

For projects that want to fully adopt Invar's patterns, use the `/invar-onboard` skill:

```bash
# Install the onboarding skill
invar skill add invar-onboard

# Run assessment on your project
# (in Claude Code or Pi)
> /invar-onboard
```

### Migration Workflow

```
/invar-onboard
       │
       ▼
┌─────────────────────────────────────────┐
│  Phase 1: ASSESS (Automatic)            │
│  • Code metrics and architecture        │
│  • Pattern detection (error handling)   │
│  • Core/Shell separation assessment     │
│  • Risk and effort estimation           │
│                                         │
│  Output: docs/invar-onboard-assessment.md
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Phase 2: DISCUSS (With User)           │
│  • Present findings                     │
│  • Discuss risk mitigation              │
│  • Confirm scope and priorities         │
└─────────────────────────────────────────┘
       │
       ▼ (user confirms)
┌─────────────────────────────────────────┐
│  Phase 3: PLAN (Automatic)              │
│  • Dependency analysis                  │
│  • Phase decomposition                  │
│  • Session planning                     │
│                                         │
│  Output: docs/invar-onboard-roadmap.md  │
└─────────────────────────────────────────┘
```

### Language Support

The onboarding skill includes language-specific pattern guides:

<table>
<tr>
<th>Python</th>
<th>TypeScript</th>
</tr>
<tr>
<td>

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

</td>
<td>

```typescript
// Error handling: neverthrow
import { Result, ResultAsync, ok, err } from 'neverthrow';

function getUser(id: string): ResultAsync<User, NotFoundError> {
  return ResultAsync.fromPromise(
    db.user.findUnique({ where: { id } }),
    () => new DbError('query_failed')
  ).andThen(user =>
    user ? ok(user) : err(new NotFoundError(`User ${id}`))
  );
}

// Contracts: Zod schemas
import { z } from 'zod';

const AmountSchema = z.number().positive();

function calculateTax(amount: number): number {
  AmountSchema.parse(amount);
  return amount * 0.1;
}
```

</td>
</tr>
</table>

### When to Use `/invar-onboard` vs `/refactor`

| Scenario | Skill | Purpose |
|----------|-------|---------|
| Existing project → Invar | `/invar-onboard` | One-time framework migration |
| Already Invar project | `/refactor` (coming soon) | Continuous code improvement |

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
| `invar init` | Initialize or update project (interactive) |
| `invar init --claude` | Quick setup for Claude Code |
| `invar init --pi` | Quick setup for Pi agent |
| `invar init --claude --pi` | Setup for both agents (DX-81) |
| `invar init --mcp-only` | MCP tools only (no framework files) |
| `invar uninstall` | Remove Invar from project (preserves user content) |
| `invar sig <file>` | Show signatures and contracts |
| `invar map` | Symbol map with reference counts |
| `invar doc toc <file>` | View document structure (headings) |
| `invar doc read <file> <section>` | Read specific section by slug/fuzzy/index |
| `invar doc find <pattern> <files>` | Search sections by title pattern |
| `invar doc replace <file> <section>` | Replace section content |
| `invar doc insert <file> <anchor>` | Insert content relative to section |
| `invar doc delete <file> <section>` | Delete section |
| `invar rules` | List all rules with severity |
| `invar test` | Property-based tests (Hypothesis) |
| `invar verify` | Symbolic verification (CrossHair) |
| `invar mutate` | Mutation testing (find gaps in tests) |
| `invar hooks` | Manage Claude Code hooks |
| `invar skill` | Manage extension skills |
| `invar mcp` | Start MCP server for Claude Code |
| `invar dev sync` | Sync Invar protocol updates |
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
