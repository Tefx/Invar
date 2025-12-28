# LX-03: Multi-Agent Support Implementation

**Status:** In Progress
**Created:** 2025-12-28
**Series:** LX (Language/Platform eXtension)
**Depends on:** LX-02 (Agent Portability Analysis)
**Related:** DX-62 (Proactive Reference Reading)

---

## Executive Summary

基于 LX-02 的可移植性分析，本提案实施 Invar 对多个 coding agent 的支持。目标是让 Invar 的核心价值（USBV 工作流、契约驱动、Guard 验证）能在 Claude Code 之外的 agent 中使用。

**策略:** 渐进式支持，从文档开始，逐步添加工具集成。

---

## Phase 1: Documentation (✅ Complete)

### 已完成工作

创建了 `docs/guides/` 目录，包含完整的集成文档：

| 文件 | 大小 | 内容 |
|------|------|------|
| `multi-agent.md` | 5 KB | 总览、对比矩阵、MCP 通用配置 |
| `cline.md` | 8 KB | .clinerules 模板、Plan Mode 映射 |
| `cursor.md` | 9 KB | .cursorrules、hooks.json、pytest 拦截 |
| `aider.md` | 9 KB | CONVENTIONS.md、auto-lint 集成 |
| `continue.md` | 11 KB | config.json、customCommands |

### 文档特点

每个指南包含：

1. **Quick Start** - 5 分钟内可运行
2. **完整配置模板** - 复制即用
3. **MCP 配置** - 多种选项 (uvx, venv, global)
4. **Feature Mapping** - 与 Claude Code 对比
5. **Troubleshooting** - 常见问题解决

### Agent 特有功能覆盖

| Agent | 独特功能 | 文档覆盖 |
|-------|----------|----------|
| Cline | Plan Mode | ✅ USBV 阶段映射 |
| Cursor | Hooks (beta) | ✅ pytest 拦截脚本 |
| Aider | auto-lint | ✅ Guard 反馈循环 |
| Continue | customCommands | ✅ 类 Skill 配置 |

---

## Phase 2: Template Generation

### 目标

扩展 `invar init` 支持多 agent：

```bash
invar init                    # Claude Code (默认)
invar init --agent=cline      # Cline
invar init --agent=cursor     # Cursor
invar init --agent=aider      # Aider
invar init --agent=continue   # Continue
invar init --agent=universal  # 仅 MCP + 通用指令
```

### 实现设计

#### 2.1 模板文件结构

```
src/invar/templates/
├── config/                    # 现有
│   ├── CLAUDE.md.jinja
│   ├── INVAR.md.jinja
│   └── context.md.jinja
├── agents/                    # NEW
│   ├── cline/
│   │   └── clinerules.jinja
│   ├── cursor/
│   │   ├── cursorrules.jinja
│   │   ├── rules/
│   │   │   ├── invar-core.mdc.jinja
│   │   │   └── invar-workflow.mdc.jinja
│   │   └── hooks/
│   │       └── check-command.js
│   ├── aider/
│   │   ├── CONVENTIONS.md.jinja
│   │   └── aider.conf.yml.jinja
│   └── continue/
│       ├── config.json.jinja
│       └── rules/
│           └── invar.md.jinja
└── universal/                 # NEW
    └── INVAR-INSTRUCTIONS.md.jinja
```

#### 2.2 CLI 修改

```python
# src/invar/shell/commands/init.py

SUPPORTED_AGENTS = {
    "claude": "Claude Code (default)",
    "cline": "Cline VS Code extension",
    "cursor": "Cursor IDE",
    "aider": "Aider terminal assistant",
    "continue": "Continue.dev extension",
    "universal": "Universal MCP + instructions",
}

def init_command(
    agent: str = "claude",
    # ... existing params
):
    """Initialize Invar for the specified agent."""
    if agent == "claude":
        # Existing behavior
        generate_claude_config()
    elif agent == "cline":
        generate_clinerules()
        print_mcp_instructions("cline")
    elif agent == "cursor":
        generate_cursorrules()
        generate_cursor_hooks()
        print_mcp_instructions("cursor")
    # ... etc
```

#### 2.3 生成文件映射

| Agent | 生成文件 |
|-------|----------|
| claude | CLAUDE.md, .claude/skills/, .claude/hooks/, .invar/ |
| cline | .clinerules, .invar/ |
| cursor | .cursorrules, .cursor/rules/, .cursor/hooks/, .invar/ |
| aider | CONVENTIONS.md, .aider.conf.yml, .invar/ |
| continue | .continue/config.json, .continue/rules/, .invar/ |
| universal | INVAR-INSTRUCTIONS.md, .invar/ |

### 工作量估算

| 任务 | 时间 |
|------|------|
| 创建模板文件 | 2 天 |
| 修改 init 命令 | 1 天 |
| 测试各 agent | 1 天 |
| 文档更新 | 0.5 天 |
| **总计** | **4.5 天** |

---

## Phase 3: MCP Compatibility Testing

### 目标

验证 Invar MCP server 在各 agent 中正常工作。

### 测试矩阵

| Agent | MCP 配置 | guard | sig | map | 状态 |
|-------|----------|-------|-----|-----|------|
| Claude Code | ✅ 原生 | ✅ | ✅ | ✅ | 已验证 |
| Cline | 待测试 | ? | ? | ? | 待验证 |
| Cursor | 待测试 | ? | ? | ? | 待验证 |
| Continue | 待测试 | ? | ? | ? | 待验证 |
| Aider | N/A (CLI) | ✅ | ✅ | ✅ | 已验证 |

### 测试计划

1. **环境准备**
   - 安装各 agent
   - 配置 MCP

2. **功能测试**
   - 调用 invar_guard
   - 调用 invar_sig
   - 调用 invar_map
   - 验证输出格式

3. **错误处理测试**
   - 缺少依赖
   - 权限问题
   - 超时处理

### 工作量估算

| 任务 | 时间 |
|------|------|
| 环境准备 | 1 天 |
| Cline 测试 | 0.5 天 |
| Cursor 测试 | 0.5 天 |
| Continue 测试 | 0.5 天 |
| 修复问题 | 1 天 |
| **总计** | **3.5 天** |

---

## Phase 4: Hooks Portability

### 目标

将 Claude Code hooks 移植到支持 hooks 的 agent。

### 当前 Claude Code Hooks

```
.claude/hooks/
├── PreToolUse.sh      # pytest/crosshair 拦截
├── PostToolUse.sh     # 输出处理
├── UserPromptSubmit.sh # 协议刷新
└── Stop.sh            # 会话结束
```

### Cursor Hooks 移植

Cursor 1.7+ 支持部分 hooks：

| Claude Code | Cursor | 移植可行性 |
|-------------|--------|------------|
| PreToolUse | beforeShellExecution | ✅ 可移植 |
| PostToolUse | afterFileEdit | ⚠️ 部分 |
| UserPromptSubmit | N/A | ❌ 不支持 |
| Stop | stop | ✅ 可移植 |

### 实现

```javascript
// .cursor/hooks/check-command.js
// 已在 Phase 1 文档中提供实现
```

### 工作量估算

| 任务 | 时间 |
|------|------|
| Cursor hooks 实现 | 1 天 |
| 测试验证 | 0.5 天 |
| 文档更新 | 0.5 天 |
| **总计** | **2 天** |

---

## Phase 5: Documentation Integration

### 目标

将新的 multi-agent 文档集成到主文档结构。

### 任务清单

1. **更新 docs/agents.md**
   - 添加 "Other Agents" 章节
   - 链接到 guides/

2. **更新 docs/index.html**
   - 添加 multi-agent 入口

3. **更新 README.md**
   - 添加支持的 agent 列表

4. **创建 docs/guides/index.md**
   - guides 目录索引

### 工作量估算

| 任务 | 时间 |
|------|------|
| 更新现有文档 | 0.5 天 |
| 创建索引 | 0.25 天 |
| 链接验证 | 0.25 天 |
| **总计** | **1 天** |

---

## Phase 6: Community Outreach

### 目标

在各 agent 社区推广 Invar 集成。

### 渠道

| Agent | 社区渠道 | 行动 |
|-------|----------|------|
| Cline | GitHub Issues/Discussions | 提交集成示例 |
| Cursor | Forum, Discord | 分享 hooks 配置 |
| Aider | GitHub Discussions | 展示 auto-lint 集成 |
| Continue | Discord, GitHub | MCP 集成示例 |

### 内容

1. **博客文章** - "Using Invar with [Agent]"
2. **GitHub Gist** - 配置片段
3. **讨论帖** - 集成指南

### 工作量估算

| 任务 | 时间 |
|------|------|
| 准备内容 | 1 天 |
| 发布到各社区 | 0.5 天 |
| 回复问题 | 持续 |
| **总计** | **1.5 天** |

---

## Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Documentation                    ✅ COMPLETE      │
│  - docs/guides/ 创建                                        │
│  - 5 个 agent 集成指南                                      │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Template Generation              ⏳ NEXT          │
│  - invar init --agent=X                                     │
│  - 模板文件创建                                             │
│  - 预计: 4.5 天                                             │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: MCP Compatibility Testing        ⏳ PENDING       │
│  - 各 agent MCP 验证                                        │
│  - 预计: 3.5 天                                             │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: Hooks Portability                ⏳ PENDING       │
│  - Cursor hooks 移植                                        │
│  - 预计: 2 天                                               │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: Documentation Integration        ⏳ PENDING       │
│  - 主文档链接                                               │
│  - 预计: 1 天                                               │
├─────────────────────────────────────────────────────────────┤
│  Phase 6: Community Outreach               ⏳ PENDING       │
│  - 社区推广                                                 │
│  - 预计: 1.5 天                                             │
└─────────────────────────────────────────────────────────────┘

总预计: ~13.5 天 (Phase 1 已完成)
```

---

## Success Metrics

| 指标 | 目标 |
|------|------|
| 文档完成度 | ✅ 5/5 agents |
| init --agent 支持 | 0/5 → 5/5 |
| MCP 验证通过 | 0/4 → 4/4 |
| 社区讨论 | 0 → 4+ 帖 |
| 外部用户反馈 | 收集并迭代 |

---

## Risks and Mitigations

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| MCP 兼容性问题 | 中 | 提供 CLI fallback |
| Agent 更新破坏集成 | 低 | 版本锁定 + 文档 |
| Hooks API 变化 | 中 | Cursor hooks 仍是 beta |
| 社区不感兴趣 | 低 | 从最活跃社区开始 |

---

## Dependencies

### 外部依赖

- Cursor 1.7+ (hooks 功能)
- Cline 最新版 (MCP 支持)
- Continue 最新版 (MCP 支持)
- Aider 最新版

### 内部依赖

- LX-02 分析 (已完成)
- 现有 MCP server 实现
- 现有模板系统

---

## Open Questions

1. **是否需要 pi (shittycodingagent) 支持?**
   - 用户量小，但理念相近
   - Skills 格式兼容
   - 决定: Phase 6 后评估

2. **是否创建独立的 npm/pypi 包?**
   - 例如: `@invar/cursor-config`
   - 决定: 根据社区需求

3. **如何处理 agent 版本差异?**
   - 例如: Cursor 1.6 vs 1.7
   - 决定: 文档注明最低版本

---

## Changelog

### 2025-12-28

- ✅ Phase 1 完成
  - 创建 docs/guides/ 目录
  - 创建 multi-agent.md
  - 创建 cline.md
  - 创建 cursor.md
  - 创建 aider.md
  - 创建 continue.md

---

## References

- [LX-02: Agent Portability Analysis](./LX-02-agent-portability-analysis.md)
- [Cline GitHub](https://github.com/cline/cline)
- [Cursor Docs](https://cursor.com/docs)
- [Aider Docs](https://aider.chat/docs)
- [Continue Docs](https://docs.continue.dev/)
