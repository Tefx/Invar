# DX-21: Package Architecture and Init Integration

**Date:** 2025-12-23
**Status:** Implemented ✅
**Priority:** ★★★★☆
**Effort:** 4.5 days

---

## Executive Summary

本提案包含两个相关改进：

1. **DX-21A: 包拆分** - `invar-runtime` (轻量运行时) + `invar-tools` (完整工具)
2. **DX-21B: Claude 初始化整合** - `invar init --claude` 调用 `claude /init` 并智能配置 MCP

### 最终命名方案

| 包名 | 用途 | 大小 |
|------|------|------|
| `invar-runtime` | 项目运行时依赖 | ~3MB |
| `invar-tools` | 开发/CI 工具 | ~100MB |

### PyPI 名称可用性

| 名称 | 状态 |
|------|------|
| `invar` | ❌ 已占用 (2015 年废弃的地图工具) |
| `python-invar` | ✅ 我们当前的包 (将废弃) |
| `invar-runtime` | ✅ 可用 |
| `invar-tools` | ✅ 可用 |

---

## Part A: Package Split (包拆分)

### Problem

当前 `python-invar` (~100MB) 包含所有依赖，但项目运行时只需要 `deal` + 自定义装饰器 (~3MB)。

### Solution: Two Packages

#### `invar-runtime` (轻量运行时)

```toml
# invar-runtime/pyproject.toml
[project]
name = "invar-runtime"
dependencies = [
    "deal>=4.0",
]
```

**包含模块：**
```
invar_runtime/
├── __init__.py          # 导出所有 API
├── contracts.py         # Contract 类 + pre/post
├── decorators.py        # must_use, strategy, skip_property_test
├── invariant.py         # invariant 函数
└── resource.py          # must_close 装饰器
```

#### `invar-tools` (完整工具)

```toml
# invar-tools/pyproject.toml (或根目录 pyproject.toml)
[project]
name = "invar-tools"
dependencies = [
    "invar-runtime>=1.0",
    "pydantic>=2.0",
    "typer>=0.9",
    "rich>=13.0",
    "returns>=0.20",
    "deal>=4.0",
    "hypothesis>=6.0",
    "crosshair-tool>=0.0.60",
    "mcp>=1.0",
]

[project.scripts]
invar = "invar.shell.cli:app"
```

**包含模块：**
```
invar/
├── __init__.py          # 版本信息，从 invar_runtime 导入
├── core/                # 静态分析逻辑
├── shell/               # CLI 命令
└── mcp/                 # MCP server
```

### Usage Patterns

```bash
# 项目依赖 (轻量)
pip install invar-runtime

# 开发者工具
uvx invar-tools guard              # 推荐：无需安装
pip install invar-tools            # 或：全局安装
pipx install invar-tools           # 或：隔离安装

# 命令使用
invar guard
invar map --top 10
invar sig src/myapp/core/models.py
```

```python
# 项目代码
from invar_runtime import pre, post, Contract, must_use
from invar_runtime import invariant, must_close
```

### Repository Structure (Option B: Flat)

```
invar/
├── pyproject.toml              # invar-tools
├── runtime/
│   ├── pyproject.toml          # invar-runtime
│   └── src/invar_runtime/      # runtime 代码
├── src/invar/                  # tools 代码
├── tests/
└── docs/
```

---

## Part B: Init Integration (初始化整合)

### Background

- **`claude /init`**: Claude Code 斜杠命令，分析代码库生成智能 CLAUDE.md
- **`invar init`**: 创建 INVAR.md, .invar/, .mcp.json

### Solution

`invar init --claude` 整合两个初始化流程，并智能配置 MCP 执行方式。

### New CLI Interface

```bash
# 完整初始化 (推荐)
invar init --claude
# 1. 运行 claude /init (智能生成 CLAUDE.md)
# 2. 追加 Invar 引用到 CLAUDE.md
# 3. 创建 INVAR.md, .invar/
# 4. 智能检测 MCP 执行方式并生成 .mcp.json

# 指定 MCP 执行方式
invar init --claude --mcp-method uvx      # 使用 uvx (推荐)
invar init --claude --mcp-method command  # 使用 PATH 中的 invar
invar init --claude --mcp-method python   # 使用当前 Python

# 非交互模式
invar init --claude --mcp-method uvx -y

# 基础初始化 (不运行 claude /init)
invar init
```

### MCP Smart Detection

```python
# src/invar/shell/mcp_config.py (新文件)

from dataclasses import dataclass
from enum import Enum
import shutil
import sys

class McpMethod(Enum):
    UVX = "uvx"
    COMMAND = "command"
    PYTHON = "python"

@dataclass
class McpExecConfig:
    method: McpMethod
    command: str
    args: list[str]
    description: str

def detect_available_methods() -> list[McpExecConfig]:
    """Detect available MCP execution methods, ordered by preference."""
    methods = []

    # 1. uvx (推荐 - 隔离、自动更新)
    if shutil.which("uvx"):
        methods.append(McpExecConfig(
            method=McpMethod.UVX,
            command="uvx",
            args=["invar-tools", "mcp"],
            description="uvx (推荐 - 隔离环境)",
        ))

    # 2. invar 命令在 PATH
    if shutil.which("invar"):
        methods.append(McpExecConfig(
            method=McpMethod.COMMAND,
            command="invar",
            args=["mcp"],
            description="invar 命令",
        ))

    # 3. 当前 Python (fallback)
    methods.append(McpExecConfig(
        method=McpMethod.PYTHON,
        command=sys.executable,
        args=["-m", "invar.mcp"],
        description=f"当前 Python ({sys.executable})",
    ))

    return methods
```

### Generated MCP Config

**Using uvx (recommended):**
```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

**Using command:**
```json
{
  "mcpServers": {
    "invar": {
      "command": "invar",
      "args": ["mcp"]
    }
  }
}
```

---

## Files to Update

### Core Configuration

| File | Change |
|------|--------|
| `pyproject.toml` | Rename to `invar-tools`, update dependencies |
| `runtime/pyproject.toml` | **New** - `invar-runtime` config |
| `.github/workflows/publish.yml` | Publish two packages |
| `.github/workflows/ci.yml` | Update install commands |
| `.pre-commit-config.yaml` | Update package name |

### Documentation

| File | Change |
|------|--------|
| `README.md` | Update install commands, badges |
| `CLAUDE.md` | Update package names, commands |
| `INVAR.md` | Update install commands |
| `docs/index.html` | Update PyPI links |
| `docs/DESIGN.md` | Update package references |
| `.invar/context.md` | Update project status |

### Templates

| File | Change |
|------|--------|
| `src/invar/templates/pre-commit-config.yaml.template` | `python-invar` → `invar-tools` |
| `src/invar/templates/CLAUDE.md.template` | Update install commands |

### Code

| File | Change |
|------|--------|
| `src/invar/__init__.py` | Import from `invar_runtime` |
| `src/invar/shell/init_cmd.py` | Add `--claude`, `--mcp-method` flags |
| `src/invar/shell/mcp_config.py` | **New** - MCP detection logic |
| `src/invar/shell/templates.py` | Use new MCP config logic |
| `runtime/src/invar_runtime/__init__.py` | **New** - Runtime exports |
| `runtime/src/invar_runtime/contracts.py` | **Move** from `src/invar/` |
| `runtime/src/invar_runtime/decorators.py` | **Move** from `src/invar/` |
| `runtime/src/invar_runtime/invariant.py` | **Move** from `src/invar/` |
| `runtime/src/invar_runtime/resource.py` | **Move** from `src/invar/` |

---

## Implementation Plan

| Phase | Task | Scope | Effort |
|-------|------|-------|--------|
| 1 | Create `runtime/` directory structure | A | 0.5 day |
| 2 | Move runtime modules to `invar_runtime` | A | 0.5 day |
| 3 | Create `runtime/pyproject.toml` | A | 0.25 day |
| 4 | Update root `pyproject.toml` for `invar-tools` | A | 0.25 day |
| 5 | Update `invar/__init__.py` to import from runtime | A | 0.25 day |
| 6 | Create `mcp_config.py` with smart detection | A+B | 0.5 day |
| 7 | Add `--claude` flag to `init_cmd.py` | B | 0.5 day |
| 8 | Implement `run_claude_init()` | B | 0.25 day |
| 9 | Implement `append_invar_reference_to_claude_md()` | B | 0.25 day |
| 10 | Update all documentation | A+B | 0.5 day |
| 11 | Update GitHub Actions for two packages | A | 0.25 day |
| 12 | Testing and verification | A+B | 0.5 day |
| **Total** | | | **4.5 days** |

---

## Acceptance Criteria

### DX-21A: Package Split

```
□ invar-runtime 可独立安装
  pip install invar-runtime
  python -c "from invar_runtime import pre, post, Contract"

□ invar-tools 可独立安装
  pip install invar-tools
  invar guard --help

□ uvx 可直接运行
  uvx invar-tools guard --static

□ 所有 python-invar 引用已更新
  grep -r "python-invar" 返回空 (除历史文档)

□ CI/CD 正常工作
  两个包都能发布到 PyPI
```

### DX-21B: Claude Integration

```
□ invar init --claude 调用 claude /init
□ CLAUDE.md 保留 claude /init 生成的内容
□ Invar 引用被追加（不覆盖）
□ 缺少 claude CLI 时给出友好提示
□ --mcp-method 正确选择执行方式
□ .mcp.json 使用选择的执行方式
```

### Combined

```
□ invar init --claude --mcp-method uvx -y 一键完成所有配置
□ 现有 invar init 行为保持兼容（不带 --claude）
```

---

## Migration Guide

### For Users

```bash
# Before (python-invar)
pip install python-invar

# After (invar-tools)
pip install invar-tools
# or
uvx invar-tools guard
```

### For Projects

```toml
# Before
dependencies = ["python-invar"]

# After
dependencies = ["invar-runtime"]
```

### Deprecation

`python-invar` will be deprecated with a message pointing to `invar-tools`:

```
DEPRECATION: python-invar is deprecated. Install invar-tools instead:
  pip install invar-tools
```

---

## References

- [Claude Code Memory Docs](https://code.claude.com/docs/en/memory)
- [Slash Commands Reference](https://code.claude.com/docs/en/slash-commands)
- [Using CLAUDE.MD files](https://www.claude.com/blog/using-claude-md-files)

---

*Proposal v2.0 | 2025-12-23 | Updated with final naming scheme*
