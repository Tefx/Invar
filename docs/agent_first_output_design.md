# Invar 输出格式变更：Agent First

## 设计原则：Agent First

**核心理念**：
> Agent Native ≠ 仅用于 AI
> Agent Native = 机器可读的默认输出，人类可读作为 opt-in

**变更理由**：
1. **一致性**：所有场景默认为 JSON，降低认知负担
2. **可编程性**：脚本、CI/CD、Agent 都直接使用 JSON
3. **灵活性**：`--human` 提供人类可读输出
4. **MCP 修复**：`structuredContent` 支持真正的 Agent Native

---

## 行为对比表

| 场景 | 命令 | 旧行为 | 新行为 |
|-------|--------|--------|--------|
| **CLI 终端** | `invar guard` | Rich 彩色 | **JSON** 🔴 变更 |
| **CLI --human** | `invar guard --human` | Rich 彩色 | Rich 彩色 ✅ |
| **CLI --agent** | `invar guard --agent` | JSON | JSON ✅ |
| **CLI 管道** | `invar guard \| jq .` | JSON | JSON ✅ |
| **MCP 调用** | `invar_guard(changed=true)` | TextContent | **structuredContent** ✅ |

---

## 详细场景

### 场景 1：CLI 终端（默认）⚠️ 行为变更

**命令**：
```bash
invar guard
invar guard --changed
invar guard src/myapp/core
```

**旧输出**：
```
Invar Guard Report
========================================
No violations found.
----------------------------------------
Files checked: 1 | Errors: 0 | Warnings: 0
Contract coverage: 100% (1/1 functions)

Code Health: 100% ████████████████████ (Excellent)
✓ Doctests passed
✓ CrossHair: no counterexamples found
✓ Hypothesis: property tests passed
----------------------------------------
Guard passed.
```

**新输出**：
```json
{
  "status": "passed",
  "errors": 0,
  "warnings": 0,
  "infos": 0,
  "suggests": 0,
  "files_checked": 1,
  "violations": [],
  "contract_coverage": {
    "total": 1,
    "with_contracts": 1,
    "percentage": 100.0
  },
  "verification_level": "standard",
  "doctest": {
    "passed": true,
    "output": ""
  },
  "crosshair": {
    "status": "verified",
    "proven": 1,
    "time_seconds": 0.5
  },
  "property_tests": {
    "status": "passed",
    "tested": 1,
    "examples": 100
  },
  "routing": {
    "crosshair_proven": 1,
    "hypothesis_tested": 0,
    "doctests_passed": 1,
    "routed_to_hypothesis": 0
  }
}
```

**影响**：
- ✅ 脚本可直接解析
- ✅ Agent 可直接使用
- ⚠️ 人类用户看到的是 JSON

---

### 场景 2：CLI --human（人类可读）✅ 推荐

**命令**：
```bash
invar guard --human
invar guard --changed --human
```

**输出**：Rich 格式化（与旧默认行为相同）

```
Invar Guard Report
========================================
No violations found.
----------------------------------------
Files checked: 1 | Errors: 0 | Warnings: 0
Contract coverage: 100% (1/1 functions)

Code Health: 100% ████████████████████ (Excellent)
✓ Doctests passed
✓ CrossHair: no counterexamples found
✓ Hypothesis: property tests passed
----------------------------------------
Guard passed.
```

**用途**：
- 人类用户交互式使用
- 调试和可视化
- 快速浏览结果

---

### 场景 3：CLI --agent（JSON）

**命令**：
```bash
invar guard --agent
```

**输出**：JSON（与默认行为相同）

```json
{
  "status": "passed",
  ...
}
```

**注意**：
- `--agent` 标志现在为 no-op（与默认相同）
- 保留是为了向后兼容
- 文档可以标注为"已废弃"

---

### 场景 4：CLI 管道（JSON）

**命令**：
```bash
invar guard | jq .
invar guard > result.json
```

**输出**：JSON（无变化）

```json
{
  "status": "passed",
  ...
}
```

---

### 场景 5：MCP 调用（结构化对象）✅ 修复

**MCP 工具调用**：
```python
invar_guard(changed=true, strict=false, coverage=true)
```

**修复前**：
```json
{
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"status\": \"passed\", ...}"
    }],
    "isError": false
  }
}
```

**修复后**：
```json
{
  "result": {
    "content": [{
      "type": "text",
      "text": "{\n  \"status\": \"passed\",\n  ...\n}"
    }],
    "structuredContent": {
      "status": "passed",
      "errors": 0,
      "warnings": 0,
      "infos": 0,
      "suggests": 0,
      "files_checked": 1,
      "violations": [],
      "contract_coverage": {
        "total": 1,
        "with_contracts": 1,
        "percentage": 100.0
      },
      "verification_level": "standard",
      "doctest": {
        "passed": true,
        "output": ""
      },
      "crosshair": {
        "status": "verified",
        "proven": 1,
        "time_seconds": 0.5
      },
      "property_tests": {
        "status": "passed",
        "tested": 1,
        "examples": 100
      },
      "routing": {
        "crosshair_proven": 1,
        "hypothesis_tested": 0,
        "doctests_passed": 1,
        "routed_to_hypothesis": 0
      },
      "coverage": {
        "phases_tracked": ["doctest", "hypothesis"],
        "overall_branch_coverage": 85.0
      }
    },
    "isError": false
  }
}
```

**优势**：
- Agent 直接访问 `structuredContent`（真正的 JSON 对象）
- `content` 保留格式化 JSON 文本（向后兼容）
- 符合 MCP 规范的结构化内容

---

## 输出模式决策逻辑

### 新逻辑（guard.py）

```python
def _determine_output_mode(
    human: bool,
    agent: bool = False,
    json_output: bool = False
) -> bool:
    """Determine if agent JSON output should be used.

    NEW: Agent First - JSON is default, human output is opt-in.

    Priority:
    1. --human flag → human output (Rich)
    2. 默认 → JSON output (machine-readable)
    3. --agent/--json flags → JSON output (no-op, kept for compat)
    """
    # 1. --human 强制人类输出（优先级最高）
    if human:
        return False  # use_agent = False

    # 2. 默认行为：JSON（Agent First）
    # --agent/--json 现在是 no-op，但保留向后兼容
    return True
```

**移除**：
- ❌ TTY 自动检测逻辑（`_detect_agent_mode()`）
- ❌ `INVAR_MODE` 环境变量检测

---

## 实现清单

### 1. CLI 输出模式变更

**文件**：`src/invar/shell/commands/guard.py`

**修改**：

```python
# 旧逻辑（DX-26: TTY auto-detection）
def _determine_output_mode(human: bool, agent: bool = False, json_output: bool = False) -> bool:
    if human:
        return False
    if json_output or agent:
        return True
    return _detect_agent_mode()  # TTY 检测

# 新逻辑（Agent First）
def _determine_output_mode(human: bool, agent: bool = False, json_output: bool = False) -> bool:
    """Determine output mode with Agent First principle.

    - --human: Rich output (human-readable)
    - Default: JSON output (machine-readable)
    - --agent/--json: No-op (already default)
    """
    if human:
        return False  # --human 强制 Rich 输出

    # 默认 JSON 输出
    return True
```

**废弃**：
- `_detect_agent_mode()` 函数
- TTY 检测逻辑
- `INVAR_MODE` 环境变量

---

### 2. MCP Handler 修复

**文件**：`src/invar/mcp/handlers.py`

**修改**：

```python
async def _execute_command(
    cmd: list[str],
    timeout: int = 600
) -> list[TextContent] | tuple[list[TextContent], dict]:
    """Execute command and return result.

    Returns:
        - If stdout is valid JSON: (list[TextContent], dict) - structured + unstructured
        - Otherwise: list[TextContent] - unstructured only

    This enables Agent Native output with `structuredContent` field.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 尝试解析为 JSON
        try:
            parsed = json.loads(result.stdout)
            # 返回 tuple: (unstructured, structured)
            # MCP Server 会自动将 dict 放入 structuredContent
            return ([TextContent(type="text", text=json.dumps(parsed, indent=2))], parsed)
        except json.JSONDecodeError:
            # 非 JSON 输出（错误消息）
            output = result.stdout
            if result.stderr:
                output += f"\n\nStderr:\n{result.stderr}"
            return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text=f"Error: Command timed out ({timeout}s}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]
```

**更新所有 handlers 的返回类型**：

```python
# 修改前
async def _run_guard(args: dict[str, Any]) -> list[TextContent]:
    ...
    return await _execute_command(cmd)

# 修改后
async def _run_guard(args: dict[str, Any]) -> list[TextContent] | tuple[list[TextContent], dict]:
    ...
    return await _execute_command(cmd)
```

**受影响的 handlers**：
- `_run_guard`
- `_run_sig`
- `_run_map`
- `_run_refs`
- `_run_doc_toc`
- `_run_doc_read`
- `_run_doc_read_many`
- `_run_doc_find`
- `_run_doc_replace`
- `_run_doc_insert`
- `_run_doc_delete`

---

## 用户影响分析

### 受益用户

1. **Agent 用户**
   - 直接使用 `structuredContent`
   - 无需解析 JSON 文本
   - 符合 Agent Native 原则

2. **脚本/CI/CD 用户**
   - 默认 JSON 可直接解析
   - 无需添加 `--agent` 或管道
   - 更可预测的行为

3. **新用户**
   - 一致的 JSON 输出
   - 降低学习成本
   - 更容易集成到工具链

### 需要调整的用户

1. **交互式终端用户**
   - 旧行为：`invar guard` → Rich 彩色
   - 新行为：`invar guard` → JSON
   - 调整：使用 `invar guard --human`

2. **插件/集成依赖 Rich 输出**
   - 如果依赖 Rich 格式（如进度条）
   - 调整：使用 `--human` 标志

---

## 迁移指南

### 对于终端用户

**建议**：
1. 创建别名（bash/zsh）：
   ```bash
   alias invh='invar guard --human'  # 人类可读输出
   alias inva='invar guard'          # JSON 输出
   ```

2. 更新工作流：
   - 交互式开发：`invar guard --human`
   - 脚本集成：`invar guard | jq .`

3. 文档更新：
   - 示例使用 `--human` 标志
   - 说明默认 JSON 输出

### 对于 Agent 用户

**无需改变**：
- 直接使用 MCP 工具
- 访问 `structuredContent` 字段
- 享受 Agent Native 体验

### 对于脚本用户

**简化**：
```bash
# 旧方式
invar guard --agent | jq .status

# 新方式（--agent 不再需要）
invar guard | jq .status
```

---

## 向后兼容性

### 保留的功能

| 功能 | 状态 |
|------|------|
| `--human` 标志 | ✅ 保留（优先级最高） |
| `--agent` 标志 | ✅ 保留（no-op） |
| `--json` 标志 | ✅ 保留（no-op） |
| JSON 输出格式 | ✅ 完全兼容 |
| Rich 输出格式 | ✅ 通过 `--human` |
| MCP 协议 | ✅ 符合规范 |

### 废弃的功能

| 功能 | 状态 | 替代方案 |
|------|------|----------|
| TTY 自动检测 | ❌ 移除 | 始终输出 JSON |
| `INVAR_MODE` 环境变量 | ❌ 移除 | 无需 |
| 终端默认 Rich | ❌ 改变 | 使用 `--human` |

---

## 测试清单

### CLI 测试

```bash
# 1. 默认 JSON 输出（新行为）
invar guard | jq .status  # 应输出 JSON
invar guard | jq .errors    # 应输出数字

# 2. --human Rich 输出（保留）
invar guard --human        # 应 Rich 格式化
invar guard --human --changed  # 应 Rich 格式化

# 3. --agent（no-op，但保留）
invar guard --agent | jq .status  # 应 JSON

# 4. 管道（无变化）
invar guard > result.json && cat result.json | jq .
```

### MCP 测试

```python
# 1. 调用 invar_guard
result = await invar_guard(changed=True)

# 2. 检查响应结构
assert hasattr(result, 'structuredContent')
assert isinstance(result.structuredContent, dict)

# 3. 验证数据完整性
assert 'status' in result.structuredContent
assert 'violations' in result.structuredContent

# 4. 检查 content 字段（向后兼容）
assert isinstance(result.content[0].text, str)
json.loads(result.content[0].text)  # 应可解析
```

### 集成测试

```bash
# 1. 脚本解析
invar guard | jq -r '.status'  # 应输出 "passed" 或 "failed"

# 2. CI/CD 集成
invar guard --changed
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo "Guard passed"
else
  echo "Guard failed"
fi
```

---

## 文档更新

### README 更新

```markdown
## 输出格式

**默认**：机器可读的 JSON（Agent Native）

```bash
$ invar guard
{
  "status": "passed",
  "errors": 0,
  ...
}
```

**人类可读**：添加 `--human` 标志

```bash
$ invar guard --human
Invar Guard Report
========================================
...
```

**向后兼容**：
- `--agent`、`--json` 标志保留（现为 no-op）
- `--human` 提供彩色 Rich 输出
```

### CLAUDE.md 更新

```markdown
### Tool Substitution Rules (ENFORCED)

| Task | ❌ NEVER Use | ✅ ALWAYS Use |
|------|-------------|---------------|
| Verify code quality | `Bash("pytest ...")` | `invar_guard` |

### Output Formats

- **CLI**: JSON by default (use `--human` for Rich output)
- **MCP**: `structuredContent` field (Agent Native)
```

---

## 发布说明

### Breaking Changes

⚠️ **CLI 默认输出从 Rich 改为 JSON**

- **影响**：终端用户看到的是 JSON 而非彩色文本
- **迁移**：使用 `invar guard --human` 获得人类可读输出
- **理由**：Agent First 原则，统一输出格式

### Features

✅ **MCP `structuredContent` 支持**

- Agent 直接访问结构化 JSON 对象
- 符合 MCP 规范
- 真正的 Agent Native 体验

### Deprecations

🚫 **TTY 自动检测移除**

- 环境不再根据 TTY 自动切换输出
- 使用 `--human` 标志明确控制

---

## 总结

| 维度 | 状态 |
|------|------|
| **Agent First** | ✅ 默认 JSON |
| **MCP structuredContent** | ✅ 完整支持 |
| **向后兼容** | ✅ 通过 `--human` |
| **用户选择** | ✅ JSON/Rich 都可用 |
| **Agent 体验** | ✅ 大幅提升 |
| **人类体验** | ✅ 通过 `--human` |

**设计原则**：
> Agent Native = 机器可读的默认输出，人类可读作为 opt-in

**实施策略**：
1. 修改 CLI 输出决策逻辑（移除 TTY 检测）
2. 修复 MCP handler 返回类型（支持 `structuredContent`）
3. 更新文档和示例
4. 清晰的迁移指南
