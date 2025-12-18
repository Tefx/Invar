# Protocol Evolution: v3.5 → v3.6

> 基于 Phase 3 实践经验的协议改进分析

---

## 1. 变更概览

| 方面 | v3.5 | v3.6 | 变更原因 |
|------|------|------|----------|
| 工作流 | ICIV (4步) | ICIDV (6步) | 预防性检查 |
| Law 4 | 单一验证 | 三层验证 | 集成覆盖 |
| Quick Reference | 无工作流 | 含工作流 | 快速参考 |

---

## 2. 核心变更：ICIV → ICIDV

### 2.1 变更对比

**v3.5 ICIV:**
```
Intent → Contract → Implementation → Verify
  │         │            │            │
  │         │            │            └─ pytest --doctest-modules
  │         │            └─ 写代码，<50行，<300行
  │         └─ 定义 @pre/@post，写 doctest
  └─ 理解任务，分类 Core/Shell
```

**v3.6 ICIDV:**
```
Intent → Contract → Inspect → Design → Implement → Verify
  │         │          │        │          │          │
  │         │          │        │          │          └─ Unit + Integration + Guard
  │         │          │        │          └─ 写代码
  │         │          │        └─ 规划模块拆分，统一签名
  │         │          └─ 检查文件大小，检查现有模式
  │         └─ 定义契约
  └─ 理解任务
```

### 2.2 新增步骤的必要性

#### Inspect（检查）

**没有 Inspect 时发生了什么：**

```
Phase 3 实际过程：
1. 看到任务：添加 purity 检测
2. 直接开始写代码
3. 写完发现 parser.py 从 189 行变成 352 行
4. Guard 报错：File has 352 lines (max: 300)
5. 被迫紧急重构，创建 purity.py
6. 需要写 wrapper 函数适配签名
7. Wrapper 函数又触发 "missing contract" 警告
```

**如果有 Inspect：**

```
1. 看到任务：添加 purity 检测
2. 检查 parser.py 当前大小：189 行
3. 估算新代码：~160 行
4. 189 + 160 = 349 > 300，需要拆分
5. 提前规划 purity.py 模块
6. 直接在正确的位置写代码
7. 无需紧急重构
```

**量化影响：**
- 无 Inspect：额外花费 25% 时间重构
- 有 Inspect：节省重构时间，代码更整洁

#### Design（设计）

**没有 Design 时发生了什么：**

```
现有规则签名：
  check_file_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]

我写的新规则签名：
  check_impure_calls(file_info: FileInfo, strict_pure: bool) -> list[Violation]
                                         ↑
                                    不一致！

结果：
1. 无法直接放入 rules.py 的规则列表
2. 需要写 wrapper 函数适配签名
3. Wrapper 函数没有 @pre，触发警告
4. 增加了不必要的复杂性
```

**如果有 Design：**

```
1. 检查现有规则签名模式
2. 发现所有规则都用 (FileInfo, RuleConfig)
3. 新规则也用 (FileInfo, RuleConfig)
4. 直接集成，无需 wrapper
```

### 2.3 检查清单的价值

**Inspect 检查清单：**
```
□ Target file current size? (if >200 lines, be careful)
  → parser.py: 189 行，接近限制

□ How do similar functions look? (signature patterns)
  → 所有规则都是 (FileInfo, RuleConfig) -> list[Violation]

□ Edge cases? (class methods, async, nested functions)
  → 类方法未被检查，需要决策
```

**Design 检查清单：**
```
□ Will file exceed 280 lines?
  → 是，需要提前规划 purity.py

□ Does signature match existing?
  → 不匹配，需要调整设计

□ Config option added?
  → 是，需要规划集成测试
```

---

## 3. 核心变更：Law 4 增强

### 3.1 变更对比

**v3.5 Law 4:**
```
Run tests after every change. No exceptions.

pytest --doctest-modules
```

**v3.6 Law 4:**
```
Run ALL verification after every change. No exceptions.

# Unit tests (doctest)
pytest --doctest-modules

# Architecture check
invar guard

# Integration (if config options changed)
# Test: config file enables feature
# Test: CLI flag overrides config
```

### 3.2 为什么需要三层验证？

**Phase 3 发现的 Bug：**

```python
# cli.py 中的代码
def guard(
    ...
    strict_pure: bool = typer.Option(False, "--strict-pure", ...),
) -> None:
    config = config_result.unwrap()
    if strict_pure:
        config.strict_pure = True

    report = _scan_and_check(path, config)
    _output_rich(report, strict_pure)  # ← BUG: 应该是 config.strict_pure
```

**测试覆盖情况：**

| 测试类型 | 是否通过 | 能否发现此 Bug |
|----------|----------|----------------|
| Unit (doctest) | ✅ 通过 | ❌ 不能 |
| Architecture (guard) | ✅ 通过 | ❌ 不能 |
| **Integration** | 未执行 | ✅ 能发现 |

**Bug 的影响：**
- 用户在 config 文件设置 `strict_pure = true`
- 功能生效，但输出不显示 "(strict-pure mode enabled)"
- 用户可能误以为配置没生效

**集成测试场景：**
```
场景 1: 无配置，无 CLI flag
  → strict_pure = false, 输出无提示 ✓

场景 2: 配置 strict_pure=true，无 CLI flag
  → strict_pure = true, 输出应有提示
  → 实际：输出无提示 ✗ ← BUG

场景 3: 配置 strict_pure=false，CLI --strict-pure
  → strict_pure = true, 输出应有提示 ✓
```

### 3.3 三层验证的职责

| 层级 | 工具 | 捕获的问题类型 |
|------|------|----------------|
| Unit | pytest --doctest-modules | 逻辑错误、契约违反、边界条件 |
| Architecture | invar guard | 文件大小、禁止导入、缺失契约 |
| Integration | 手动/脚本 | 配置交互、CLI 覆盖、端到端流程 |

**为什么不能只靠 Unit 测试？**

Unit 测试测的是函数级别的正确性：
```python
>>> _output_rich(report, True)  # 测试 strict_pure=True 的输出
>>> _output_rich(report, False)  # 测试 strict_pure=False 的输出
```

但它不测：
- "当配置文件有 strict_pure=true 时，传给 _output_rich 的值是什么？"
- 这是 **集成问题**，不是 **单元问题**

---

## 4. 变更必要性的实证分析

### 4.1 如果 v3.5 不变

继续使用 v3.5 会发生什么：

```
下一个 Phase 开发：

1. Agent 按 ICIV 工作
2. 直接进入 Implementation
3. 可能再次遇到：
   - 文件大小超限 → 紧急重构
   - 签名不一致 → 需要 wrapper
   - 配置功能不测 → 集成 bug 遗留
4. 重复 Phase 3 的问题
```

### 4.2 v3.6 的预期效果

使用 v3.6 的预期：

```
下一个 Phase 开发：

1. Agent 按 ICIDV 工作
2. Inspect 阶段：
   - 检查目标文件大小
   - 检查现有签名模式
   - 识别边界情况
3. Design 阶段：
   - 如果文件会超限，提前规划拆分
   - 确保签名一致
   - 规划集成测试场景
4. 实现顺利，无意外重构
5. Verify 阶段三层验证，捕获集成 bug
```

### 4.3 成本收益分析

| 方面 | 成本 | 收益 |
|------|------|------|
| Inspect | +5分钟检查 | -30分钟重构 |
| Design | +10分钟规划 | -20分钟修复不一致 |
| 集成测试 | +5分钟测试 | 避免线上 bug |
| **总计** | +20分钟 | -50分钟 + 质量提升 |

---

## 5. 变更的兼容性

### 5.1 向后兼容

v3.6 完全兼容 v3.5：
- 所有 v3.5 项目可以直接使用 v3.6
- 新增的 Inspect/Design 是**建议**，不是强制
- Guard 工具无需修改

### 5.2 渐进采用

可以渐进采用 v3.6：

**阶段 1：只用增强的 Law 4**
```bash
# 每次修改后运行
pytest --doctest-modules
invar guard
# 手动测试配置场景（如果改了配置）
```

**阶段 2：添加 Inspect**
```
在写代码前检查：
- 目标文件多大了？
- 现有函数签名是什么样？
```

**阶段 3：完整 ICIDV**
```
完整流程，包括 Design 阶段的规划
```

---

## 6. 总结

### 6.1 为什么必须变更？

| 问题 | v3.5 的不足 | v3.6 的解决 |
|------|-------------|-------------|
| 文件大小意外 | 无预检机制 | Inspect 阶段检查 |
| 签名不一致 | 无设计检查 | Design 阶段统一 |
| 集成 bug | 只有 Unit 测试 | 三层验证 |

### 6.2 变更的核心理念

**v3.5 理念：**
> "先做，做完验证"

**v3.6 理念：**
> "先看，再想，然后做，最后全面验证"

### 6.3 一句话总结

> **v3.6 将 "后置发现问题" 升级为 "前置预防问题"，用 20 分钟的检查和规划，节省 50 分钟的返工和修复。**

---

*Based on Phase 3 implementation experience, 2024-12-19*
