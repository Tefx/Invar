# DX-23: Entry Point 检测与 Monad Runner 模式

> **"Shell 内部保持 Result，边界处运行 Monad"**

## 状态

- **ID**: DX-23
- **状态**: Draft
- **来源**: [feedback-memo.md](../history/feedback/feedback-memo.md)
- **关联**: DX-22 Part 2 (Shell 架构规则)

---

## 问题陈述

### 现象

Shell 层要求函数返回 `Result[T, E]`，但框架回调无法遵守：

```python
# Flask 期望的签名
@app.route("/")
def home() -> str:
    return render_template("index.html")

# Invar shell_result 规则期望
@app.route("/")
def home() -> Result[str, str]:  # Flask 不理解 Result!
    return Success(render_template("index.html"))
```

### 受影响的框架

| 类型 | 框架 | 回调形式 |
|------|------|----------|
| Web | Flask, Django, FastAPI | `@app.route`, `@router.get` |
| CLI | Typer, Click | `@app.command`, `@click.command` |
| 测试 | pytest | `@pytest.fixture` |
| 事件 | 各种 | `@on_event`, middleware |

### 当前解决方案 (Hack)

```toml
# pyproject.toml - 排除框架代码
exclude_paths = ["src/web", "src/cli"]  # 但这些仍然是 Shell 代码!
```

**问题:** 框架代码被完全排除在检查之外，失去了所有保护。

---

## 设计哲学

### Haskell 类比

```haskell
-- Haskell: ExceptT monad 处理错误
loadConfig :: FilePath -> ExceptT ConfigError IO Config
loadConfig path = do
    content <- liftIO $ readFile path
    parseConfig content

-- main 是边界: "运行" monad，提取值
main :: IO ()
main = do
    result <- runExceptT $ loadConfig "config.yaml"
    case result of
        Left err  -> handleError err
        Right cfg -> runApp cfg
```

**关键洞察:**

```
Haskell 中:
  • main 不是独立的"层"
  • main 是 monad 的 "runner"
  • 在 main 处，monad 被"运行"，值被提取

Python/Invar 中:
  • Entry point 不是独立的"层"
  • Entry point 是 Result monad 的 "runner"
  • 在 entry point 处，Result 被"运行"，值被提取给框架
```

### 核心原则

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   Shell 内部: 保持在 Result monad 中 (不妥协)                            │
│                                                                         │
│   Entry Point: 是 monad runner，不是业务逻辑                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 解决方案

### 层级模型 (保持两层)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Framework (Flask/FastAPI/Typer)                                         │
│ 期望: str, Response, dict, None                                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  Shell Layer                  │
                    │  ┌─────────────────────────┐  │
                    │  │ Entry Point (边界)      │  │
                    │  │ • 豁免 Result 要求      │  │
                    │  │ • 必须精简 (monad runner)│  │
                    │  └───────────┬─────────────┘  │
                    │              │ Result[T, E]   │
                    │  ┌───────────▼─────────────┐  │
                    │  │ Shell Internal          │  │
                    │  │ • 必须返回 Result       │  │
                    │  │ • 包含业务逻辑          │  │
                    │  └───────────┬─────────────┘  │
                    └──────────────┼────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │ Core Layer                    │
                    │ • 纯函数, @pre/@post          │
                    └───────────────────────────────┘
```

**不增加第三层!** Entry point 是 Shell 的子类型，不是独立层。

### Entry Point 检测

```python
# 自动检测的装饰器模式 (内置，无需配置)
ENTRY_POINT_DECORATORS = frozenset([
    # Web frameworks
    "app.route", "app.get", "app.post", "app.put", "app.delete", "app.patch",
    "router.get", "router.post", "router.put", "router.delete", "router.patch",
    "blueprint.route",
    # FastAPI specific
    "api_router.get", "api_router.post",
    # CLI frameworks
    "app.command",      # Typer
    "click.command", "click.group",
    # Testing
    "pytest.fixture", "fixture",
    # Event handlers
    "on_event", "middleware",
    # Django
    "admin.register",
])

def is_entry_point(symbol: Symbol, source: str) -> bool:
    """检测函数是否为框架入口点"""
    # 1. 检查装饰器模式
    for decorator in symbol.decorators:
        for pattern in ENTRY_POINT_DECORATORS:
            if pattern in decorator:
                return True

    # 2. 检查显式标记 (边缘情况逃生舱)
    # 函数前的注释: # @shell:entry
    if _has_entry_marker(symbol, source):
        return True

    return False
```

### 规则变更

#### 1. 修改 `shell_result` 规则

```python
def check_shell_result(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Shell-internal 函数必须返回 Result[T, E]"""
    violations = []

    if not file_info.is_shell:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # 跳过返回 None 的函数 (原有逻辑)
        if "-> None" in symbol.signature or "->" not in symbol.signature:
            continue

        # 跳过生成器 (原有逻辑)
        if "Iterator[" in symbol.signature or "Generator[" in symbol.signature:
            continue

        # DX-23: 跳过 Entry Points
        if is_entry_point(symbol, file_info.source):
            continue

        # 检查 Result 返回类型
        if "Result[" not in symbol.signature:
            violations.append(Violation(
                rule="shell_result",
                severity=Severity.WARNING,
                file=file_info.path,
                line=symbol.line,
                message=f"Shell function '{symbol.name}' should return Result[T, E]",
                suggestion="Use Result[T, E] from returns library",
            ))

    return violations
```

#### 2. 新增 `entry_point_too_thick` 规则

```python
# 默认阈值
ENTRY_POINT_MAX_LINES = 15

def check_entry_point_thin(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Entry points 应该精简，只做 monad running"""
    violations = []

    if not file_info.is_shell:
        return violations

    max_lines = getattr(config, 'entry_max_lines', ENTRY_POINT_MAX_LINES)

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        if not is_entry_point(symbol, file_info.source):
            continue

        if symbol.lines > max_lines:
            violations.append(Violation(
                rule="entry_point_too_thick",
                severity=Severity.WARNING,
                file=file_info.path,
                line=symbol.line,
                message=f"Entry point '{symbol.name}' has {symbol.lines} lines (max: {max_lines})",
                suggestion="Move business logic to Shell function returning Result[T, E]",
            ))

    return violations
```

### 显式标记 (逃生舱)

对于无法自动检测的框架回调：

```python
# @shell:entry - Custom event handler for legacy system
def on_legacy_event(data: dict) -> dict:
    """Entry point for legacy system callback."""
    result = process_legacy_event(data)
    match result:
        case Success(value):
            return {"status": "ok", "data": value}
        case Failure(error):
            return {"status": "error", "message": str(error)}
```

---

## 推荐的代码模式

### 错误示例

```python
# ❌ 错误: Entry point 太厚
@app.route("/contact", methods=["POST"])
def contact():
    # 20+ 行业务逻辑直接在这里
    email = request.form.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400

    if not validate_email(email):
        return jsonify({"error": "Invalid email"}), 400

    try:
        contact = Contact(email=email)
        db.session.add(contact)
        db.session.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"id": contact.id}), 201
```

### 正确示例

```python
# ✅ 正确: Entry point 精简，委托给 Shell

# Shell-internal: 返回 Result
def handle_contact_form(form: dict) -> Result[Contact, str]:
    """Process contact form submission."""
    email = form.get("email")
    if not email:
        return Failure("Missing email")

    if not validate_email(email):
        return Failure("Invalid email")

    return save_contact(email)  # 另一个返回 Result 的 Shell 函数


# Entry point: Monad runner (~5 行)
@app.route("/contact", methods=["POST"])
def contact():
    """Entry point: runs Result monad at framework boundary."""
    result = handle_contact_form(request.form)
    match result:
        case Success(contact):
            return jsonify({"id": contact.id}), 201
        case Failure(error):
            return jsonify({"error": error}), 400
```

---

## 配置

### 新增配置项 (可选)

```toml
# pyproject.toml
[tool.invar.guard]
entry_max_lines = 15  # Entry point 最大行数，默认 15
```

### 配置决策

| 潜在配置 | 决定 | 原因 |
|---------|------|------|
| `entry_point_patterns` | ❌ 不暴露 | 内置常见框架，Agent-Native |
| `entry_max_lines` | ✅ 暴露 | 项目风格差异 |
| `disable_entry_check` | ❌ 不提供 | 架构检查不可绕过 |

---

## 实现计划

### 文件变更

```
src/invar/core/entry_points.py (新建)
  • ENTRY_POINT_DECORATORS 常量
  • is_entry_point() 检测函数
  • _has_entry_marker() 标记检测
  约 60 行

src/invar/core/rules.py
  • 修改 check_shell_result: 调用 is_entry_point()
  • 新增 check_entry_point_thin
  约 40 行修改/新增

src/invar/core/rule_meta.py
  • 新增 entry_point_too_thick 规则元数据
  约 10 行

src/invar/core/models.py
  • RuleConfig 添加 entry_max_lines 字段
  约 5 行

总计: ~115 行代码变更
```

### 实现步骤

```
1. 创建 entry_points.py 模块
   • 定义 ENTRY_POINT_DECORATORS
   • 实现 is_entry_point()
   • 添加 doctests

2. 修改 rules.py
   • 导入 is_entry_point
   • 修改 check_shell_result
   • 新增 check_entry_point_thin

3. 更新 rule_meta.py
   • 添加 entry_point_too_thick 元数据

4. 更新 models.py
   • RuleConfig 添加 entry_max_lines

5. 运行 invar guard 验证
```

### 工作量估计

```
开发: 0.5 天
测试: 0.25 天
文档: 0.25 天
总计: 1 天
```

---

## 与 DX-22 的关系

```
DX-22: 智能验证策略
├── Part 1: 验证分流 (CrossHair/Hypothesis)
├── Part 2: Shell 架构规则
│   ├── shell_pure_logic (ERROR)
│   ├── shell_too_complex (INFO)
│   └── → 引用 DX-23 的 entry point 规则
├── Part 3: Fix-or-Explain
├── Part 4: 配置极简
└── Part 5: 配置简化

DX-23 提供:
  • Entry point 检测逻辑
  • shell_result 规则修改
  • entry_point_too_thick 规则

依赖关系:
  • DX-22 和 DX-23 可独立实现
  • DX-22 Part 2 引用 DX-23 的规则
```

---

## 测试策略

### 单元测试

```python
def test_is_entry_point_flask():
    """Flask route is detected as entry point."""
    symbol = Symbol(name="index", decorators=["@app.route('/')"])
    assert is_entry_point(symbol, "") is True

def test_is_entry_point_typer():
    """Typer command is detected as entry point."""
    symbol = Symbol(name="main", decorators=["@app.command()"])
    assert is_entry_point(symbol, "") is True

def test_is_entry_point_explicit_marker():
    """Explicit marker is detected."""
    source = "# @shell:entry\ndef handler(): pass"
    symbol = Symbol(name="handler", decorators=[])
    assert is_entry_point(symbol, source) is True

def test_shell_result_skips_entry_point():
    """shell_result rule skips entry points."""
    # Entry point without Result - no violation
    ...

def test_entry_point_too_thick():
    """Entry points exceeding max_lines trigger warning."""
    ...
```

---

## 决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 独立提案 vs 合并 DX-22 | 独立 DX-23 | 问题独立、哲学独立、可独立排期 |
| 两层 vs 三层 | 两层 | Entry point 是 Shell 子类型，不是独立层 |
| 装饰器配置 | 内置 | Agent-Native，覆盖常见框架 |
| 行数阈值 | 15 | 足够写 match/case，防止业务逻辑 |
| 规则级别 | WARNING | 引导但不阻止 |

---

## 参考

- [feedback-memo.md](../history/feedback/feedback-memo.md) - 问题来源
- DX-22 - 智能验证策略 (关联提案)
- Haskell `ExceptT` monad - 设计灵感
- `returns` library - Python Result 实现
