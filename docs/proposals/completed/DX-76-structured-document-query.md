# DX-76: Structured Document Query Tools

**Status:** ✅ Completed (Archived 2026-01-03)
**Created:** 2026-01-02
**Completed:** Phase A-1 (d256a37), Phase A-2 (9ec8f9d), Phase B (d42161b)
**Related:** DX-75 (Attention-Aware Framework), DX-77 (Enhancements)

## Problem Statement

LLM Agents 在读取长文档（PRD、Spec、设计文档）时面临三个问题：

| 问题 | 描述 | 影响 |
|------|------|------|
| **注意力漂移** | 读取 2000+ 行文档时，后半部分被略读 | 遗漏需求 |
| **Token 浪费** | 全量读取时，大部分内容与当前任务无关 | 成本 + 上下文污染 |
| **Grep 不可靠** | 关键词搜索无法理解文档结构 | 遗漏结构化信息 |

### 与 DX-75 的关系

```
DX-75 (代码审查):  注意力漂移  →  遗漏 bug     →  影响质量
DX-76 (文档阅读):  注意力漂移  →  遗漏需求    →  影响完整性
```

相同的现象，不同的领域。DX-75 的解决方案（枚举 + 分块 + 隔离）可能同样适用。

---

## Tool Design

### 命名规范

使用 `invar_doc_*` 前缀，与现有 `invar_guard`, `invar_sig`, `invar_map` 保持一致：

| 工具 | 用途 | 类比 |
|------|------|------|
| `invar_doc_toc` | 提取结构 | `invar_sig` |
| `invar_doc_read` | 读取章节 | `find_symbol --include_body` |
| `invar_doc_find` | 查找章节 | `invar_map` + grep |
| `invar_doc_replace` | 替换章节 | `replace_symbol_body` |
| `invar_doc_insert` | 插入章节 | `insert_after_symbol` |
| `invar_doc_delete` | 删除章节 | - |

**CLI 别名:** `invar doc toc`, `invar doc read`, etc.

### 核心工具 (Phase A-1)

#### invar_doc_toc

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_toc                                              │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 展示文档结构 (Table of Contents)                   │
│                                                             │
│  Input:                                                     │
│    file: Path | glob pattern (支持多文件)                    │
│    depth: int = None (all levels)                           │
│    format: "json" | "text" = "json"                         │
│                                                             │
│  Output (JSON, 默认):                                       │
│    {                                                        │
│      "sections": [                                          │
│        {"title": "Introduction", "slug": "introduction",    │
│         "level": 1, "line_start": 1, "line_end": 45,        │
│         "char_count": 1200, "path": "introduction",         │
│         "children": [...]},                                 │
│        ...                                                  │
│      ],                                                     │
│      "frontmatter": {"line_start": 1, "line_end": 5}        │
│    }                                                        │
│                                                             │
│  Output (text, --format=text):                              │
│    [frontmatter] (1-5, 120B)                                │
│    # Introduction (6-45, 1.2K)                              │
│      ## Background (10-20, 400B)                            │
│      ## Goals (21-45, 800B)                                 │
│    # Requirements (46-200, 8.5K)                            │
│      ## Functional (47-150, 5.2K)                           │
│                                                             │
│  Value: 快速了解结构，决定读取策略                            │
└─────────────────────────────────────────────────────────────┘
```

#### invar_doc_read

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_read                                             │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 读取指定章节内容                                   │
│                                                             │
│  Input:                                                     │
│    file: Path                                               │
│    section: str (章节路径)                                   │
│    include_children: bool = True                            │
│                                                             │
│  Section Addressing (章节寻址):                              │
│    • Path: "Requirements/Functional/Auth"                   │
│    • Fuzzy: "auth" (自动匹配最相关)                          │
│    • Index: "#1/#0/#2" (按顺序索引)                          │
│    • Line: "@48" (行号)                                     │
│    • Frontmatter: "@frontmatter"                            │
│                                                             │
│  Output (JSON):                                             │
│    {"path": "requirements/auth", "content": "...",          │
│     "line_start": 48, "line_end": 80}                       │
│                                                             │
│  Value: 精确获取，避免全量读取                               │
└─────────────────────────────────────────────────────────────┘
```

#### invar_doc_find

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_find                                             │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 查找匹配的章节                                     │
│                                                             │
│  Input:                                                     │
│    file: Path | glob pattern (支持多文件)                    │
│    pattern: str (标题 glob 模式)                             │
│    content: str = None (内容搜索)                            │
│    level: int = None (限定层级)                              │
│                                                             │
│  Output (JSON):                                             │
│    {"matches": [                                            │
│      {"file": "spec.md",                                    │
│       "path": "requirements/functional/authentication",     │
│       "title": "Authentication",                            │
│       "line_start": 48, "line_end": 80, "char_count": 1500},│
│      {"file": "spec.md",                                    │
│       "path": "security/authorization", ...}                │
│    ]}                                                       │
│                                                             │
│  Value: 结构感知的搜索，优于纯 grep                          │
└─────────────────────────────────────────────────────────────┘
```

### 扩展工具 (Phase A-2, if needed)

#### invar_doc_replace

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_replace                                          │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 替换章节内容                                       │
│                                                             │
│  Input:                                                     │
│    file: Path                                               │
│    section: str                                             │
│    content: str (新内容)                                     │
│    keep_heading: bool = True                                │
│    include_children: bool = True                            │
│                                                             │
│  Behavior:                                                  │
│    • 替换从当前 heading 到下一个同级 heading 之间的内容       │
│    • keep_heading=True 保留原标题行                          │
│    • include_children=True 替换整个子树                      │
│                                                             │
│  Output (JSON):                                             │
│    {"success": true, "old_content": "...",                  │
│     "new_line_start": 48, "new_line_end": 85}               │
└─────────────────────────────────────────────────────────────┘
```

#### invar_doc_insert

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_insert                                           │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 插入新章节                                         │
│                                                             │
│  Input:                                                     │
│    file: Path                                               │
│    anchor: str (参考章节)                                    │
│    content: str (新章节，含 heading)                         │
│    position: "before" | "after" | "first_child" | "last_child"│
│                                                             │
│  Output (JSON):                                             │
│    {"success": true, "inserted_at": 85,                     │
│     "new_section_path": "requirements/new-feature"}         │
└─────────────────────────────────────────────────────────────┘
```

#### invar_doc_delete

```
┌─────────────────────────────────────────────────────────────┐
│  invar_doc_delete                                           │
│  ───────────────────────────────────────────────────────────│
│  Purpose: 删除章节                                           │
│                                                             │
│  Input:                                                     │
│    file: Path                                               │
│    section: str                                             │
│    include_children: bool = True                            │
│                                                             │
│  Output (JSON):                                             │
│    {"success": true, "deleted_content": "...",              │
│     "deleted_lines": [48, 80]}                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Section Path Syntax

```
┌─────────────────────────────────────────────────────────────┐
│  章节寻址语法                                                │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Slug Path (推荐):                                          │
│    "requirements/functional/authentication"                 │
│    - 自动 slugify 标题                                       │
│    - 大小写不敏感                                            │
│    - 空格 → 连字符                                           │
│                                                             │
│  Fuzzy Match:                                               │
│    "auth" → 匹配 "Authentication" 或 "Authorization"         │
│    - 如果歧义，返回错误并列出候选                            │
│                                                             │
│  Index Path:                                                │
│    "#0/#1/#0" → 第1个H1 / 第2个子H2 / 第1个子H3              │
│    - 确定性寻址                                              │
│                                                             │
│  Line Anchor:                                               │
│    "@48" → 第48行开始的章节                                  │
│    - 从 invar_doc_toc 输出直接使用                           │
│                                                             │
│  Frontmatter:                                               │
│    "@frontmatter" → YAML front matter 块                    │
│    - 特殊保留路径                                            │
│                                                             │
│  歧义处理:                                                   │
│    invar_doc_read file.md "overview"                        │
│    → Error: Ambiguous "overview" matches:                   │
│         1. introduction/overview (@5)                       │
│         2. summary/overview (@180)                          │
│       Use full path or @line to disambiguate.               │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### 技术决策

#### Parser 选择: markdown-it-py

| 维度 | [mistune](https://github.com/lepture/mistune) | [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | 决策 |
|------|--------|----------------|------|
| **速度** | 最快 (~14ms) | 较慢 (~42ms, 3x) | 单文件解析不重要 |
| **CommonMark** | 部分兼容 | 完全兼容 | ✅ 更安全 |
| **行号支持** | 需自定义 | **内置 `token.map`** | ✅ 省去自定义 |
| **边界情况** | 可能有问题 | 处理更好 | ✅ 更可靠 |
| **生态** | 独立 | Jupyter/MkDocs 依赖 | 成熟 |

**结论:** 使用 **markdown-it-py**

```python
from markdown_it import MarkdownIt

md = MarkdownIt()
tokens = md.parse("# Hello\n\nWorld")
# tokens[0].map = [0, 1]  # 行号范围，0-indexed
```

#### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Tools / CLI Commands                                   │
│  (doc_toc, doc_read, doc_find, ...)                         │
├─────────────────────────────────────────────────────────────┤
│  src/invar/shell/doc_tools.py                               │
│  - I/O 操作 (文件读写)                                       │
│  - 返回 Result[T, Error]                                    │
├─────────────────────────────────────────────────────────────┤
│  src/invar/core/doc_parser.py                               │
│  - 纯逻辑，无 I/O                                           │
│  - @pre/@post 契约                                          │
│  - Section 语义层                                            │
├─────────────────────────────────────────────────────────────┤
│  markdown-it-py (外部库)                                     │
│  - Markdown → Token AST                                     │
│  - 行号映射                                                  │
└─────────────────────────────────────────────────────────────┘
```

#### Core 模块设计

```python
# src/invar/core/doc_parser.py

@dataclass
class Section:
    """A document section (heading + content)."""
    title: str           # "Authentication"
    slug: str            # "authentication"
    level: int           # 1-6
    line_start: int      # 48
    line_end: int        # 80
    char_count: int      # 1500
    path: str            # "requirements/functional/authentication"
    children: list[Section]

@pre(lambda source: isinstance(source, str))
@post(lambda result: all(s.line_start > 0 for s in result))
def parse_toc(source: str) -> list[Section]:
    """Parse markdown source into section tree."""
    ...

@pre(lambda sections, path: len(path) > 0)
def find_section(sections: list[Section], path: str) -> Section | None:
    """Find section by path (slug, fuzzy, index, or line)."""
    ...

@pre(lambda source, section: section.line_start <= section.line_end)
def extract_content(source: str, section: Section) -> str:
    """Extract section content from source."""
    ...
```

---

## Implementation Path

### Phase B: Protocol Only (推荐起点)

**零代码，仅提示词更新。**

```
/investigate 和 /develop UNDERSTAND 阶段添加：

对于 >500 行文档:
1. 首先: grep "^#" 提取所有 headings
2. 创建 TodoWrite 列出每个 section
3. 逐 section 处理，明确标记已读
4. 维护 running summary (关键需求列表)
5. 完成时: 对照 heading 列表验证覆盖
```

| 成本 | 收益 |
|------|------|
| ~50 行提示词 | 防止遗漏 |

### Phase A-1: Core Tools

**实现核心三件套。**

| 工具 | 行数估算 | 依赖 |
|------|---------|------|
| doc_toc | ~150 | doc_parser |
| doc_read | ~100 | doc_parser |
| doc_find | ~100 | doc_parser |
| doc_parser (core) | ~300 | markdown-it-py |
| **Total** | ~650 | |

### Phase A-2: Extended Tools (if needed)

| 工具 | 行数估算 | 触发条件 |
|------|---------|---------|
| doc_replace | ~200 | 频繁编辑 spec |
| doc_insert | ~150 | 需要结构化插入 |
| doc_delete | ~100 | 需要结构化删除 |

---

## Recommended Path

```
Phase B (立即): 添加文档处理协议到 skill 提示词
     ↓
验证: 是否经常需要手动 grep + offset?
     ↓
如果是 → Phase A-1: 实现 doc_toc, doc_read, doc_find
     ↓
如果结构编辑频繁 → Phase A-2: doc_replace, doc_insert, doc_delete
```

---

## Decisions Made

| 问题 | 决策 | 理由 |
|------|------|------|
| Parser | markdown-it-py | 内置行号，CommonMark 兼容 |
| 架构 | Core + Shell 分层 | 符合 Invar 规范 |
| 命名 | `invar_doc_*` 前缀 | 与 `invar_guard`, `invar_sig`, `invar_map` 一致 |
| 格式 | 仅 Markdown | 现阶段足够，可扩展 |
| 缓存 | 不需要 | 工具不消耗 token |
| 输出格式 | JSON 默认，可选 text | Agent native (更易解析) |
| 多文件 | 支持 glob pattern | toc/find 支持批量操作 |
| Setext headings | 支持 | `===` 和 `---` 下划线标题 |
| Front matter | 显示 + 可查询 | toc 显示位置，`@frontmatter` 可访问 |
| 结构校验 | 静默 (A) | 不校验层级跳跃，与 markdown 容忍度一致 |
| 内部链接 | 延后 | 后续版本考虑 `[text](#anchor)` 导航 |

---

## Appendix: Edge Cases

### Markdown 解析复杂性

```markdown
# Section 1

```markdown
# This is code, not a heading
```

## Real Section 2

| Header | Col |
|--------|-----|
| # Not a heading | data |

<details>
<summary>## Also not a heading</summary>
Content
</details>
```

**markdown-it-py 处理:**
- ✅ Fenced code blocks — 正确识别为代码
- ✅ Tables — 正确处理
- ✅ HTML blocks — 正确跳过
- ✅ Setext headings — `===` (H1) 和 `---` (H2) 原生支持
- ⚠️ Front matter — 需要 `mdit-py-plugins` 扩展

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-02 | Initial draft for discussion |
| 0.2 | 2026-01-02 | 完整工具设计、架构决策 (markdown-it-py)、章节寻址语法 |
| 0.3 | 2026-01-02 | 最终设计决策: `invar_doc_*` 命名、JSON 默认输出、多文件支持、Setext/Frontmatter 处理 |
| 1.0 | 2026-01-02 | ✅ Phase A-1 实施完成 (d256a37): doc_toc, doc_read, doc_find + doc_parser |
| 1.1 | 2026-01-02 | ✅ Phase A-2 实施完成 (9ec8f9d): doc_replace, doc_insert, doc_delete |
| 1.2 | 2026-01-02 | ✅ Phase B 实施完成 (d42161b): INVAR.md protocol updates |
| 2.0 | 2026-01-03 | ✅ Archived - All phases complete, enhanced by DX-77 |

---
