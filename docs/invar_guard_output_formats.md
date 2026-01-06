# Invar Guard 输出格式总结

## 修复前 vs 修复后对比

### 核心问题
**修复前**：所有 MCP 工具返回 `list[TextContent]`，Agent 接收到文本形式的 JSON
**修复后**：MCP 工具返回 `(list[TextContent], dict)`，Agent 接收到真正的结构化 JSON

---

## CLI 模式（直接调用命令行）

### 场景 1：默认（终端 TTY）

**命令**：
```bash
invar guard
invar guard --changed
invar guard src/myapp/core
```

**输出格式**：Rich 格式化（彩色、表格、进度条）

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

**特点**：
- 彩色输出（使用 Rich 库）
- 文件名高亮、图标指示
- 进度条显示 Code Health
- 易读的表格和分组

---

### 场景 2：--human（强制人类可读）

**命令**：
```bash
invar guard --human
invar guard --changed --human
```

**输出格式**：与默认相同（Rich 格式化）

```
Invar Guard Report
========================================
No violations found.
----------------------------------------
...
（与场景 1 完全相同）
```

**用途**：
- 测试/调试时确保人类可读输出
- 覆盖自动 TTY 检测

---

### 场景 3：--agent（强制 JSON）

**命令**：
```bash
invar guard --agent
invar guard --changed --agent
```

**输出格式**：JSON（打印到 stdout）

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
  },
  "coverage": {
    "phases_tracked": ["doctest", "hypothesis"],
    "overall_branch_coverage": 85.0
  }
}
```

**用途**：
- 脚本解析、CI/CD 集成
- 测试 Agent 输出格式
- 日志收集和分析

---

### 场景 4：管道/重定向（自动 JSON）

**命令**：
```bash
invar guard | jq .
invar guard > result.json
cat result.json | jq .status
```

**输出格式**：JSON（自动检测非 TTY）

```json
{
  "status": "passed",
  "errors": 0,
  "warnings": 0,
  ...
}
```

**自动检测逻辑**（`guard.py:435`）：
```python
def _detect_agent_mode() -> bool:
    """Detect agent context: INVAR_MODE=agent OR non-TTY (pipe/redirect)."""
    import sys
    return os.getenv("INVAR_MODE") == "agent" or not sys.stdout.isatty()
```

---

## MCP 模式（通过 MCP Server 调用）

### 场景 1：默认（Agent 调用）

**MCP 工具调用**：
```python
# Agent 调用
invar_guard(changed=true, strict=false, coverage=true)
```

**修复前**（问题）：
```json
{
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\": \"passed\", \"errors\": 0, ...}"
      }
    ],
    "isError": false
  }
}
```

**问题**：
- Agent 只看到 `type: "text"` 的内容
- 即使内容是 JSON 字符串，仍需手动解析
- 违反 Agent Native 原则

---

### 场景 2：修复后（结构化 JSON）

**修复后**：
```json
{
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"status\": \"passed\",\n  \"errors\": 0,\n  ...\n}"
      }
    ],
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
- **Agent Native**：Agent 直接访问 `structuredContent` 中的对象
- **向后兼容**：`content` 字段仍包含格式化的 JSON 文本
- **类型安全**：MCP 库自动验证 `structuredContent` 符合 schema

---

## 完整对比表

| 模式 | 命令/调用 | 参数 | 输出格式 | Agent 原生 | 修复后 |
|------|------------|------|-----------|-----------|--------|
| **CLI 终端** | `invar guard` | 默认 | Rich 彩色文本 | N/A | N/A |
| **CLI --human** | `invar guard --human` | `--human` | Rich 彩色文本 | N/A | N/A |
| **CLI --agent** | `invar guard --agent` | `--agent` | JSON 字符串 | ❌ | ✅ |
| **CLI 管道** | `invar guard \| jq .` | 无 | JSON 字符串 | ❌ | ✅ |
| **MCP 调用** | `invar_guard(changed=true)` | 自动检测 | TextContent | ❌ | ✅ |

---

## 实现细节

### CLI 输出决策（`guard.py:417-436`）

```python
def _determine_output_mode(human: bool, agent: bool = False, json_output: bool = False) -> bool:
    """Determine if agent JSON output should be used."""
    # 1. --human flag → human output (优先级最高)
    if human:
        return False

    # 2. --agent/--json flags → JSON output
    if json_output or agent:
        return True

    # 3. TTY auto-detection → 默认行为
    return _detect_agent_mode()  # True = 非TTY
```

**优先级**：`--human` > `--agent`/`--json` > TTY 检测

---

### MCP 输出转换（修复后）

**handlers.py: _execute_command**：
```python
async def _execute_command(cmd: list[str], timeout: int = 600):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # 尝试解析为 JSON
    try:
        parsed = json.loads(result.stdout)
        # 返回 tuple: (unstructured, structured)
        return ([TextContent(type="text", text=json.dumps(parsed, indent=2))], parsed)
    except json.JSONDecodeError:
        # 非 JSON 输出（错误消息）
        output = result.stdout
        if result.stderr:
            output += f"\n\nStderr:\n{result.stderr}"
        return [TextContent(type="text", text=output)]
```

**MCP Server 自动处理**：
- `dict` 返回值 → 放入 `structuredContent` + 生成 `content`
- `list[TextContent]` 返回值 → 仅放入 `content`

---

## Agent 体验改进

### 修复前

```python
# Agent 看到的输出
result = await invar_guard(changed=True)
content = result[0].text  # 获取文本
data = json.loads(content)  # 手动解析
status = data["status"]    # 使用数据
```

### 修复后

```python
# Agent 直接获取结构化数据
result = await invar_guard(changed=True)
# result 是 MCP 返回的 ServerResult
data = result.structuredContent  # 直接获取字典
status = data["status"]         # 无需解析
```

**优势**：
- 减少代码复杂度
- 避免解析错误
- 类型提示友好（`dict[str, Any]`）

---

## 向后兼容性

所有场景保持向后兼容：

1. **旧 Agent**：仍可通过 `content` 字段获取 JSON 文本
2. **新 Agent**：直接使用 `structuredContent` 获取结构化数据
3. **非 MCP 调用**：无任何影响（CLI 模式不变）

---

## 测试建议

### CLI 测试

```bash
# 测试终端输出（应 Rich 格式化）
invar guard

# 测试 --human（应 Rich 格式化）
invar guard --human

# 测试 --agent（应 JSON）
invar guard --agent | jq .

# 测试管道（应 JSON）
invar guard > result.json && cat result.json | jq .status
```

### MCP 测试

```python
# 使用 Claude Code 或 Pi 测试
# 1. 调用 invar_guard
# 2. 检查响应中是否有 structuredContent
# 3. 验证 structuredContent 为有效的 JSON 对象
```

---

## 总结

| 维度 | 状态 |
|------|------|
| **CLI 人类输出** | ✅ 完美（Rich） |
| **CLI JSON 输出** | ✅ 完美 |
| **MCP 结构化输出** | 🔧 需要修复 |
| **Agent Native** | 🔧 修复后实现 |
| **向后兼容** | ✅ 完全兼容 |
| **TTY 自动检测** | ✅ 工作正常 |

**修复后**：
- CLI 模式：无变化（继续使用 Rich/JSON）
- MCP 模式：符合 Agent Native（返回 `structuredContent`）
- Agent 体验：大幅提升（直接访问结构化数据）
