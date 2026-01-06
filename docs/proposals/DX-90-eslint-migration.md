# DX-90: ESLint Migration Proposal

## Status: Draft

## Problem Statement

内嵌 ESLint (`@invar/eslint-plugin`) 存在持续的稳定性问题：

| 问题 | 影响 |
|------|------|
| Timeout (120s) | 大项目扫描慢，需要复杂 ignore 逻辑 |
| Module Resolution | 内嵌 vs 项目依赖冲突，频繁修复 |
| 依赖链 | ESLint + @typescript-eslint/parser 版本兼容性 |
| 维护成本 | 每次上游更新都可能破坏 |

Git 历史显示多次紧急修复：`60b90a0`, `7f75b31`, `8920562`, `33cdb49`

## Current State

### 15 个自定义规则

| 规则 | 复杂度 | 依赖 TS 类型 | 分类 |
|------|--------|-------------|------|
| `no-io-in-core` | 简单 | ❌ | Core/Shell |
| `no-impure-calls-in-core` | 简单 | ❌ | Core/Shell |
| `no-pure-logic-in-shell` | 复杂 | ❌ | Core/Shell |
| `shell-complexity` | 复杂 | ❌ | Core/Shell |
| `shell-result-type` | 中等 | ✅ | Core/Shell |
| `no-any-in-schema` | 简单 | ❌ | Schema |
| `no-empty-schema` | 简单 | ❌ | Schema |
| `no-redundant-type-schema` | 中等 | ✅ | Schema |
| `require-schema-validation` | 复杂 | ✅ | Schema |
| `require-complete-validation` | 中等 | ✅ | Schema |
| `max-file-lines` | 简单 | ❌ | Structure |
| `max-function-lines` | 简单 | ❌ | Structure |
| `thin-entry-points` | 中等 | ❌ | Structure |
| `require-jsdoc-example` | 简单 | ❌ | Structure |
| `no-runtime-imports` | 简单 | ❌ | Import |

**统计:** 10 个不依赖 TS 类型, 5 个依赖 TS 类型

---

## Proposed Solution: Migrate to oxlint

### Why oxlint?

| 特性 | ESLint | oxlint |
|------|--------|--------|
| 速度 | 1x | 50-100x |
| 语言 | JavaScript | Rust + JS 插件 |
| 内置规则 | 需要安装插件 | 645+ 内置 |
| 自定义规则 | ✅ | ✅ (2025.10 发布) |
| 依赖 | 复杂 node_modules | 单一二进制 |

**关键:** oxlint 2025 年 10 月发布了 [JS 插件支持](https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html)，兼容 ESLint API。

### Migration Strategy

```
Phase 1: oxlint 基础集成 (无自定义规则)
    ↓
Phase 2: 迁移不依赖 TS 类型的规则 (10 个)
    ↓
Phase 3: 迁移依赖 TS 类型的规则 (5 个)
    ↓
Phase 4: 移除 ESLint 依赖
```

---

## Phase 1: oxlint Basic Integration

### 1.1 安装方式

```python
# src/invar/shell/prove/guard_ts.py

def _get_oxlint_binary() -> Path | None:
    """Get oxlint binary path.

    Priority:
    1. Embedded binary in site-packages (future)
    2. Global install via npm/cargo
    3. npx fallback
    """
    # Check global install
    result = subprocess.run(
        ["oxlint", "--version"],
        capture_output=True,
        timeout=5,
    )
    if result.returncode == 0:
        return Path("oxlint")

    return None  # Will use npx fallback
```

### 1.2 运行 oxlint

```python
def run_oxlint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run oxlint for fast linting.

    Uses oxlint's built-in rules + @invar plugin (Phase 2+).
    """
    cmd = ["oxlint", "--format=json"]

    result = subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=30,  # oxlint is fast, 30s is plenty
    )

    # Parse JSON output (oxlint uses ESLint-compatible format)
    violations = _parse_oxlint_output(result.stdout)
    return Success(violations)
```

### 1.3 Fallback 策略

```python
def run_typescript_lint(project_path: Path) -> Result[...]:
    """Run TypeScript linting with fallback.

    Priority:
    1. oxlint (fast, preferred)
    2. ESLint (legacy fallback)
    """
    oxlint_result = run_oxlint(project_path)
    if isinstance(oxlint_result, Success):
        return oxlint_result

    # Fallback to ESLint if oxlint unavailable
    return run_eslint(project_path)
```

---

## Phase 2: Migrate Non-TS Rules (10 rules)

### 2.1 Plugin Structure

```
typescript/packages/oxlint-plugin/
├── package.json
├── src/
│   ├── index.ts          # Plugin entry
│   └── rules/
│       ├── no-io-in-core.ts
│       ├── no-impure-calls-in-core.ts
│       ├── max-file-lines.ts
│       ├── max-function-lines.ts
│       ├── no-any-in-schema.ts
│       ├── no-empty-schema.ts
│       ├── no-runtime-imports.ts
│       ├── require-jsdoc-example.ts
│       ├── thin-entry-points.ts
│       └── shell-complexity.ts
└── dist/
    └── index.js          # Bundled for embedding
```

### 2.2 Rule Migration Example

现有 ESLint 规则已使用 ESLint Rule API，oxlint 兼容该 API：

```typescript
// 几乎无需修改，oxlint 兼容 ESLint Rule API
import type { Rule } from 'eslint';  // oxlint 支持此类型

export const noIoInCore: Rule.RuleModule = {
  meta: {
    type: 'problem',
    docs: { description: '...' },
    messages: { ioInCore: '...' },
  },
  create(context) {
    // 完全相同的实现
    return {
      ImportDeclaration(node) { ... },
      CallExpression(node) { ... },
    };
  },
};
```

### 2.3 Migration Checklist (Phase 2)

- [ ] `no-io-in-core` - 直接迁移
- [ ] `no-impure-calls-in-core` - 直接迁移
- [ ] `max-file-lines` - 直接迁移
- [ ] `max-function-lines` - 直接迁移
- [ ] `no-any-in-schema` - 直接迁移
- [ ] `no-empty-schema` - 直接迁移
- [ ] `no-runtime-imports` - 直接迁移
- [ ] `require-jsdoc-example` - 直接迁移
- [ ] `thin-entry-points` - 直接迁移
- [ ] `shell-complexity` - 直接迁移 (复杂但不依赖类型)
- [ ] `no-pure-logic-in-shell` - 直接迁移 (复杂但不依赖类型)

---

## Phase 3: Migrate TS-Dependent Rules (5 rules)

这些规则需要类型信息，有两个选项：

### Option A: oxlint Type-Aware Mode

oxlint 正在开发类型感知模式。等待官方支持后迁移。

### Option B: TypeScript Compiler API

直接使用 TypeScript Compiler API 实现，绕过 linter：

```typescript
// src/invar/node_tools/ts-checker/index.ts
import * as ts from 'typescript';

interface CheckResult {
  rule: string;
  file: string;
  line: number;
  message: string;
}

export function checkShellResultType(
  program: ts.Program,
  sourceFile: ts.SourceFile
): CheckResult[] {
  const results: CheckResult[] = [];
  const checker = program.getTypeChecker();

  function visit(node: ts.Node) {
    if (ts.isFunctionDeclaration(node) && isInShell(sourceFile.fileName)) {
      const signature = checker.getSignatureFromDeclaration(node);
      const returnType = checker.getReturnTypeOfSignature(signature!);
      const typeString = checker.typeToString(returnType);

      if (!isResultType(typeString)) {
        results.push({
          rule: '@invar/shell-result-type',
          file: sourceFile.fileName,
          line: sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1,
          message: `Shell function should return Result<T, E>`,
        });
      }
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return results;
}
```

### 5 个 TS 依赖规则处理方案

| 规则 | 建议方案 | 原因 |
|------|----------|------|
| `shell-result-type` | TS Compiler API | 核心规则，类型检查简单 |
| `require-schema-validation` | TS Compiler API | 核心规则，需要类型推断 |
| `require-complete-validation` | TS Compiler API | 与上一个规则相关 |
| `no-redundant-type-schema` | 降级为警告 | 低优先级，可后续实现 |

---

## Phase 4: Remove ESLint Dependency

### 4.1 清理步骤

1. 删除 `src/invar/node_tools/eslint-plugin/`
2. 删除 `typescript/packages/eslint-plugin/`
3. 更新 `guard_ts.py` 移除 ESLint 代码路径
4. 更新 `pyproject.toml` 移除 ESLint 嵌入配置
5. 更新文档

### 4.2 最终架构

```
TypeScript Guard Pipeline
         │
         ├── tsc (类型检查)
         │
         ├── oxlint (快速 lint)
         │   ├── 内置规则 (645+)
         │   └── @invar/oxlint-plugin (10 规则)
         │
         ├── ts-checker (类型相关检查)
         │   └── 5 个 TS 依赖规则
         │
         └── vitest (测试)
```

---

## Timeline

| Phase | 内容 | 估计工作量 |
|-------|------|-----------|
| Phase 1 | oxlint 集成 + fallback | 1-2 天 |
| Phase 2 | 迁移 10 个非 TS 规则 | 2-3 天 |
| Phase 3 | 实现 ts-checker | 3-5 天 |
| Phase 4 | 移除 ESLint | 1 天 |

**总计:** 约 1-2 周

---

## Risk Assessment

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| oxlint JS 插件不稳定 | 中 | 保留 ESLint fallback 直到验证 |
| 规则行为差异 | 低 | 保持测试用例，对比输出 |
| ts-checker 性能 | 中 | 只对 shell/ 目录运行，缓存 Program |

---

## Decision Required

1. **Phase 2 vs Phase 3 优先级:** 先迁移简单规则还是先实现 ts-checker?
2. **Fallback 保留时长:** ESLint fallback 保留多久?
3. **oxlint 安装方式:** 嵌入二进制 vs 要求用户安装?

---

## References

- [oxlint JS Plugins Preview](https://oxc.rs/blog/2025-10-09-oxlint-js-plugins.html)
- [oxlint Beta Announcement](https://oxc.rs/blog/2025-03-15-oxlint-beta)
- [Biome vs ESLint 2025](https://medium.com/@harryespant/biome-vs-eslint-the-ultimate-2025-showdown)
- [Biome Custom Rules Discussion](https://github.com/biomejs/biome/discussions/231)
