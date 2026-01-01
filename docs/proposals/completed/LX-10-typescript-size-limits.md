# LX-10: Language-Aware Layered Size Limits

> **Status:** Implemented
> **Created:** 2026-01-02
> **Updated:** 2026-01-02
> **Complexity:** Low (reuse existing classification + hardcoded defaults)

---

## Problem

### Issue 1: Uniform Limits Ignore Code Layer Differences

Current limits are uniform across all code:
- `max_file_lines = 500`
- `max_function_lines = 50`

But **Core** and **Shell** have fundamentally different characteristics:

| Layer | Characteristics | Current Compliance |
|-------|----------------|-------------------|
| **Core** | Pure functions, small, focused | 92.3% under 50 lines |
| **Shell** | CLI entry points, I/O, error handling | **76.4%** under 50 lines |
| **Tests** | Setup, fixtures, many assertions | Variable |

Data from Invar codebase analysis:
- Core: avg 27 lines/function, 7.7% exceed 50 lines
- Shell: avg 38 lines/function, **23.6% exceed 50 lines**
- 5 files exceed 500 lines with no escape hatches

### Issue 2: TypeScript Requires More Lines

TypeScript code requires ~30% more lines than Python for equivalent functionality:

| Factor | Python | TypeScript | Overhead |
|--------|--------|------------|----------|
| Type annotations | Optional, inline | Required, multi-line | +20-30% |
| Interface definitions | dataclass ~3 lines | interface ~10 lines | +30% |
| Zod schemas (contracts) | @pre/@post 1 line | z.object({...}) multi-line | +50% |
| JSX (React) | N/A | Significant | +50%+ |

---

## Solution

Implement **language-aware layered size limits**:

1. **Layer detection**: Reuse existing `FileInfo.is_core`/`is_shell` (from `classify_file()`)
2. **Per-layer limits**: Different limits for Core/Shell/Tests/Default
3. **Per-language multiplier**: TypeScript gets 1.3x Python limits

### Proposed Limits

#### Python

| Layer | File Lines | Function Lines | Rationale |
|-------|-----------|----------------|-----------|
| **Core** | 500 | 50 | Pure functions should be small |
| **Shell** | 700 | 100 | CLI/IO naturally larger |
| **Tests** | 1000 | 200 | Test setup can be verbose |
| **Default** | 600 | 80 | Fallback for unclassified |

#### TypeScript (Python × 1.3)

| Layer | File Lines | Function Lines | Rationale |
|-------|-----------|----------------|-----------|
| **Core** | 650 | 65 | Type overhead |
| **Shell** | 910 | 130 | API routes, React components |
| **Tests** | 1300 | 260 | Test boilerplate |
| **Default** | 780 | 104 | Fallback |

---

## Design

### Layer Detection (Reuse Existing)

Guard already classifies files via `FileInfo.is_core` and `FileInfo.is_shell` (set by `classify_file()` in `shell/config.py`).

**No new detection needed for Core/Shell.** Only tests detection requires path check:

```python
class CodeLayer(Enum):
    CORE = "core"
    SHELL = "shell"
    TESTS = "tests"
    DEFAULT = "default"

def get_layer(file_info: FileInfo) -> CodeLayer:
    """
    Determine layer from existing FileInfo classification.

    >>> file_info = FileInfo(path="src/core/logic.py", is_core=True)
    >>> get_layer(file_info)
    <CodeLayer.CORE: 'core'>
    """
    # Tests: path-based (no is_tests field exists)
    path_lower = file_info.path.replace("\\", "/").lower()
    if "/tests/" in path_lower or "/test/" in path_lower or "test_" in path_lower:
        return CodeLayer.TESTS

    # Core/Shell: use existing classification
    if file_info.is_core:
        return CodeLayer.CORE
    if file_info.is_shell:
        return CodeLayer.SHELL

    return CodeLayer.DEFAULT
```

**Key insight:** `classify_file()` already handles Core/Shell detection via:
- Path patterns (configurable in `pyproject.toml`)
- Content analysis (imports like `from returns.result`)
- Default classification rules

### Hardcoded Defaults

```python
@dataclass(frozen=True)
class LayerLimits:
    """Size limits for a specific code layer."""
    max_file_lines: int
    max_function_lines: int

# Python defaults (hardcoded, no config needed)
PYTHON_LAYER_LIMITS: dict[CodeLayer, LayerLimits] = {
    CodeLayer.CORE: LayerLimits(500, 50),
    CodeLayer.SHELL: LayerLimits(700, 100),
    CodeLayer.TESTS: LayerLimits(1000, 200),
    CodeLayer.DEFAULT: LayerLimits(600, 80),
}

# TypeScript = Python × 1.3
TYPESCRIPT_LAYER_LIMITS: dict[CodeLayer, LayerLimits] = {
    CodeLayer.CORE: LayerLimits(650, 65),
    CodeLayer.SHELL: LayerLimits(910, 130),
    CodeLayer.TESTS: LayerLimits(1300, 260),
    CodeLayer.DEFAULT: LayerLimits(780, 104),
}

def get_limits(layer: CodeLayer, language: str) -> LayerLimits:
    """Get limits for layer and language."""
    limits = TYPESCRIPT_LAYER_LIMITS if language == "typescript" else PYTHON_LAYER_LIMITS
    return limits[layer]
```

### Configuration (Optional Override)

用户可选择覆盖默认值，但**大多数项目无需配置**：

```toml
# pyproject.toml - 仅需覆盖时使用
[tool.invar.guard.layers.shell]
max_function_lines = 120  # 覆盖默认的 100
```

### Rules Update

```python
def check_file_size(file_info: FileInfo, language: str) -> list[Violation]:
    layer = get_layer(file_info)  # Uses existing is_core/is_shell
    limits = get_limits(layer, language)  # Hardcoded defaults

    if file_info.lines > limits.max_file_lines:
        return [Violation(
            rule="file_size",
            severity=Severity.ERROR,
            message=f"File has {file_info.lines} lines (max: {limits.max_file_lines} for {layer.value})",
            # ...
        )]
```

---

## Implementation Plan

### Phase 1: Models (30min)

| Task | File | Changes |
|------|------|---------|
| Add `CodeLayer` enum | core/models.py | 4 values |
| Add `LayerLimits` dataclass | core/models.py | 2 fields |
| Add `get_layer()` | core/models.py | Uses `is_core`/`is_shell` |
| Add `PYTHON_LAYER_LIMITS` | core/models.py | Hardcoded dict |
| Add `TYPESCRIPT_LAYER_LIMITS` | core/models.py | Hardcoded dict |

### Phase 2: Rules (30min)

| Task | File | Changes |
|------|------|---------|
| Update `check_file_size()` | core/rules.py | Use `get_limits()` |
| Update `check_function_size()` | core/rules.py | Use `get_limits()` |

### Phase 3: Tests (30min)

| Task | File | Changes |
|------|------|---------|
| Test `get_layer()` | tests/core/ | Core/Shell/Tests/Default |
| Test limits lookup | tests/core/ | Python/TypeScript |

**Total: ~1.5 hours**

**Why so simple?**
- 硬编码默认值，无需配置解析
- 复用现有 `is_core`/`is_shell` 分类
- 无迁移，直接生效

---

## Migration

### 无需迁移

分层限制自动生效，所有变化都是**更宽松**：

| 文件类型 | 旧限制 | 新限制 | 变化 |
|---------|-------|-------|------|
| Core (is_core=True) | 500/50 | 500/50 | 无变化 |
| Shell (is_shell=True) | 500/50 | 700/100 | 更宽松 |
| Tests | 500/50 | 1000/200 | 更宽松 |
| Default | 500/50 | 600/80 | 更宽松 |

### 可选清理

升级后可移除不再需要的 escape hatches：

```python
# 这些可能不再需要：
# @invar:allow file_size: Shell file with CLI logic
# @invar:allow function_size: Complex CLI command
```

---

## Alternatives Considered

| 方案 | 优点 | 缺点 | 决定 |
|------|-----|------|------|
| 路径检测 | 简单 | 重复 `classify_file()` 逻辑 | ❌ |
| 用户配置 | 灵活 | 增加复杂度，大多数用户不需要 | ❌ |
| 统一放宽 600/80 | 简单 | 不鼓励 Core 纯净 | ❌ |
| 仅按语言 | 简单 | 不解决 Shell 层问题 | ❌ |
| **硬编码分层** | 零配置，自动生效 | 少数用户可能需要覆盖 | ✅ |

---

## Success Criteria

- [ ] Invar codebase 无需 file_size/function_size escape hatches
- [ ] Shell 函数 (guard, init) 不再触发警告
- [ ] Core 层保持严格 500/50 限制
- [ ] TypeScript 项目自动获得 1.3x 限制

---

## Summary Table

| Language | Layer | File Lines | Function Lines |
|----------|-------|-----------|----------------|
| Python | Core | 500 | 50 |
| Python | Shell | 700 | 100 |
| Python | Tests | 1000 | 200 |
| Python | Default | 600 | 80 |
| TypeScript | Core | 650 | 65 |
| TypeScript | Shell | 910 | 130 |
| TypeScript | Tests | 1300 | 260 |
| TypeScript | Default | 780 | 104 |
