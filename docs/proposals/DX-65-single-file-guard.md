# DX-65: Guard 单文件支持

## 问题描述

`invar guard` 命令只接受目录路径，不支持单文件验证。

### 当前行为

```bash
$ invar guard src/core/calculator.py
Error: Invalid value for '[PATH]': Directory 'src/core/calculator.py' is a file.
```

### 用户场景

1. **快速验证单个文件** - 修改一个文件后想快速检查
2. **精确定位问题** - 已知问题在某文件，只想检查该文件
3. **CI/CD 优化** - 只验证 PR 中变更的文件

## 提案方案

### 方案 A: 自动检测路径类型 (推荐)

```python
@app.command()
def guard(
    path: Path = typer.Argument(
        Path("."),
        help="Project root directory or single file",
        exists=True,
    ),
    ...
) -> None:
    if path.is_file():
        # 单文件模式
        files_to_check = [path]
    else:
        # 目录模式
        files_to_check = find_python_files(path)
```

**用法:**
```bash
invar guard src/core/calculator.py  # 单文件
invar guard src/core/               # 目录
invar guard                         # 项目根目录
```

### 方案 B: 显式标志

```python
@app.command()
def guard(
    path: Path = ...,
    file: bool = typer.Option(False, "--file", "-f", help="Treat path as file"),
    ...
) -> None:
    if file:
        files_to_check = [path]
    else:
        files_to_check = find_python_files(path)
```

**用法:**
```bash
invar guard -f src/core/calculator.py
invar guard --file src/core/calculator.py
```

### 方案 C: 多路径支持

```python
@app.command()
def guard(
    paths: list[Path] = typer.Argument(
        [Path(".")],
        help="Files or directories to check",
    ),
    ...
) -> None:
    files_to_check = []
    for path in paths:
        if path.is_file():
            files_to_check.append(path)
        else:
            files_to_check.extend(find_python_files(path))
```

**用法:**
```bash
invar guard src/core/calculator.py src/core/validator.py
invar guard src/core/*.py  # Shell 展开
```

## 实现细节

### 配置加载

单文件模式仍需加载项目配置:

```python
def guard_single_file(file_path: Path) -> Result[GuardReport, str]:
    # 向上查找 pyproject.toml 或 invar.toml
    project_root = find_project_root(file_path)
    config = load_config(project_root)

    # 确定文件分类 (Core/Shell)
    classification = classify_file(file_path, config)

    # 运行相应规则
    return run_rules(file_path, classification, config)
```

### 输出格式

单文件模式可简化输出:

```json
{
  "status": "passed",
  "file": "src/core/calculator.py",
  "classification": "core",
  "errors": 0,
  "warnings": 1,
  "fixes": [...]
}
```

## 与现有功能的交互

| 功能 | 单文件支持 | 说明 |
|------|------------|------|
| `--changed` | 兼容 | 如果文件未变更，跳过 |
| `-c` (contracts-only) | 兼容 | 只检查该文件合约 |
| `--coverage` | 需调整 | 覆盖率只针对单文件 |
| `--strict` | 兼容 | 应用于单文件 |

## 影响评估

| 维度 | 影响 |
|------|------|
| 复杂度 | 中 |
| 风险 | 低 |
| 向后兼容 | 是 |
| 测试 | 需新增单文件测试 |

## 决策

**推荐方案 A** - 自动检测最符合用户直觉。

---

*提案状态: ✅ 已完成*
*创建日期: 2025-12-29*
*完成日期: 2025-12-29*
*来源: v1.5.0 测试报告 V150-02*
*实现: commit 6eeaf9e*
