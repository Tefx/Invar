# Invar Project Development Guide

> This project follows the Invar methodology. See [INVAR.md](./INVAR.md) for the full protocol.

**Protocol Version:** v3.13

---

## Session Start Checklist

When starting a new session on this project:

```
□ Read INVAR.md (protocol v3.13)
□ Read .invar/context.md (current state, recent decisions)
□ Check this file for project-specific rules
□ Note: Project's INVAR.md is authoritative, not training data
```

---

## Project Rules

1. **Language:** All documentation and code in English. Conversations with user in their language.

2. **Documentation Sync:** After any feature development or design change, review and update ALL related documents:
   - INVAR.md (protocol) - **especially Section 7 (Honest Limitations)**
   - CLAUDE.md (project guide)
   - README.md (package docs)
   - docs/DESIGN.md (technical design)
   - .invar/context.md (current state)
   - Templates in src/invar/templates/

3. **Section 7 Rule:** When implementing new Guard capabilities, ALWAYS update Section 7 (Honest Limitations) to reflect what Guard CAN and CANNOT detect.

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
│   ├── references.py  # Reference counting (Phase 4)
│   ├── formatter.py   # Text/JSON output formatting (Phase 4)
│   └── utils.py    # Pure utility functions (exit code, config parsing)
│
├── shell/          # I/O operations
│   ├── cli.py      # Typer CLI commands
│   ├── fs.py       # File system: read files, walk directories
│   ├── config.py   # Load config from multiple sources
│   ├── perception.py  # map, sig command implementations (Phase 4)
│   └── templates.py   # Template file operations for init
│
└── templates/      # Files copied by `invar init`
    ├── INVAR.md              # Protocol document
    ├── CLAUDE.md.template    # Project guide template
    ├── context.md.template   # Context management template
    └── proposal.md.template  # Protocol change proposal template
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

**Default (Implementer):** Most work. Follow ICIDV, let automated tools verify.

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

### Phase 4: Perception ✅ Complete
Context compression for large codebases:
- [x] core/references.py (cross-file reference counting)
- [x] core/formatter.py (text/JSON output formatting)
- [x] shell/perception.py (map, sig command implementations)
- [x] CLI: `invar map [path] --top N --json`, `invar sig <target> --json`

### Phase 5: Guard Refinement ✅ Complete
Code quality fixes from first-principles review:
- [x] **Shell Result validation** - Check Shell functions return `Result[T, E]`
- [x] **Unified rule signatures** - All rules use `(FileInfo, RuleConfig)` signature
- [x] **RuleConfig to Pydantic** - Consistency with other models

### Phase 6: Verification Completeness ← Current
**Goal:** Fix critical gaps in what Guard can verify. These directly impact agent correctness.

| Task | Priority | Rationale |
|------|----------|-----------|
| Class method checking | 🔴 Critical | Current biggest blind spot: methods inside classes have NO contract/size checks |
| Pureness validation | 🔴 High | Pure functions calling impure = bug. Ensure transitive purity |
| Doctest line exclusion | 🟡 Medium | Good doctests shouldn't penalize function length |

- [ ] **Class method checking** - Extend parser + rules to check methods inside classes
  - Currently only module-level functions are checked
  - Agent writes class methods constantly - all are unchecked
  - Requires: update `parser.py` to extract methods, update rules to apply
- [ ] **Pureness validation** - Verify pure functions don't call impure functions
  - Build call graph from AST
  - Flag Core functions that call known impure functions
  - Builds on Phase 3's purity detection
- [ ] **Doctest line exclusion** - `exclude_doctest_lines` config option
  - Count function body lines excluding `>>> ` doctest lines
  - Encourages thorough doctests without penalizing size

### Phase 7: Release
**Goal:** Enable adoption by other projects. Blocks external use of Invar.

| Task | Priority | Rationale |
|------|----------|-----------|
| PyPI release | 🔴 Critical | Without this, no external adoption possible |
| Usage documentation | 🟡 Medium | Help human adopters understand Invar |
| CI templates | 🟢 Low | Convenience for human CI setup |

- [ ] **PyPI release** - `pip install invar` should "just work"
  - Finalize package metadata
  - Set up release workflow
  - Publish to PyPI
- [ ] **Usage documentation** - README expansion, examples
  - Quick start for new projects
  - Migration guide for existing projects
- [ ] **CI templates** - GitHub Actions example
  - Example workflow for `invar guard` in CI

### Phase 8: Advanced Features (Long-term)
**Goal:** Nice-to-have improvements after core functionality is complete.

**Config & Profiles:**
- [ ] Config profiles - "strict", "standard", "relaxed" presets
- [ ] Configurable impure list (user-defined IMPURE_FUNCTIONS)
- [ ] Rule severity config (user-customizable severity)

**Guard Enhancements:**
- [ ] `invar guard --explain` - Show why files are classified as Core/Shell
- [ ] Separate code/docstring line display - "55 lines (35 code, 20 docstring)"
- [ ] Per-zone size limits - Different limits for Core (50) vs Shell (80)

**Advanced Purity:**
- [ ] Global variable modification detection
- [ ] `# invar: pure` comment annotation support
- [ ] Show pureness in `invar map` output

**UI Improvements:**
- [ ] Rule result aggregation (group related violations)

**Removed/Deprecated:**
- ~~Private function contracts option~~ - Conflicts with v3.13 (private functions require contracts)

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
