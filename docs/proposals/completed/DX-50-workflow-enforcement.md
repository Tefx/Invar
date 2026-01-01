# DX-50: Workflow Enforcement

> **"协议存在但执行依赖自觉，需要更强的强制机制。"**

**Status:** ✅ Implemented
**Created:** 2025-12-26
**Updated:** 2026-01-02
**Effort:** Medium
**Risk:** Low
**Breaking:** No

> **Implementation Note:** Workflow Routing is now enforced in CLAUDE.md with mandatory Skill tool invocation. See "Workflow Routing (MANDATORY)" section in CLAUDE.md.

---

## Problem Statement

Agent 容易跳过 Invar workflow，即使协议明确规定了触发条件和流程。

### 观察到的问题

当用户说 "review and fix" 时，Agent 直接开始手动分析，跳过了 `/review` skill。

### 根本原因

1. **把 workflow 当作"可选最佳实践"而非"必须遵守的协议"**
   - Agent 认为"我知道怎么做"就跳过流程
   - 过度自信导致协议失效

2. **没有内化"触发词 → workflow"的映射**
   - CLAUDE.md 定义了触发词，但 Agent 没有自动识别
   - "review" 应触发 `/review` skill

3. **Check-In 被当作仪式而非状态同步点**
   - 任务切换时没有重新运行 Check-In
   - 跳过读取 context.md

4. **效率优化偏见**
   - 直接分析"更快"，跳过 Skill 调用
   - 短期效率 vs 流程一致性的权衡失败

---

## Proposed Solution

### Option A: 强化 CLAUDE.md 指令

在 CLAUDE.md 中更明确地标注触发词和强制要求：

```markdown
## Workflow Routing (MANDATORY)

When user message contains these triggers, you MUST invoke the corresponding skill:

| Trigger Words | Skill | Notes |
|---------------|-------|-------|
| "review", "audit" | `/review` or `/audit` | Distinguish: audit=read-only, review=fix-loop |
| "implement", "add", "fix" | `/develop` | Unless in review context |
| "why", "explain", "investigate" | `/investigate` | Research mode |
| "compare", "should we" | `/propose` | Decision facilitation |

**Violation check:** Before writing ANY code, ask yourself:
- "Am I in a workflow?"
- "Did I invoke the correct skill?"
```

### Option B: 自动化触发词检测

在 Guard 或 pre-commit hook 中检测 Agent 是否遵守了 workflow routing。

```python
# 伪代码
def check_workflow_compliance(user_message, agent_response):
    triggers = extract_triggers(user_message)  # ["review", "fix"]
    expected_skill = map_triggers_to_skill(triggers)  # "/review"
    actual_skill = extract_skill_call(agent_response)

    if expected_skill and not actual_skill:
        return Violation("workflow_skip", f"Expected {expected_skill} but no skill invoked")
```

### Option C: 强制 Check-In on Task Switch

每次用户消息后，强制重新评估：
1. 这是什么 workflow？
2. 需要切换吗？
3. 需要重新 Check-In 吗？

---

## Recommendation

**短期 (Option A):** 强化 CLAUDE.md 指令，让 Agent 更容易自觉遵守

**中期 (Option C):** 建立任务切换检查习惯

**长期 (Option B):** 自动化检测（可能需要 Claude Code hook 支持）

---

## Success Criteria

- [x] CLAUDE.md 包含明确的 workflow routing 表 ✓ (2025-12-26)
- [ ] Agent 在 "review" 触发词出现时自动调用 `/review` skill
- [ ] 任务切换时 Agent 主动重新 Check-In
- [ ] 0 次 workflow 跳过事件（在正常使用中）

---

## Related

- DX-47: Command/Skill separation (defines `/audit` vs `/review`)
- DX-42: Workflow auto-routing (automated routing infrastructure)
- Lesson #29: Agent Workflow Compliance (context.md)

---

## Open Questions

1. 如何检测 "任务切换"？用户消息的语义变化？
2. Option B 的自动化检测是否可行？需要什么基础设施？
3. 是否应该有"强制模式"让 Agent 无法跳过 workflow？
