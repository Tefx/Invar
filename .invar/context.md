# Invar Project Context

*Last updated: 2024-12-18*

## Current State

- **Phase 1 (Guard):** Complete ✅
- **Phase 2 (Adoption):** Complete ✅
- **Phase 3 (Perception):** Not started
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | ✅ Complete | Flexible config, pattern matching |
| 3 | Guard Enhancement | ← Current | Pureness detection, better line count |
| 4 | Perception | Pending | map, sig commands |
| 5 | Polish | Pending | Docs, CI, PyPI release |
| 6 | Advanced Verification | Long-term | # invar: pure, validation |

## Phase 2: Adoption ✅ Complete

**Implemented:**
1. [x] Multiple config sources: pyproject.toml > invar.toml > .invar/config.toml > defaults
2. [x] Pattern-based Core/Shell classification (`core_patterns`, `shell_patterns`)
3. [x] Flexible `invar init` with `--dirs`/`--no-dirs` options
4. [x] Auto-detect config location (creates invar.toml if no pyproject.toml)

## Phase 3: Guard Enhancement (Current)

**Goal:** Enhance verification for better self-dogfooding.

**Rationale:** By improving guard now, we get immediate feedback while developing subsequent phases.

**Tasks:**
1. [ ] Function-internal import detection
2. [ ] Impure function call detection (datetime.now, random.*, open, print)
3. [ ] Code line count excluding docstrings/comments
4. [ ] `--strict-pure` mode

## Phase 4: Perception (Next)

**Goal:** Context compression for large codebases.

**Tasks:**
1. [ ] core/references.py (reference counting)
2. [ ] core/formatter.py (output formatting)
3. [ ] shell/cli.py (map, sig commands)

## Recent Decisions

1. **Config flexibility** (2024-12-18)
   - Support multiple config sources: pyproject.toml, invar.toml, .invar/config.toml
   - Allows adoption without pyproject.toml

2. **Pattern-based classification** (2024-12-18)
   - `core_patterns` and `shell_patterns` for glob matching
   - Enables zero-refactor adoption for existing projects
   - Priority: patterns > paths > defaults

3. **Flexible invar init** (2024-12-18)
   - Works without pyproject.toml (creates invar.toml)
   - Optional directory creation (--dirs / --no-dirs)

## Lessons Learned

1. **@pre lambda signature** → Must accept ALL function parameters
2. **returns Result checking** → Use isinstance(result, Failure)
3. **Default exclude_paths** → Must include .venv, __pycache__, .pytest_cache
4. **AST symbol extraction** → Use tree.body, not ast.walk()
5. **CLI function size** → Extract helpers to keep under 50 lines
6. **Pattern matching** → `**/domain/**` needs special handling for subpaths
7. **Docstring in line count** → Good doctests can push functions over 50-line limit
8. **Core vs Shell contracts** → Core needs @pre/@post, Shell needs Result[T, E]

## Documentation Checklist

After any feature development or design change:
- [ ] INVAR.md (protocol)
- [ ] CLAUDE.md (project guide)
- [ ] README.md (package docs)
- [ ] docs/DESIGN.md (technical design)
- [ ] .invar/context.md (current state)
- [ ] src/invar/templates/INVAR.md (sync with root)

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.4 |
| CLAUDE.md | Development guide + project rules |
| docs/DESIGN.md | Technical design (includes Phase 2 design) |
| docs/AGENTS.md | Role definitions |

## Architecture

```
src/invar/
├── core/           # Pure logic, no I/O, has contracts
├── shell/          # I/O operations, returns Result
└── templates/      # Files for invar init
```

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
