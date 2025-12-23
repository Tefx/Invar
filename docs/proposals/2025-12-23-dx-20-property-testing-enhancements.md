# DX-20: Property Testing Enhancements

**Date:** 2025-12-23
**Status:** Draft (待讨论)
**Priority:** ★★☆☆☆ (Low, optimization)
**Effort:** 3-5 days
**Depends on:** DX-08 + DX-19 (已完成)

---

## Executive Summary

DX-08 实现了从 `@pre/@post` 合约自动生成 Hypothesis 属性测试的基础设施。DX-19 将其集成到默认的 STANDARD 验证级别。本提案解决当前实现的四个限制：

1. **无缓存** - 每次运行都重新解析合约
2. **模式有限** - 只支持简单类型约束
3. **无诊断** - 无法识别慢速测试
4. **无跳过机制** - 无法选择性跳过特定函数

---

## Proposal A: Strategy Caching (策略缓存)

**Priority:** ★★☆☆☆
**Effort:** 1 day

### Problem

每次 `invar guard` 都重新解析所有合约并生成策略，浪费时间。在 100+ 函数的项目中，重复解析可能增加 1-2 秒延迟。

### Solution

```python
# src/invar/shell/property_cache.py

from pathlib import Path
import hashlib
import json
from dataclasses import dataclass
from hypothesis import strategies as st

@dataclass
class CachedStrategy:
    """Cached Hypothesis strategy with metadata."""
    file_hash: str          # Source file content hash
    func_name: str          # Function name
    strategy_repr: str      # Serialized strategy representation
    generated_at: float     # Timestamp

class PropertyCache:
    """Cache for generated property test strategies.

    Uses file content hash to invalidate cache when source changes.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, CachedStrategy] = {}

    def get_cache_key(self, file_path: Path, func_name: str) -> str:
        """Generate cache key from file path and function name."""
        return f"{file_path.stem}::{func_name}"

    def get_file_hash(self, content: str) -> str:
        """Hash file content for cache invalidation."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, file_path: Path, func_name: str,
            current_hash: str) -> CachedStrategy | None:
        """Retrieve cached strategy if still valid."""
        key = self.get_cache_key(file_path, func_name)
        cached = self._memory_cache.get(key)

        if cached and cached.file_hash == current_hash:
            return cached

        # Try disk cache
        disk_path = self.cache_dir / f"{key.replace('::', '_')}.json"
        if disk_path.exists():
            data = json.loads(disk_path.read_text())
            if data["file_hash"] == current_hash:
                cached = CachedStrategy(**data)
                self._memory_cache[key] = cached
                return cached

        return None

    def put(self, file_path: Path, func_name: str,
            file_hash: str, strategy_repr: str) -> None:
        """Cache a generated strategy."""
        import time

        key = self.get_cache_key(file_path, func_name)
        cached = CachedStrategy(
            file_hash=file_hash,
            func_name=func_name,
            strategy_repr=strategy_repr,
            generated_at=time.time(),
        )

        self._memory_cache[key] = cached

        # Persist to disk
        disk_path = self.cache_dir / f"{key.replace('::', '_')}.json"
        disk_path.write_text(json.dumps(cached.__dict__))
```

### Integration

```python
# src/invar/shell/property_tests.py - 修改

def run_property_tests_on_files(
    files: list[Path],
    max_examples: int = 100,
    cache: PropertyCache | None = None,  # 新增
) -> Result[PropertyTestReport, str]:
    """Run property tests with optional caching."""
    ...
```

### Tasks

```
□ 创建 PropertyCache 类
  ├── 实现内存缓存 (dict)
  ├── 实现磁盘缓存 (JSON)
  └── 基于文件哈希的失效机制

□ 集成到 property_tests.py
  ├── 检查缓存命中
  ├── 缓存新生成的策略
  └── 添加缓存统计到输出

□ 添加缓存目录到 .invar/cache/property/
```

---

## Proposal B: Complex Pattern Support (复杂类型模式支持)

**Priority:** ★★☆☆☆
**Effort:** 2-3 days

### Problem

当前只支持简单合约模式，复杂模式被跳过。

**Currently Supported:**
```python
@pre(lambda x: x > 0)                    # ✓ 支持
@pre(lambda items: len(items) > 0)       # ✓ 支持
@pre(lambda s: len(s) <= 100)            # ✓ 支持
```

**Not Supported (skipped):**
```python
@pre(lambda x, y: x < y)                 # ✗ 多参数关系
@pre(lambda items: all(i > 0 for i in items))  # ✗ 嵌套约束
@pre(lambda d: "key" in d)               # ✗ 字典包含
@pre(lambda x: isinstance(x, (int, str)))  # ✗ Union 类型
```

### Solution

```python
# src/invar/core/property_gen.py - 扩展

from hypothesis import strategies as st
from typing import Union, get_args, get_origin
import re

class PatternRegistry:
    """Registry of contract patterns and their strategy generators."""

    def __init__(self):
        self.patterns: list[tuple[re.Pattern, callable]] = []
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in pattern handlers."""
        # 多参数关系: x < y
        self.register(
            pattern=r"(\w+)\s*<\s*(\w+)",
            generator=self._gen_ordered_pair,
        )

        # all() 约束: all(i > 0 for i in items)
        self.register(
            pattern=r"all\((\w+)\s*>\s*(\d+)\s+for\s+\w+\s+in\s+(\w+)\)",
            generator=self._gen_positive_list,
        )

        # 字典包含: "key" in d
        self.register(
            pattern=r"[\"'](\w+)['\"]\s+in\s+(\w+)",
            generator=self._gen_dict_with_key,
        )

    def register(self, pattern: str, generator: callable) -> None:
        """Register a new pattern handler."""
        self.patterns.append((re.compile(pattern), generator))

    def _gen_ordered_pair(self, match, type_hints) -> dict[str, st.SearchStrategy]:
        """Generate strategies for x < y constraint."""
        x_name, y_name = match.groups()
        # 使用 flatmap 确保 x < y
        return {
            y_name: st.floats(min_value=-1e6, max_value=1e6),
            x_name: st.floats().flatmap(
                lambda y: st.floats(max_value=y, exclude_max=True)
            ),
        }

    def _gen_positive_list(self, match, type_hints) -> dict[str, st.SearchStrategy]:
        """Generate strategy for all(i > 0 for i in items)."""
        threshold = int(match.group(2))
        param_name = match.group(3)
        return {
            param_name: st.lists(
                st.floats(min_value=threshold, exclude_min=True),
                min_size=1,
            ),
        }

    def _gen_dict_with_key(self, match, type_hints) -> dict[str, st.SearchStrategy]:
        """Generate strategy for 'key' in d."""
        key = match.group(1)
        param_name = match.group(2)
        return {
            param_name: st.fixed_dictionaries({key: st.text()}),
        }


def strategy_for_union(type_hint) -> st.SearchStrategy:
    """Generate strategy for Union types.

    >>> from typing import Union
    >>> s = strategy_for_union(Union[int, str])
    >>> s  # doctest: +ELLIPSIS
    one_of(integers(), text())
    """
    if get_origin(type_hint) is Union:
        args = get_args(type_hint)
        strategies = [strategy_for_type(arg) for arg in args]
        return st.one_of(*strategies)
    return strategy_for_type(type_hint)
```

### Implementation Phases

| Phase | Pattern | Complexity |
|-------|---------|------------|
| 1 | Multi-param relations (`x < y`) | Low |
| 2 | `all()` constraints | Medium |
| 3 | Union types | Medium |
| 4 | Nested dict/list | High |
| 5 | Custom Pydantic models | High |

### Tasks

```
□ 创建 PatternRegistry 类
  ├── 定义模式接口
  ├── 实现默认模式处理器
  └── 支持用户注册自定义模式

□ Phase 1: Multi-param relations
  ├── 解析 x < y, x <= y, x == y 模式
  ├── 使用 flatmap 生成有序对
  └── 添加测试用例

□ Phase 2: all() constraints
  ├── 解析 all(...for...in...) 模式
  ├── 生成满足约束的列表
  └── 处理嵌套条件

□ Phase 3: Union types
  ├── 检测 Union 类型注解
  ├── 生成 st.one_of() 组合
  └── 处理 Optional (= Union[T, None])
```

---

## Proposal C: Performance Profiling (性能分析工具)

**Priority:** ★★★☆☆
**Effort:** 1 day

### Problem

无法识别哪些函数的属性测试很慢，难以优化。

### Solution

```python
# src/invar/shell/property_profile.py

from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class FunctionProfile:
    """Profile data for a single function's property tests."""
    func_name: str
    file_path: Path
    examples_run: int
    total_time_ms: float
    avg_time_per_example_ms: float
    slowest_example_ms: float
    strategy_gen_time_ms: float

    @property
    def is_slow(self) -> bool:
        """Flag if function is slow (> 100ms per example)."""
        return self.avg_time_per_example_ms > 100

@dataclass
class ProfileReport:
    """Aggregated profile report for property tests."""
    functions: list[FunctionProfile] = field(default_factory=list)
    total_time_ms: float = 0

    def slowest(self, n: int = 5) -> list[FunctionProfile]:
        """Return n slowest functions."""
        return sorted(
            self.functions,
            key=lambda f: f.total_time_ms,
            reverse=True
        )[:n]

    def format_report(self) -> str:
        """Format human-readable profile report."""
        lines = ["Property Test Performance Profile", "=" * 40]

        slow = [f for f in self.functions if f.is_slow]
        if slow:
            lines.append(f"\n⚠️  {len(slow)} slow functions (>100ms/example):")
            for f in slow:
                lines.append(
                    f"  {f.func_name}: {f.avg_time_per_example_ms:.1f}ms/ex "
                    f"({f.file_path.name})"
                )

        lines.append(f"\nTop 5 slowest:")
        for f in self.slowest(5):
            lines.append(
                f"  {f.func_name}: {f.total_time_ms:.0f}ms total, "
                f"{f.examples_run} examples"
            )

        lines.append(f"\nTotal: {self.total_time_ms:.0f}ms")
        return "\n".join(lines)
```

### CLI Integration

```bash
# New --profile flag
invar guard --profile        # Show property test performance report
invar test --profile <file>  # Single file profiling
```

### Example Output

```
Property Test Performance Profile
========================================

⚠️  2 slow functions (>100ms/example):
  calculate_trajectory: 234.5ms/ex (physics.py)
  parse_complex_grammar: 156.2ms/ex (parser.py)

Top 5 slowest:
  calculate_trajectory: 4690ms total, 20 examples
  parse_complex_grammar: 3124ms total, 20 examples
  validate_schema: 890ms total, 100 examples
  process_batch: 456ms total, 100 examples
  transform_data: 234ms total, 100 examples

Total: 9394ms
```

### Tasks

```
□ 创建 FunctionProfile 和 ProfileReport 类

□ 集成到 property_tests.py
  ├── 记录每个函数的执行时间
  ├── 记录策略生成时间
  └── 记录最慢示例时间

□ 添加 --profile 标志到 CLI
  ├── guard 命令
  └── test 命令

□ 添加到 JSON 输出 (agent 模式)
```

---

## Proposal D: Selective Skip (选择性跳过)

**Priority:** ★★★★☆
**Effort:** 0.5 day

### Problem

某些函数的属性测试很慢或有已知问题，需要临时跳过。

### Solution 1: Decorator-based

```python
# src/invar/decorators.py - 新增

def skip_property_test(reason: str = ""):
    """Mark a function to be skipped during property testing.

    Usage:
        @skip_property_test("Complex numeric edge cases")
        @pre(lambda x: x > 0)
        def complex_calculation(x: float) -> float:
            ...
    """
    def decorator(func):
        func._invar_skip_property = True
        func._invar_skip_reason = reason
        return func
    return decorator

def slow_property_test(max_examples: int = 10):
    """Mark a function as slow, reducing example count.

    Usage:
        @slow_property_test(max_examples=5)
        @pre(lambda x: x > 0)
        def expensive_calculation(x: float) -> float:
            ...
    """
    def decorator(func):
        func._invar_slow_property = True
        func._invar_max_examples = max_examples
        return func
    return decorator
```

### Solution 2: Config-based

```toml
# pyproject.toml

[tool.invar.property]
# Global skip patterns (regex)
skip_functions = [
    "test_*",           # Skip all test_ prefixed
    "*_deprecated",     # Skip deprecated functions
]

# Slow function config
slow_functions = [
    { pattern = "calculate_*", max_examples = 10 },
    { pattern = "parse_*", max_examples = 20 },
]

# Skip entire files
skip_files = [
    "src/legacy/**",
    "src/experimental/**",
]
```

### Detection Logic

```python
# src/invar/shell/property_tests.py - 扩展

import fnmatch
from typing import Callable

def should_skip_property_test(func: Callable, config: dict) -> tuple[bool, str]:
    """Determine if a function should be skipped for property testing.

    Returns (should_skip, reason).
    """
    # Check decorator
    if getattr(func, "_invar_skip_property", False):
        return True, getattr(func, "_invar_skip_reason", "decorated")

    # Check config
    func_name = func.__name__
    for pattern in config.get("skip_functions", []):
        if fnmatch.fnmatch(func_name, pattern):
            return True, f"matches skip pattern: {pattern}"

    return False, ""

def get_max_examples(func: Callable, config: dict, default: int = 100) -> int:
    """Get max examples for a function, respecting slow markers."""
    # Check decorator
    if getattr(func, "_invar_slow_property", False):
        return getattr(func, "_invar_max_examples", 10)

    # Check config
    func_name = func.__name__
    for slow_config in config.get("slow_functions", []):
        if fnmatch.fnmatch(func_name, slow_config["pattern"]):
            return slow_config.get("max_examples", 10)

    return default
```

### Tasks

```
□ 添加装饰器到 decorators.py
  ├── @skip_property_test(reason)
  └── @slow_property_test(max_examples)

□ 扩展配置解析
  ├── 解析 skip_functions 列表
  ├── 解析 slow_functions 配置
  └── 解析 skip_files 列表

□ 集成到 property_tests.py
  ├── 检查跳过条件
  ├── 应用 max_examples 配置
  └── 报告跳过原因

□ 更新输出格式
  ├── Human-readable: 显示跳过的函数和原因
  └── JSON: 包含 skipped_functions 列表
```

---

## Implementation Roadmap

| Phase | Proposal | Effort | Priority | Rationale |
|-------|----------|--------|----------|-----------|
| 1 | D: Selective Skip | 0.5 day | High | Unblocks slow CI immediately |
| 2 | C: Performance Profiling | 1 day | Medium | Diagnostic tool for optimization |
| 3 | A: Strategy Caching | 1 day | Low | Optimization, not critical |
| 4 | B: Complex Patterns | 2-3 days | Low | Enhancement, incremental value |

**Recommendation:** Implement D (Selective Skip) first - it immediately solves the problem of slow functions blocking CI.

---

## Acceptance Criteria

```
□ Property tests can be skipped via decorator
□ Property tests can be skipped via config file
□ Slow functions can have custom max_examples
□ --profile shows performance report
□ Strategy caching reduces repeated parsing time
□ At least 3 complex patterns supported (x < y, all(), Union)
```

---

## Relationship to Other Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-08 | Foundation - contract-driven property testing |
| DX-19 | Integration - property tests in STANDARD level |
| DX-20 | Enhancement - this proposal, improves DX-08/19 |

---

*Proposal v1.0 | 2025-12-23*
