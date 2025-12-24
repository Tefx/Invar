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
| DX-22 | verification-strategy | Smart routing, Shell rules, Fix-or-Explain, de-duplication, config simplification |
| DX-23 | entry-point-detection | Auto-detect entry points, exemptions from Result requirement |
| DX-26 | guard-simplification | Simplify guard CLI: 9→5 flags, TTY auto-detect, property test output |

### In Progress / Partial

| ID | Name | Description |
|----|------|-------------|
| DX-11 | documentation-restructure | Documentation and structure improvements |
| DX-16 | agent-tool-enforcement | MCP tool enforcement for AI agents |
| DX-17 | workflow-enforcement | Session start and ICIDIV workflow enforcement |
| DX-20 | property-testing-enhancements | Property testing UX improvements |
| DX-24 | mechanism-documentation | **60%** - Architecture (core-shell, entry-points, fix-or-explain), verification (smart-routing), rules (severity-design) complete; contracts/ and workflow/ pending |
| DX-28 | semantic-verification | **65%** - @relates, format specs, mutation testing, skip abuse prevention done; contract quality rules pending |
| - | dx-improvements | Collection of DX-01 to DX-10 proposals |

**DX-24 Remaining:**
- `contracts/` directory (pre-post.md, doctests.md, contract-complete.md)
- `workflow/` directory (icidiv.md, session-start.md)

**DX-28 Remaining:**
- Contract quality rules (filter_dual_coverage, parser_format_test, etc.)
- Bidirectional testing framework
- CrossHair symbolic verification of @relates

### Backlog

| ID | Name | Description |
|----|------|-------------|
| DX-25 | functional-patterns | Haskell-inspired patterns: Validation, NewType, NonEmpty, Monoid |
| DX-27 | system-prompt-protocol | System Prompt injection for Check-In/Final enforcement |
| DX-29 | pure-content-detection | Explicit @invar:module markers, deprecate path/pattern config |
| - | AGENT-IMPROVEMENTS | Agent role and workflow improvements |

## Archived

Older research-based proposals moved to `archive/`:

- 2024-12-21-guard-enhancements.md
- 2024-12-21-language-inspired-enhancements.md
- 2024-12-21-test-first-enhancement.md

## Template

See `.invar/proposals/TEMPLATE.md` for proposal template.
