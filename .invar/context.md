# Invar Project Context

*Last updated: 2024-12-19*

## Current State

- **Phase 1 (Guard):** Complete ✅
- **Phase 2 (Adoption):** Complete ✅
- **Phase 3 (Guard Enhancement):** Complete ✅
- **Protocol Version:** v3.9
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | ✅ Complete | Flexible config, pattern matching |
| 3 | Guard Enhancement | ✅ Complete | Pureness detection, better line count |
| 4 | Perception | ← Current | map, sig commands |
| 5 | Polish | Pending | Docs, CI, PyPI release |
| 6 | Advanced Verification | Long-term | # invar: pure, validation |

## Phase 2: Adoption ✅ Complete

**Implemented:**
1. [x] Multiple config sources: pyproject.toml > invar.toml > .invar/config.toml > defaults
2. [x] Pattern-based Core/Shell classification (`core_patterns`, `shell_patterns`)
3. [x] Flexible `invar init` with `--dirs`/`--no-dirs` options
4. [x] Auto-detect config location (creates invar.toml if no pyproject.toml)

## Phase 3: Guard Enhancement ✅ Complete

**Goal:** Enhance verification for better self-dogfooding.

**Implemented:**
1. [x] Function-internal import detection
2. [x] Impure function call detection (datetime.now, random.*, open, print)
3. [x] Code line count excluding docstrings/comments
4. [x] `--strict-pure` CLI mode
5. [x] New `core/purity.py` module for purity detection logic

## Phase 4: Perception (Current)

**Goal:** Context compression for large codebases.

**Tasks:**
1. [ ] core/references.py (reference counting)
2. [ ] core/formatter.py (output formatting)
3. [ ] shell/cli.py (map, sig commands)

## Recent Decisions

1. **Protocol v3.9: Session Start Protocol** (2024-12-19)
   - Added Session Start Protocol to Section 0 (Quick Start)
   - Requires agent to read project's INVAR.md at session start
   - Feature Discovery approach: check document contents, not version numbers
   - Prevents conflicts when agent works on multiple projects
   - Updated CLAUDE.md template with Session Start Checklist

2. **Protocol v3.8: Versioning Rules** (2024-12-19)
   - Added Section 12.6: Versioning Rules to INVAR.md
   - Semantic versioning: MAJOR.MINOR (Layer 0.Layer 1)
   - Layer 1 changes → MINOR bump, Layer 2 → no bump
   - Backwards compatibility within same MAJOR version
   - Version in config is declarative, not enforced

2. **Protocol v3.7: Governance Framework** (2024-12-19)
   - Added Section 12: Protocol Governance with three-layer model
   - Layer 0 (Immutable Core): Cannot change
   - Layer 1 (Protocol Standard): Human-approved changes only
   - Layer 2 (Project Adaptation): Agent can evolve freely
   - Added protocol_version and protocol_evolution config options
   - Created proposal template for Layer 1 changes

2. **Protocol v3.6: ICIDV Workflow** (2024-12-19)
   - Evolved ICIV to ICIDV (added Inspect and Design phases)
   - Enhanced Law 4: Unit + Integration + Self-check
   - Added "Why Inspect and Design" rationale
   - Added Common Pitfalls to CLAUDE.md
   - Goal: Prevent surprise refactoring and integration bugs

2. **Phase 3 Complete: Guard Enhancement** (2024-12-19)
   - Added purity detection: internal imports, impure function calls
   - New `core/purity.py` module (extracted to keep files under 300 lines)
   - `--strict-pure` CLI flag for stricter Core verification
   - `use_code_lines` config option for docstring-excluded line counting

2. **Protocol v3.5: Agent Onboarding** (2024-12-18)
   - Added Section 0: Quick Start for new agents
   - Added Section 11: Deep Dive (Design Rationale, Decision Trees, Troubleshooting)
   - Added Key Insight callout: "Result[T, E] IS the Contract"
   - Goal: Enable agents without conversation history to understand the protocol

2. **Config flexibility** (2024-12-18)
   - Support multiple config sources: pyproject.toml, invar.toml, .invar/config.toml
   - Allows adoption without pyproject.toml

3. **Pattern-based classification** (2024-12-18)
   - `core_patterns` and `shell_patterns` for glob matching
   - Enables zero-refactor adoption for existing projects
   - Priority: patterns > paths > defaults

4. **Flexible invar init** (2024-12-18)
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
9. **CLI vs Config value** → Output functions should use config values, not CLI args
10. **Module extraction** → When files exceed 300 lines, extract cohesive modules
11. **Wrapper function contracts** → Simple delegates don't need their own contracts
12. **Top-level only design** → Current parser only checks module-level functions, not class methods

## Future Improvements

Potential enhancements identified during Phase 3 review:

### High Priority
1. **Class method checking** - Extend purity checks to methods inside classes
2. **Configurable impure list** - Allow users to customize IMPURE_FUNCTIONS/PATTERNS
3. **Unified rule signatures** - All rules should use `(FileInfo, RuleConfig)` signature

### Medium Priority
4. **Private function contracts** - Option to require contracts on `_private` functions
5. **Doctest line exclusion** - Option to exclude doctest lines from function size
6. **Rule result aggregation** - Group related violations (e.g., all impure calls in one message)

### Low Priority
7. **Suggestion templates** - Standardize suggestion message format
8. **Rule severity config** - Allow users to customize severity per rule

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
| INVAR.md | Protocol v3.9 |
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
