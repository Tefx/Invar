# DX-77: MCP Document Tools Enhancements

**Status:** ✅ Phase A Completed (Archived 2026-01-03)
**Created:** 2026-01-02
**Completed:** Unicode fuzzy (0d6b721), Batch read (9f888b6), Tests (641a772)
**Dependencies:** DX-76 Phase A-2 (completed)

## Executive Summary

Based on real-world usage of DX-76 document tools, this proposal identifies improvement opportunities to enhance usability, efficiency, and agent adoption. Focus areas: fuzzy matching, batch operations, workflow optimization, and error handling.

**Priority**: Medium
**Effort**: 1 week (Phase A completed)

---

## Part 1: Current State Analysis

### 1.1 What Works Well

✅ **Semantic addressing** - slug/fuzzy/index/line modes work as designed
✅ **Tool discoverability** - "INSTEAD of" hints guide agent behavior
✅ **Type safety** - Result[T, E] pattern prevents silent failures
✅ **Performance** - 3-5x faster than Read() for targeted section access

### 1.2 Pain Points from Real Usage

#### P1: Fuzzy Matching Limitations

**Current behavior:**
```python
# ✅ Works - ASCII slug
invar_doc_read(section="phase-b")  # Finds "6.1 Phase B: ..."

# ❌ Fails - Chinese/non-ASCII fuzzy match
invar_doc_read(section="验证计划")  # Should find "6.2 Phase B 验证计划"
```

**Impact**: Agent needs exact slug or index for non-ASCII headings.

#### P2: Multi-Section Workflow Overhead

**Current workflow:**
```python
# Agent needs 4 separate calls for related sections
invar_doc_toc("file.md")                    # 1. Get structure
invar_doc_read(section="6-1-phase-b")       # 2. Read section 1
invar_doc_read(section="6-2-phase-b")       # 3. Read section 2
invar_doc_read(section="6-3-phase-a")       # 4. Read section 3
```

**Impact**: Higher token cost, slower for multi-section analysis.

#### P3: Edit-After-Read Friction

**Current workflow:**
```python
# Step 1: Read to decide
result = invar_doc_read(section="phase-b")
# Step 2: Agent analyzes content
# Step 3: Decide to replace
invar_doc_replace(section="phase-b", content="...")
# Problem: Two separate calls, agent must repeat section path
```

**Impact**: Agent needs to track section paths across calls.

#### P4: Limited Section Discovery

**Current:**
```python
# Can only find by exact title pattern
invar_doc_find(pattern="*Phase*")

# Cannot search by:
# - Content keywords ("验证计划" in content)
# - Section level (all H3 sections)
# - Date ranges (added after 2024-01-01)
```

**Impact**: Agent falls back to full Read() for content-based discovery.

---

## Part 2: Proposed Enhancements

### 2.1 Enhanced Fuzzy Matching (Priority: High)

**Goal**: Support Unicode-aware fuzzy matching for international content.

**Implementation:**

```python
# src/invar/core/doc_parser.py

def _normalize_for_fuzzy(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    >>> _normalize_for_fuzzy("验证计划")
    '验证计划'
    >>> _normalize_for_fuzzy("Phase B 验证计划")
    'phaseb验证计划'
    """
    # Remove: punctuation, whitespace, convert ASCII to lowercase
    # Keep: Unicode characters (Chinese, etc.)
    import re
    ascii_lower = ''.join(c.lower() if c.isascii() else c for c in text)
    return re.sub(r'[^\w]', '', ascii_lower)

@pre(lambda pattern, sections: len(pattern) > 0)
@post(lambda result: result is None or isinstance(result, Section))
def find_by_fuzzy_normalized(
    pattern: str,
    sections: list[Section]
) -> Section | None:
    """Find section by normalized fuzzy match."""
    normalized_pattern = _normalize_for_fuzzy(pattern)
    for section in sections:
        if normalized_pattern in _normalize_for_fuzzy(section.title):
            return section
    return None
```

**Benefits:**
- ✅ Supports Chinese/Japanese/Korean/Cyrillic in fuzzy mode
- ✅ More tolerant of spacing and punctuation
- ✅ Backward compatible with existing ASCII slugs

---

### 2.2 Batch Section Operations (Priority: High)

**Goal**: Reduce tool calls for multi-section workflows.

#### Option A: Multi-Read (Recommended)

**New tool: `invar_doc_read_many`**

```python
# MCP tool definition
Tool(
    name="invar_doc_read_many",
    title="Read Multiple Markdown Sections",
    description=(
        "Read multiple sections from a markdown document in one call. "
        "Use this INSTEAD of multiple invar_doc_read() calls."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of section paths (slug/fuzzy/index/line)"
            }
        },
        "required": ["file", "sections"]
    }
)

# Usage example
invar_doc_read_many(
    file="DX-75.md",
    sections=["6-1-phase-b", "6-2-phase-b", "6-3-phase-a"]
)
# Returns: [
#   {"path": "6-1-phase-b", "content": "..."},
#   {"path": "6-2-phase-b", "content": "..."},
#   {"path": "6-3-phase-a", "content": "..."}
# ]
```

**Benefits:**
- ✅ Reduces 4 calls → 2 calls (toc + read_many)
- ✅ Lower latency (parallel section extraction)
- ✅ Preserves section-level granularity

#### Option B: Extended TOC (Alternative)

**Extend `invar_doc_toc` with content preview:**

```python
invar_doc_toc(
    file="DX-75.md",
    include_preview=True,  # New parameter
    preview_lines=5        # First 5 lines of each section
)
```

**Trade-off**: Single call, but TOC becomes large for big documents.

**Decision**: Implement Option A (multi-read) for better composability.

---

### 2.3 Edit Context Preservation (Priority: Medium)

**Goal**: Reduce redundancy in read → edit workflows.

**New parameter for edit tools: `context`**

```python
# Current workflow (2 tool calls)
content = invar_doc_read(section="phase-b")
# ... agent analyzes ...
invar_doc_replace(section="phase-b", content="new content")

# Proposed workflow (2 tool calls, but with context)
result = invar_doc_read(section="phase-b")
# Returns: {"path": "6-1-phase-b", "content": "...", "context_token": "abc123"}

invar_doc_replace(
    context_token="abc123",  # Reuses section resolution
    content="new content"
)
```

**Benefits:**
- ✅ Agent doesn't need to repeat section path
- ✅ Safer (context token validates section unchanged)
- ✅ Faster (skip section re-resolution)

**Implementation complexity**: Medium (needs stateful context tracking).

**Decision**: Defer to Phase B (validate demand first).

---

### 2.4 Advanced Section Discovery (Priority: Low)

**Goal**: Enable content-based and attribute-based section search.

**Extended `invar_doc_find` parameters:**

```python
invar_doc_find(
    file="DX-75.md",

    # Existing
    pattern="*Phase*",

    # New filters
    level=3,              # Only H3 sections
    content_pattern="验证",  # Sections containing "验证"
    min_size=1000,        # Sections >= 1000 chars
    max_depth=2           # Max 2 levels deep in tree
)
```

**Use case**: "Find all H3 sections about validation"

**Decision**: Implement in Phase B if usage patterns justify complexity.

---

## Part 3: Implementation Plan

### Phase A: Core Improvements (Week 1)

**High-priority, low-risk changes:**

| Task | Files | Effort |
|------|-------|--------|
| 2.1 Enhanced fuzzy matching | `doc_parser.py` | 2 days |
| 2.2 Multi-read tool | `doc_tools.py`, `server.py`, `handlers.py` | 3 days |
| Tests for A | `test_doc_parser.py`, `test_mcp_doc_tools.py` | 1 day |

**Deliverables:**
- ✅ Unicode-aware fuzzy matching
- ✅ `invar_doc_read_many` MCP tool
- ✅ Integration tests for both

### Phase B: Validation & Advanced Features (Week 2)

**Validate demand before implementing:**

| Task | Trigger | Effort |
|------|---------|--------|
| 2.3 Edit context tokens | Agent frequently repeats section paths | 2 days |
| 2.4 Advanced filters | Agent uses Grep as fallback | 2 days |
| Performance benchmarks | Phase A complete | 1 day |

**Decision gate**: Only proceed if real usage shows need.

---

## Part 4: Acceptance Criteria

### 4.1 Phase A Success Metrics

**Fuzzy Matching:**
```python
# Must pass all tests
assert find_section("验证计划", toc) is not None
assert find_section("phase b", toc).slug == "phase-b"
assert find_section("PhaseB", toc).slug == "phase-b"
```

**Multi-Read:**
```python
# Must complete in <50% time of sequential reads
import time
start = time.time()
results = invar_doc_read_many(sections=["a", "b", "c"])
elapsed = time.time() - start

# Compare to sequential baseline
assert elapsed < 0.5 * baseline_time
assert len(results) == 3
```

### 4.2 Phase B Validation

**Context tokens** - Measure agent behavior:
- Track: How often agent repeats section paths in edit calls
- Threshold: If >50% of edits repeat path, implement context tokens
- Method: Analyze MCP handler logs

**Advanced filters** - Monitor fallback patterns:
- Track: How often agent uses Grep after doc_find fails
- Threshold: If >20% of doc_find calls → Grep fallback, implement filters
- Method: Skill execution logs

---

## Part 5: Risk Assessment

### 5.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unicode normalization bugs | High | Comprehensive unicode test suite |
| Multi-read performance regression | Medium | Benchmark against sequential reads |
| Context token state management | High | Defer to Phase B, validate approach first |

### 5.2 Adoption Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent doesn't discover new tools | Medium | Update INVAR_INSTRUCTIONS with examples |
| Breaking changes to existing workflows | Low | All changes are additive (new tools/params) |

---

## Part 6: Success Indicators

**Phase A (Quantitative):**
- [ ] Fuzzy matching works for 100% of Unicode test cases
- [ ] Multi-read reduces tool calls by 50%+ in validation scenarios
- [ ] Zero regressions in existing doc tool tests

**Phase B (Qualitative):**
- [ ] Agent uses multi-read in 80%+ of multi-section workflows
- [ ] Zero requests for "read multiple sections at once" workarounds
- [ ] Positive feedback from validation scenarios (DX-75, DX-76)

---

## Appendix A: Alternatives Considered

### A.1 Server-Side Section Caching

**Idea**: Cache section resolution results in MCP server.

**Rejected because:**
- Adds stateful complexity to server
- Doesn't reduce tool calls (caching is invisible to agent)
- File edits invalidate cache (complex invalidation logic)

### A.2 Mega-Tool with All Operations

**Idea**: Single `invar_doc` tool with mode parameter.

**Rejected because:**
- Violates single-responsibility principle
- Harder for agent to discover specific operations
- Complex inputSchema reduces type safety

### A.3 SQL-Like Query Language

**Idea**: `invar_doc_query("SELECT * FROM sections WHERE level=3")`

**Rejected because:**
- Overkill for current use cases
- Higher learning curve for agent
- Adds parser complexity to Core layer

---

## Appendix B: Related Work

**DX-76**: Document tools foundation (slug, fuzzy, index, line addressing)
**DX-75**: Attention-aware framework (validates multi-section workflows)
**DX-74**: Experiment framework (Unicode content in test scenarios)

---

## Document History

- **2026-01-03**: Initial draft based on real usage feedback
- **2026-01-03**: Phase A implementation completed (Unicode fuzzy + batch read)
- **2026-01-03**: ✅ Archived - All deliverables completed, tests passing
