# DX-81: 多 Agent 初始化支持

**Status**: Draft
**Created**: 2026-01-03
**Priority**: Medium
**Type**: Enhancement

---

## Problem

### 当前限制

`invar init` 强制互斥选择 Claude Code 或 Pi，不支持同时配置两个 agent：

```python
# src/invar/shell/commands/init.py:394-396
if claude and pi:
    console.print("[red]Error:[/red] Cannot use --claude and --pi together.")
    raise typer.Exit(1)
```

**用户体验问题：**
```bash
$ invar init --claude --pi
Error: Cannot use --claude and --pi together.
```

### 真实场景需求

#### 场景 1: 团队协作项目
**背景：**
- 团队成员使用不同 agent（有人用 Claude Code，有人用 Pi）
- 需要同一份代码库支持两个 agent

**当前方案（繁琐）：**
1. 选择主 agent 初始化：`invar init --claude`
2. 手动安装另一个 agent 的 hooks：
   ```python
   python3 -c "
   from pathlib import Path
   from invar.shell.pi_hooks import install_pi_hooks
   from rich.console import Console
   install_pi_hooks(Path('.'), Console())
   "
   ```
3. 验证两个 hooks 都安装

**问题：**
- 非标准流程，文档缺失
- 容易出错（手动执行 Python 代码）
- 无法自动化

---

#### 场景 2: 开源项目
**背景：**
- 开源项目需要支持所有 agent
- 贡献者使用不同工具

**当前方案（不完善）：**
- 只能选一个 agent 初始化
- 其他 agent 用户需要自己配置

**问题：**
- 降低贡献者门槛
- 需要额外文档说明

---

#### 场景 3: Agent 切换
**背景：**
- 用户想尝试不同 agent
- 不想删除现有配置

**当前方案（麻烦）：**
- 手动安装新 agent hooks
- 可能遗漏配置

---

## Analysis

### FILE_CATEGORIES 设计分析

```python
FILE_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "required": [
        ("INVAR.md", "Protocol and contract rules"),
        (".invar/", "Config, context, examples"),
    ],
    "optional": [
        (".pre-commit-config.yaml", "Verification before commit"),
        ("src/core/", "Pure logic directory"),
        ("src/shell/", "I/O operations directory"),
    ],
    "claude": [
        ("CLAUDE.md", "Agent instructions"),
        (".claude/skills/", "Workflow automation"),
        (".claude/commands/", "User commands (/audit, /guard)"),
        (".claude/hooks/", "Tool guidance (+ settings.local.json)"),
        (".mcp.json", "MCP server config"),
    ],
    "pi": [
        ("CLAUDE.md", "Agent instructions (Pi compatible)"),
        (".claude/skills/", "Workflow automation (Pi compatible)"),
        (".pi/hooks/", "Pi-specific hooks"),
    ],
}
```

### 文件冲突分析

| 文件/目录 | Claude | Pi | 冲突？ | 说明 |
|----------|--------|-----|--------|------|
| **CLAUDE.md** | ✅ | ✅ | ❌ 无冲突 | 通用 agent 指令，完全共享 |
| **.claude/skills/** | ✅ | ✅ | ❌ 无冲突 | 平台无关，完全共享 |
| **.claude/commands/** | ✅ | ✅ | ❌ 无冲突 | 文档类文件，完全共享 |
| **.claude/hooks/** | ✅ | ❌ | ❌ 无冲突 | Claude 专用（Shell 脚本） |
| **.pi/hooks/** | ❌ | ✅ | ❌ 无冲突 | Pi 专用（TypeScript） |
| **.mcp.json** | ✅ | ❌ | ❌ 无冲突 | Claude 专用（MCP 配置） |
| **.claude/settings.local.json** | ✅ | ⚠️ | ⚠️ 部分共用* | Feedback 配置位置 |

*注：Feedback 配置当前写在 `.claude/settings.local.json`，Pi 无独立配置文件（已知限制）。

**结论：✅ 无文件冲突，设计上完全隔离**

---

### 磁盘占用分析

```
仅 Claude Code: ~1.2 MB
├── .claude/hooks/       (Shell 脚本，~50 KB)
├── .mcp.json            (~1 KB)
└── 共享文件              (~1.15 MB)

仅 Pi: ~1.0 MB
├── .pi/hooks/           (TypeScript，~30 KB)
└── 共享文件              (~1.15 MB)

双 Agent: ~1.3 MB
├── .claude/hooks/       (~50 KB)
├── .pi/hooks/           (~30 KB)
├── .mcp.json            (~1 KB)
└── 共享文件              (~1.15 MB)
```

**增量成本：约 100 KB（hooks 文件）**

---

## Solution

### 设计原则

1. **向后兼容：** 保留 `--claude` 和 `--pi` 单独使用
2. **显式优于隐式：** 明确标志，避免默认行为改变
3. **最小改动：** 利用现有基础设施
4. **用户友好：** 交互式多选支持

---

### 方案 A: 移除互斥 + 支持组合标志（推荐）

**命令行接口：**
```bash
# 单个 agent（向后兼容）
invar init --claude
invar init --pi

# 组合标志（新功能）
invar init --claude --pi

# 交互式模式（改进）
invar init  # 多选 checkbox
```

**代码修改：**

```python
# src/invar/shell/commands/init.py

def init(
    # ... 参数保持不变
    claude: bool = typer.Option(False, "--claude", ...),
    pi: bool = typer.Option(False, "--pi", ...),
):
    """Initialize Invar in a project.

    Supports multiple agents via combined flags:
        invar init --claude --pi
    """
    # 移除互斥检查
    # if claude and pi:  # ← 删除这行
    #     console.print("[red]Error:[/red] Cannot use --claude and --pi together.")
    #     raise typer.Exit(1)

    # 确定 agents 列表
    if claude and pi:
        # 新：双 agent 模式
        agents = ["claude", "pi"]
        console.print(f"\n[bold]Invar v{__version__} - Multi-Agent Setup[/bold]")
        console.print("=" * 45)
        console.print("[dim]Configuring for: Claude Code + Pi[/dim]")
    elif claude:
        agents = ["claude"]
        console.print(f"\n[bold]Invar v{__version__} - Quick Setup (Claude Code)[/bold]")
    elif pi:
        agents = ["pi"]
        console.print(f"\n[bold]Invar v{__version__} - Quick Setup (Pi)[/bold]")
    else:
        # 交互式模式
        agents = _prompt_agent_selection()  # ← 改为多选

    # 构建 selected_files
    selected_files: dict[str, bool] = {}

    # 添加所有选中 agents 的文件
    for agent in agents:
        config = AGENT_CONFIGS.get(agent)
        if config:
            category = config["category"]
            for file, _ in FILE_CATEGORIES.get(category, []):
                selected_files[file] = True

    # 添加 optional 类别
    for file, _ in FILE_CATEGORIES.get("optional", []):
        selected_files[file] = True

    # ... 后续逻辑保持不变
```

**交互式多选改进：**

```python
def _prompt_agent_selection() -> list[str]:
    """Prompt user to select agent(s) using checkbox."""
    import questionary

    choices = [
        questionary.Choice("Claude Code (MCP + hooks)", value="claude", checked=True),
        questionary.Choice("Pi Coding Agent (hooks)", value="pi"),
        questionary.Choice("Other (AGENT.md)", value="generic"),
    ]

    # 从 select 改为 checkbox
    selected = questionary.checkbox(
        "Select agent(s) to configure:",
        choices=choices,
        instruction="Space to toggle, Enter to confirm",
        style=_get_prompt_style(),
    ).ask()

    # 处理空选择
    if not selected:
        return ["claude"]  # 默认 Claude Code

    return selected  # 返回列表（可能多个）
```

---

### 方案 B: 新增 `--agents` 标志

**命令行接口：**
```bash
invar init --agents claude,pi
invar init --agents claude
invar init --agents pi,generic
```

**优点：**
- 更清晰的语义
- 易于扩展（支持更多 agent）

**缺点：**
- 与现有 `--claude`, `--pi` 并存，可能混淆
- 需要更多参数验证

**评估：** 不推荐（增加复杂度，破坏一致性）

---

## Implementation

### Phase A: 核心功能（移除互斥）

**文件：** `src/invar/shell/commands/init.py`

**修改 1: 移除互斥检查**
```python
# 删除 394-396 行
# if claude and pi:
#     console.print("[red]Error:[/red] Cannot use --claude and --pi together.")
#     raise typer.Exit(1)
```

**修改 2: 支持多 agent**
```python
# 行 472-503，重构 agents 确定逻辑
if claude or pi:
    agents = []
    if claude:
        agents.append("claude")
    if pi:
        agents.append("pi")

    # 构建 selected_files
    selected_files: dict[str, bool] = {}
    for agent in agents:
        category = AGENT_CONFIGS[agent]["category"]
        for file, _ in FILE_CATEGORIES.get(category, []):
            selected_files[file] = True

    # 添加 optional
    for file, _ in FILE_CATEGORIES["optional"]:
        selected_files[file] = True

    # Feedback 提示（双 agent 时只显示一次）
    feedback_enabled = True
    if len(agents) > 1:
        console.print(f"\n[dim]📊 Configuring for {len(agents)} agents: {', '.join(agents)}[/dim]")
    console.print("[dim]📊 Feedback collection enabled by default (stored locally in .invar/feedback/)[/dim]")
    console.print("[dim]   To disable: Set feedback.enabled=false in .claude/settings.local.json[/dim]")
else:
    # 交互式模式
    agents = _prompt_agent_selection()
    selected_files = _prompt_file_selection(agents)
    feedback_enabled = _prompt_feedback_consent()
```

**修改 3: Hooks 安装逻辑**
```python
# 行 593-599，循环安装所有 agent hooks
for agent in agents:
    if agent == "claude" and selected_files.get(".claude/hooks/", True):
        install_claude_hooks(path, console)
    elif agent == "pi" and selected_files.get(".pi/hooks/", True):
        install_pi_hooks(path, console)
```

---

### Phase B: 交互式多选

**文件：** `src/invar/shell/commands/init.py`

**修改：** `_prompt_agent_selection()` 函数
```python
def _prompt_agent_selection() -> list[str]:
    """Prompt user to select agent(s) using checkbox."""
    import questionary

    choices = [
        questionary.Choice(
            "Claude Code (MCP + hooks)",
            value="claude",
            checked=True  # 默认选中
        ),
        questionary.Choice(
            "Pi Coding Agent (hooks)",
            value="pi",
            checked=False
        ),
        questionary.Choice(
            "Other (AGENT.md)",
            value="generic",
            checked=False
        ),
    ]

    selected = questionary.checkbox(
        "Select agent(s) to configure:",
        choices=choices,
        instruction="[Space to toggle, Enter to confirm, select multiple if needed]",
        style=_get_prompt_style(),
    ).ask()

    # 处理 Ctrl+C 或空选择
    if not selected:
        console.print("[yellow]No agents selected, using Claude Code as default.[/yellow]")
        return ["claude"]

    return selected
```

---

### Phase C: 文档更新

**文件：** `CLAUDE.md`, `README.md`, `.invar/context.md`

**CLAUDE.md 更新：**
```markdown
## Init 命令

### 单 Agent 模式
```bash
invar init --claude  # Claude Code only
invar init --pi      # Pi only
```

### 多 Agent 模式（新）
```bash
invar init --claude --pi  # 同时支持两个 agent
```

### 交互式模式
```bash
invar init  # 可多选 agent（checkbox）
```
```

**README.md 更新：**
```markdown
### Multi-Agent Support

Projects can support multiple AI agents simultaneously:

```bash
# Configure for Claude Code + Pi
invar init --claude --pi

# Or select interactively (checkbox allows multiple)
invar init
```

**File layout:**
- `.claude/hooks/` - Claude Code specific
- `.pi/hooks/` - Pi specific
- `.claude/skills/` - Shared across agents
- `CLAUDE.md` - Universal agent instructions
```

---

## Testing

### 测试用例

#### 1. 单 Agent 模式（回归测试）

```bash
# Test 1: Claude only
cd /tmp/test-single-claude
invar init --claude
assert_exists .claude/hooks/
assert_exists .mcp.json
assert_not_exists .pi/

# Test 2: Pi only
cd /tmp/test-single-pi
invar init --pi
assert_exists .pi/hooks/
assert_not_exists .claude/hooks/
assert_not_exists .mcp.json
```

#### 2. 双 Agent 模式（新功能）

```bash
# Test 3: Claude + Pi
cd /tmp/test-dual-agent
invar init --claude --pi

assert_exists .claude/hooks/
assert_exists .pi/hooks/
assert_exists .mcp.json
assert_exists .claude/skills/
assert_file_count .claude/skills/ 5  # develop, investigate, propose, review, invar-reflect

# Verify hooks work independently
cat .claude/hooks/PreToolUse.sh | grep "invar_guard\|invar guard"
cat .pi/hooks/invar.ts | grep "invar guard"
```

#### 3. 交互式多选

```bash
# Test 4: Interactive checkbox
cd /tmp/test-interactive
# 模拟用户选择 claude + pi（空格选中两个）
echo -e " \n\n" | invar init

assert_exists .claude/hooks/
assert_exists .pi/hooks/
```

#### 4. 文件去重

```bash
# Test 5: Verify no duplicate files
cd /tmp/test-dual-agent
invar init --claude --pi

# CLAUDE.md 不应该重复
file_count=$(find . -name "CLAUDE.md" | wc -l)
assert_equals $file_count 1

# skills 不应该重复
skill_count=$(find .claude/skills/develop -name "SKILL.md" | wc -l)
assert_equals $skill_count 1
```

---

### 集成测试脚本

```bash
#!/bin/bash
# tests/integration/test_multi_agent_init.sh

set -e

echo "Testing multi-agent init support..."

# Cleanup
rm -rf /tmp/invar-test-multi-agent
mkdir -p /tmp/invar-test-multi-agent
cd /tmp/invar-test-multi-agent
touch pyproject.toml

# Test dual-agent init
echo "✓ Test 1: Dual-agent init"
invar init --claude --pi

# Verify Claude files
test -d .claude/hooks || (echo "❌ Missing .claude/hooks" && exit 1)
test -f .mcp.json || (echo "❌ Missing .mcp.json" && exit 1)

# Verify Pi files
test -d .pi/hooks || (echo "❌ Missing .pi/hooks" && exit 1)
test -f .pi/hooks/invar.ts || (echo "❌ Missing .pi/hooks/invar.ts" && exit 1)

# Verify shared files (no duplicates)
claude_md_count=$(find . -name "CLAUDE.md" -type f | wc -l)
test "$claude_md_count" -eq 1 || (echo "❌ CLAUDE.md duplicated" && exit 1)

skills_count=$(find .claude/skills -name "SKILL.md" -type f | wc -l)
test "$skills_count" -eq 5 || (echo "❌ Expected 5 skills, found $skills_count" && exit 1)

# Verify feedback config
grep -q "feedback" .claude/settings.local.json || (echo "❌ Missing feedback config" && exit 1)

echo "✅ All tests passed"

# Cleanup
cd /
rm -rf /tmp/invar-test-multi-agent
```

---

## Compatibility

### 向后兼容性

**✅ 完全兼容：**

| 场景 | 旧行为 | 新行为 | 兼容性 |
|------|--------|--------|--------|
| `invar init --claude` | 仅 Claude | 仅 Claude | ✅ 不变 |
| `invar init --pi` | 仅 Pi | 仅 Pi | ✅ 不变 |
| `invar init` (交互式) | 单选 | 多选 | ⚠️ 改进* |
| `invar init --claude --pi` | Error | Claude + Pi | ✅ 新功能 |

*交互式改为多选可能改变用户习惯，但体验更好（更灵活）。

**迁移指南：**

无需迁移。现有项目继续工作。

如需添加第二个 agent：
```bash
# 选项 1: 重新 init（安全，会 merge）
invar init --claude --pi

# 选项 2: 单独安装 hooks
python3 -c "
from pathlib import Path
from invar.shell.pi_hooks import install_pi_hooks
from rich.console import Console
install_pi_hooks(Path('.'), Console())
"
```

---

### 已知限制

#### 1. Feedback 配置位置

**问题：**
Feedback 配置写在 `.claude/settings.local.json`，Pi 无独立配置文件。

**影响：**
- Claude Code 用户可通过配置文件禁用 feedback
- Pi 用户无法通过配置文件禁用（需修改 init 逻辑或手动删除 `.invar/feedback/`）

**解决方案（未来）：**
- 支持 `.pi/settings.json`（需要另一个 DX proposal）
- 或使用通用配置文件 `.invar/config.toml`

**当前行为：**
- 两个 agent 都默认启用 feedback
- 都存储在 `.invar/feedback/`（共享目录）

---

#### 2. MCP 配置

**问题：**
`.mcp.json` 只有 Claude Code 需要，Pi 不使用。

**当前行为：**
双 agent 模式会创建 `.mcp.json`（即使 Pi 不用）。

**影响：**
无实际影响，Pi 忽略此文件。

**替代方案：**
可以在 Pi-only 模式跳过 `.mcp.json` 创建，但当前设计选择总是创建（便于后续添加 Claude Code）。

---

## Timeline

### Phase A: 核心功能（1-2 小时）
- [ ] 移除互斥检查
- [ ] 重构 agents 列表逻辑
- [ ] 更新 hooks 安装循环
- [ ] 单元测试

### Phase B: 交互式多选（1 小时）
- [ ] 修改 `_prompt_agent_selection()` 为 checkbox
- [ ] 更新提示文本
- [ ] 测试交互流程

### Phase C: 文档和测试（2 小时）
- [ ] 更新 CLAUDE.md
- [ ] 更新 README.md
- [ ] 集成测试脚本
- [ ] 手动测试所有场景

**总计：4-5 小时**

---

## Alternatives Considered

### 替代方案 1: `invar init --both`

**命令：**
```bash
invar init --both  # 等价于 --claude --pi
```

**评估：**
- ❌ 只支持两个 agent，不可扩展（未来可能有第三个 agent）
- ❌ 语义不够清晰（"both" 是哪两个？）
- ✅ 更短的命令

**结论：** 不推荐（可扩展性差）

---

### 替代方案 2: 配置文件驱动

**方案：**
在 `pyproject.toml` 或 `.invar/config.toml` 中指定 agents：

```toml
[tool.invar.agents]
enabled = ["claude", "pi"]
```

然后运行：
```bash
invar init  # 读取配置文件
```

**评估：**
- ✅ 声明式配置
- ✅ 便于版本控制
- ❌ 增加复杂度（需要文件解析）
- ❌ 对 quick setup 不友好

**结论：** 可作为未来改进（DX-82），但不适合初始实现

---

### 替代方案 3: 后安装脚本

**方案：**
保持当前互斥，提供官方安装脚本：

```bash
# scripts/add_agent.sh
#!/bin/bash
AGENT=$1  # claude or pi
if [ "$AGENT" == "pi" ]; then
    python3 -c "..."  # 安装 Pi hooks
elif [ "$AGENT" == "claude" ]; then
    python3 -c "..."  # 安装 Claude hooks
fi
```

**评估：**
- ✅ 不改动核心代码
- ❌ 非标准流程
- ❌ 需要额外文档
- ❌ 用户体验差

**结论：** 不推荐（治标不治本）

---

## Open Questions

### Q1: 是否支持三个及以上 agent？

**当前设计：** 支持任意数量（`agents` 是列表）

**实际情况：**
- 目前只有 `claude`, `pi`, `generic` 三个选项
- 未来可能增加（如 Cursor, Windsurf 等）

**建议：** 设计上支持多个，实现上暂时只测试 2 个组合

---

### Q2: 交互式模式默认选中哪些？

**当前建议：**
- Claude Code: 默认选中（主流）
- Pi: 默认不选中
- Generic: 默认不选中

**理由：**
- 大多数用户只需要一个 agent
- 默认选中 Claude 降低门槛
- 用户可按需添加 Pi

**备选：**
- 不默认选中任何（强制用户主动选择）
- 根据项目已有文件智能选中（如存在 `.pi/` 则选中 Pi）

**决策：** 默认选中 Claude（与当前行为一致）

---

### Q3: 是否需要 `invar init --remove-agent`？

**场景：**
用户想移除某个 agent 的配置。

**当前方案：**
手动删除对应目录（如 `rm -rf .pi/`）

**是否需要命令：**
- ✅ 更安全（避免误删）
- ✅ 更清晰（显式操作）
- ❌ 增加复杂度

**建议：** 后续 proposal（DX-82）处理，不在本 proposal 范围

---

## Success Metrics

发布后 30 天内：

1. **采用率：** 至少 5% 的新项目使用双 agent 配置
2. **错误率：** 双 agent init 零错误报告
3. **文档访问：** 多 agent 文档页面访问量 > 100
4. **用户反馈：** 无负面反馈（回归问题）

---

## References

- **FILE_CATEGORIES 设计：** `src/invar/shell/commands/init.py:39-64`
- **Claude hooks：** `src/invar/shell/claude_hooks.py`
- **Pi hooks：** `src/invar/shell/pi_hooks.py`
- **相关 issues：** DX-80（Tool Selection 文档）

---

## Decision

**推荐：** 方案 A（移除互斥 + 支持组合标志）

**理由：**
1. ✅ 最小改动，利用现有基础设施
2. ✅ 向后兼容，不破坏现有工作流
3. ✅ 可扩展，支持未来更多 agent
4. ✅ 用户友好，交互式多选体验好

**实施优先级：** Medium（非紧急，但有明确需求）

**下一步：**
1. 征求社区反馈（GitHub Discussion）
2. 如无异议，开始 Phase A 实现
3. 集成测试后发布 v1.15.0

---

**Status**: Awaiting Review
