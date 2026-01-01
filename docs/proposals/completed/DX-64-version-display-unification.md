# DX-64: 版本显示统一

## 问题描述

`invar version` 命令显示 `1.0.0`，但实际 PyPI 包版本是 `1.5.0`。

### 当前行为

```bash
$ invar version
invar 1.0.0

$ pip show invar-tools | grep Version
Version: 1.5.0
```

### 问题影响

1. **用户困惑** - 不清楚实际安装的版本
2. **故障排除困难** - 报告问题时版本信息不准确
3. **升级验证困难** - 无法确认升级是否成功

## 提案方案

### 方案 A: 显示包版本 (推荐)

从 `importlib.metadata` 获取实际包版本:

```python
import importlib.metadata

@app.command()
def version() -> None:
    """Show Invar version."""
    pkg_version = importlib.metadata.version("invar-tools")
    console.print(f"invar-tools {pkg_version}")
```

**输出:**
```
invar-tools 1.5.0
```

### 方案 B: 同时显示包版本和协议版本

```python
@app.command()
def version() -> None:
    """Show Invar version."""
    pkg_version = importlib.metadata.version("invar-tools")
    protocol_version = "5.0"  # 从 INVAR.md 或配置读取
    console.print(f"invar-tools {pkg_version}")
    console.print(f"protocol {protocol_version}")
```

**输出:**
```
invar-tools 1.5.0
protocol 5.0
```

### 方案 C: 详细版本信息

```python
@app.command()
def version(verbose: bool = False) -> None:
    """Show Invar version."""
    pkg_version = importlib.metadata.version("invar-tools")

    if verbose:
        console.print(f"invar-tools: {pkg_version}")
        console.print(f"protocol: 5.0")
        console.print(f"python: {sys.version.split()[0]}")
        console.print(f"platform: {sys.platform}")
    else:
        console.print(f"invar-tools {pkg_version}")
```

## 实现计划

1. 修改 `src/invar/shell/commands/guard.py` 中的 `version` 命令
2. 使用 `importlib.metadata.version()` 获取包版本
3. 可选: 添加 `--verbose` 标志显示详细信息

## 影响评估

| 维度 | 影响 |
|------|------|
| 复杂度 | 低 |
| 风险 | 低 |
| 向后兼容 | 是 (输出格式变化) |
| 测试 | 需更新版本测试 |

## 决策

**推荐方案 A** - 简单直接，解决核心问题。

---

*提案状态: ✅ 已完成*
*创建日期: 2025-12-29*
*完成日期: 2025-12-29*
*来源: v1.5.0 测试报告 V150-01*
*实现: commit c1a446e*
