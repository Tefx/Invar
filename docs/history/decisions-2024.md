# Design Decisions

## 2024-12-18: Phase 2 Implementation Lessons

**Observation:** During Phase 2 development, `classify_file` function exceeded 50-line limit due to docstring.

**Solution:** Extract helper function `_matches_path_prefix` to reduce main function size.

**Lesson:** Function size limits are effective at forcing refactoring. Good docstrings can push functions over the limit - consider this when writing comprehensive examples.

**Pattern matching edge case:** `**/domain/**` requires special handling to match `src/domain/models.py`. The `matches_pattern` function handles this by trying multiple subpath matches.

---

## 2024-12-18: Pattern-based Classification (Phase 2)

**Decision:** Support glob patterns for Core/Shell classification alongside path-based approach.

**Rationale:**
- Existing projects have established structures (Django, Flask, etc.)
- Requiring src/core and src/shell forces major refactoring
- Patterns allow zero-refactor adoption
- Priority: patterns > paths > defaults

**Configuration:**
```toml
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**"]
```

**Status:** Planned for Phase 2

---

## 2024-12-18: Multiple Configuration Sources (Phase 2)

**Decision:** Support pyproject.toml, invar.toml, and .invar/config.toml with priority order.

**Rationale:**
- Not all projects use pyproject.toml (scripts, notebooks, legacy projects)
- invar.toml provides standalone configuration
- Lowers adoption barrier significantly

**Priority:**
1. pyproject.toml [tool.invar.guard]
2. invar.toml [guard]
3. .invar/config.toml [guard]
4. Built-in defaults

**Status:** Planned for Phase 2

---

## 2024-12-18: Flexible invar init (Phase 2)

**Decision:** Make `invar init` work without pyproject.toml and make directory creation optional.

**Rationale:**
- Current requirement of pyproject.toml is a barrier
- Not all projects need src/core and src/shell directories
- Flexibility increases adoption

**Options:**
```bash
invar init              # Interactive
invar init --dirs       # Always create directories
invar init --no-dirs    # Never create directories
```

**Status:** Planned for Phase 2

---

## 2024-12-18: Context Management Approach

**Decision:** Use `.invar/context.md` file for context persistence

**Rationale:**
- Simple file-based approach, no external dependencies
- Version controlled with project
- Human and AI readable
- Follows Occam's razor principle

**Alternatives Considered:**
- claude-mem (SQLite + Chroma) → Too heavy for single-project use
- Enhanced CLAUDE.md → Would mix static and dynamic content
- No context management → Would lose information across sessions

---

## 2024-12-18: Agent Roles as Optional

**Decision:** Keep roles (Implementer, Reviewer, Adversary) optional, not core protocol

**Rationale:**
- 80% of value comes from Four Laws + ICIV
- Roles are cognitive tools, not enforceable rules
- Different projects need different review intensity
- Keeps INVAR.md focused and concise

**Location:**
- INVAR.md Section 9: Brief mention with decision flow
- CLAUDE.md: Detailed "When to Use Each Role" guidance
- docs/AGENTS.md: Full role definitions and prompts

---

## 2024-12-18: Distribution via PyPI with Templates

**Decision:** Bundle templates in PyPI package, copy on `invar init`

**Rationale:**
- Single `pip install invar` provides complete experience
- Templates always in sync with tool version
- No separate download needed

**Implementation:**
- Templates in src/invar/templates/
- pyproject.toml force-include for non-Python files
- importlib.resources for package data access

---

## 2024-12-17: Top-Level Symbols Only

**Decision:** Use `tree.body` instead of `ast.walk()` in parser

**Rationale:**
- Only need top-level functions and classes
- ast.walk() traversed into class bodies, flagging methods as functions
- Simpler and more correct behavior

**Impact:** Fixed false positives in guard output

---

## 2024-12-17: Core Receives Strings, Not Paths

**Decision:** Core functions receive file content as strings, Shell handles I/O

**Rationale:**
- Maintains Core purity (no file system access)
- Makes Core functions easily testable
- Clear separation of concerns

**Example:**
```python
# Shell reads file
content = Path("foo.py").read_text()

# Core processes string (pure)
info = parse_source(content, path="foo.py")
```

---

*Add new decisions at the top of this file.*
