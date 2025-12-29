# LX-02: Agent Portability Analysis

**Status:** ✅ Complete (Research)
**Created:** 2025-12-28
**Series:** LX (Language/Platform eXtension)
**Related:** LX-01 (Multi-language feasibility)
**Informs:** LX-03 (docs), LX-04 (framework design)

---

## Executive Summary

Invar 目前深度绑定 Claude Code 的机制（Skills, Hooks, CLAUDE.md, MCP）。本文档分析这些机制在其他开源 coding agent 中的适用性，为 Invar 的跨平台策略提供依据。

**关键发现:**
- **MCP** 是唯一接近通用的标准 (Claude Code, Cline, Continue, Aider, Cursor 均支持)
- **Hooks** 仅 Claude Code 和 Cursor 1.7+ 支持
- **Skills** 是 Claude Code 独有机制
- **指令文件** 各 agent 有不同格式但概念相似

---

## Part 1: Invar 机制清单

### 1.1 当前使用的机制

| 机制 | 文件/目录 | 功能 | Claude Code 特有? |
|------|-----------|------|-------------------|
| **CLAUDE.md** | `CLAUDE.md` | 项目指令 | ✅ 是 |
| **Skills** | `.claude/skills/` | 可复用工作流 | ✅ 是 |
| **Commands** | `.claude/commands/` | 用户可调用命令 | ✅ 是 |
| **Hooks** | `.claude/hooks/` | 工具调用拦截 | ⚠️ 仅 Cursor 1.7+ 类似 |
| **Settings** | `.claude/settings.local.json` | 权限配置 | ✅ 是 |
| **MCP Server** | `invar.mcp` | 工具暴露 | ✅ 通用标准 |
| **System Reminder** | 注入到对话 | 上下文提醒 | ⚠️ 实现方式不同 |
| **Context Files** | `.invar/context.md` | 项目状态 | ❌ 纯文件 |
| **Examples** | `.invar/examples/` | 模式示例 | ❌ 纯文件 |

### 1.2 机制依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Specific                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ Skills  │ │Commands │ │ Hooks   │ │ Settings.json   │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘   │
│       │           │           │                │            │
│       └───────────┼───────────┼────────────────┘            │
│                   │           │                             │
│                   ▼           ▼                             │
│              ┌─────────────────────┐                        │
│              │     CLAUDE.md       │                        │
│              └──────────┬──────────┘                        │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Portable Layer         │                                   │
│                         ▼                                   │
│              ┌─────────────────────┐                        │
│              │    MCP Server       │  ← 唯一通用接口         │
│              └──────────┬──────────┘                        │
│                         │                                   │
│       ┌─────────────────┼─────────────────┐                │
│       ▼                 ▼                 ▼                │
│  ┌─────────┐     ┌───────────┐     ┌───────────┐          │
│  │context.md│    │examples/  │     │Pure Files │          │
│  └─────────┘     └───────────┘     └───────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 2: 主流 Coding Agent 对比

### 2.1 机制支持矩阵

| 机制 | Claude Code | Cursor | Cline | Continue | Aider |
|------|-------------|--------|-------|----------|-------|
| **指令文件** | CLAUDE.md | .cursorrules | .clinerules | config.yaml | CONVENTIONS.md |
| **目录规则** | .claude/ | .cursor/rules/ | - | .continue/rules/ | - |
| **Hooks** | ✅ 4种 | ✅ Beta (1.7+) | ❌ | ❌ | ❌ |
| **Skills/Commands** | ✅ | ❌ | ❌ (Modes) | ✅ customCommands | ❌ |
| **MCP** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Plan Mode** | ❌ (manual) | ❌ | ✅ | ❌ | ❌ |
| **自动测试** | ❌ | ❌ | ❌ | ❌ | ✅ lint/test |

### 2.2 详细分析

#### Claude Code

```
.claude/
├── settings.local.json    # 权限、MCP 配置
├── commands/              # 用户可调用命令 (markdown)
├── hooks/                 # 工具拦截 (shell scripts)
│   ├── PreToolUse.sh
│   ├── PostToolUse.sh
│   ├── UserPromptSubmit.sh
│   └── Stop.sh
└── skills/                # Agent 可调用工作流 (markdown)
    └── {name}/SKILL.md
```

**Hooks 机制:**
- `PreToolUse`: 工具执行前，可阻止
- `PostToolUse`: 工具执行后，可修改输出
- `UserPromptSubmit`: 用户消息提交时
- `Stop`: 会话结束时

**优势:** 最完整的扩展体系
**劣势:** 完全私有，无法迁移

#### Cursor (1.7+)

```
.cursor/
├── rules/                 # MDC 格式规则文件
│   └── *.mdc
└── hooks.json             # Hook 配置 (Beta)
```

**Hooks 机制 (Beta):**
- `afterFileEdit`: 文件修改后
- `beforeShellExecution`: Shell 命令前
- `stop`: 会话结束

**优势:** 开始支持 hooks，有市场份额
**劣势:** Hooks 仍是 Beta，覆盖不如 Claude Code

#### Cline (VS Code)

```
.clinerules              # 项目级规则
.roomodes                # Roo-Cline 模式定义 (fork)
```

**特点:**
- Plan & Act 模式分离
- MCP 支持完整
- 无 Hook 系统
- Custom Roles 定义

**优势:** 开源，社区活跃
**劣势:** 无 Hook，扩展能力有限

#### Continue.dev

```
.continue/
├── config.json           # 主配置
└── rules/                # 规则目录
```

**特点:**
- 完整 MCP 支持 (首个全特性支持)
- customCommands 数组
- 无 Hook 系统

**优势:** MCP 支持最好
**劣势:** 无 Hook

#### Aider

```
.aider.conf.yml           # YAML 配置
CONVENTIONS.md            # 编码约定
.aiderignore              # 忽略文件
```

**特点:**
- 约定文件作为持久记忆
- 自动 lint/test 验证
- 无 Hook 系统
- Git-aware 编辑

**优势:** 简单，自动验证
**劣势:** 扩展能力最弱

---

## Part 3: 可移植性评估

### 3.1 Invar 机制可移植性

| Invar 机制 | 可移植性 | 移植策略 |
|------------|----------|----------|
| **USBV 工作流** | ✅ 高 | 写入任何指令文件 |
| **Check-In/Final** | ✅ 高 | 写入指令文件 |
| **Guard (MCP)** | ✅ 高 | MCP 是通用标准 |
| **Context.md** | ✅ 高 | 纯文件，任何 agent 可读 |
| **Examples/** | ✅ 高 | 纯文件 |
| **Skills** | ❌ 低 | Claude Code 独有 |
| **Hooks 拦截** | ⚠️ 中 | 仅 Cursor 1.7+ 类似 |
| **自动路由** | ⚠️ 中 | 需要 skill 或类似机制 |

### 3.2 核心价值分析

```
Invar 价值层次:

┌─────────────────────────────────────────────────────────┐
│  Layer 1: 理念 (100% 可移植)                            │
│  ├── USBV 工作流                                        │
│  ├── Core/Shell 分离                                    │
│  ├── 契约驱动开发                                       │
│  └── 对抗性审查                                         │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 工具 (通过 MCP 可移植)                        │
│  ├── invar guard                                        │
│  ├── invar sig                                          │
│  └── invar map                                          │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 集成 (Claude Code 特定)                       │
│  ├── Skills (自动路由)                                  │
│  ├── Hooks (命令拦截)                                   │
│  └── Commands (用户调用)                                │
└─────────────────────────────────────────────────────────┘
```

### 3.3 关键洞察

> **MCP 是唯一的通用桥梁**
>
> 所有主流 coding agent 都支持 MCP。Invar 的核心工具 (guard, sig, map)
> 通过 MCP 暴露，理论上任何支持 MCP 的 agent 都可以使用。

> **Hooks 是差异化但非通用**
>
> Invar 的 pytest/crosshair 拦截依赖 PreToolUse hook。
> 这在 Aider/Cline/Continue 中无法实现。

> **Skills 是编排层，非核心**
>
> Skills 提供便捷的工作流编排，但 USBV 工作流可以通过
> 指令文件描述，agent 会自然遵循。

---

## Part 4: 移植策略

### 4.1 三层移植方案

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: 通用指令层 (所有 agent)                            │
│                                                             │
│  创建 INVAR.md 通用版本:                                    │
│  - USBV 工作流描述                                          │
│  - Core/Shell 规则                                          │
│  - 契约要求                                                 │
│  - 验证步骤 (调用 MCP 工具)                                 │
│                                                             │
│  + 适配文件:                                                │
│  - CLAUDE.md (Claude Code)                                  │
│  - .cursorrules (Cursor)                                    │
│  - .clinerules (Cline)                                      │
│  - CONVENTIONS.md (Aider)                                   │
│  - config.yaml (Continue)                                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 2: MCP 工具层 (支持 MCP 的 agent)                     │
│                                                             │
│  invar MCP server:                                          │
│  - invar_guard()                                            │
│  - invar_sig()                                              │
│  - invar_map()                                              │
│                                                             │
│  配置方式:                                                  │
│  - Claude Code: settings.local.json                         │
│  - Cursor: MCP 配置                                         │
│  - Cline: MCP 设置                                          │
│  - Continue: config.json mcpServers                         │
│  - Aider: 需确认                                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 3: 增强层 (特定 agent)                                │
│                                                             │
│  Claude Code:                                               │
│  - Skills (自动路由)                                        │
│  - Hooks (命令拦截)                                         │
│  - Commands (用户调用)                                      │
│                                                             │
│  Cursor 1.7+:                                               │
│  - hooks.json (部分拦截)                                    │
│  - .cursor/rules/ (MDC 规则)                                │
│                                                             │
│  Cline:                                                     │
│  - Custom Roles                                             │
│  - Plan Mode 集成                                           │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 `invar init` 多 Agent 支持

```bash
# 当前
invar init                    # 生成 Claude Code 配置

# 建议扩展
invar init --agent=claude     # Claude Code (默认)
invar init --agent=cursor     # Cursor
invar init --agent=cline      # Cline
invar init --agent=continue   # Continue.dev
invar init --agent=aider      # Aider
invar init --agent=universal  # 仅生成 MCP + 通用指令
```

### 4.3 生成文件映射

| Agent | 指令文件 | MCP 配置 | Hooks |
|-------|----------|----------|-------|
| Claude Code | CLAUDE.md | settings.local.json | .claude/hooks/ |
| Cursor | .cursorrules | cursor 设置 | .cursor/hooks.json |
| Cline | .clinerules | 扩展设置 | N/A |
| Continue | .continue/config.yaml | mcpServers | N/A |
| Aider | CONVENTIONS.md | N/A (CLI) | N/A |

---

## Part 5: 功能降级矩阵

### 5.1 在无 Hooks 的 Agent 中

| 原功能 | Claude Code | 其他 Agent | 降级策略 |
|--------|-------------|------------|----------|
| pytest 拦截 | Hook 阻止 | ❌ 无法阻止 | 指令中说明 "使用 invar guard 而非 pytest" |
| 自动路由 | Skill 触发 | ❌ 无自动 | 指令中写明触发词 → 行为映射 |
| 协议刷新 | Hook 注入 | ❌ 无注入 | 依赖指令文件，用户手动触发 |

### 5.2 功能可用性

| 功能 | Claude | Cursor | Cline | Continue | Aider |
|------|--------|--------|-------|----------|-------|
| USBV 工作流 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Guard 验证 | ✅ MCP | ✅ MCP | ✅ MCP | ✅ MCP | ⚠️ CLI |
| 命令拦截 | ✅ | ⚠️ Beta | ❌ | ❌ | ✅ 内置 |
| 自动路由 | ✅ | ❌ | ⚠️ Modes | ⚠️ Commands | ❌ |
| 对抗性审查 | ✅ Skill | ✅ 指令 | ✅ 指令 | ✅ 指令 | ✅ 指令 |

---

## Part 6: 建议行动

### 6.1 短期 (低成本)

1. **创建 INVAR-UNIVERSAL.md**
   - 提取 CLAUDE.md 中与 Claude Code 无关的内容
   - 作为所有 agent 的基础指令
   - 包含 USBV 工作流、契约要求、验证步骤

2. **文档化 MCP 配置**
   - 为每个主流 agent 提供 MCP 配置示例
   - 添加到 Invar 文档

### 6.2 中期 (需开发)

3. **扩展 `invar init`**
   - 添加 `--agent` 参数
   - 生成适配的配置文件

4. **创建适配器模板**
   - `.cursorrules.jinja`
   - `.clinerules.jinja`
   - `CONVENTIONS.md.jinja`

### 6.3 长期 (战略)

5. **评估 Hooks 替代方案**
   - 对于无 Hook 的 agent，研究是否有其他拦截机制
   - 例如: Aider 的 auto-lint 可能可以集成 invar guard

6. **社区贡献**
   - 为其他 agent 贡献 Invar 集成
   - 例如: Cline 插件、Continue 扩展

---

## Part 7: 结论

### 7.1 可移植性总结

```
                        可移植性
                            │
  ┌─────────────────────────┼─────────────────────────┐
  │                         │                         │
  ▼                         ▼                         ▼
理念 100%              工具 ~80%              集成 ~20%
USBV 工作流           MCP (Guard/Sig/Map)    Skills/Hooks
Core/Shell            纯文件 (context.md)    Commands
契约驱动              Examples               自动路由
```

### 7.2 关键结论

1. **Invar 的核心价值可移植**
   - USBV 工作流、契约驱动、Core/Shell 分离是理念
   - 可以通过任何 agent 的指令文件表达

2. **MCP 是跨平台关键**
   - `invar guard/sig/map` 通过 MCP 暴露
   - 所有主流 agent 支持 MCP

3. **Hooks 是差异化但非必需**
   - pytest 拦截是便利功能，非核心价值
   - 无 Hook 的 agent 可以通过指令约束

4. **Skills 是 Claude Code 独有优势**
   - 提供最佳用户体验
   - 其他 agent 需手动触发或简化体验

### 7.3 推荐策略

**拥抱 MCP，接受降级:**

```
Claude Code: 完整体验 (Skills + Hooks + MCP)
     ↓
Cursor 1.7+: 良好体验 (Rules + Hooks Beta + MCP)
     ↓
Cline/Continue: 基础体验 (Rules + MCP)
     ↓
Aider: 最小体验 (Conventions + CLI)
```

每个层级都能使用 Invar 的核心价值，只是便利性逐级降低。

---

## References

- [Aider Configuration](https://aider.chat/docs/config.html)
- [Cline GitHub](https://github.com/cline/cline)
- [Continue MCP Support](https://blog.continue.dev/model-context-protocol/)
- [Cursor Hooks Guide](https://skywork.ai/blog/how-to-cursor-1-7-hooks-guide/)
- [Cursor Rules Documentation](https://cursor.com/docs/context/rules)
- [Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
- [MCP Joins Linux Foundation](https://github.blog/open-source/maintainers/mcp-joins-the-linux-foundation-what-this-means-for-developers-building-the-next-era-of-ai-tools-and-agents/)

---

*Research completed 2025-12-28*
