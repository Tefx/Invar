# DX-54: Agent Native Context Management

> **"AI 管理自己的状态，用户专注于任务。"**

**Status:** ✅ Complete
**Created:** 2025-12-27
**Effort:** Low
**Risk:** Low

---

## Problem Statement

### Issue 1: Check-In 执行无意义命令

当前 Check-In 设计：
```
Check-In:
  invar_guard(changed=true)  → 干净仓库输出 "No changed Python files"
  invar_map(top=10)          → 每次都运行，连续会话冗余
```

**问题：** 开销不小，价值不大。

### Issue 2: 长对话上下文丢失

Check-In 信息被后续对话"挤出" context window，AI 可能忘记项目规则。

### Issue 3: 用户手动刷新不是 Agent Native

依赖用户说"提醒一下规则"是糟糕的设计。

---

## Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Session Boundary (用户可见)                        │
│   Check-In: 读取 context.md，轻量签到                       │
│   Final: guard 验证                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Workflow Refresh (硬约束)                          │
│   每个 Skill Entry Actions: 读取 context.md                │
│   进入 /develop, /review 等时自动刷新                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Document Self-Reminder (软约束)                    │
│   context.md: Key Rules + Self-Reminder                    │
│   CLAUDE.md: Context Management 指导                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

### Phase 1: Simplified Check-In

**CLAUDE.md Check-In 部分修改为：**

```markdown
## Check-In

Your first message MUST display:

✓ Check-In: [project] | [branch] | [clean/dirty]

Actions:
1. Read `.invar/context.md` (Key Rules + Current State)
2. Show one-line status

Do NOT execute guard or map at Check-In.
Guard is for VALIDATE phase and Final only.
```

### Phase 2: Workflow Refresh + Document Self-Reminder

**2.1 Skill Entry Actions (硬约束)**

所有 Skill 模板添加：

```markdown
## Entry Actions

### Context Refresh

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules)
2. Display routing announcement
```

**2.2 context.md 增强**

添加 Key Rules 和 Self-Reminder：

```markdown
## Key Rules (Quick Reference)

### Core/Shell Separation
- **Core** (`**/core/**`): @pre/@post + doctests, NO I/O imports
- **Shell** (`**/shell/**`): Result[T, E] return type

### USBV Workflow
1. Understand → 2. Specify (contracts first) → 3. Build → 4. Validate

### Verification
- Final must show: `✓ Final: guard PASS | ...`

## Self-Reminder

When to re-read this file:
- Starting a new task
- Completing a task
- Conversation has been going on for a while
- Unsure about project rules
```

**2.3 CLAUDE.md Context Management (软约束)**

```markdown
## Context Management (Agent Native)

Re-read `.invar/context.md` when:
1. Entering any workflow (/develop, /review, etc.)
2. Completing a TodoWrite task
3. Conversation exceeds ~15-20 exchanges
4. Unsure about project rules

Refresh is transparent - do not announce it.
```

### Phase 3: Observe and Iterate

实施 Phase 1+2 后观察效果，按需决定是否需要更多机制。

---

## Coverage Analysis

| 场景 | 刷新机制 | 覆盖 |
|------|---------|------|
| 会话开始 | Check-In 读取 context.md | ✅ |
| 进入工作流 | Skill Entry Actions | ✅ |
| 长对话无工作流 | Self-Reminder + 指导 | ⚠️ 软约束 |
| 会话恢复 | Check-In | ✅ |

**预期覆盖率：**
- 开发类任务：~95%（大多进入工作流）
- 问答类任务：~60%（依赖自提醒）

---

## Files Modified

### Templates
- `src/invar/templates/context.md.template`
- `src/invar/templates/config/context.md.jinja`
- `src/invar/templates/config/CLAUDE.md.jinja`
- `src/invar/templates/skills/*/SKILL.md.jinja`

### Project Files
- `.invar/context.md`
- `CLAUDE.md`
- `.claude/skills/*/SKILL.md`

---

## Success Criteria

- [x] Check-In 不执行 guard/map
- [x] context.md 包含 Key Rules + Self-Reminder
- [x] CLAUDE.md 包含 Context Management 指导
- [x] Skill Entry Actions 包含 context.md 读取
- [ ] 长对话仍遵守规则（观察验证）

---

## Why Not Phase-based?

Phase-based Check-In (每个 USBV 阶段都验证) 被否决：

| 问题 | 描述 |
|------|------|
| 过度中断 | 用户看到状态噪音 |
| 非开发任务尴尬 | 问答类无法套用 USBV |
| 阶段回退困境 | 实际开发是迭代的 |
| Guard 重复 | 一个任务可能执行 4 次 guard |

---

## Why Not claude-mem Dependency?

| 考量 | 决策 |
|------|------|
| 静态规则存储 | 不适合 - rules 不变，搜索浪费 |
| 额外依赖 | 避免 - 现有机制足够 |
| 复杂度 | 保持简单 - 文档 + 工作流 |

---

## Related

- DX-51: Workflow Phase Visibility
- DX-53: Review Loop Effectiveness
- Lesson #19: PreToolUse hooks are ineffective
- Lesson #29: Agent Workflow Compliance
