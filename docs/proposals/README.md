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
| DX-16 | agent-tool-enforcement | **Phase 1 Complete** - MCP server with invar_guard/sig/map tools |
| DX-17 | workflow-enforcement | **Evolved** - Check-In format in INVAR.md v3.27 |
| DX-21 | package-and-init | Two-package architecture (invar-tools + invar-runtime) |
| DX-22 | verification-strategy | Smart routing, Shell rules, Fix-or-Explain, content-based detection |
| DX-23 | entry-point-detection | Auto-detect entry points, exemptions from Result requirement |
| DX-26 | guard-simplification | Simplify guard CLI: 9→5 flags, TTY auto-detect, property test output |

### In Progress / Partial

| ID | Name | Description |
|----|------|-------------|
| DX-20 | property-testing-enhancements | Property testing UX improvements |
| DX-24 | mechanism-documentation | **40%** - architecture/, rules/, verification/ partial; contracts/ and workflow/ pending |
| DX-28 | semantic-verification | **65%** - @relates, format specs, mutation testing, skip abuse prevention done |

**DX-24 Completed:**
- `mechanisms/README.md` - Index and overview
- `mechanisms/architecture/README.md` - Core/Shell overview
- `mechanisms/rules/README.md` - Rule system overview
- `mechanisms/rules/severity-design.md` - ERROR/WARNING/INFO design
- `mechanisms/verification/README.md` - Verification pipeline
- `mechanisms/verification/smart-routing.md` - CrossHair/Hypothesis routing

**DX-24 Remaining:**
- `architecture/` detailed docs (core-shell.md, entry-points.md, result-monad.md)
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
| DX-29 | pure-content-detection | Explicit @invar:module markers (pending review) |

### Archived / Merged

| ID | Name | Status |
|----|------|--------|
| DX-11 | documentation-restructure | Merged into DX-24 |
| DX-15, 18, 19 | - | Merged into other proposals or never created |
| dx-improvements | DX-01 to DX-10 | Historical collection, see `2025-12-21-dx-improvements.md` |

## Archived

Older research-based proposals moved to `archive/`:

- 2024-12-21-guard-enhancements.md
- 2024-12-21-language-inspired-enhancements.md
- 2024-12-21-test-first-enhancement.md

## Template

See `.invar/proposals/TEMPLATE.md` for proposal template.
