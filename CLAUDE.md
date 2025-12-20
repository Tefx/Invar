# Invar Project Development Guide

> **"Agent-Native Execution, Human-Directed Purpose"**

This project follows the Invar methodology. See [INVAR.md](./INVAR.md) for the protocol.

**Protocol Version:** v3.17 | **PyPI:** `python-invar` v0.1.0

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
```

---

## Project Rules

1. **Language:** Documentation and code in English. Conversations in user's language.

2. **Agent-Native:** Design for Agent consumption. Automatic > Opt-in. Default ON > OFF.

3. **Verify Always:** Run `invar guard` and `pytest --doctest-modules` after changes.

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
│   └── templates.py   # Template operations
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

## Development Workflow (ICIDV)

1. **Intent** - Understand task, classify Core/Shell
2. **Contract** - Define signature, @pre/@post, doctests
3. **Inspect** - Check file sizes, existing patterns (use `--changed`)
4. **Design** - Plan extraction if file > 400 lines
5. **Implement** - Write explicit code
6. **Verify** - `pytest --doctest-modules && invar guard`

---

## Guard Commands

```bash
invar guard              # Check all files
invar guard --changed    # Modified files only (shows INSPECT info)
invar guard --explain    # Detailed explanations
invar guard --agent      # JSON output
invar rules              # List all rules
```

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
| [INVAR.md](./INVAR.md) | Protocol (88 lines) |
| [docs/VISION.md](./docs/VISION.md) | Design philosophy |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical architecture |
| [.invar/context.md](./.invar/context.md) | Current state, lessons |

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
