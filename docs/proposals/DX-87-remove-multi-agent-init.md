# DX-87: Remove Multi-Agent Init Support

**Status**: Draft
**Created**: 2026-02-12
**Priority**: Medium
**Type**: Breaking Change (DX)

---

## Executive Summary

Invar currently supports initializing multiple agents in a single command (e.g. `invar init --claude --pi`) and interactive multi-select.

This proposal removes that capability and enforces **single-agent initialization only**.

**Rationale (source: user decision):** exposing real configuration conflicts is better than hiding them behind tooling automation.

---

## Problem

Multi-agent init creates a perception that coexistence is "solved" by Invar, even when agent ecosystems disagree on:
- rule file names
- skill discovery/precedence
- MCP configuration formats
- hooks capabilities

This can hide problems until later and increases Invar's maintenance surface area.

---

## Decision

### 1) CLI flags

If more than one agent flag is provided, `invar init` must **error and exit**.

Examples that must fail:

```bash
invar init --claude --pi
invar init --claude --opencode
```

The error should be explicit about the policy:

> Cannot initialize multiple agents in one run. Run init separately per agent.

### 2) Interactive init

Interactive selection must be **single-select** (not checkbox multi-select).

---

## Manual Coexistence (Supported, Explicit)

Users can still configure multiple agents in a project by running init multiple times explicitly:

```bash
invar init --claude
invar init --pi
```

Invar does not attempt to "make them consistent" automatically; it only performs agent-specific installation for the selected agent on each run.

---

## Scope

In scope:
- Remove combined-agent init behavior.
- Remove interactive multi-select.
- Update docs/proposals and guides to avoid implying first-class multi-agent coexistence.

Out of scope:
- New conflict-resolution mechanisms.
- Automatic migration of existing repos.

---

## Compatibility

This is a breaking change.

Versioning plan is intentionally deferred.

---

## References

- Source of removed capability: DX-81 (implemented v1.15.0): `docs/proposals/DX-81-multi-agent-init.md`
- Decision source: user directive "删除 init 命令同时传/选择多个 agent 的能力" + follow-up "A 1" + "a".
