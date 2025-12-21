# Invar Project Development Guide

> **"Agent-Native Execution, Human-Directed Purpose"**

This project follows the Invar methodology. See [INVAR.md](./INVAR.md) for the protocol.

**Protocol Version:** v3.23 | **PyPI:** `python-invar` | **Smart Guard:** `invar guard` = static + doctests

---

## Core Principle

Invar enables humans to effectively direct AI agents in producing high-quality code.

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

- **Human**: Directs goals, reviews output, makes decisions
- **Agent**: Follows Protocol, uses Tools, produces code
- **Invar**: Agent-Native toolkit (Agent is primary user)

---

## Session Start

```
□ Read INVAR.md (88 lines, compressed protocol)
□ Read .invar/context.md (current state, lessons learned)
□ Run: invar guard --changed (verify before changes)
□ Run: invar map --top 10 (understand project structure)
```

---

## Project Rules

1. **Language:** Documentation and code in English. Conversations in user's language.

2. **Agent-Native:** Design for Agent consumption. Automatic > Opt-in. Default ON > OFF.

3. **Verify Always:** Run `invar guard` after changes (Smart Guard runs static + doctests).

4. **Warning Policy:** Fix warnings in files you modify (you touched it, you own it).

---

## Project Structure

```
src/invar/
├── core/              # Pure logic, no I/O, requires @pre/@post
│   ├── models.py      # Pydantic: Symbol, Violation, RuleConfig
│   ├── parser.py      # AST: source string → symbols
│   ├── rules.py       # Rule checking: file info → violations
│   ├── purity.py      # Internal imports, impure calls
│   ├── contracts.py   # Contract quality detection
│   ├── suggestions.py # Fix suggestions + lambda skeletons
│   ├── rule_meta.py   # Centralized RULE_META
│   ├── inspect.py     # File context for INSPECT section
│   ├── references.py  # Cross-file reference counting
│   ├── formatter.py   # Text/JSON output
│   └── utils.py       # Pure utilities
│
├── shell/             # I/O operations, returns Result[T, E]
│   ├── cli.py         # Typer CLI commands
│   ├── fs.py          # File system operations
│   ├── config.py      # Config loading
│   ├── git.py         # Git operations (--changed mode)
│   ├── perception.py  # map, sig commands
│   ├── templates.py   # Template operations
│   ├── init_cmd.py    # init command
│   └── testing.py     # test, verify commands
│
└── templates/         # Files for invar init
```

**Key insight:** Core receives string content, Shell handles I/O.

---

## Quick Rules

| Rule | Requirement |
|------|-------------|
| Core | No I/O, `@pre`/`@post` contracts |
| Shell | Returns `Result[T, E]` |
| Files | < 500 lines |
| Functions | < 50 lines |
| Types | Full annotations, Pydantic models |

---

## Development Workflow (ICIDIV)

1. **Intent** - Understand task, classify Core/Shell, list edge cases
2. **Contract** - Write COMPLETE @pre/@post AND doctests BEFORE code
   - Include: normal case, boundaries, edge conditions
   - Self-test: Can this contract regenerate the function?
3. **Inspect** - `invar sig <file>` for contracts, `invar map --top 10` for entry points
4. **Design** - Decompose into sub-functions:
   - List functions (name + description)
   - Identify dependencies, order: leaves first
   - If file > 400 lines, plan extraction
5. **Implement** - Write code to pass the doctests you already wrote
6. **Verify** - `invar guard` (Smart Guard: static + doctests, zero decisions)
   - If violations: Reflect (why?) → Fix → Verify again

---

## Tool Selection

### Always Use Invar For:
```bash
invar sig <file>           # See contracts (UNIQUE: shows @pre/@post)
invar map --top 10         # Find entry points (UNIQUE: reference count ranking)
invar guard --changed      # Verify code quality (REQUIRED)
```

### Task-Based Selection:

| I want to... | Tool | Why |
|--------------|------|-----|
| See contracts/patterns | `invar sig <file>` | Only Invar shows @pre/@post |
| Find hot spots | `invar map --top 10` | Only Invar has ref counts |
| Find specific symbol | Serena `find_symbol` | More precise, pattern matching |
| Find references | Serena `find_referencing_symbols` | Cross-file analysis |
| Edit function body | Serena `replace_symbol_body` | Semantic editing |
| Rename across project | Serena `rename_symbol` | Automatic refactoring |
| Verify after changes | `invar guard --changed` | Smart Guard (static + doctests) |

### Other Commands
```bash
invar guard --prove      # Add CrossHair symbolic verification
invar guard --explain    # Detailed explanations
invar rules              # List all rules
```

### Guard Usage (DX-09)

**Default:** `invar guard` runs STANDARD = static + doctests. **Trust this.**

**Do NOT use --quick unless:**
- Debugging a specific static analysis issue
- Performance profiling the guard itself
- Explicitly testing --quick behavior

**Why?** Default is only 0.4s slower. Bypassing doctests saves 0.4s but risks missing failures.

**Before major changes:** Run `invar guard --prove` for full verification including CrossHair.

---

## Agent Roles

| Command | Role | Purpose |
|---------|------|---------|
| `/review` | Reviewer | Critical code review |
| `/attack` | Adversary | Try to break the code |

Use Reviewer for architecture decisions. Use Adversary for security-critical code.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol reference |
| [docs/VISION.md](./docs/VISION.md) | Design philosophy |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical architecture |
| [.invar/context.md](./.invar/context.md) | Current state, lessons |

---

## Documentation Structure (DX-11)

| File | Owner | Edit? | Purpose |
|------|-------|-------|---------|
| INVAR.md | Invar | No | Protocol (`invar update` to sync) |
| CLAUDE.md | User | Yes | Project customization (this file) |
| .invar/context.md | User | Yes | Project state, lessons learned |
| .invar/examples/ | Invar | No | Reference examples |

**Decision rule:** Is this Invar protocol or project-specific?
- Protocol content → Already in INVAR.md, don't duplicate
- Project-specific → Add to CLAUDE.md or context.md

---

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1-8 | Complete | Guard, Perception, Agent-Native |
| 9 | Complete | PyPI release (python-invar v0.1.0) |
| 10-11 | Complete | Agent decision support (P7, P24-P28) |

Feature complete. See `.invar/context.md` for current state.

---

## Dependencies

```bash
pip install python-invar        # Install from PyPI
pip install -e ".[dev]"         # Development mode
```
