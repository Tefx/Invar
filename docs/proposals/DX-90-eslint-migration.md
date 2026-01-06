# DX-90: ESLint Migration Proposal

## Status: Approved

## Problem Statement

内嵌 ESLint (`@invar/eslint-plugin`) 存在持续的稳定性问题：

| 问题 | 影响 |
|------|------|
| Timeout (120s) | 大项目扫描慢，需要复杂 ignore 逻辑 |
| Module Resolution | 内嵌 vs 项目依赖冲突，频繁修复 |
| 依赖链 | ESLint + @typescript-eslint/parser 版本兼容性 |
| 维护成本 | 每次上游更新都可能破坏 |

Git 历史显示多次紧急修复：`60b90a0`, `7f75b31`, `8920562`, `33cdb49`

---

## Solution: Migrate to oxlint

### Why oxlint?

| 特性 | ESLint | oxlint |
|------|--------|--------|
| 速度 | 1x | 50-100x |
| 语言 | JavaScript | Rust + JS 插件 |
| 内置规则 | 需要安装插件 | 645+ 内置 |
| 自定义规则 | ✅ | ✅ (2025.10 发布) |
| 依赖 | 复杂 node_modules | 单一二进制 |

**关键:** oxlint 2025 年 10 月发布了 [JS 插件支持](https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html)，兼容 ESLint Rule API。

---

## Cross-Platform Strategy

### 问题：二进制嵌入的平台兼容性

| 组件 | 类型 | 跨平台 |
|------|------|--------|
| **oxlint 本体** | Rust 原生二进制 | ❌ 需要 6 个平台构建 |
| **@invar/oxlint-plugin** | JavaScript 代码 | ✅ 跨平台 |

如果嵌入 oxlint 二进制：
- 需要为 linux-x64, linux-arm64, darwin-x64, darwin-arm64, win32-x64, win32-arm64 分别构建
- 包体积膨胀 ~6 倍
- 构建和发布流程复杂化

### 解决方案：只嵌入 JS 插件

```
Python 包嵌入 (跨平台)          用户安装 (平台相关)
───────────────────────────────────────────────────
@invar/oxlint-plugin      +      oxlint
(JavaScript, ~100KB)             (用户自行安装)
```

### oxlint 安装方式

```bash
# 方式 1: npm 全局安装 (推荐)
npm install -g oxlint

# 方式 2: 包管理器
brew install oxlint          # macOS
cargo install oxlint         # Rust 用户

# 方式 3: npx 按需下载 (零配置，稍慢)
npx oxlint                   # 自动下载对应平台版本
```

### 检测逻辑

```python
def _get_oxlint_cmd() -> list[str] | None:
    """获取 oxlint 命令"""
    # 优先级 1: 全局安装 (最快)
    if _check_tool_available("oxlint", ["--version"]):
        return ["oxlint"]

    # 优先级 2: npx (自动下载对应平台)
    if _check_tool_available("npx", ["--version"]):
        return ["npx", "oxlint"]

    return None
```

---

## File Filtering Strategy

### 问题：检查范围控制

TS 项目应该只检查项目代码，跳过：
- `node_modules/` - 第三方依赖
- `dist/`, `build/` - 编译输出
- `.next/`, `.nuxt/` - 框架生成
- `coverage/` - 测试覆盖率报告
- 其他生成目录

### 解决方案：智能文件过滤

#### 1. 默认忽略列表

```python
DEFAULT_IGNORE_PATTERNS = [
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/.nuxt/**",
    "**/.cache/**",
    "**/coverage/**",
    "**/.turbo/**",
    "**/.vercel/**",
    "**/playwright-report/**",
    "**/test-results/**",
    "**/*.min.js",
    "**/*.bundle.js",
]
```

#### 2. 基于 tsconfig.json 的智能检测

```python
def _get_project_files(project_path: Path) -> list[str]:
    """获取项目文件列表，排除依赖和生成文件"""

    # 优先使用 tsconfig.json 的 include/exclude
    tsconfig = project_path / "tsconfig.json"
    if tsconfig.exists():
        config = json.loads(tsconfig.read_text())
        include = config.get("include", ["src/**/*"])
        exclude = config.get("exclude", [])
        # 使用 tsconfig 定义的范围
        return _glob_with_patterns(project_path, include, exclude)

    # 回退到默认模式：src/ 目录
    return _glob_with_patterns(
        project_path,
        include=["src/**/*.ts", "src/**/*.tsx"],
        exclude=DEFAULT_IGNORE_PATTERNS,
    )
```

#### 3. oxlint 命令行参数

```python
def run_oxlint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    cmd = _get_oxlint_cmd()
    if not cmd:
        return Failure("oxlint not available")

    cmd.extend([
        "--format=json",
        "--tsconfig", "tsconfig.json",
        # 显式忽略模式
        "--ignore-pattern", "node_modules",
        "--ignore-pattern", "dist",
        "--ignore-pattern", "build",
        "--ignore-pattern", ".next",
        "--ignore-pattern", "coverage",
    ])

    # 只检查 src/ 目录（如果存在）
    src_dir = project_path / "src"
    if src_dir.exists():
        cmd.append("src/")
    else:
        cmd.append(".")

    # ...
```

#### 4. 配置文件支持 (oxlint.json)

用户可通过项目根目录的 `oxlint.json` 自定义：

```json
{
  "ignorePatterns": [
    "node_modules",
    "dist",
    "custom-generated/"
  ],
  "include": ["src/", "lib/"],
  "plugins": ["@invar"]
}
```

### 检查范围优先级

```
1. oxlint.json (项目自定义)
       ↓
2. tsconfig.json include/exclude
       ↓
3. 默认规则 (src/ + DEFAULT_IGNORE_PATTERNS)
```

---

## Rule Analysis

### 重要发现：所有规则都是 AST 级别检查

分析现有 15 个规则的实现后发现，**没有规则依赖真正的 TypeScript 类型推断**：

| 规则 | 检查方式 | 需要 TS 类型推断? |
|------|----------|------------------|
| `shell-result-type` | 类型注解文本匹配 `Result<` | ❌ |
| `require-schema-validation` | 类型注解文本匹配 `z.infer` | ❌ |
| `no-redundant-type-schema` | AST 调用链检查 | ❌ |
| `require-complete-validation` | AST `TSTypeReference` 检查 | ❌ |
| 其他 11 个规则 | 纯 AST 检查 | ❌ |

**结论：所有 15 个规则可直接迁移到 oxlint JS 插件。**

### 规则清单

| # | 规则 | 复杂度 | 分类 |
|---|------|--------|------|
| 1 | `no-io-in-core` | 简单 | Core/Shell |
| 2 | `no-impure-calls-in-core` | 简单 | Core/Shell |
| 3 | `no-pure-logic-in-shell` | 复杂 | Core/Shell |
| 4 | `shell-complexity` | 复杂 | Core/Shell |
| 5 | `shell-result-type` | 中等 | Core/Shell |
| 6 | `no-any-in-schema` | 简单 | Schema |
| 7 | `no-empty-schema` | 简单 | Schema |
| 8 | `no-redundant-type-schema` | 中等 | Schema |
| 9 | `require-schema-validation` | 复杂 | Schema |
| 10 | `require-complete-validation` | 中等 | Schema |
| 11 | `max-file-lines` | 简单 | Structure |
| 12 | `max-function-lines` | 简单 | Structure |
| 13 | `thin-entry-points` | 中等 | Structure |
| 14 | `require-jsdoc-example` | 简单 | Structure |
| 15 | `no-runtime-imports` | 简单 | Import |

---

## Migration Plan

### 简化的 2 阶段方案

```
Phase 1: oxlint 基础集成 (1-2 天)
    │
    ├── 添加 oxlint 调用
    ├── 保留 ESLint fallback
    └── 验证 JSON 输出兼容性
    │
    ▼
Phase 2: 迁移全部规则 + 移除 ESLint (3-4 天)
    │
    ├── 迁移 15 个规则到 oxlint-plugin
    ├── 测试用例验证
    ├── 移除 eslint-plugin
    └── 更新文档
```

**总耗时：4-6 天**

---

## Phase 1: oxlint Basic Integration

### 1.1 安装检测

```python
# src/invar/shell/prove/guard_ts.py

def _get_oxlint_cmd(project_path: Path) -> list[str] | None:
    """Get oxlint command.

    Priority:
    1. Global install (oxlint)
    2. Project-local (npx oxlint)
    3. None if unavailable
    """
    # Check global install
    if _check_tool_available("oxlint", ["--version"]):
        return ["oxlint"]

    # Check npx availability
    if _check_tool_available("npx", ["oxlint", "--version"]):
        return ["npx", "oxlint"]

    return None
```

### 1.2 运行 oxlint

```python
def run_oxlint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run oxlint for fast linting.

    Uses oxlint's built-in rules + @invar plugin.
    Output format compatible with ESLint JSON.
    """
    cmd = _get_oxlint_cmd(project_path)
    if not cmd:
        return Failure("oxlint not available")

    cmd.extend([
        "--format=json",
        "--tsconfig", "tsconfig.json",
        ".",
    ])

    result = subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=30,  # oxlint is fast
    )

    violations = _parse_oxlint_output(result.stdout)
    return Success(violations)
```

### 1.3 Fallback 策略

```python
def run_typescript_lint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run TypeScript linting with fallback.

    Priority:
    1. oxlint (fast, preferred)
    2. ESLint (legacy fallback, will be removed in Phase 2)
    """
    oxlint_result = run_oxlint(project_path)
    if isinstance(oxlint_result, Success):
        return oxlint_result

    # Fallback to ESLint if oxlint unavailable
    return run_eslint(project_path)
```

---

## Phase 2: Migrate Rules + Remove ESLint

### 2.1 Plugin Structure

```
typescript/packages/oxlint-plugin/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Plugin entry
│   ├── configs.ts            # recommended/strict presets
│   └── rules/
│       ├── no-io-in-core.ts
│       ├── no-impure-calls-in-core.ts
│       ├── no-pure-logic-in-shell.ts
│       ├── shell-complexity.ts
│       ├── shell-result-type.ts
│       ├── no-any-in-schema.ts
│       ├── no-empty-schema.ts
│       ├── no-redundant-type-schema.ts
│       ├── require-schema-validation.ts
│       ├── require-complete-validation.ts
│       ├── max-file-lines.ts
│       ├── max-function-lines.ts
│       ├── thin-entry-points.ts
│       ├── require-jsdoc-example.ts
│       └── no-runtime-imports.ts
├── dist/
│   └── index.js              # Bundled for embedding
└── __tests__/
    └── rules.test.ts         # Migrated from eslint-plugin
```

### 2.2 Rule Migration

oxlint 兼容 ESLint Rule API，规则代码几乎无需修改：

```typescript
// 直接复制，仅更新 import
import type { Rule } from 'eslint';  // oxlint 兼容

export const noIoInCore: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: { description: '...' },
    messages: { ioInCore: '...' },
  },
  create(context) {
    // 实现完全相同
    return {
      ImportDeclaration(node) { ... },
      CallExpression(node) { ... },
    };
  },
};
```

### 2.3 Migration Checklist

- [ ] 创建 `typescript/packages/oxlint-plugin/` 结构
- [ ] 复制 15 个规则文件
- [ ] 复制测试用例
- [ ] 验证规则行为一致
- [ ] 更新 `guard_ts.py` 移除 ESLint 代码
- [ ] 删除 `src/invar/node_tools/eslint-plugin/`
- [ ] 删除 `typescript/packages/eslint-plugin/`
- [ ] 更新 `pyproject.toml`
- [ ] 更新文档

---

## Progressive Enhancement Architecture

### 检查能力分层

```
Level 1: AST 检查 (当前 + Phase 1-2)
├── oxlint JS 插件
├── 能力：语法模式匹配、文本检查
└── 覆盖：15/15 规则 ✅

Level 2: 类型感知 (未来按需)
├── ts-checker 组件
├── 能力：类型推断、类型兼容性
└── 场景：检查无类型注解的返回类型

Level 3: 跨文件分析 (未来按需)
├── project-analyzer 组件
├── 能力：追踪 import 链、全局符号表
└── 场景：检测间接 I/O 依赖
```

### 预留接口

```python
# src/invar/shell/prove/guard_ts.py

def run_typescript_guard(project_path: Path) -> Result[TypeScriptGuardResult, str]:
    """TypeScript verification pipeline.

    Layered architecture:
    - Level 1: oxlint (AST checks) - always run
    - Level 2: ts-checker (type-aware) - future, optional
    - Level 3: project-analyzer (cross-file) - future, optional
    """
    all_violations: list[TypeScriptViolation] = []

    # Level 1: Fast AST checks (oxlint) - required
    oxlint_result = run_oxlint(project_path)
    match oxlint_result:
        case Success(violations):
            all_violations.extend(violations)
        case Failure(err):
            # oxlint is required, report as tool error
            return Failure(f"oxlint failed: {err}")

    # Level 2: Type-aware checks (future, optional)
    if _has_ts_checker():
        ts_checker_result = run_ts_checker(project_path)
        match ts_checker_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(_):
                pass  # Optional, don't fail

    # Level 3: Cross-file analysis (future, optional)
    if _has_project_analyzer():
        analyzer_result = run_project_analyzer(project_path)
        match analyzer_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(_):
                pass  # Optional, don't fail

    return Success(_build_result(all_violations))
```

```typescript
// typescript/packages/ts-checker/src/index.ts (预留，暂不实现)

export interface TypeChecker {
  // Level 2: 单文件类型检查
  checkInferredReturnType(file: string, func: string): CheckResult;
  checkSchemaTypeUsage(file: string, param: string): CheckResult;
}

export interface ProjectAnalyzer {
  // Level 3: 跨文件分析
  traceImportChain(file: string, symbol: string): ImportChain;
  findIndirectIoDependencies(file: string): Dependency[];
}
```

### 未来扩展示例

**Level 2 场景：检查无类型注解的返回类型**

```typescript
// 当前 shell-result-type 只能检查有注解的情况
export function fetchUser(id: string): Result<User, Error> { ... }  // ✅ 检测到

// Level 2 可以检查无注解的情况
export function fetchUser(id: string) {  // ← 无返回类型注解
  return ok(user);  // ts-checker 可推断实际返回 Result<User, Error>
}
```

**Level 3 场景：检测间接 I/O 依赖**

```typescript
// core/logic.ts
import { helper } from './helper';  // helper 间接依赖 fs

// core/helper.ts
import { readConfig } from '../shell/config';  // 违规！

// project-analyzer 可追踪: logic.ts → helper.ts → config.ts → fs
```

---

## Timeline

| Phase | 内容 | 耗时 |
|-------|------|------|
| Phase 1 | oxlint 集成 + fallback | 1-2 天 |
| Phase 2 | 迁移 15 规则 + 移除 ESLint | 3-4 天 |
| **总计** | | **4-6 天** |

### Future (按需)

| 组件 | 触发条件 | 预计耗时 |
|------|----------|----------|
| ts-checker | 需要类型推断规则 | 2-3 天 |
| project-analyzer | 需要跨文件分析 | 3-5 天 |

---

## Deliverables

### Phase 1
- [ ] `guard_ts.py` 添加 `run_oxlint()` 函数
- [ ] `guard_ts.py` 添加 fallback 逻辑
- [ ] 集成测试验证

### Phase 2
- [ ] `typescript/packages/oxlint-plugin/` 完整实现
- [ ] 15 个规则迁移 + 测试
- [ ] 删除 `eslint-plugin` 相关代码
- [ ] 文档更新

### Architecture (预留)
- [ ] `guard_ts.py` 分层接口
- [ ] `ts-checker` 接口定义 (不实现)
- [ ] `project-analyzer` 接口定义 (不实现)

---

## Risk Assessment

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| oxlint JS 插件 API 差异 | 低 | 已验证规则代码兼容 |
| 规则行为细微差异 | 低 | 保留测试用例，逐个验证 |
| oxlint 安装问题 | 中 | 文档说明安装方式，CI 验证 |

---

## References

- [oxlint JS Plugins Preview](https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html)
- [oxlint Beta Announcement](https://oxc.rs/blog/2025-03-15-oxlint-beta)
- [oxlint 1.0 Stable](https://voidzero.dev/posts/announcing-oxlint-1-stable)
- [Biome vs ESLint 2025](https://medium.com/@harryespant/biome-vs-eslint-the-ultimate-2025-showdown)
