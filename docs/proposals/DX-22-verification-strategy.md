# DX-22: 智能验证策略

> **"正确的工具用于正确的代码，强制执行而非建议"**

## 状态

- **ID**: DX-22
- **状态**: Draft
- **依赖**: DX-12 (Hypothesis fallback), DX-13 (Incremental prove)
- **关联**: DX-23 (Entry point detection)

## 问题陈述

当前验证系统存在以下问题：

1. **重复验证**: CrossHair 和 Hypothesis 都运行在相同代码上，浪费时间
2. **错误分类**: C 扩展代码尝试 CrossHair 后失败，没有智能 fallback
3. **Shell 无覆盖**: Shell 模块完全没有自动化测试，架构问题无人检测
4. **统计误导**: 覆盖率重复计算，不区分"证明"和"测试"
5. **警告被忽略**: INFO/WARNING 级别的建议 Agent 可以直接跳过

## 设计原则

### Agent-Native

```
自动 > 手动
默认正确 > 需要配置
零决策 > 多选项
强制执行 > 建议忽略
```

### 配置极简

```
❌ 不要: 暴露每个内部参数
✅ 要: 只保留人类真正需要调整的选项
```

### Fix-or-Explain

```
❌ 不要: 警告可以无限忽略
✅ 要: 必须修复 OR 显式说明理由
```

---

## 解决方案概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DX-22 核心改进                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 智能验证分流                                                    │
│     Core + 纯 Python  → CrossHair (证明)                            │
│     Core + C 扩展     → Hypothesis (测试)  ← 自动检测               │
│     Shell             → Doctests + 架构规则                         │
│                                                                     │
│  2. Shell 架构规则 (详见 DX-23)                                     │
│     shell_pure_logic  → ERROR (必须移到 Core)                       │
│     shell_too_complex → INFO + 模式检测 + 重构建议                  │
│     entry_point       → 框架回调豁免 Result，但需保持精简           │
│                                                                     │
│  3. Fix-or-Explain 强制                                             │
│     单个警告 → 显示建议                                             │
│     累积 5+ → ERROR 阻止                                            │
│     @shell_complexity 标记 → 解除警告                               │
│                                                                     │
│  4. 去重统计                                                        │
│     CrossHair 证明的 → 不重复计入 Hypothesis                        │
│     分类显示证明/测试覆盖率                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: 智能验证分流

### 1.1 代码自动分类

```
文件自动分类（无需配置）：
┌─────────────────────────────────────────────────────────────┐
│ 输入: Python 文件                                           │
│                                                             │
│ 分析:                                                       │
│   1. 检测 import 语句 → 是否有 C 扩展库                     │
│   2. 检测 @pre/@post 契约 → 是否可验证                      │
│   3. 检测 Core/Shell 分类 → 适用什么规则                    │
│                                                             │
│ 输出:                                                       │
│   ┌─────────────┬──────────────┬────────────────────────┐  │
│   │ 类型        │ 验证策略      │ 示例                   │  │
│   ├─────────────┼──────────────┼────────────────────────┤  │
│   │ Core+纯Py   │ CrossHair    │ parser.py, rules.py    │  │
│   │ Core+C扩展  │ Hypothesis   │ (如有 numpy 依赖)      │  │
│   │ Shell       │ Doctests     │ cli.py, fs.py          │  │
│   │ 无契约      │ 跳过         │ __init__.py            │  │
│   └─────────────┴──────────────┴────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 验证流程

```python
def smart_verify(file: Path) -> VerificationResult:
    """智能选择验证策略 - Agent-Native: 零决策"""

    source = file.read_text()
    has_contracts = detect_contracts(source)
    is_pure_python = not has_incompatible_imports(source)
    is_core = file_info.is_core

    if not has_contracts:
        return Skip("no_contracts")

    if is_core and is_pure_python:
        # Core + 纯 Python: CrossHair 优先
        result = run_crosshair(file)
        if result.proven:
            return Proven(tool="crosshair")  # 无需 Hypothesis
        if result.error or result.timeout:
            return run_hypothesis(file)      # Fallback
        return result

    if is_core and not is_pure_python:
        # Core + C扩展: 直接 Hypothesis（不浪费时间尝试 CrossHair）
        return run_hypothesis(file)

    # Shell: 仅 Doctests + 架构规则
    return Skip("shell_doctest_only")
```

### 1.3 不兼容库检测（内置）

```python
# 内置黑名单 - 不暴露为配置项
CROSSHAIR_INCOMPATIBLE = frozenset([
    # C 扩展 (无法符号化)
    "numpy", "pandas", "scipy", "sklearn",
    "torch", "tensorflow", "cv2", "PIL",
    # 网络 I/O (非确定性)
    "requests", "aiohttp", "httpx",
    # 系统调用 (副作用)
    "subprocess", "multiprocessing",
])

def has_incompatible_imports(source: str) -> bool:
    """检测是否包含 CrossHair 不兼容的库"""
    for lib in CROSSHAIR_INCOMPATIBLE:
        if f"import {lib}" in source or f"from {lib}" in source:
            return True
    return False
```

### 1.4 去重统计报告

```
改进前 (重复计算，误导):
  CrossHair: 149/149 ✓
  Hypothesis: 149/149 ✓     ← 重复！
  Doctests: 149/149 ✓

改进后 (去重 + 分类):
  Core 验证:
    ✓ 证明 (CrossHair): 130 函数    ← 数学保证
    ✓ 测试 (Hypothesis): 19 函数    ← C扩展自动检测
  Shell 验证:
    ✓ 文档示例: 88 函数

  总计: 237/237 函数已验证
  证明级覆盖: 130/149 Core (87%)    ← 新指标
```

---

## Part 2: Shell 架构规则

### 2.1 规则定义

| 规则 | 级别 | 触发条件 | 原因 |
|------|------|----------|------|
| `shell_pure_logic` | **ERROR** | Shell 函数无 I/O 操作 | 架构违规，纯逻辑必须在 Core |
| `shell_too_complex` | **INFO** | Shell 函数分支 > 阈值 | 可能合理，需审查或说明 |
| `entry_point_too_thick` | **WARNING** | Entry point > 15 行 | 应精简，委托给 Shell 函数 |

> **注:** `shell_result` 规则和 `entry_point_too_thick` 规则的详细设计见 [DX-23](./DX-23-entry-point-detection.md)。
> Entry point 是 Shell 的子类型，用于处理框架回调 (Flask routes, Typer commands 等)。

### 2.2 shell_pure_logic (ERROR)

**为什么是 ERROR：**
- Shell 的定义就是 "I/O 层"
- 纯逻辑在 Shell = 无法用契约测试 = 无法用 CrossHair 验证
- 这是架构错误，不是风格问题
- **总有解决方案：移到 Core**

```python
# 检测逻辑
IO_INDICATORS = [
    ".read(", ".write(", ".read_text(", ".write_text(",
    "open(", "Path(",
    "subprocess.", "os.system(",
    "requests.", "aiohttp.",
    "print(", "console.", "typer.",
    "Success(", "Failure(",  # Result 包装是 Shell 特征
]

def has_io_operations(source: str) -> bool:
    return any(indicator in source for indicator in IO_INDICATORS)

# 规则
if not has_io and sym.lines > 5:  # 排除简单 wrapper
    return Violation(
        rule="shell_pure_logic",
        severity=Severity.ERROR,  # 阻止！
        message=f"'{sym.name}' has no I/O - pure logic belongs in Core",
        suggestion="Move to src/invar/core/ and add @pre/@post contracts",
    )
```

### 2.3 shell_too_complex (INFO + 智能建议)

**为什么是 INFO：**
- 有时复杂度是合理的（CLI 参数、多源配置、错误处理）
- 不应阻止，但应引导 Agent 尝试解决

**智能模式检测：**

```python
class BranchPattern(Enum):
    TYPE_DISPATCH = "type_dispatch"      # if type == "a" elif type == "b"
    ERROR_HANDLING = "error_handling"    # except A: ... except B: ...
    CONFIG_CASCADE = "config_cascade"    # if exists(a) elif exists(b)
    NESTED_CONDITIONS = "nested"         # if: if: if:
    VALIDATION_CHAIN = "validation"      # if not x: return; if not y: return
    UNKNOWN = "unknown"
```

**针对性重构建议：**

```python
REFACTORING_TEMPLATES = {
    BranchPattern.TYPE_DISPATCH: """
# 1. Core: 表驱动分发 (可测试)
HANDLERS = {"a": handle_a, "b": handle_b, ...}

@pre(lambda key: key in HANDLERS)
def get_handler(key: str) -> Callable:
    return HANDLERS[key]

# 2. Shell: 单行调用
def process(key, *args):
    return get_handler(key)(*args)
""",

    BranchPattern.CONFIG_CASCADE: """
# 1. Core: 定义优先级 (可测试)
CONFIG_SOURCES = [
    ("pyproject.toml", ["tool", "invar", "guard"]),
    ("invar.toml", ["guard"]),
]

# 2. Shell: 简单迭代
def load_config(root):
    for filename, keys in CONFIG_SOURCES:
        if (root / filename).exists():
            return extract_nested(load_toml(root / filename), keys)
    return {}
""",
    # ... 其他模式
}
```

**输出示例：**

```
INFO shell_too_complex at src/invar/shell/config.py:42

  Function 'load_config' has 5 branches (config_cascade pattern)

  **Recommended Refactoring**:
  ```python
  # 1. Core: 定义优先级 (可测试)
  CONFIG_SOURCES = [...]

  # 2. Shell: 简单迭代
  def load_config(root):
      for filename, keys in CONFIG_SOURCES:
          ...
  ```

  **If complexity is necessary**, add marker:
  ```python
  # @shell_complexity: Multi-source config with fallback logic
  def load_config(...):
  ```
```

---

## Part 3: Fix-or-Explain 强制机制

### 3.1 为什么需要强制

```
问题: INFO 级别警告 Agent 会直接忽略
解决: 累积阈值 + 显式标记机制
```

### 3.2 @shell_complexity 标记

```python
# 方式 1: 修复问题
def simple_function():  # ✓ 通过
    ...

# 方式 2: 显式说明理由
# @shell_complexity: CLI 参数解析，typer 回调必需
def complex_but_justified():  # ✓ 通过（已说明）
    ...

# 无效: 忽略警告
def ignored():  # ✗ 累积后阻止
    ...
```

### 3.3 累积阈值

```python
def check_complexity_debt(project_violations: list[Violation]) -> list[Violation]:
    """项目级复杂度债务检查"""

    unaddressed = [v for v in project_violations
                   if v.rule == "shell_too_complex"]

    if len(unaddressed) >= 5:  # 累积阈值
        return [Violation(
            rule="shell_complexity_debt",
            severity=Severity.ERROR,  # 阻止！
            message=f"Project has {len(unaddressed)} unaddressed complexity warnings",
            suggestion=(
                "You must address these before proceeding:\n"
                "1. Refactor following suggestions, OR\n"
                "2. Add @shell_complexity: markers with justification"
            ),
        )]
    return []
```

### 3.4 强制性保证链

```
┌─────────────────────────────────────────────────────────────────┐
│ 强制性链条（不可绕过）                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  层级 1: 单函数                                                 │
│    shell_pure_logic     → ERROR 立即阻止                        │
│    shell_too_complex    → INFO 显示建议                         │
│                                                                 │
│  层级 2: 项目累积                                               │
│    未处理 too_complex >= 5 → ERROR 阻止                         │
│                                                                 │
│  层级 3: Pre-commit                                             │
│    --strict 模式 → 所有 WARNING 也阻止                          │
│                                                                 │
│  解除方式（仅两种）:                                            │
│    ✓ 重构代码                                                   │
│    ✓ 添加 @shell_complexity: 标记说明理由                       │
│                                                                 │
│  无效方式:                                                      │
│    ✗ 忽略（累积后阻止）                                         │
│    ✗ 关闭规则（不提供此配置）                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 4: 配置（极简）

```toml
# pyproject.toml - 仅 2 个新选项

[tool.invar.guard]
# 现有配置保持不变
max_file_lines = 500
max_function_lines = 50
require_contracts = true
require_doctests = true

# DX-22 新增
shell_max_branches = 3              # Shell 函数分支阈值
shell_complexity_debt_limit = 5     # 累积警告阈值（可选）
entry_max_lines = 15                # Entry point 最大行数 (DX-23)
```

**配置决策：**

| 潜在配置 | 决定 | 原因 |
|---------|------|------|
| `crosshair_timeout` | ❌ 不暴露 | 内部自适应 |
| `hypothesis_examples` | ❌ 不暴露 | 100 是合理默认 |
| `incompatible_libs` | ❌ 不暴露 | 内置黑名单足够 |
| `shell_max_branches` | ✅ 暴露 | 项目风格差异 |
| `shell_complexity_debt_limit` | ✅ 暴露 | 严格项目可调低 |
| `entry_max_lines` | ✅ 暴露 | Entry point 大小限制 (DX-23) |
| `entry_point_patterns` | ❌ 不暴露 | 内置常见框架，Agent-Native (DX-23) |
| `disable_shell_rules` | ❌ 不提供 | 不允许关闭架构检查 |

---

## Part 5: 现有配置简化

### 5.1 现状分析

当前 `pyproject.toml` 有 **16+ 配置项**：

```toml
[tool.invar.guard]
core_paths = [...]              # 1. 目录分类
shell_paths = [...]             # 2. 目录分类
max_file_lines = 500            # 3. 大小限制
max_function_lines = 50         # 4. 大小限制
require_contracts = true        # 5. Core 要求
require_doctests = true         # 6. Core 要求
forbidden_imports = [...]       # 7. 禁止导入列表
exclude_paths = [...]           # 8. 排除路径
strict_pure = true              # 9. 纯度检查
use_code_lines = false          # 10. 行数计算方式
exclude_doctest_lines = true    # 11. 行数计算方式

[tool.invar.guard.severity_overrides]
partial_contract = "off"        # 12. 严重度覆盖

[[tool.invar.guard.rule_exclusions]]
pattern = "..."                 # 13-16. 规则排除（多个）
rules = [...]

[tool.invar]
protocol_version = "..."        # 17. 协议版本
protocol_evolution = "..."      # 18. 协议演进
test_style = "..."              # 19. 测试风格
```

### 5.2 简化方案

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        配置简化: 16+ → 6 项                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ 保留 (人类真正需要)                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  exclude_paths          项目结构差异大，必须手动指定                         │
│  max_file_lines         风格偏好，但有合理默认 (500)                         │
│  max_function_lines     风格偏好，但有合理默认 (50)                          │
│  shell_max_branches     DX-22 新增，Shell 分支阈值                          │
│  shell_complexity_debt  DX-22 新增，累积警告阈值                            │
│  entry_max_lines        DX-23 新增，Entry point 大小限制                    │
│                                                                             │
│  🔄 自动检测 (Agent-Native)                                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  core_paths             → 检测 */core/** 或包含契约的模块                    │
│  shell_paths            → 检测 */shell/** 或包含 Result 的模块              │
│  require_contracts      → Core 自动要求，Shell 自动豁免                     │
│  require_doctests       → Core 自动要求，Shell 自动豁免                     │
│                                                                             │
│  🔒 硬编码 (合理默认)                                                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│  forbidden_imports      标准 I/O 库列表，无需自定义                          │
│  strict_pure            始终 ON，纯度检查是核心功能                          │
│  protocol_version       内部版本控制，对用户无意义                           │
│  protocol_evolution     内部，由项目维护者决定                               │
│                                                                             │
│  ❌ 移除/简化                                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  use_code_lines         → 合并为单一默认行为                                 │
│  exclude_doctest_lines  → 合并为单一默认行为                                 │
│  severity_overrides     → 如果默认正确则不需要                               │
│  rule_exclusions        → 改用代码内标记 (见 5.3)                            │
│  test_style             → 自动检测 (有 tests/ 则 separate)                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 配置 vs 代码内标记

**问题:** `rule_exclusions` 配置复杂且远离代码

```toml
# 当前: 配置文件中（远离代码）
[[tool.invar.guard.rule_exclusions]]
pattern = "**/hypothesis_strategies.py"
rules = ["internal_import"]
```

**改进:** 代码内标记（就近原则）

```python
# 改进: 代码文件中（就在需要的地方）
# @invar:allow internal_import - Lazy imports for optional hypothesis/numpy
from invar.core.timeout_inference import infer_timeout
```

**优势:**
- 理由就在代码旁边，Agent 可以理解
- 不需要维护配置文件
- 更精确（函数级别 vs 文件级别）

### 5.4 简化后的配置

```toml
# pyproject.toml - 简化后 (6 项)

[tool.invar.guard]
# 路径排除 (项目差异)
exclude_paths = ["tests", "scripts", ".venv"]

# 大小限制 (风格偏好，可选)
# max_file_lines = 500       # 默认 500，通常不需要改
# max_function_lines = 50    # 默认 50，通常不需要改

# Shell 复杂度 (DX-22，可选)
# shell_max_branches = 3     # 默认 3，通常不需要改
# shell_complexity_debt = 5  # 默认 5，通常不需要改

# Entry point (DX-23，可选)
# entry_max_lines = 15       # 默认 15，通常不需要改
```

**对比:**

| 指标 | 简化前 | 简化后 |
|------|--------|--------|
| 配置项数量 | 16+ | 6 (5 可选) |
| 必须配置 | 多项 | 仅 exclude_paths |
| 决策点 | 多 | 极少 |
| 配置文件行数 | ~50 | ~12 |

### 5.5 自动检测逻辑

```python
def auto_detect_module_type(file_path: Path, source: str) -> ModuleType:
    """自动检测模块类型，无需手动配置 core_paths/shell_paths"""

    # 1. 路径约定
    if "/core/" in str(file_path) or file_path.parent.name == "core":
        return ModuleType.CORE
    if "/shell/" in str(file_path) or file_path.parent.name == "shell":
        return ModuleType.SHELL

    # 2. 特征检测
    has_contracts = "@pre(" in source or "@post(" in source
    has_result = "Result[" in source or "Success(" in source or "Failure(" in source
    has_io = any(ind in source for ind in IO_INDICATORS)

    if has_contracts and not has_io:
        return ModuleType.CORE
    if has_result or has_io:
        return ModuleType.SHELL

    # 3. 默认: 普通模块
    return ModuleType.UNKNOWN
```

### 5.6 迁移路径

```
阶段 A: 支持两种方式 (向后兼容)
  - 旧配置继续工作
  - 新自动检测同时生效
  - 显式配置覆盖自动检测

阶段 B: 弃用警告
  - 检测到旧配置项时显示警告
  - 提示使用代码内标记替代

阶段 C: 移除旧配置 (下一大版本)
  - 移除 core_paths, shell_paths 等
  - 仅保留简化后的 5 项
```

---

## 实现计划

### 阶段 1: 智能分类 (低风险)

```
文件: src/invar/shell/prove.py
改动:
  1. 添加 has_incompatible_imports() 检测
  2. 修改验证流程跳过不兼容文件
  3. 自动 fallback 到 Hypothesis
```

### 阶段 2: 去重统计 (低风险)

```
文件: src/invar/shell/guard_output.py
改动:
  1. 分类显示结果
  2. 添加"证明级覆盖"指标
```

### 阶段 3: Shell 规则 (中风险)

```
文件: src/invar/core/rules.py, src/invar/core/rule_meta.py
改动:
  1. 添加 check_shell_architecture() 规则
  2. 添加 I/O 检测和分支计数
  3. 添加模式检测和建议生成

依赖: DX-23 Entry Point 检测
  - shell_result 规则修改 (跳过 entry points)
  - entry_point_too_thick 新规则
  - 详见 DX-23 实现计划
```

### 阶段 4: Fix-or-Explain (中风险)

```
文件: src/invar/core/rules.py
改动:
  1. 添加 @shell_complexity 标记检测
  2. 添加 check_complexity_debt() 项目级检查
```

### 阶段 5: Pre-commit 更新 (低风险)

```
文件: src/invar/templates/pre-commit-config.yaml.template
改动:
  1. 确保 --strict 模式启用
```

### 阶段 6: 文档 (低风险)

```
文件: docs/VERIFICATION.md (新建)
内容:
  1. Verification Strategy Overview (English)
  2. Code Classification (Core pure/C-ext, Shell)
  3. Tool Selection (CrossHair vs Hypothesis)
  4. Shell Architecture Rules
  5. Fix-or-Explain Mechanism
  6. Configuration Reference
  7. Examples and Best Practices
```

**文档目的:**
- 为用户提供完整的验证策略指南
- 英文编写，与代码库文档风格一致
- 包含可执行示例，Agent 可直接引用

### 阶段 7: 配置简化 (中风险)

```
文件: src/invar/shell/config.py, src/invar/core/models.py
改动:
  1. 添加 auto_detect_module_type() 自动检测
  2. 弃用 core_paths, shell_paths 配置
  3. 添加 @invar:allow 代码内标记解析
  4. 移除 use_code_lines, exclude_doctest_lines (合并为默认行为)
  5. 弃用 severity_overrides (改善默认值)
```

**迁移策略:**
- 阶段 A: 新旧并存，显式配置优先
- 阶段 B: 弃用警告
- 阶段 C: 移除旧配置 (v2.0)

---

## 测试策略总结

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Invar 测试策略                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  代码类型          │ 主要验证      │ 架构规则      │ 强制性         │
│  ─────────────────┼──────────────┼──────────────┼───────────────  │
│  Core (纯 Python) │ CrossHair    │ 契约+Doctest │ ERROR 阻止      │
│  Core (C 扩展)    │ Hypothesis   │ 契约+Doctest │ ERROR 阻止      │
│  Shell            │ Doctests     │ 架构规则     │ 累积后 ERROR    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Shell 架构规则                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  规则                  │ 级别    │ 可解除方式                      │
│  ─────────────────────┼────────┼────────────────────────────────  │
│  shell_pure_logic     │ ERROR  │ 移动到 Core                      │
│  shell_too_complex    │ INFO   │ 重构 OR @shell_complexity 标记   │
│  entry_point_too_thick│ WARNING│ 精简，委托给 Shell 函数 (DX-23)  │
│  complexity_debt      │ ERROR  │ 处理累积的 too_complex 警告      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Agent-Native 原则                                                  │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ✓ 零决策: `invar guard` 自动选择最优策略                           │
│  ✓ 自动分类: 检测 import 判断 CrossHair/Hypothesis                  │
│  ✓ 可执行建议: 模式检测 + 重构模板，Agent 可直接应用                │
│  ✓ 强制执行: Fix-or-Explain，不能无限忽略                           │
│  ✓ 去重统计: 证明/测试 分开计算                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| shell_pure_logic 级别 | ERROR | 架构违规，总有解决方案 |
| shell_too_complex 级别 | INFO | 可能合理，需人工判断 |
| entry_point_too_thick 级别 | WARNING | 引导但不阻止 (DX-23) |
| 累积阈值 | 5 | 平衡灵活性和强制性 |
| 配置项数量 | 3 (DX-22) + 1 (DX-23) | Agent-Native: 极简 |
| 规则关闭选项 | 不提供 | 架构检查不可绕过 |
| 模式检测 | 5 种 + unknown | 覆盖常见场景 |
| Entry point 检测 | 独立 DX-23 | 问题独立，可独立排期 |
| Entry point 层级 | Shell 子类型 | 保持两层架构 (DX-23) |

---

## 参考

- DX-12: Hypothesis as CrossHair fallback
- DX-13: Incremental CrossHair verification
- DX-19: Simplified verification levels
- [DX-23](./DX-23-entry-point-detection.md): Entry point detection and monad runner pattern
- INVAR.md: Agent-Native principles
