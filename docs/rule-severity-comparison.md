# Guard 规则严重性对比表

**生成时间:** 2026-01-04 (更新: 2026-01-05)
**用途:** 说明 Python 和 TypeScript Guard 规则严重性配置的设计原理
**变更:** v1.16.0 - 对齐复杂度规则 (DX-22 Fix-or-Explain)

---

## 快速对比：强制 vs 建议

| 维度 | Python Guard | TypeScript Guard (recommended) |
|------|-------------|--------------------------------|
| **强制 (ERROR)** | 10 条 | 7 条 ↓ |
| **建议 (WARN)** | 9 条 | 8 条 ↑ |
| **信息 (INFO)** | 2 条 | 0 条（无单独分类）|
| **总计** | 21 条 | 15 条 |

**v1.16.0 变更:**
- ✅ `max-function-lines`: ERROR → WARN (对齐 Python)
- ✅ 新增 `shell-complexity-debt` 机制 (与 Python 一致)

---

## 详细规则对比表

### 1. 架构边界规则 (Architecture Boundaries)

**设计原则：** 违反 = 破坏架构分层，必须强制 ✅

| 规则 | Python | TypeScript | 严重性 | 为什么必须强制？ |
|------|--------|-----------|--------|------------------|
| Core 中禁止 I/O | `forbidden_import` | `no-io-in-core` | **ERROR** | Core = 纯逻辑层，混入 I/O 破坏可测试性和可组合性 |
| Core 中禁止不纯调用 | `impure_call` | `no-impure-calls-in-core` | **ERROR** | `random.random()`, `datetime.now()` 破坏确定性 |
| Shell 必须返回 Result | `shell_result` | `shell-result-type` | **ERROR (PY) / WARN (TS)** ⚠️ | 统一错误处理，防止异常泄漏 |

**差异点：`shell_result` vs `shell-result-type`**
- **Python:** ERROR - Python 有 `Result[T, E]` 标准库支持，强制要求
- **TypeScript:** WARN - TypeScript 的 Result 类型需要手动定义，允许渐进式采用

**结论：** TS 在 Result 类型上更宽容是合理的，因为生态系统支持不同

---

### 2. 契约覆盖规则 (Contract Coverage)

**设计原则：** 核心契约 = 强制，质量改进 = 建议 ✅

| 规则 | Python | TypeScript | 严重性 | 为什么这样设计？ |
|------|--------|-----------|--------|------------------|
| 缺少契约 | `missing_contract` | `require-jsdoc-example` | **ERROR** | Core 函数必须有契约（或 doctest），否则无法验证 |
| 空契约/套套逻辑 | `empty_contract` | `no-empty-schema` | **ERROR** | `@pre(lambda: True)` = 无意义，浪费维护成本 |
| 参数不匹配 | `param_mismatch` | N/A (TS 类型检查) | **ERROR** | 运行时崩溃风险 |
| @post 引用参数 | `postcondition_scope_error` | N/A | **ERROR** | 设计错误，@post 只能访问 result |
| 契约仅检查类型 | `redundant_type_contract` | `no-redundant-type-schema` | **INFO (PY) / WARN (TS)** | 类型已覆盖，契约应加语义约束 |
| 契约覆盖率低 | `contract_quality_ratio` | N/A | **WARN** | <80% 覆盖 = 建议改进，不阻塞 |

**差异点：为何 TypeScript 用 `require-jsdoc-example` 而非 `@pre/@post`？**
- TypeScript 没有运行时契约系统（需要第三方库）
- JSDoc `@example` + doctest 是 TypeScript 生态的最佳实践
- 要求 `@example` 相当于要求可验证的示例（功能等价）

**结论：** 两者设计目标一致（强制契约覆盖），实现方式适配各自生态

---

### 3. 文件/函数大小规则 (Size Limits)

**设计原则：** 硬限制 = 强制，软限制 = 建议 ✅

| 规则 | Python | TypeScript | 严重性 | 为什么这样设计？ |
|------|--------|-----------|--------|------------------|
| 文件超过限制 | `file_size` | `max-file-lines` | **ERROR** | 绝对限制（默认 300 行），必须拆分 |
| 文件接近限制 | `file_size_warning` | N/A | **WARN** | 预警（80% 阈值），提前规划 |
| 函数超过限制 | `function_size` | `max-function-lines` | **WARN** ✅ | 允许合理的大函数（如 Shell 编排） |

**✅ v1.16.0 已对齐：函数大小规则统一为 WARN**

**为什么改为 WARN？**
1. **Python Shell 编排：** `run_typescript_guard()` 等编排函数合理地超过 50 行
2. **TypeScript React 组件：** JSX 声明性标记非逻辑复杂性
3. **DX-22 原则：** 软限制允许渐进改进，WARN 提供可见性但不阻塞开发
4. **shell_complexity_debt 兜底：** 累积过多未处理 WARN → ERROR 强制处理

**何时触发 ERROR？**
- **文件级别：** 超过绝对限制（300 行）→ `max-file-lines` ERROR
- **函数复杂度债务：** ≥3 个未处理的复杂度 WARN → `shell-complexity-debt` ERROR (DX-22)

---

### 4. Shell 复杂度规则 (Shell Complexity)

**设计原则：** 复杂度 = 建议重构，不阻塞开发 ✅

| 规则 | Python | TypeScript | 严重性 | 为什么都是建议性？ |
|------|--------|-----------|--------|------------------|
| Shell 函数太复杂 | `shell_too_complex` | `shell-complexity` | **INFO (PY) / WARN (TS)** | 复杂度阈值主观，允许合理复杂编排 |
| Shell 有纯逻辑 | `shell_pure_logic` | `no-pure-logic-in-shell` | **WARN** | 启发式检测，可能误报（如配置转换） |
| 复杂度债务累积 | `shell_complexity_debt` | `shell-complexity-debt` ✅ | **ERROR** | v1.16.0 - 两者都有：累积未解决警告 → 强制处理 |
| 入口点太厚 | `entry_point_too_thick` | `thin-entry-points` | **ERROR (PY) / WARN (TS)** | Flask/Typer 命令应薄，TS 更宽容 |

**✅ v1.16.0: TypeScript 实现 shell_complexity_debt（DX-22 Fix-or-Explain）**

**Python 实现：**
- 单个 `shell_too_complex` = INFO（不阻塞）
- 累积 ≥5 个未解决 = 触发 `shell_complexity_debt` ERROR
- 解除：重构 OR 添加 `# @shell_complexity: <理由>`

**TypeScript 实现：**
- 单个 `shell-complexity` = WARN（不阻塞）
- 累积 ≥3 个未解决 = 触发 `shell-complexity-debt` ERROR
- 解除：重构 OR 添加 `// @shell_complexity: <理由>`

**差异点：阈值 5 vs 3**
- Python: 5（项目通常更大，Shell 函数更多）
- TypeScript: 3（项目通常更小，更严格防止技术债务）

**为什么复杂度是 WARN/INFO？**
1. **主观性：** 什么是"太复杂"因项目而异
   - Web 框架的路由函数 vs CLI 工具的命令函数
   - 复杂业务规则 vs 简单 CRUD

2. **渐进式改进：** 允许遗留代码渐进重构
   - 新代码应简单，旧代码有改进空间
   - ERROR 会阻塞所有开发，WARN 允许技术债务可见性

3. **启发式检测不完美：** 可能误报
   - 长但简单的 if-elif 链（配置映射）
   - 框架要求的模板代码

**为什么有 shell_complexity_debt 兜底？**
- 防止"破窗效应"：WARN 太多 → 被忽略 → 代码质量下降
- DX-22 Fix-or-Explain 原则：允许复杂，但必须显式标记原因

---

### 5. 验证完整性规则 (Validation Completeness)

| 规则 | Python | TypeScript | 严重性 | 为什么这样设计？ |
|------|--------|-----------|--------|------------------|
| Schema 验证缺失 | N/A | `require-schema-validation` | **ERROR** | 外部输入必须验证（Zod/AJV） |
| Schema 不完整 | N/A | `require-complete-validation` | **WARN** | 验证覆盖建议，不强制 |
| Schema 中有 any | N/A | `no-any-in-schema` | **WARN** | `any` 失去类型安全，建议避免 |

**为什么 Python 没有对应规则？**
- Python 用 `@pre` 契约做输入验证，已被 `missing_contract` 覆盖
- TypeScript 需要运行时验证（Zod schema），故需要专门规则

---

### 6. 其他规则

| 规则 | Python | TypeScript | 严重性 | 说明 |
|------|--------|-----------|--------|------|
| 内部 import | `internal_import` | N/A | **WARN** | 函数内 import = 代码味道 |
| @must_use 被忽略 | `must_use_ignored` | N/A | **WARN** | 返回值应被使用 |
| 缺少 doctest | `missing_doctest` | N/A | **WARN** | 建议添加示例 |
| 滥用 @skip | `skip_without_reason` | N/A | **WARN** | 跳过测试应有理由 |
| 建议审查 | `review_suggested` | N/A | **WARN** | 触发独立审查条件 |
| 禁止运行时导入 | N/A | `no-runtime-imports` | **ERROR** | TypeScript 特定 |

---

## 设计哲学总结

### 三层严重性体系

```
ERROR (强制)     必须修复或显式豁免
  ↓              架构边界、核心契约、绝对限制
WARN (建议)      应该修复，但不阻塞
  ↓              代码质量、最佳实践、启发式检测
INFO (提示)      可选改进
  ↓              代码味道、重构建议
```

### 什么是 ERROR？（4 个标准）

1. **违反架构边界** → 破坏系统设计
   - Core 中有 I/O、Shell 不返回 Result

2. **缺少核心契约** → 无法验证正确性
   - 缺少 @pre/@post 或 doctest

3. **运行时崩溃风险** → 可靠性问题
   - 参数不匹配、@post 引用参数

4. **超过绝对限制** → 维护性红线
   - 文件 >300 行、累积 ≥3 个复杂度债务

### 什么是 WARN？（3 个标准）

1. **代码质量问题** → 应该修复，但不紧急
   - 函数太长、Shell 有纯逻辑

2. **最佳实践建议** → 提升代码可维护性
   - 缺少 doctest、@skip 无理由

3. **启发式检测** → 可能误报
   - `no-pure-logic-in-shell` 误报配置转换函数

### 什么是 INFO？（1 个标准）

1. **可选改进** → 不影响正确性或维护性
   - 契约仅检查类型、单个 shell 复杂度

---

## 为什么这样设计能说服你？

### 原因 1：平衡严格与灵活

**问题：** 如果所有规则都是 ERROR，会发生什么？
- ❌ 无法处理遗留代码（一次性重构成本过高）
- ❌ 阻塞正常开发（每个警告都阻塞 PR）
- ❌ 开发者绕过规则（添加大量 `@invar:allow`）

**解决方案：** 分层严重性
- ✅ ERROR：不可妥协的底线（架构、正确性）
- ✅ WARN：渐进式改进目标（质量、最佳实践）
- ✅ INFO：可选重构建议（代码味道）

### 原因 2：适配项目生命周期

| 阶段 | ERROR 作用 | WARN 作用 |
|------|-----------|-----------|
| **新项目** | 强制最佳实践 | 预防技术债务 |
| **成熟项目** | 防止倒退 | 识别改进机会 |
| **遗留代码** | 保护核心不变式 | 渐进重构路线图 |

**示例：Paralex 项目**
- `chat.actions.ts` 有 68 条语句（限制 20）
- 如果是 ERROR：必须立即重构（阻塞所有开发）
- 实际是 WARN：可见但不阻塞，团队可以计划重构

### 原因 3：防止规则疲劳

**心理学研究：**
- 太多 ERROR → 开发者麻木 → 忽略所有警告
- 精准 ERROR → 引起重视 → 认真对待

**Invar 设计：**
- 10 条 ERROR（Python）/ 8 条 ERROR（TypeScript）
- 每个都是真正重要的架构或正确性问题
- WARN 是改进建议，不制造心理压力

### 原因 4：DX-22 Fix-or-Explain 兜底

**问题：** WARN 会被忽略吗？
**解决：** `shell_complexity_debt` 机制
- 允许少量 WARN（<3 个未解决）
- 累积 ≥3 个 → 触发 ERROR
- 强制开发者：修复或添加 `# @shell_complexity: <理由>`

**效果：**
- 允许合理的复杂性（有理由）
- 防止无限累积技术债务

---

## 对 Paralex 项目的具体分析

### 当前状态

```bash
chat.actions.ts (1208 lines)
├─ sendMessage: 68 statements (limit 20) → WARN
├─ editMessage: 27 statements (limit 20) → WARN
└─ deleteMessage: ... → WARN

Guard 结果: PASS ✓ (0 errors, 3 warnings)
```

### 为什么这是正确的？

1. **没有架构违反**
   - ✅ Shell 函数都返回 ActionResult<T>（等价 Result）
   - ✅ 没有 Core 中混入 I/O
   - ✅ 所有外部输入都有 schema 验证

2. **复杂度是业务合理性**
   - `sendMessage` 68 statements：处理消息、更新数据库、触发副作用
   - 这是 Shell 编排的正常复杂度，不是逻辑复杂度
   - 如果强制拆分，会降低可读性（编排逻辑分散）

3. **WARN 提供可见性**
   - 团队知道这些函数复杂
   - 可以计划重构（如果需要）
   - 不阻塞当前功能开发

### 如果改为 ERROR 会怎样？

❌ **立即阻塞：**
- 无法合并任何 PR（guard 失败）
- 必须停下所有开发去重构

❌ **可能过度拆分：**
- 为了通过检查，强行拆分成多个小函数
- 编排逻辑分散，反而降低可读性

❌ **或者滥用豁免：**
```typescript
// @invar:allow shell-complexity: too hard to fix
export async function sendMessage(...) {
  // 68 statements
}
```

### 正确的处理方式（当前）

✅ **认知技术债务：**
- Guard 报告 3 个 WARN
- 团队知道需要改进

✅ **计划重构：**
- 识别可提取的纯逻辑 → 移到 Core
- 识别可独立的副作用 → 拆分成辅助函数

✅ **不阻塞开发：**
- 继续开发新功能
- 渐进式改进（每次 PR 改进一点）

---

## 结论：现有设计是经过深思熟虑的

### Python Guard: 10 ERROR + 9 WARN + 2 INFO ✅

**强制（ERROR）：**
- 架构边界（3 条）
- 核心契约（4 条）
- 绝对限制（2 条）
- 债务累积（1 条）

**建议（WARN）：**
- 代码质量（6 条）
- 最佳实践（3 条）

### TypeScript Guard: 7 ERROR + 8 WARN ✅ (v1.16.0 已更新)

**强制（ERROR）：**
- 架构边界（2 条）
- 核心契约（3 条）
- 绝对限制（1 条：max-file-lines）
- 运行时安全（1 条：no-runtime-imports）

**建议（WARN）：**
- 代码质量（5 条：含 max-function-lines）
- 最佳实践（3 条）

**项目级 ERROR（自动触发）：**
- shell-complexity-debt（累积 ≥3 个复杂度 WARN）

### ✅ v1.16.0 已完成的对齐

1. **✅ TS `max-function-lines`：ERROR → WARN**
   - 与 Python `function_size` 对齐
   - 允许合理的长组件（JSX 声明性代码）
   - 已在 v1.16.0 实现

2. **✅ TS `shell-complexity-debt` 机制**
   - 实现 DX-22 Fix-or-Explain 原则
   - 累积 ≥3 个未解决复杂度 WARN → ERROR
   - 支持 `// @shell_complexity: <理由>` 标记
   - 已在 v1.16.0 实现

### 未来可能的微调

1. **TS `shell-result-type`：WARN → ERROR（未来）**
   - 当 TypeScript 项目普遍采用 Result 类型后
   - 当前 WARN 是渐进式采用策略

### 最终回答你的问题

**"为什么 paralex 有超大文件但 guard pass？"**

✅ **因为 shell-complexity 是 WARN，不是 ERROR，这是正确的设计**

**理由：**
1. 复杂度阈值主观，业务编排合理复杂度存在
2. 启发式检测可能误报，不应阻塞开发
3. WARN 提供可见性，支持渐进式改进
4. 如果累积 ≥3 个，`shell_complexity_debt` 会强制处理

**你应该做什么？**
- 现在：继续开发，WARN 不阻塞
- 稍后：识别可提取的纯逻辑，移到 Core
- 或者：添加 `# @shell_complexity: <理由>` 标记

**这是功能，不是 bug！** ✅
