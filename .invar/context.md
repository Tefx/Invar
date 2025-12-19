# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **Phase 1-8:** Complete ✅
- **Phase 9.1 (Friction Reduction):** Complete ✅
- **Phase 9.2 (Agent Experience):** Complete ✅
- **Phase 9.3 (Token Optimization):** Complete ✅
- **Protocol Version:** v3.17
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
| 9 | Release | ✅ Complete | PyPI (python-invar), CI workflows |
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

1. **Phase 9 Release Complete** (2025-12-20)
   - PyPI package name: `python-invar` (original `invar` taken, may apply PEP 541 later)
   - CLI command: `invar` (unchanged)
   - Fixed dependencies: `deal` and `returns` moved to runtime deps
   - Added: LICENSE, py.typed, GitHub Actions CI/publish workflows
   - README updated with badges and correct info

2. **Phase 9.3 Complete** (2025-12-20)
   - P6: Protocol compression (INVAR.md 1296 → 88 lines)
   - Detailed protocol moved to `docs/INVAR-DETAILED.md`
   - Essential info preserved: Core/Shell, Contracts, Size Limits, Guard Commands, ICIDV, Config
   - Details now discoverable via `invar guard --explain`, `invar rules`, hints

2. **Phase 9.2 Complete** (2025-12-20)
   - P3: `core/rule_meta.py` with centralized RULE_META, `invar rules` command
   - P5: Always-on hints from RULE_META.hint, `--explain` for details
   - P4: Lambda skeleton templates in suggestions (no example conditions)
   - P14: INSPECT section in `--changed` mode (file context, patterns)

2. **Phase 9.1 Complete** (2025-12-20)
   - P12: `strict_pure` default ON - agents benefit from more checking
   - P11: `INVAR_MODE=agent` auto-detection for all commands
   - P1: `max_file_lines` 500 + `rule_exclusions` for generated files
   - P2: `severity_overrides` + `redundant_type_contract` OFF + `--pedantic`
   - P8: `file_size_warning` at 80% threshold warns before hitting limit

3. **Agent Improvements Proposals** (2025-12-19)
   - Created `.invar/proposals/AGENT-IMPROVEMENTS.md` with 14 proposals
   - Based on agent experience implementing Phase 8
   - Focus: reduce friction, improve signal-to-noise, prevent formal compliance

3. **Phase 8 Complete** (2025-12-19)
   - `--changed` for faster Agent iteration
   - `--agent` for machine-parseable fix instructions
   - Param mismatch catches runtime bugs before they happen

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
17. **Inline suppression trap** → Per-function suppression enables formal compliance; use config-level exclusions instead
18. **Trivial contracts are expected** → When forcing contracts, some will be isinstance(); this is cost of "forcing thinking", manage noise via defaults
19. **Agent-Native Principle** → Automatic > Opt-in; agents won't use flags they don't know about; default ON beats default OFF
20. **Mechanical vs Reasoning** → Agent time is for reasoning, tool time is for mechanics; templates should enable thinking, not replace it
21. **Documentation ≠ Behavior** → Documentation doesn't change agent behavior; only automatic + enforced mechanisms do; links don't get clicked
22. **Don't Force, Show** → Don't force agent to read/run commands; auto-embed information in output they will see
23. **Single Source of Truth** → Rule metadata (hints, detects, cannot_detect) defined once in RULE_META, used by all outputs
24. **Core imports are forbidden** → pathlib, os, sys etc. forbidden in Core; use fnmatch instead of PurePath for glob matching
25. **fnmatch doesn't respect paths** → fnmatch's `*` matches `/`; check path component counts for non-** patterns
26. **Protocol compression** → Information available via commands/hints doesn't need to be in the protocol; compress once tooling provides discoverability
27. **PyPI naming** → Check name availability early; `python-X` is valid convention when `X` is taken; PEP 541 allows reclaiming abandoned packages
28. **Runtime vs dev deps** → If code imports it, it's a runtime dep; `deal` and `returns` used in src/ must be in dependencies, not dev

## Future Improvements

### Phase 9: Agent-Native Polish (see `.invar/proposals/AGENT-IMPROVEMENTS.md`)

**9.1 Friction Reduction + Agent-Native Defaults ✅ Complete:**
- [x] P12: `strict_pure` default ON (agents need more checking)
- [x] P11: INVAR_MODE env var for agent auto-detection (all commands)
- [x] P1: Relaxed limits (`max_file_lines` 300→500) + `rule_exclusions` config
- [x] P2: `severity_overrides` config + `redundant_type_contract` OFF + `--pedantic`
- [x] P8: File size warnings at 80% threshold (`file_size_warning` rule)

**9.2 Agent Experience + ICIDV + Rule Metadata ✅ Complete:**
- [x] P3: RULE_META system + auto-embed in output + `invar rules` command
- [x] P5: Always-on hints (uses P3 RULE_META.hint) + `--explain` details
- [x] P4: Lambda skeleton templates (no example conditions)
- [x] P14: Automatic inspection + unified --changed output format

**9.3 Token Optimization ✅ Complete:**
- [x] P6: Protocol compression (INVAR.md 1296 → 88 lines, detailed docs in INVAR-DETAILED.md)

### Phase 10: Advanced Verification
- [ ] P13: Mechanical vs Reasoning work audit (systematic review)
- [ ] P7: Semantic contract validation (catch `x == x`)
- [ ] P8b: Function-level size warnings (deferred from P8)
- [ ] P9: Context sync command (`invar context log`)
- [ ] P10: Contract inheritance (Liskov validation)

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.17 (compressed, 88 lines) |
| docs/INVAR-DETAILED.md | Full protocol details |
| CLAUDE.md | Development guide |
| docs/DESIGN.md | Technical design |
| .invar/proposals/AGENT-IMPROVEMENTS.md | 14 improvement proposals |
| .invar/proposals/PHASE-9-REFLECTION.md | Phase 9 retrospective + new proposals |
| .invar/proposals/NEW-PROPOSALS-P15-P23.md | Detailed specs for P15-P23 |
| core/contracts.py | Contract quality detection (Phase 7, 8) |
| core/suggestions.py | Fix suggestion + lambda skeletons (P4) |
| core/formatter.py | Agent-mode output formatting |
| core/rule_meta.py | Centralized rule metadata (P3) |
| core/inspect.py | File context for INSPECT section (P14) |
| shell/git.py | Git operations for --changed mode |

## Architecture

```
src/invar/
├── core/           # Pure logic, no I/O, has contracts
│   ├── contracts.py   # Contract quality + param mismatch
│   ├── suggestions.py # Fix suggestions + lambda skeletons (P4)
│   ├── formatter.py   # Agent-mode output
│   ├── rule_meta.py   # Centralized RULE_META (P3)
│   └── inspect.py     # File context for INSPECT (P14)
├── shell/          # I/O operations, returns Result
│   └── git.py         # Git operations for --changed
└── templates/      # Files for invar init
```

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
