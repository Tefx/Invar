# Invar Project Context

*Last updated: 2025-12-19*

## Current State

- **Phase 1-6:** Complete ✅
- **Phase 7 (Agent-Native Foundation):** ← Current
- **Protocol Version:** v3.14
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | ✅ Complete | Flexible config, pattern matching |
| 3 | Guard Enhancement | ✅ Complete | Pureness detection, better line count |
| 4 | Perception | ✅ Complete | map, sig commands for context compression |
| 5 | Guard Refinement | ✅ Complete | Shell validation, unified signatures, Pydantic RuleConfig |
| 6 | Verification Completeness | ✅ Complete | Class methods, pureness validation, doctest exclusion |
| 7 | Agent-Native Foundation | ← Current | Empty contract detection, fix suggestions |
| 8 | Agent Efficiency | Next | --changed mode, --agent-mode output |
| 9 | Release | Future | PyPI, documentation, CI templates |
| 10 | Agent-Native Advanced | Long-term | Rules YAML, precheck command |

## Core Insight: Invar Serves Agents, Not Humans

**Fundamental realization (2025-12-19):** Invar is built for AI Agents, not human programmers.

| Dimension | Human Programmer | AI Agent |
|-----------|-----------------|----------|
| Understanding | Intuition + experience | Pattern matching, needs explicit rules |
| Failure mode | Carelessness, fatigue | Formal compliance without substance |
| Verification | Subjective judgment | Needs machine-verifiable YES/NO |
| Fixes | Understands suggestions | Needs exact code to apply |

**Agent-specific failure:** `@pre(lambda x: True)` - passes Guard but provides zero value. This is the prototypical Agent error: achieving formal compliance without actual verification.

## Phase 6: Verification Completeness ✅ Complete

**Implemented:**
1. [x] Class method checking - Parser extracts methods from classes
2. [x] Pureness validation - Methods checked for internal imports and impure calls
3. [x] Doctest line exclusion - `exclude_doctest_lines` config option

## Phase 7: Agent-Native Foundation ← Current

**Goal:** Detect Agent-specific failure modes (formal compliance without substance).

| Task | Status | Description |
|------|--------|-------------|
| 7.1 Empty contract detection | 🔄 | Detect `@pre(lambda: True)` tautologies |
| 7.2 Redundant type detection | ⬜ | Detect isinstance-only contracts when types annotated |
| 7.3 Concrete fix suggestions | ⬜ | Generate usable code, not vague suggestions |

**New files:** `core/contracts.py`, `core/suggestions.py`

## Recent Decisions

1. **Agent-Native Redesign** (2025-12-19)
   - Recognized Invar serves Agents, not humans
   - Reorganized phases to address Agent-specific needs
   - Added Phase 7-8 for Agent-native features
   - Key insight: Agents achieve "formal compliance without substance"
   - Guard must detect empty/meaningless contracts

2. **Protocol v3.14** (2025-12-19)
   - Updated Section 7 with Phase 6 capabilities
   - Added Contract Quality Guidance
   - Clarified use_code_lines vs exclude_doctest_lines

3. **Phase 6 Complete** (2025-12-19)
   - Class method extraction in parser.py
   - Rules now check methods for contracts, doctests, size
   - Purity checks extended to methods

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
11. **Private function contracts** → v3.13: Private functions REQUIRE contracts
12. **Section 7 sync** → When implementing new Guard capabilities, update Section 7
13. **AST reference counting** → Only count ast.Call nodes to avoid double-counting
14. **Shell Result warnings = design feedback** → Often means function belongs in Core
15. **Agent vs Human perspective** → Invar is for agents. Never weaken verification
16. **Formal compliance ≠ Actual verification** → `@pre(lambda: True)` passes but is worthless
17. **Suggestions must be code** → Agents need exact code, not "consider adding..."
18. **use_code_lines vs exclude_doctest_lines** → Mutually exclusive, don't enable both

## Future Improvements

### Phase 8: Agent Efficiency
- `--changed` mode (only check git-modified files)
- `--agent-mode` output (JSON with fix instructions)
- Contract param mismatch detection

### Phase 9: Release
- PyPI release
- Usage documentation
- CI templates

### Phase 10: Agent-Native Advanced
- Rules YAML化
- ICIDV precheck command
- Rule conflict resolution
- Config profiles

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.14 |
| CLAUDE.md | Development guide + project rules |
| docs/DESIGN.md | Technical design |
| core/contracts.py | Contract quality detection (Phase 7) |
| core/suggestions.py | Fix suggestion generation (Phase 7) |

## Architecture

```
src/invar/
├── core/           # Pure logic, no I/O, has contracts
│   ├── contracts.py   # NEW: Contract quality detection
│   └── suggestions.py # NEW: Fix suggestion generation
├── shell/          # I/O operations, returns Result
└── templates/      # Files for invar init
```

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
