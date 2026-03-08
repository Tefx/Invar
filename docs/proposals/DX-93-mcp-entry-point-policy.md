# DX-93: MCP Entry Point Thickness Policy

**Status:** Draft
**Date:** 2026-03-08
**Related:** DX-22, DX-23, guard-fp-field-verify

## Motivation

Recent cross-project feedback shows that `entry_point_too_thick` is calibrated well for
traditional HTTP/CLI entry points, but is too strict when applied to MCP / FastMCP tool
handlers.

The current rule intent remains valid: entry points should stay thin and should not absorb
business logic. However, MCP tools have legitimate protocol-adaptation overhead that is not
the same as Flask/Typer/FastAPI route overhead.

## Current State

- `entry_point_too_thick` originates from DX-23 and defaults to 15 lines.
- Current enforcement uses a single threshold for all detected entry points.
- `mcp.tool` was recently added to entry-point detection.
- The rule is currently emitted as `ERROR`.

Relevant code:
- `src/invar/core/entry_points.py`
- `src/invar/core/rules.py`
- `src/invar/core/rule_meta.py`

## Problem Statement

Treating MCP tools exactly like HTTP/CLI entry points causes false pressure:

1. It conflates protocol-adaptation code with business logic.
2. It encourages single-use helper extraction purely to satisfy line limits.
3. It creates poor agent incentives: "pass the rule" instead of "improve structure".
4. It increases escape-hatch pressure for a case that is often architecturally legitimate.

## Architectural Diagnosis

The rule protects an important invariant:

- entry points are protocol adapters / monad runners
- business logic should live in Shell/Core helpers, not boundary functions

That principle still applies to MCP tools.

What differs is the amount of legitimate boundary code:

| Entry point type | Typical protocol overhead | Current 15-line fit |
|------------------|---------------------------|---------------------|
| Flask/FastAPI route | low | good |
| Typer/Click command | low | good |
| MCP / FastMCP tool | medium-high | poor |

MCP tools often need more lines for:

- schema or argument adaptation
- protocol-specific error mapping
- context injection and response shaping
- tool-facing documentation / structured payload handling

## Options

### Option A: Keep one global 15-line threshold

**Pros**
- simplest implementation
- keeps one universal mental model

**Cons**
- continues to over-penalize MCP tool handlers
- encourages artificial helper splitting
- likely increases escape-hatch debt

**Verdict:** Reject

### Option B: Raise only the MCP-tool threshold

Example:
- default entry points: 15
- `mcp.tool`: 35

**Pros**
- minimal implementation change
- directly addresses current feedback
- preserves current behavior for web/CLI entry points

**Cons**
- introduces a special case
- threshold still remains raw-line-based

**Verdict:** Recommended first step

### Option C: Keep threshold, downgrade MCP severity

Example:
- default entry points: ERROR at 15
- `mcp.tool`: WARNING at 15

**Pros**
- reduces immediate friction
- cheaper than deeper rule redesign

**Cons**
- does not fix the root calibration problem
- still signals too many architecturally acceptable handlers

**Verdict:** Acceptable fallback, not preferred primary fix

### Option D: Exclude protocol boilerplate from line counting

**Pros**
- most semantically accurate in theory

**Cons**
- difficult to define and maintain
- easy to game
- adds significant detector complexity

**Verdict:** Defer

### Option E: Type-specific entry-point policies

Example policy surface:

```toml
[tool.invar.guard.entry_point_thresholds]
default = 15
mcp_tool = 35
```

**Pros**
- principled long-term model
- scales to future protocol types
- reduces false positives without weakening the design goal

**Cons**
- requires entry-point-type classification in the rule path
- needs docs and migration work

**Verdict:** Preferred long-term design

## Recommendation

Adopt a two-step approach:

### Phase 1: Immediate calibration

- keep the default threshold at 15 for traditional entry points
- introduce an MCP-specific threshold of 35
- keep the current design goal: MCP tools should still be thin, just not unrealistically thin

### Phase 2: Formalize type-specific policy

- classify entry points by kind
- resolve thresholds by kind rather than by one global limit
- keep the current single global config as a backward-compatible fallback

## Why 35?

35 is intentionally conservative:

- high enough to avoid forcing protocol-only helper splitting
- low enough to still catch genuinely overgrown tool handlers
- easier to adjust down later than to begin with too-small calibration

## Non-Goals

- do not remove `entry_point_too_thick`
- do not globally relax all entry points
- do not redesign line counting semantics in this proposal
- do not make escape hatches the default answer for MCP tools

## Implementation Plan

### Step 1: Classify MCP entry points explicitly

Scope:
- extend entry-point detection to return both "is entry point" and entry-point kind
- ensure `mcp.tool` resolves to a stable internal kind such as `mcp_tool`

Acceptance:
- rule logic can distinguish traditional entry points from MCP tools
- existing non-MCP entry-point detection behavior does not regress

### Step 2: Add type-aware threshold lookup

Scope:
- keep `entry_max_lines` as the default fallback
- add a kind-aware threshold resolution path
- set `mcp_tool = 35`

Acceptance:
- Flask/Typer/FastAPI remain at 15 unless overridden
- MCP tools use 35
- existing config continues to work

### Step 3: Improve diagnostic messaging

Scope:
- update the violation message/hint so MCP tools get MCP-specific guidance
- explain that protocol adaptation is acceptable, but business logic still belongs outside the tool body

Acceptance:
- fix hints reduce pressure toward single-use helper extraction
- message is clearer about why MCP is treated differently

### Step 4: Add focused regression coverage

Scope:
- MCP tool examples below and above the new threshold
- traditional entry points still enforced at 15
- control cases proving truly thick MCP handlers still trigger

Acceptance:
- regressions cover both policy branches
- no false weakening of the rule for non-MCP entry points

### Step 5: Cross-project field verification

Scope:
- re-run guard on real MCP-heavy repos (for example `../tasca`)
- confirm the rule no longer pressures legitimate MCP handlers while still surfacing real Shell problems

Acceptance:
- previously contentious MCP thickness findings are reduced or correctly reclassified
- unrelated project-side findings remain visible

## Migration Strategy

1. Keep the current global threshold config as fallback.
2. Introduce MCP-specific handling as an additive change.
3. Update rule docs to explain that MCP tools have higher protocol overhead.
4. Collect follow-up evidence before generalizing to more entry-point types.

## Risks

### Risk: Threshold creep

Every new protocol type may ask for exceptions.

Mitigation:
- require evidence before introducing new per-type thresholds

### Risk: Agents still game the rule

Agents may continue to split code unnecessarily.

Mitigation:
- improve the MCP-specific fix hint to discourage single-use extraction performed only for line count

### Risk: 35 is too high

Some genuinely thick MCP handlers may slip through.

Mitigation:
- field-verify against real repos and recalibrate if needed

## Decision Summary

The feedback is reasonable.

The architecture principle should remain unchanged, but the enforcement policy should evolve from:

- one universal entry-point thickness threshold

to:

- type-aware entry-point thickness policy, starting with MCP-specific calibration.
