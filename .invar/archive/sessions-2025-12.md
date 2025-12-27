# Session History Archive (2025-12)

*Archived from context.md on 2025-12-27 per DX-58*

This file contains historical session records. For current project state, see `../.invar/context.md`.

---

## Session 2025-12-26: DX-47/48 Implementation & Workflow Compliance Issue

### DX-47: Command/Skill Separation

实施了 command 和 skill 的明确分离：
- `/audit` — 用户命令，只读代码审查
- `/guard` — 用户命令，运行验证
- `/review` — Agent skill，adversarial review + fix loop

### DX-48: Code Structure Reorganization

分阶段执行：
- **DX-48a**: 删除 664 行死代码（contracts.py, decorators.py, invariant.py, resource.py, deprecated/）
- **DX-48b-lite**: 创建 shell/commands/ 和 shell/prove/ 子目录，移动 10 个文件

### Lesson #29: Agent Workflow Compliance

**问题发现:** 当用户说 "review and fix" 时，Agent 直接开始手动分析，跳过了 `/review` skill。

**根本原因分析:**
1. 把 workflow 当作"可选最佳实践"而非"必须遵守的协议"
2. 没有内化"触发词 → workflow"的映射
3. Check-In 被当作仪式而非状态同步点
4. 效率优化偏见

---

## Session 2025-12-25: DX-32 USBV Implementation & Review Gate Integration

### DX-32: USBV Workflow Implementation

Replaced ICIDIV with USBV (Understand → Specify → Build → Validate):
- **Key insight:** Inspect before Contract. Depth varies naturally.
- **Iteration:** VALIDATE failure returns to appropriate phase

### Review Gate Integration (DX-31 Phase 2)

Integrated independent reviewer subagent into USBV's VALIDATE phase.

**Trigger conditions:**
- Escape hatches >= 3 (`@invar:allow` markers)
- Contract coverage < 50% in Core files
- Security-sensitive paths detected

---

## Session 2025-12-25: DX-31 Review Trigger

### DX-31 Phase 1: Guard Trigger Rule

Implemented `review_suggested` rule that triggers independent review suggestion.

### DX-32 Proposal: Workflow Iteration

**Key Insight:** Contract-before-Inspect is problematic for brownfield development.

---

## Session 2025-12-24: DX-22 AST Detection & Tech Debt Resolution

### The Problem

Full `invar guard` scan revealed 36 errors that previous `--changed` checks missed.

### The Solution

1. **AST-Based Detection** - Replaced string matching with AST parsing
2. **Tech Debt Resolution** - 14 → 0 errors
3. **DX-29 Proposal Created** - Pure content detection

---

## Session 2025-12-24: DX-28 Skip Abuse Prevention

### The Problem

Batch-added `@skip_property_test` to 4 functions without proper justification.

### The Solution

1. Decorator enhanced with required reason string
2. Guard rule added to detect bare/empty skip usage

---

## Session 2025-12-23: DX-21 Package Split & Claude Init (v1.0.0)

### DX-21A: Package Split

Split into two packages:
- `invar-runtime` (~3MB) - Runtime contracts
- `invar-tools` (~100MB) - Development tools

### DX-21B: Claude Init Integration

`invar init --claude` integrates with Claude Code's `/init` command.

---

## Session 2025-12-23: DX-19 Verification Simplification

Simplified from 4 levels to 2:
- STATIC (`--static`) - Rules only
- STANDARD (default) - Rules + doctests + CrossHair + Hypothesis

---

## Session 2025-12-22: DX-16 Agent Tool Enforcement (Phase 1)

Created MCP server with tools: `invar_guard`, `invar_sig`, `invar_map`

---

## Session 2025-12-22: DX-15 & DX-12-B Implementation

- DX-15: Auto Verification Level Selection
- DX-12-B: @strategy Decorator

---

## Session 2025-12-22: Zero Technical Debt & Template Improvements

Resolved all 75 warnings. Added Shell example to templates.

---

## Session 2025-12-21 Evening: DX-11 & Enforcement Reflection

Implemented multi-agent documentation restructure and `invar update` command.

---

## Earlier Version Changes

See Version History in context.md for release summary.

---

*This archive is for reference only. Active development state is in context.md.*
