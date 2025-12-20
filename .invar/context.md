# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **PyPI:** `python-invar` v0.3.1
- **Protocol:** v3.18
- **GitHub Pages:** https://tefx.github.io/Invar/
- **Status:** Feature complete, stricter enforcement enabled
- **Blockers:** None

## Recent Changes (v0.3.0)

### Breaking Changes
| Rule | Before | After |
|------|--------|-------|
| `missing_contract` | WARNING | **ERROR** |
| `impure_call` | WARNING | **ERROR** |
| `empty_contract` | WARNING | **ERROR** |

### New Features
- **Code Health Display** - Percentage + progress bar in Guard output
- **Warning Policy** - "You touched it, you own it" in CLAUDE.md
- **Tool Selection Guide** - Task-based with Serena fallbacks
- **Technical Debt Section** - In context.md template
- **GitHub Pages** - Project landing page

## Core Principle

> **"Agent-Native Execution, Human-Directed Purpose"**

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

## Implementation Summary

| Phase | Status | Key Features |
|-------|--------|--------------|
| 1-8 | Complete | Guard, Perception (map/sig), Agent-Native defaults |
| 9 | Complete | PyPI release, RULE_META, Protocol compression |
| 10 | Complete | Tautology detection (P7), Import alternatives (P17) |
| 11 | Complete | Coverage stats (P24), Extraction analysis (P25), Pattern alternatives (P27), Partial contract detection (P28) |
| 12 | Complete | Stricter enforcement, Code Health, GitHub Pages |

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2025-12 | Initial PyPI release |
| 0.2.0 | 2025-12 | README rewrite, pre-commit hooks |
| 0.2.1 | 2025-12 | Hooks default ON |
| 0.2.2 | 2025-12 | Auto-install hooks, universal venv support |
| 0.3.0 | 2025-12 | Stricter enforcement, Code Health, GitHub Pages |
| 0.3.1 | 2025-12 | Smart Guard, Ruff pre-commit, CI fixes |

## Tool Priority

| Task | Primary | Fallback |
|------|---------|----------|
| See contracts | `invar sig` | — |
| Find entry points | `invar map --top` | — |
| Find specific symbol | Serena `find_symbol` | `invar map` + grep |
| Find references | Serena `find_referencing_symbols` | `invar map` |
| Edit function | Serena `replace_symbol_body` | Standard edit |
| Verify | `invar guard` | — |

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.18 |
| docs/INVAR-GUIDE.md | Why & How |
| docs/VISION.md | Design philosophy |
| CLAUDE.md | Development guide |
| docs/index.html | GitHub Pages |

## Lessons Learned

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Guard/Agent Boundary** - Guard does mechanical analysis, Agent does reasoning
4. **Facts Only** - Report facts, don't judge "strength" or "quality"
5. **Stricter is Better** - Enforce architecture at commit time, not review time
6. **Tool Complementarity** - Invar for contracts/verification, Serena for navigation/editing
7. **Meta-changes Need Meta-verification** - Rule severity changes need full guard, not --changed

## Technical Debt

*Run `invar guard` to check current status.*

| File | Warning | Priority |
|------|---------|----------|
| cli.py | 495 lines (99%), 4 functions > 50 lines | Low |
| contracts.py | 492 lines (98%) | Low |
| rules.py | 430 lines (86%) | Low |

---

*Update this file when: completing phases, making design decisions, releasing versions.*
