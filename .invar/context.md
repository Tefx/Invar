# Invar Project Context

*Last updated: 2025-12-19*

## Current State

- **Phase 1-8:** Complete ✅
- **Phase 9 (Release):** Next
- **Protocol Version:** v3.16
- **Blockers:** None

## Implementation Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Guard (MVP) | ✅ Complete | Core architecture enforcement |
| 2 | Adoption | ✅ Complete | Flexible config, pattern matching |
| 3 | Guard Enhancement | ✅ Complete | Pureness detection, better line count |
| 4 | Perception | ✅ Complete | map, sig commands for context compression |
| 5 | Guard Refinement | ✅ Complete | Shell validation, unified signatures |
| 6 | Verification Completeness | ✅ Complete | Class methods, pureness validation |
| 7 | Agent-Native Foundation | ✅ Complete | Empty contract, fix suggestions |
| 8 | Agent Efficiency | ✅ Complete | --changed, --agent, param mismatch |
| 9 | Release | Next | PyPI, documentation, CI templates |
| 10 | Agent-Native Advanced | Long-term | Rules YAML, precheck command |

## Core Insight: Invar Serves Agents, Not Humans

**Fundamental realization:** Invar is built for AI Agents, not human programmers.

| Dimension | Human Programmer | AI Agent |
|-----------|-----------------|----------|
| Understanding | Intuition + experience | Pattern matching, needs explicit rules |
| Failure mode | Carelessness, fatigue | Formal compliance without substance |
| Verification | Subjective judgment | Needs machine-verifiable YES/NO |
| Fixes | Understands suggestions | Needs exact code to apply |

## Phase 8: Agent Efficiency ✅ Complete

**Implemented:**
1. [x] `--changed` mode - Only check git-modified files
2. [x] `--agent` mode - JSON with structured fix instructions
3. [x] @pre param mismatch detection - ERROR when lambda params != function params

**New files:** `shell/git.py`

**Key fixes:**
- Bracket-aware param extraction (handles `dict[K, V]`, `tuple[A, B]`)
- Only check @pre contracts (not @post which takes `result`)

## Recent Decisions

1. **Phase 8 Complete** (2025-12-19)
   - `--changed` for faster Agent iteration
   - `--agent` for machine-parseable fix instructions
   - Param mismatch catches runtime bugs before they happen

2. **Protocol v3.16** (2025-12-19)
   - Updated Section 7 with Phase 8 capabilities
   - Removed implemented items from Planned Improvements

## Lessons Learned

1. **@pre lambda signature** → Must accept ALL function parameters
2. **returns Result checking** → Use isinstance(result, Failure)
3. **Default exclude_paths** → Must include .venv, __pycache__
4. **AST symbol extraction** → Use tree.body, not ast.walk()
5. **CLI function size** → Extract helpers to keep under 50 lines
6. **Pattern matching** → `**/domain/**` needs special handling
7. **Docstring in line count** → Good doctests can push over 50 lines
8. **Core vs Shell contracts** → Core needs @pre/@post, Shell needs Result
9. **CLI vs Config value** → Use config values, not CLI args
10. **Module extraction** → When files exceed 300 lines, extract modules
11. **Section 7 sync** → Update Section 7 when implementing Guard features
12. **Agent perspective** → Invar is for agents, never weaken verification
13. **Formal compliance ≠ verification** → `@pre(lambda: True)` is worthless
14. **Suggestions must be code** → Agents need exact code to apply
15. **@post vs @pre params** → @post takes `result`, not function params
16. **Bracket-aware parsing** → `dict[K, V]` has comma inside brackets

## Future Improvements

### Phase 9: Release
- PyPI release
- Usage documentation
- CI templates

### Phase 10: Agent-Native Advanced
- Rules YAML化
- ICIDV precheck command
- Config profiles

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.16 |
| CLAUDE.md | Development guide |
| docs/DESIGN.md | Technical design |
| core/contracts.py | Contract quality detection (Phase 7, 8) |
| core/suggestions.py | Fix suggestion generation |
| core/formatter.py | Agent-mode output formatting |
| shell/git.py | Git operations for --changed mode |

## Architecture

```
src/invar/
├── core/           # Pure logic, no I/O, has contracts
│   ├── contracts.py   # Contract quality + param mismatch
│   ├── suggestions.py # Fix suggestion generation
│   └── formatter.py   # Agent-mode output
├── shell/          # I/O operations, returns Result
│   └── git.py         # Git operations for --changed
└── templates/      # Files for invar init
```

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
