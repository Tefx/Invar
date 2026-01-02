# DX-76: Structured Document Query Tools

**Status:** Discussion
**Created:** 2026-01-02
**Related:** DX-75 (Attention-Aware Framework)

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

## Proposed Solution

### 核心思路

参考 Serena 对代码的 symbolic 操作：

| Serena (代码) | DX-76 (文档) | 功能 |
|--------------|-------------|------|
| `get_symbols_overview` | `doc_map` | 提取结构 |
| `find_symbol` | `doc_fetch` | 读取指定部分 |
| `replace_symbol_body` | `doc_replace` | 修改指定部分 |

### 工具设计 (草案)

#### doc_map

```
doc_map <file>

输出:
# Introduction (1-45, 850 chars)
  ## Background (5-20, 320 chars)
  ## Goals (21-45, 530 chars)
# Requirements (46-200, 3200 chars)
  ## Functional (47-120, 1500 chars)
    ### Authentication (48-80, 700 chars)
    ### Authorization (81-120, 800 chars)
  ## Non-Functional (121-200, 1700 chars)
# Implementation Notes (201-350, 2800 chars)
...
```

**价值:** 快速了解文档结构，决定读取哪些部分。

#### doc_fetch

```
doc_fetch <file> "Requirements/Functional/Authentication"

输出:
### Authentication

Users must be able to:
- Login with email/password
- Login with OAuth (Google, GitHub)
- Reset password via email
...
```

**价值:** 精确读取，避免 token 浪费。

#### doc_replace

```
doc_replace <file> "Requirements/Functional/Authentication" <new_content>
```

**价值:** 结构化编辑，保持文档一致性。

---

## Value Assessment

### 支持论点

| 论点 | 分析 |
|------|------|
| **问题真实** | 读 500+ 行 spec，section 8 确实比 section 1 更容易遗漏 |
| **Markdown 有结构** | Heading hierarchy 提供天然的 symbolic structure |
| **Serena 模式验证** | 代码的 symbolic 操作已证明有效 |
| **分块处理** | Section-by-section 允许 attention refresh |

### 反对论点

| 论点 | 分析 |
|------|------|
| **Markdown 解析复杂** | 无正式 AST，边界情况多 |
| **未解决核心问题** | 漂移是 PROCESSING 问题，不仅是 READING 问题 |
| **现有工具可能足够** | `grep "^#"` + `Read --offset` 能做类似效果 |
| **文档格式多样** | PRD 结构差异大 |

### 关键洞察

**核心价值不在工具，而在处理协议。**

DX-75 的教训：枚举 → 逐个处理 → 防止漂移

同样适用于文档：枚举章节 → 逐章处理 → 防止遗漏

---

## Implementation Options

### Option B: Protocol Only (推荐起点)

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

### Option A-lite: doc_toc Only

**仅实现结构提取，80% 价值 20% 成本。**

```python
def doc_toc(file: Path) -> list[SectionInfo]:
    """Extract heading structure with line ranges."""
```

| 成本 | 收益 |
|------|------|
| ~200 行代码 | 结构可视化 |

### Option A-full: Complete Toolset

**完整 Serena 风格工具。**

| 成本 | 收益 |
|------|------|
| ~800 行代码 | 精确操作 |

**延后理由:**
- `doc_replace` 对于 spec 很少使用（我们通常不编辑 spec）
- 复杂的 heading 层级继承处理

---

## Recommended Path

```
Phase B (立即): 添加文档处理协议
     ↓
验证: 是否经常需要手动 grep + offset?
     ↓
如果是 → Phase A-lite: 实现 doc_toc
     ↓
如果结构操作频繁 → Phase A-full
```

---

## Open Questions

1. **实现位置:** Core (纯解析) + Shell (文件操作)?
2. **Markdown 解析器:** 使用现有库 (mistune/markdown-it) 还是自定义?
3. **非 Markdown 格式:** 是否需要支持 RST, AsciiDoc?
4. **嵌套复杂度:** 如何处理深层嵌套 (H1 > H2 > H3 > H4)?
5. **表格/代码块:** Section 边界如何处理嵌入的表格和代码块?

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

**需要考虑:**
- Fenced code blocks (```)
- Inline code with #
- HTML 块中的 markdown
- Tables 中的 #
- Front matter (YAML)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-02 | Initial draft for discussion |

---

*Discussion phase - not yet approved for implementation.*
