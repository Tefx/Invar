# DX-80: Guard CLI默认行为对齐MCP（Bug修复）

**Status**: Draft
**Created**: 2026-01-03
**Priority**: High
**Type**: Bug Fix + Enhancement

---

## Problem

### 设计遗留问题

CLI和MCP对同一工具的默认行为不一致，违反agent-first设计原则。

**当前状态**：
```python
# MCP实现（正确的默认值）
async def _run_guard(args: dict[str, Any]):
    if args.get("changed", True):  # 默认True ✅
        cmd.append("--changed")

# CLI实现（遗留的错误默认值）
def guard(
    changed: bool = typer.Option(False, ...)  # 默认False ❌
):
```

**结果**：
| Agent | 调用方式 | 实际行为 | 体验 |
|-------|---------|---------|------|
| Claude Code | `invar_guard()` | 增量检查（快） | ✅ 好 |
| Pi | `invar guard` | 全检查（慢） | ❌ 差 |

**证据**：
1. MCP实现已经是`changed=True`（这是设计意图）
2. 379处文档都建议显式用`--changed`（说明当前默认值不是最佳实践）
3. Invar是agent-first框架，CLI也是给agent用的

### 用户报告的问题

原始问题：
> "pi coding agent不能使用mcp，但是又不知道uvx invar tools，本地invar又找不到"

**根本原因**：
1. Pi不支持MCP → 必须用CLI
2. CLI默认全检查慢 → 需要agent自己加`--changed`
3. 文档没有明确说明调用方式 → agent不知道怎么优化

---

## Solution

### 方案：对齐默认值 + 添加显式标志

**代码修改**：
```python
def guard(
    path: Path = typer.Argument(...),
    changed: bool = typer.Option(
        True,  # 修复：改为True，和MCP对齐
        "--changed/--all",  # 添加--all标志，明确语义
        help="Check git-modified files only (use --all for full check)"
    ),
    # ... 其他参数
):
    """Check project against Invar architecture rules.

    Smart Guard: Runs static + doctests + CrossHair + Hypothesis.

    By default, checks only git-modified files for fast feedback.
    Use --all to check the entire project (useful for CI/release).
    """
```

**调用方式**：
```bash
# 新默认行为（对齐MCP）
invar guard                      # 检查修改文件（快）✨
uvx invar-tools guard            # 同上

# 显式全检查
invar guard --all                # 检查全部文件
uvx invar-tools guard --all

# 向后兼容
invar guard --changed            # 仍然有效（显式指定默认行为）
```

**Typer实现细节**：
```python
# Typer的--changed/--all语法自动处理互斥：
# --changed → changed=True
# --all → changed=False
# 无标志 → changed=True（默认值）
```

---

## Documentation Updates

### 1. 新增Tool Selection章节

**位置**：CLAUDE.md的Quick Reference之后

**理由**：
- Critical Rules提到工具名 → Tool Selection立即解释如何调用
- 逻辑连续，减少查找时间
- 最高频操作靠前位置

**内容**：

```markdown
## Tool Selection

### Calling Methods (Priority Order)

Invar tools can be called in 3 ways. **Try in order:**

1. **MCP tools** (Claude Code with MCP enabled)
   - Direct function calls: `invar_guard()`, `invar_sig()`, etc.
   - No Bash wrapper needed

2. **CLI command** (if `invar` installed in PATH)
   - Via Bash: `invar guard`, `invar sig`, etc.
   - Install: `pip install invar-tools`

3. **uvx fallback** (always available, no install needed)
   - Via Bash: `uvx invar-tools guard`, `uvx invar-tools sig`, etc.

---

### Parameter Reference

**guard** - Verify code quality
```python
# MCP
invar_guard()                    # Check changed files (default)
invar_guard(changed=False)       # Check all files

# CLI
invar guard                      # Check changed files (default)
invar guard --all                # Check all files
```

**sig** - Show function signatures and contracts
```python
# MCP
invar_sig(target="src/foo.py")

# CLI
invar sig src/foo.py
invar sig src/foo.py::function_name
```

**map** - Find entry points
```python
# MCP
invar_map(path=".", top=10)

# CLI
invar map [path] --top 10
```

**refs** - Find all references to a symbol
```python
# MCP
invar_refs(target="src/foo.py::MyClass")

# CLI
invar refs src/foo.py::MyClass
```

**doc*** - Document tools
```python
# MCP
invar_doc_toc(file="docs/spec.md")
invar_doc_read(file="docs/spec.md", section="intro")

# CLI
invar doc toc docs/spec.md
invar doc read docs/spec.md intro
```

---

### Quick Examples

```python
# Verify after changes (all three methods identical)
invar_guard()                        # MCP
bash("invar guard")                  # CLI
bash("uvx invar-tools guard")        # uvx

# Full project check
invar_guard(changed=False)           # MCP
bash("invar guard --all")            # CLI

# See function contracts
invar_sig(target="src/core/parser.py")
bash("invar sig src/core/parser.py")
```

**Note**: All three methods now have identical default behavior.
```

### 2. 更新Critical Rules（无需改动）

当前已经是通用表述：
```markdown
| **Verify** | `invar guard` — NOT pytest, NOT crosshair |
```

### 3. 更新Tools文档

**INVAR.md, README.md, templates/protocol/*.md**：

```markdown
### Smart Guard

```bash
invar guard              # Check git-modified files (fast, default)
invar guard --all        # Check entire project (CI, release)
invar guard --static     # Static only (~0.5s)
invar guard --coverage   # Collect coverage
invar guard -c           # Contract coverage only
```

**Default behavior**: Checks git-modified files for fast feedback during development.
Use `--all` for comprehensive checks before release.
```

### 4. 现有文档无需删除

**379处`invar guard --changed`仍然有效**，无需删除。它们现在是"显式指定默认行为"（冗余但无害）。

---

## Impact Analysis

### Agent使用（主要用户）✅ 改善

| Agent | 当前 | 修复后 | 影响 |
|-------|------|--------|------|
| Claude Code (MCP) | `invar_guard()` → 增量 | 无变化 | ✅ 无影响 |
| Pi (CLI) | 需手动加`--changed` | 自动增量 | ✅ **更快，更简单** |
| Aider (CLI) | 配置`--changed` | 仍然有效 | ✅ 无影响 |
| Cursor (CLI) | 需手动加`--changed` | 自动增量 | ✅ 改善 |
| Cline (CLI) | 需手动加`--changed` | 自动增量 | ✅ 改善 |

### CI脚本（极少）⚠️ 需要适配

```bash
# 受影响的CI脚本（如果存在）
# 之前
invar guard  # 检查全部

# 修复后（需要更新）
invar guard --all  # 显式全检查
```

**但是**：
1. Pre-commit hooks已经用`--changed`，不受影响
2. Invar主要是开发时工具，不是CI工具
3. 大多数CI应该用pre-commit，不是直接调用guard

### 向后兼容性 ✅ 良好

| 调用方式 | 之前 | 之后 | 兼容性 |
|---------|------|------|--------|
| `invar guard` | 全检查 | 增量检查 | ⚠️ 行为改变（但更优） |
| `invar guard --changed` | 增量检查 | 增量检查 | ✅ 无变化 |
| `invar guard --all` | ❌ 不存在 | 全检查 | ✅ 新功能 |

---

## Implementation Plan

### Phase 1: 代码修改

**文件**：`src/invar/shell/commands/guard.py`

```python
def guard(
    path: Path = typer.Argument(
        Path(),
        help="Project directory or single Python file",
        exists=True,
        file_okay=True,
        dir_okay=True,
    ),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    changed: bool = typer.Option(
        True,  # 修复：改为True
        "--changed/--all",  # 添加互斥标志
        help="Check git-modified files only (use --all for full check)"
    ),
    static: bool = typer.Option(
        False, "--static", help="Static analysis only, skip all runtime tests"
    ),
    # ... 其他参数不变
):
    """Check project against Invar architecture rules.

    Smart Guard: Runs static analysis + doctests + CrossHair + Hypothesis by default.

    By default, checks only git-modified files for fast feedback during development.
    Use --all to check the entire project (useful for CI/release).
    Use --static for quick static-only checks (~0.5s vs ~5s full).
    Use --suggest to get functional pattern suggestions (NewType, Validation, etc.).
    Use --contracts-only (-c) to check contract coverage without running tests (DX-63).
    """
    # 实现部分无需改动
```

**测试**：
```python
# 新测试用例
def test_guard_default_checks_changed_files():
    """Guard默认检查修改文件（对齐MCP）"""
    result = runner.invoke(app, ["guard", test_dir])
    # 验证只检查了git修改的文件

def test_guard_all_flag():
    """--all标志检查全部文件"""
    result = runner.invoke(app, ["guard", test_dir, "--all"])
    # 验证检查了所有文件

def test_guard_changed_flag_still_works():
    """向后兼容：--changed仍然有效"""
    result = runner.invoke(app, ["guard", test_dir, "--changed"])
    # 验证行为和默认一致
```

### Phase 2: 文档更新

**模板文件**：
1. `src/invar/templates/config/CLAUDE.md.jinja`
   - 在Quick Reference后添加Tool Selection章节

2. `src/invar/templates/protocol/python/tools.md`
   - 更新guard说明

3. `src/invar/templates/protocol/typescript/tools.md`
   - 更新guard说明

**已生成文件**（需要运行`invar dev sync`）：
1. `CLAUDE.md`
2. `INVAR.md`
3. `README.md`

### Phase 3: 验证

**手动测试**：
```bash
# 1. CLI默认行为
invar guard
# 预期：只检查修改文件

# 2. --all标志
invar guard --all
# 预期：检查全部文件

# 3. --changed标志（向后兼容）
invar guard --changed
# 预期：只检查修改文件（和默认一致）

# 4. MCP调用（应无变化）
python -c "from invar.mcp.handlers import _run_guard; import asyncio; asyncio.run(_run_guard({}))"
# 预期：仍然是增量检查
```

**集成测试**：
- 运行pre-commit hooks（应无影响）
- 测试各种agent环境（Pi, Aider, etc.）

---

## Versioning

### 版本号：v1.13.0 (minor)

**理由**：
- 添加了新的`--all`标志（功能增强）
- 默认行为变更虽是修复，但用户可感知
- 给用户明确信号"有重要对齐改动"

### Changelog

```markdown
## v1.13.0 - Guard CLI对齐MCP行为 + Tool Selection文档

### Fixed
- **guard CLI默认行为对齐MCP**：CLI和MCP默认都检查修改文件
  - 修复设计遗留问题：CLI应该和MCP行为一致（agent-first原则）
  - 之前：`invar guard`检查全部文件（慢）
  - 现在：`invar guard`检查修改文件（快，和MCP一致）

### Added
- **新增`--all`标志**：显式请求全检查
  - `invar guard --all` - 检查整个项目（CI、release场景）
  - 向后兼容：`invar guard --changed`仍然有效

- **Tool Selection文档章节**：解决Pi等不支持MCP的agent调用问题
  - 三种等价调用方式对照表（MCP / CLI / uvx）
  - 参数映射说明
  - 快速示例

### Migration
- **Agent用户（主要）**：自动获得更快体验，无需改动
- **CI脚本（极少）**：如需全检查，改为`invar guard --all`
- **Pre-commit hooks**：不受影响（已经用--changed）
```

---

## Rationale

### 为什么是Bug修复而非Breaking Change

1. **设计意图**：MCP实现已经是`changed=True`，CLI应该一致
2. **Agent-first原则**：Invar为agent优化，增量检查是正确的默认值
3. **向后兼容**：`--changed`标志仍然有效，只是变为默认
4. **文档证据**：379处建议用`--changed`，说明当前默认不合理

### 为什么现在修复

1. **用户报告**：Pi agent使用体验差
2. **工具扩展**：需要添加Tool Selection文档，顺便修复不一致
3. **时机合适**：1.13.0版本，有新功能发布窗口

---

## Risks

### 低风险

1. **Agent用户（主要）**：体验改善，无负面影响
2. **Pre-commit hooks**：已经用`--changed`，不受影响
3. **向后兼容**：`--changed`仍有效

### 中等风险

1. **CI脚本**：极少数可能需要改为`--all`
   - **缓解**：Changelog明确说明，提供迁移指南
   - **检测**：CI失败时会立即发现（检查文件变少）

### 接受的权衡

**默认行为变更 vs 一致性收益**：
- 变更影响极小（主要是agent自动适应）
- 一致性收益巨大（简化文档、改善体验）
- 符合agent-first设计原则

---

## Alternatives Considered

### 备选方案A：环境变量控制

```python
default_changed = os.getenv("INVAR_GUARD_CHANGED", "false").lower() == "true"
```

**拒绝理由**：
- 增加复杂度
- Agent需要配置环境
- 行为仍不一致（需要额外配置）

### 备选方案B：保持现状，文档说明差异

**拒绝理由**：
- 违反agent-first原则
- Agent学习负担
- 文档复杂

---

## Success Criteria

1. ✅ CLI默认行为和MCP一致
2. ✅ `--all`标志正常工作
3. ✅ 向后兼容测试通过
4. ✅ Pre-commit hooks仍然正常
5. ✅ Tool Selection文档完整准确
6. ✅ Agent用户体验改善（Pi测试）

---

## Timeline

- **Phase 1 (代码)**：1 hour
- **Phase 2 (文档)**：2 hours
- **Phase 3 (测试)**：1 hour
- **Total**: ~4 hours

---

## References

- 原始问题报告：pi coding agent调用Invar问题
- MCP实现：src/invar/mcp/handlers.py:63
- CLI实现：src/invar/shell/commands/guard.py:124
- 文档统计：379处`invar guard`引用
