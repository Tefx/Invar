# Invar Project Context

*Last updated: 2024-12-19*

## Current State

- **Phase 1-5:** Complete ✅
- **Phase 6 (Verification Completeness):** ← Current
- **Protocol Version:** v3.13
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | ✅ Complete | Flexible config, pattern matching |
| 3 | Guard Enhancement | ✅ Complete | Pureness detection, better line count |
| 4 | Perception | ✅ Complete | map, sig commands for context compression |
| 5 | Guard Refinement | ✅ Complete | Shell validation, unified signatures, Pydantic RuleConfig |
| 6 | Verification Completeness | ← Current | Class methods, pureness validation, doctest exclusion |
| 7 | Release | Next | PyPI, documentation, CI templates |
| 8 | Advanced Features | Long-term | Config profiles, advanced purity, UI polish |

## Phase Reorganization Rationale (2024-12-19)

Phases were reorganized based on two principles:
1. **Impact on agent correctness** - What helps agents write correct code?
2. **Task dependencies** - What blocks what?

**Key insight:** The biggest gap in Guard is that **class methods are not checked at all**. Agents write tons of class methods - this is a critical blind spot.

Priority order:
1. **Verification Completeness** (Phase 6) - Fix gaps that affect correctness
2. **Release** (Phase 7) - Enable external adoption
3. **Advanced Features** (Phase 8) - Nice-to-haves

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

## Phase 4: Perception ✅ Complete

**Goal:** Context compression for large codebases.

**Implemented:**
1. [x] core/references.py (cross-file reference counting)
2. [x] core/formatter.py (text/JSON output formatting)
3. [x] shell/perception.py (map, sig command implementations)
4. [x] CLI commands: `invar map [path] --top N --json`, `invar sig <target> --json`
5. [x] New models: SymbolRefs, PerceptionMap

## Phase 5: Guard Refinement ✅ Complete

**Goal:** Clean technical debt and improve consistency.

**Implemented:**
1. [x] RuleConfig moved from @dataclass to Pydantic BaseModel
2. [x] Unified rule signatures: all rules use (file_info, config) pattern
3. [x] Shell Result validation: warns when Shell functions don't return Result[T, E]
4. [x] Removed wrapper functions (_wrap_internal_imports, _wrap_impure_calls)

## Recent Decisions

1. **Phase 4/5 Retrospective** (2024-12-19)
   - Implemented Phase 5 first (Guard Refinement) to clean technical debt
   - Then implemented Phase 4 (Perception) for context compression
   - Cross-file reference counting: only counts references from OTHER files
   - Key insight: Invar is for AGENTS, not humans
   - Wrong idea: "exempt private functions from contracts" (human thinking)
   - Right idea: "contracts help agents verify ALL code" (agent thinking)
   - Shell Result warnings point to design smells, not false positives
   - 6 warnings remain → these are valid, functions may belong in Core

2. **Protocol Applied to Self** (2024-12-19)
   - Reorganized Future Improvements into Phases 5-7
   - Added Phase 5 (Guard Refinement), renamed Phase 6 (Polish), Phase 7 (Advanced)
   - Fixed wrapper functions to use `_private` prefix (passes strict mode now)
   - Added Section 7 Rule to CLAUDE.md (must update Honest Limitations)
   - Added Session Start Checklist to CLAUDE.md
   - Invar now passes `invar guard --strict` with 0 warnings

2. **First-Principles Review** (2024-12-19)
   - Comprehensive review documented in docs/FIRST_PRINCIPLES_REVIEW.md
   - Fixed Section 7 (Honest Limitations) - was factually wrong about capabilities
   - Fixed ICIV → ICIDV references in Sections 8, 9
   - Fixed Law 3 to note `invar map` is planned (Phase 4)
   - Fixed version examples in Section 12 to use 3.9
   - Identified: Shell Result validation not implemented (planned)
   - Identified: Rule signatures inconsistent (purity vs rules module)

2. **Protocol v3.9: Session Start Protocol** (2024-12-19)
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
11. **Private function contracts** → v3.13: Private functions now REQUIRE contracts by default. Public/private is a human abstraction; agents need contracts on ALL code to verify correctness. Skip only for trivial one-liners
12. **Top-level only design** → Current parser only checks module-level functions, not class methods
13. **Section 7 sync** → When implementing new Guard capabilities, ALWAYS update Section 7 (Honest Limitations)
14. **AST reference counting** → Only count ast.Call nodes to avoid double-counting (Name + Call for same reference)
15. **@pre lambda defaults** → Must include default values: `lambda pm, top_n=0:` not just `lambda pm:`
16. **Shell Result warnings are design feedback** → "Pure function in Shell should return Result" often means "this function should be in Core". Don't suppress - reconsider design
17. **Agent vs Human perspective** → Invar is for agents. Features that help humans (pre-commit hooks) don't help agents. Features that help agents write correct code (contracts, Result) should never be weakened
18. **Protocol sync after capability changes** → Add "Document" checkpoint to ICIDV: update Section 7, bump version if needed

## Future Improvements

Items now organized into development phases (see CLAUDE.md):

### Phase 6: Verification Completeness (Current)
- **Class method checking** 🔴 - Biggest gap, agents write methods constantly
- **Pureness validation** 🔴 - Pure functions can't call impure
- **Doctest line exclusion** 🟡 - Don't penalize good documentation

### Phase 7: Release
- **PyPI release** 🔴 - Required for external adoption
- Usage documentation
- CI templates

### Phase 8: Advanced Features (Long-term)
- Config profiles ("strict", "standard", "relaxed")
- Configurable impure list
- Rule severity config
- Guard --explain
- Global variable detection
- `# invar: pure` annotation

### Protocol Improvements (Layer 1 Proposals)
- Add "Document" checkpoint to ICIDV workflow (Section 2)
- Add guidance: "Shell Result warning = design smell, consider moving to Core"

### Future Discussion
- Production contract overhead: how to ensure `DEAL_DISABLE=1` or `-O` in production

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
