# Invar Proposals

This directory contains design proposals for Invar development.

## Naming Convention

- `DX-XX-name.md` - Developer Experience improvements
- Archived proposals in `archive/` subdirectory

## Proposal Status

### Implemented

| ID | Name | Description |
|----|------|-------------|
| DX-12 | hypothesis-fallback | Hypothesis as CrossHair fallback for library-dependent code |
| DX-13 | incremental-prove | Incremental CrossHair verification with caching |
| DX-14 | expanded-prove-usage | Full verification in pre-commit/CI (merged into default via DX-19) |
| DX-21 | package-and-init | Two-package architecture (invar-tools + invar-runtime) |
| DX-26 | guard-simplification | Simplify guard CLI: 9→5 flags, TTY auto-detect, property test output |

### In Progress / Partial

| ID | Name | Description |
|----|------|-------------|
| DX-11 | documentation-restructure | Documentation and structure improvements |
| DX-16 | agent-tool-enforcement | MCP tool enforcement for AI agents |
| DX-17 | workflow-enforcement | Session start and ICIDIV workflow enforcement |
| DX-20 | property-testing-enhancements | Property testing UX improvements |
| DX-22 | verification-strategy | **90%** - Shell rules, Fix-or-Explain, `@invar:allow` escape hatches |
| DX-23 | entry-point-detection | **100%** - Auto-detect + exemptions (can move to Implemented) |
| DX-24 | mechanism-documentation | **80%** - severity-design.md added, agent practices documented |
| - | dx-improvements | Collection of DX-01 to DX-10 proposals |

**DX-22 Recent Progress:**
- `shell_result`, `entry_point_too_thick` → ERROR severity
- Unified escape hatch: `# @invar:allow <rule>: <reason>`
- Severity design principles documented

**DX-24 Recent Progress:**
- Created `docs/mechanisms/rules/severity-design.md`
- Updated rules README with escape mechanisms
- Added agent quality practices to AGENTS.md

### Backlog

| ID | Name | Description |
|----|------|-------------|
| DX-25 | functional-patterns | Haskell-inspired patterns: Validation, NewType, NonEmpty, Monoid |
| DX-27 | system-prompt-protocol | System Prompt injection for Check-In/Final enforcement |
| - | AGENT-IMPROVEMENTS | Agent role and workflow improvements |

## Archived

Older research-based proposals moved to `archive/`:

- 2024-12-21-guard-enhancements.md
- 2024-12-21-language-inspired-enhancements.md
- 2024-12-21-test-first-enhancement.md

## Template

See `.invar/proposals/TEMPLATE.md` for proposal template.
