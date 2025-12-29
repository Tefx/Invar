# DX-66: 逃生舱口可见性增强

## 问题描述

当前 Guard 输出中，逃生舱口 (`@invar:allow`) 的使用情况不够明显。只有当数量达到阈值时才触发 `review_suggested`，但具体计数和位置不在输出中显示。

### 当前行为

```json
{
  "rule": "review_suggested",
  "message": "High escape hatch count (threshold: 3)"
}
```

问题:
- 不知道具体有多少个逃生舱口
- 不知道逃生舱口在哪些文件
- 不知道每个逃生舱口的理由

## 提案方案

### 方案 A: 添加逃生舱口摘要 (推荐)

在 Guard 输出中添加 `escape_hatches` 字段:

```json
{
  "status": "passed",
  "static": { ... },
  "escape_hatches": {
    "count": 5,
    "by_rule": {
      "missing_contract": 2,
      "shell_result": 3
    },
    "details": [
      {
        "file": "src/core/parser.py",
        "line": 42,
        "rule": "missing_contract",
        "reason": "Generic type inference not supported"
      },
      {
        "file": "src/shell/cli.py",
        "line": 15,
        "rule": "shell_result",
        "reason": "Entry point, errors printed to console"
      }
    ]
  }
}
```

### 方案 B: 专用命令

添加 `invar escapes` 命令:

```bash
$ invar escapes
Escape Hatches: 5

By Rule:
  missing_contract: 2
  shell_result: 3

Details:
  src/core/parser.py:42  missing_contract  "Generic type inference..."
  src/shell/cli.py:15    shell_result      "Entry point, errors..."
```

### 方案 C: 警告级别显示

在常规输出中添加信息级别消息:

```json
{
  "fixes": [
    {
      "rule": "escape_hatch_info",
      "severity": "info",
      "message": "5 escape hatches in use (2 missing_contract, 3 shell_result)"
    }
  ]
}
```

## 实现细节

### 逃生舱口解析

```python
def parse_escape_hatches(source: str) -> list[EscapeHatch]:
    """Parse @invar:allow comments from source code."""
    pattern = r'#\s*@invar:allow\s+(\w+):\s*(.+)'
    hatches = []

    for i, line in enumerate(source.splitlines(), 1):
        match = re.search(pattern, line)
        if match:
            hatches.append(EscapeHatch(
                line=i,
                rule=match.group(1),
                reason=match.group(2).strip()
            ))

    return hatches
```

### 阈值配置

在 `pyproject.toml` 中添加配置:

```toml
[tool.invar.guard]
escape_hatch_warning_threshold = 3  # 默认值
escape_hatch_error_threshold = 10   # 可选: 超过则失败
```

### 与 review_suggested 的关系

- `escape_hatch_count >= warning_threshold` → `review_suggested` 警告
- `escape_hatch_count >= error_threshold` → Guard 失败 (可选)
- 无论阈值，`escape_hatches` 摘要始终显示

## 用户价值

| 场景 | 当前 | 改进后 |
|------|------|--------|
| 快速了解逃生舱口使用 | 不可见 | 摘要可见 |
| 审查时定位逃生舱口 | 手动搜索 | 位置列表 |
| 评估技术债务 | 困难 | 按规则分类 |
| 团队规范执行 | 难以监控 | 可配置阈值 |

## 影响评估

| 维度 | 影响 |
|------|------|
| 复杂度 | 低 |
| 风险 | 低 |
| 向后兼容 | 是 (新增字段) |
| 性能 | 低 (已解析源码) |

## 决策

**推荐方案 A** - 集成到现有输出中最自然。

---

*提案状态: ✅ 已完成*
*创建日期: 2025-12-29*
*完成日期: 2025-12-29*
*来源: v1.5.0 测试报告 V150-03*
*实现: 方案 A - 集成到 Guard 输出*
