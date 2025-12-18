# Invar Project Development Guide

> This project follows the Invar methodology. See [INVAR.md](./INVAR.md) for the full protocol.

---

## Project Rules

1. **Language:** All documentation and code in English. Conversations with user in their language.

2. **Documentation Sync:** After any feature development or design change, review and update ALL related documents:
   - INVAR.md (protocol)
   - CLAUDE.md (project guide)
   - README.md (package docs)
   - docs/DESIGN.md (technical design)
   - .invar/context.md (current state)
   - Templates in src/invar/templates/

---

## Context Recovery

If starting a new session or context was summarized, read `.invar/context.md` for:
- Current project state and progress
- Recent design decisions
- Lessons learned (pitfalls to avoid)

---

## Bootstrap Status

**Phase 1 (Guard) is complete.** Invar can now check itself:

```bash
invar guard        # Verify architecture rules
pytest --doctest-modules  # Run all tests
```

**Note:** Core's "no I/O" exception - Invar's Core receives file content as strings (parsed by Shell), not file paths.

---

## Project Structure

```
src/invar/
├── core/           # Pure logic (receives file content as strings)
│   ├── models.py   # Pydantic models: Symbol, Violation, Config
│   ├── parser.py   # AST parsing: source string → symbols
│   ├── rules.py    # Rule checking: file info → violations
│   ├── purity.py   # Purity detection: internal imports, impure calls
│   └── references.py  # Reference counting (Phase 4)
│
├── shell/          # I/O operations
│   ├── cli.py      # Typer CLI commands
│   ├── fs.py       # File system: read files, walk directories
│   └── config.py   # Load config from multiple sources
│
└── templates/      # Files copied by `invar init`
    ├── INVAR.md            # Protocol document
    └── CLAUDE.md.template  # Project guide template
```

**Key insight:** Core functions receive **string content**, not file paths. Shell reads files and passes content to Core.

```python
# Shell: reads file
content = Path("foo.py").read_text()

# Core: processes string (pure)
symbols = parse_source(content)  # No I/O here
```

---

## Quick Rules

1. **Separation:** `src/invar/core` vs `src/invar/shell`
2. **Contracts:** Use `@pre`/`@post` from `deal` for Core functions
3. **Results:** Use `Result[T, E]` from `returns` for Shell functions
4. **Types:** Full type annotations, use Pydantic for models
5. **Tests:** Doctest for examples, hypothesis for properties
6. **Verify:** Run `pytest --doctest-modules` after every change

---

## Development Workflow

Follow **ICIDV** for each task (Intent → Contract → Inspect → Design → Implement → Verify):

### I - Intent
```
□ Understand what needs to be done
□ Identify affected files
□ Classify as Core or Shell
```

### C - Contract
```
□ Define function signature with types
□ Add @pre/@post decorators
□ Write doctest examples
□ Consider: empty, zero, negative, None
```

### I - Inspect (before coding!)
```
□ Check file sizes: will any exceed 280 lines after changes?
□ Check signature patterns: how do similar functions look?
□ Identify edge cases: methods, nested functions, async?
```

### D - Design
```
□ If file will exceed 280 lines → plan extraction first
□ Match existing signature patterns
□ Document non-obvious decisions
```

### I - Implementation
```
□ Write explicit code (no **kwargs, no eval)
□ Keep functions < 50 lines
□ Keep files < 300 lines
```

### V - Verify
```
□ Run pytest --doctest-modules (unit tests)
□ Run invar guard (architecture check)
□ Test config + CLI scenarios (integration)
□ Check type hints with mypy (optional)
```

---

## Common Pitfalls

Lessons learned from Invar development:

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| set() ordering | Doctest fails randomly | Use `sorted()` in tests |
| CLI vs config value | Feature works with CLI flag but not config | Pass `config.X` not `cli_arg` |
| File size surprise | Guard fails after "done" | Check file size BEFORE adding code |
| Signature mismatch | Wrapper functions needed | Match existing patterns |
| Missing integration test | Bug only found in production | Test config file scenarios |

---

## Agent Roles

This project uses role-based review. See [docs/AGENTS.md](./docs/AGENTS.md) for full definitions.

| Command | Role | Purpose |
|---------|------|---------|
| `/review` | Reviewer | Critical code review, find defects |
| `/attack` | Adversary | Try to break the code, find vulnerabilities |

### When to Use Each Role

**Default (Implementer):** Most work. Follow ICIV, let automated tools verify.

**Reviewer - Use when:**
- Design decisions affect multiple modules
- Architecture changes (new Core/Shell boundaries)
- Public API changes
- Changes to contracts (@pre/@post)
- Complex algorithms (>30 lines of logic)

**Adversary - Use when:**
- Processing user/external input
- Security-sensitive code (auth, crypto, permissions)
- Code at trust boundaries (Shell entry points)
- Financial calculations
- Data validation logic

### Decision Flow

```
Is it security-critical or processing untrusted input?
├── Yes → /attack (Adversary)
└── No → Does it affect architecture or public contracts?
    ├── Yes → /review (Reviewer)
    └── No → Default (Implementer) + automated checks
```

**Key insight:** `invar guard` and `pytest` handle most verification automatically. Use Reviewer/Adversary for decisions that require judgment, not mechanical checking.

---

## Key Design Documents

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [INVAR.md](./INVAR.md) | Protocol for agents | Always (this is the law) |
| [docs/VISION.md](./docs/VISION.md) | Philosophy | When questioning "why" |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical design | When implementing features |
| [docs/AGENTS.md](./docs/AGENTS.md) | Role definitions | When reviewing code |

---

## Implementation Phases

### Phase 1: Guard (MVP) ✅ Complete
- [x] Project skeleton
- [x] core/models.py
- [x] core/parser.py
- [x] core/rules.py
- [x] shell/fs.py
- [x] shell/config.py
- [x] shell/cli.py (guard command)
- [x] invar init command

### Phase 2: Adoption ✅ Complete
Improved usability for existing projects:
- [x] Support `invar.toml` as alternative config (no pyproject.toml required)
- [x] Pattern-based Core/Shell classification (`core_patterns`, `shell_patterns`)
- [x] Flexible `invar init` (detect config location, `--dirs`/`--no-dirs`)
- [x] Config loading priority: pyproject.toml > invar.toml > defaults

### Phase 3: Guard Enhancement ✅ Complete
Enhanced verification for better self-dogfooding:
- [x] Function-internal import detection (not just top-level)
- [x] Impure function call detection (datetime.now, random.*, open, print)
- [x] Code line count excluding docstrings/comments (`use_code_lines` config)
- [x] `--strict-pure` CLI mode
- [x] New `core/purity.py` module for purity detection

### Phase 4: Perception ← Current
Context compression for large codebases:
- [ ] core/references.py (reference counting)
- [ ] core/formatter.py (output formatting)
- [ ] shell/cli.py (map, sig commands)

### Phase 5: Polish
- [ ] Documentation (usage guide)
- [ ] CI templates
- [ ] PyPI release

### Phase 6: Advanced Verification (Long-term)
- [ ] Global variable modification detection
- [ ] `# invar: pure` comment annotation support
- [ ] Pureness validation (pure functions can't call impure)
- [ ] Show pureness in `invar map` output

---

## Testing

```bash
# Run all tests including doctests
pytest --doctest-modules src/

# Run with hypothesis (property tests)
pytest src/ -v

# Type checking (optional but recommended)
mypy src/invar/
```

---

## Dependencies

```bash
# Development setup
pip install typer rich pydantic deal returns hypothesis pytest mypy ruff
```
