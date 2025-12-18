# Invar Project Context

*Last updated: 2024-12-18*

## Current State

- **Phase 1 (Guard):** Complete ✅
- **Phase 2 (Adoption):** Planning complete, ready to implement
- **Working on:** Documentation updates for Phase 2 design
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | 📋 Planned | Flexible config, pattern matching |
| 3 | Perception | Pending | map, sig commands |
| 4 | Polish | Pending | Docs, CI, PyPI release |

## Phase 2: Adoption (Next Up)

**Goal:** Lower adoption barriers for existing projects.

**Tasks:**
1. [ ] Support `invar.toml` as alternative config source
2. [ ] Implement pattern-based Core/Shell classification
3. [ ] Update `invar init` (no pyproject.toml required, optional dirs)
4. [ ] Config loading priority: pyproject.toml > invar.toml > defaults

**Design:** See docs/DESIGN.md "Phase 2 Design: Adoption Improvements"

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

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.3 |
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
