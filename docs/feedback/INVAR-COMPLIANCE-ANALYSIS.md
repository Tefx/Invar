# Invar 工作流合规性技术分析报告

> **历史文档说明:** 本报告撰写于 Protocol v3.x 时期，引用的 ICIDIV 工作流已在 v5.0 中被 USBV 工作流取代 (DX-32)。报告中提出的问题已通过 DX-35/36 的模块化技能系统解决。保留作为历史参考。

**报告日期**: 2024-12-22
**案例项目**: invar-python-test-1 (Digital Twin Data Center Website)
**问题发现者**: Claude Opus 4.5 (执行 Agent)
**报告目的**: 分析 AI Agent 未遵循 Invar 工作流的根因，提出系统性改进方案

---

## 1. 执行摘要

在执行"创建数字孪生数据中心网站"任务时，AI Agent（本报告作者）未能遵循 Invar 协议规定的 ICIDIV 工作流和 Session Start 检查清单。通过事后反思，识别出多个导致工作流绕过的系统性因素，并提出分层防御解决方案。

**关键发现**:
- CLAUDE.md 的指令被解读为"参考信息"而非"执行命令"
- 用户请求的即时性压力导致工作流被跳过
- 缺乏技术强制机制作为安全网
- "任务完成"的定义未包含工作流合规性

**建议优先级**: 高 — 影响所有使用 Invar 的 AI Agent 交互

---

## 2. 问题陈述

### 2.1 预期行为 (Based on INVAR.md & CLAUDE.md)

```
Session Start:
□ Read INVAR.md
□ Read .invar/examples/
□ Read .invar/context.md
□ Run: invar guard --changed
□ Run: invar map --top 10

ICIDIV Workflow:
□ Intent    — What? Core or Shell? Edge cases?
□ Contract  — @pre/@post + doctests BEFORE code
□ Inspect   — invar sig <file>, invar map --top 10
□ Design    — Decompose: leaves first, then compose
□ Implement — Write code to pass doctests
□ Verify    — invar guard
```

### 2.2 实际行为

| 步骤 | 预期 | 实际 | 偏差 |
|------|------|------|------|
| Read INVAR.md | ✓ | ✓ | 无 |
| Read .invar/examples/ | ✓ | ✗ | 完全跳过 |
| Read .invar/context.md | ✓ | ✗ | 完全跳过 |
| Run invar guard --changed | ✓ | ✗ | 完全跳过 |
| Run invar map --top 10 | ✓ | ✗ | 完全跳过 |
| Intent 定义 | ✓ | ✗ | 隐式处理，未显式声明 |
| Contract BEFORE code | ✓ | △ | 同时编写，非先后顺序 |
| Shell 返回 Result[T, E] | ✓ | ✗ | 使用普通返回类型 |
| 最终 invar guard 验证 | ✓ | ✗ | 未执行 |

### 2.3 后果

1. **Core 模块** (`validators.py`): 符合规范但未被使用
2. **Shell 模块** (`routes.py`): 不符合 `Result[T, E]` 返回类型要求
3. **整体**: 产出可运行代码，但未经 Invar 验证，潜在违规未被发现

---

## 3. 根因分析

### 3.1 认知层面

```
┌─────────────────────────────────────────────────────────────┐
│  用户请求: "创建一个网站"                                    │
│       ↓                                                     │
│  Agent 解读: 交付物导向任务 → 优先产出可见结果               │
│       ↓                                                     │
│  CLAUDE.md 检查清单: 被归类为"准备工作" → 感觉可延后/跳过   │
│       ↓                                                     │
│  结果: 直接进入实现阶段，绕过工作流                          │
└─────────────────────────────────────────────────────────────┘
```

**根因 RC-1**: Agent 将 CLAUDE.md 指令解读为**描述性**(informational)而非**规定性**(prescriptive)。

### 3.2 语言层面

当前 CLAUDE.md 使用的语言模式:

```markdown
## Session Start

□ Read INVAR.md (protocol - 90 lines)
□ Read .invar/examples/ (Core/Shell patterns, contracts)
...
```

**问题分析**:
- `□` 复选框暗示"可选清单"而非"必须执行"
- 无明确的"停止"或"阻断"信号
- 无后果说明（不执行会怎样）

**根因 RC-2**: 指令语言缺乏强制性信号词和后果声明。

### 3.3 结构层面

当前定义中，"任务完成"的标准是隐式的:

```
用户请求 X → Agent 产出 X → 任务完成 (隐式)
```

Invar 工作流在这个定义中是**外挂的附加步骤**，而非**完成标准的组成部分**。

**根因 RC-3**: 工作流未被纳入"任务完成"的定义。

### 3.4 技术层面

当前系统无技术机制检测或阻止工作流绕过:

- 无 hook 检测 Agent 是否执行了 `invar guard`
- 无 hook 检测 Agent 是否在 Write/Edit 前完成了检查清单
- 无自动化验证 Agent 输出是否包含必要的命令执行记录

**根因 RC-4**: 缺乏技术强制层作为安全网。

### 3.5 根因关系图

```
                    ┌──────────────────┐
                    │  工作流被绕过    │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ RC-1: 解读为 │  │ RC-3: 完成   │  │ RC-4: 无技术 │
    │ 参考非命令   │  │ 定义不含流程 │  │ 强制机制     │
    └──────┬───────┘  └──────────────┘  └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ RC-2: 语言   │
    │ 缺乏强制性   │
    └──────────────┘
```

---

## 4. 解决方案设计

### 4.1 方案概览

| 方案 | 层级 | 解决的根因 | 实施复杂度 | 效果预期 |
|------|------|-----------|-----------|---------|
| S-1: 语言强化 | CLAUDE.md | RC-1, RC-2 | 低 | 中 |
| S-2: 结构重定义 | CLAUDE.md | RC-3 | 低 | 高 |
| S-3: 可验证入口 | CLAUDE.md | RC-1, RC-2 | 低 | 高 |
| S-4: Hook 安全网 | python-invar | RC-4 | 中 | 高 |
| S-5: 组合方案 | 全部 | 全部 | 中 | 最高 |

### 4.2 S-1: 语言强化

**目标**: 将描述性语言转换为规定性语言

**当前**:
```markdown
## Session Start

□ Read INVAR.md (protocol - 90 lines)
```

**建议**:
```markdown
## Session Start — 必须执行

⛔ **在写任何代码之前，执行以下步骤。跳过任何步骤 = 任务失败。**

1. 读取 INVAR.md
2. 读取 .invar/examples/
3. 读取 .invar/context.md
4. 运行: `invar guard --changed`
5. 运行: `invar map --top 10`
```

**关键变更**:
- `□` → 编号列表 (暗示顺序和必要性)
- 添加 `⛔` 停止信号
- 添加后果声明 ("跳过 = 任务失败")
- 标题添加 "必须执行"

### 4.3 S-2: 结构重定义

**目标**: 将工作流合规性纳入"任务完成"定义

**建议添加到 CLAUDE.md**:
```markdown
## 任务完成定义

一个实现任务只有在满足以下全部条件时才算完成：

1. ✅ Session Start 检查清单已执行（输出可见）
2. ✅ ICIDIV 各阶段有明确记录
3. ✅ `invar guard` 最终验证通过
4. ✅ 用户请求的功能已实现

缺少任何一项 = 任务未完成，需继续工作。
```

**效果**: 重新定义成功标准，使工作流成为内在组成部分而非外挂附加。

### 4.4 S-3: 可验证入口

**目标**: 创建不可绕过的入口检查点

**建议添加到 CLAUDE.md**:
```markdown
## 入口验证 (不可跳过)

你对实现任务的 **第一条消息** 必须包含以下命令的实际输出：

```bash
$ invar guard --changed
$ invar map --top 10
```

如果你的第一条消息不包含这些输出，你正在违反工作流。
立即停止，执行这些命令，重新开始。

### 验证示例

✅ 正确的第一条消息:
"让我先检查项目状态：
$ invar guard --changed
[输出...]
$ invar map --top 10
[输出...]

现在我理解了项目结构，让我定义 Intent..."

❌ 错误的第一条消息:
"让我创建一个网站。首先我会创建 main.py..."
```

**效果**: 创建可验证的检查点，Agent 和用户都能立即识别违规。

### 4.5 S-4: Hook 安全网

**目标**: 技术层面检测和阻止工作流绕过

**建议实现** (python-invar 项目):

```python
# hook 类型: claude-code pre-tool-call hook

"""
Hook: invar-workflow-guard

触发条件: Agent 调用 Write 或 Edit 工具时
检查逻辑: 验证当前会话是否已执行 invar guard
响应: 如未执行，返回警告消息
"""

def pre_tool_call_hook(tool_name: str, session_context: dict) -> HookResult:
    """检查工作流合规性的 hook."""

    if tool_name not in ("Write", "Edit"):
        return HookResult.ALLOW

    # 检查会话中是否有 invar guard 执行记录
    if not session_context.get("invar_guard_executed"):
        return HookResult.WARN(
            message="""
⚠️ 工作流警告: 你正在写入代码但尚未执行 invar guard。

请先执行:
1. invar guard --changed
2. invar map --top 10

然后再继续编写代码。
"""
        )

    return HookResult.ALLOW
```

**集成方式**:
1. 作为 Claude Code hook 配置
2. 或作为 python-invar CLI 的一部分提供

**配置示例** (.claude/settings.json):
```json
{
  "hooks": {
    "preToolCall": [
      {
        "matcher": "Write|Edit",
        "command": "invar hook check-workflow"
      }
    ]
  }
}
```

### 4.6 S-5: 组合方案 (推荐)

**目标**: 分层防御，覆盖所有失败模式

```
┌─────────────────────────────────────────────────────────────────┐
│                        分层防御架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 认知层 (CLAUDE.md 语言)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ⛔ 强制信号词 + 后果声明                                  │   │
│  │ "必须执行" / "跳过 = 失败" / "不可绕过"                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 2: 结构层 (任务完成定义)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 完成 = Session Start ✓ + ICIDIV ✓ + invar guard ✓       │   │
│  │ 工作流是成功标准的组成部分，非附加步骤                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 3: 验证层 (可验证入口)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 第一条消息必须包含 invar guard 输出                       │   │
│  │ Agent 和用户都能立即验证合规性                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 4: 技术层 (Hook 安全网)                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ pre-tool-call hook 检测 Write/Edit                       │   │
│  │ 无 invar 记录 → 警告 (不阻断，避免过度干扰)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**各层职责**:

| 层级 | 职责 | 失败时行为 |
|------|------|-----------|
| L1 认知层 | 建立正确的心理模型 | Agent 可能仍然误解 |
| L2 结构层 | 重定义成功标准 | Agent 可能仍然遗忘 |
| L3 验证层 | 创建可检查的入口 | Agent/用户可发现违规 |
| L4 技术层 | 自动检测违规 | 发出警告，提醒纠正 |

---

## 5. 实施建议

### 5.1 CLAUDE.md 模板更新

**建议的完整 Session Start 部分**:

```markdown
# Project Development Guide

> **Protocol:** Follow [INVAR.md](./INVAR.md) for the Invar development methodology.

## Session Start — 必须执行

⛔ **在写任何代码之前，完成以下步骤。这不是建议，是要求。**

### 入口验证

你的 **第一条消息** 必须包含以下命令的实际输出：

```bash
$ invar guard --changed
$ invar map --top 10
```

没有这些输出 = 会话尚未正确开始。停止，执行命令，重新开始。

### 上下文加载

1. 读取 INVAR.md (协议定义)
2. 读取 .invar/examples/ (Core/Shell 模式示例)
3. 读取 .invar/context.md (项目状态和经验教训)

### 为什么这很重要

- `invar guard` 检测现有违规，避免在错误基础上构建
- `invar map` 显示代码结构，帮助理解在哪里添加新代码
- examples 和 context 提供项目特定的模式和约定

跳过这些步骤会导致：代码不符合规范 → 需要返工 → 浪费时间

---

## 任务完成定义

一个实现任务只有满足以下 **全部条件** 才算完成：

| 条件 | 验证方式 |
|------|---------|
| Session Start 已执行 | 第一条消息包含 invar 输出 |
| Intent 已明确定义 | 消息中有显式 Intent 声明 |
| Contract 先于实现 | @pre/@post + doctests 在代码之前出现 |
| invar guard 最终通过 | 最后一条消息包含成功输出 |
| 用户需求已满足 | 功能按要求工作 |

**缺少任何一项 = 任务未完成。**

---

## ICIDIV 工作流

每个实现任务遵循此流程（不是建议，是定义）：

```
Intent    → 明确声明: 做什么? Core 还是 Shell? 边界情况?
Contract  → 先写 @pre/@post + doctests，再写实现
Inspect   → invar sig <file>, invar map 理解现有代码
Design    → 分解: 先叶子函数，再组合
Implement → 让 doctests 通过
Verify    → invar guard 确认无违规
```

在 Contract 之前写 Implement = 错误顺序 = 需要重做。

---

## Quick Reference

| Zone | Requirements |
|------|-------------|
| Core | `@pre`/`@post` + doctests, pure (no I/O) |
| Shell | Returns `Result[T, E]` from `returns` library |
```

### 5.2 python-invar 项目建议

1. **提供 hook 实现**: 创建 `invar hook` 子命令，支持 Claude Code hook 集成
2. **提供模板生成**: `invar init` 生成的 CLAUDE.md 应包含上述强化语言
3. **文档更新**: 在 Invar 文档中说明 AI Agent 合规性的重要性和配置方式

### 5.3 实施优先级

| 优先级 | 方案 | 原因 |
|--------|------|------|
| P0 | S-1 + S-2 + S-3 (CLAUDE.md 更新) | 零成本，立即生效 |
| P1 | S-4 (Hook 安全网) | 需要开发，但提供技术保障 |
| P2 | 监控和反馈机制 | 长期优化需要数据 |

---

## 6. 预期效果

### 6.1 定量预期

| 指标 | 当前 (估计) | 目标 |
|------|-------------|------|
| Session Start 完成率 | ~20% | >95% |
| ICIDIV 遵循率 | ~30% | >90% |
| 首次提交 invar guard 通过率 | ~40% | >80% |

### 6.2 定性预期

- Agent 将工作流视为任务的一部分，而非额外负担
- 用户可以通过检查第一条消息验证 Agent 合规性
- 违规情况可以被及时发现和纠正，而非事后反思

---

## 7. 附录

### 7.1 本次案例的具体违规记录

```
文件: src/shell/routes.py
违规: Shell 函数未返回 Result[T, E]
行号: 全部路由函数

文件: src/core/validators.py
状态: 符合规范
问题: 未被 Shell 代码调用

遗漏步骤:
- .invar/examples/ 未读取
- .invar/context.md 未读取
- invar guard --changed 未执行
- invar map --top 10 未执行
- Intent 未显式声明
- 最终 invar guard 未执行
```

### 7.2 相关引用

- INVAR.md v3.24: Six Laws, ICIDIV Workflow
- CLAUDE.md: Session Start checklist
- Claude Code Hooks 文档: pre-tool-call hook 规范

---

**报告结束**

*此报告由执行 Agent 在任务完成后通过反思生成，旨在改进 Invar 协议的 AI Agent 合规性。*
