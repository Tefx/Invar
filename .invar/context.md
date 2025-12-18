# Invar Project Context

*Last updated: 2024-12-18*

## Current State

- **Phase 1 (Guard):** Complete ✅
- **Phase 2 (Perception):** Not started
- **Working on:** Framework restructuring complete, ready for Phase 2
- **Blockers:** None

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| core/models.py | ✅ | Pydantic models for Symbol, Violation, etc. |
| core/parser.py | ✅ | AST parsing, extracts symbols and contracts |
| core/rules.py | ✅ | Rule checking with @pre/@post |
| shell/cli.py | ✅ | guard, init, version commands |
| shell/fs.py | ✅ | File system operations |
| shell/config.py | ✅ | Configuration loading |
| templates/ | ✅ | INVAR.md, CLAUDE.md.template, context.md.template |

## Recent Decisions

1. **Roles as optional enhancement** (2024-12-18)
   - Kept in AGENTS.md, brief mention in INVAR.md Section 9
   - Reason: 80% of value from Four Laws + ICIV, roles add complexity

2. **Context management via .invar/context.md** (2024-12-18)
   - Simple file-based approach, no external dependencies
   - Follows Occam's razor principle

3. **Templates distributed via PyPI** (2024-12-18)
   - `invar init` copies templates to user project
   - Uses importlib.resources for package data access

## Lessons Learned

1. **@pre lambda signature** → Must accept ALL function parameters
   ```python
   # Wrong: @pre(lambda x: x >= 0)
   # Right: @pre(lambda x, y: x >= 0)
   ```

2. **returns Result checking** → Use isinstance, not method
   ```python
   # Wrong: result.is_failure()
   # Right: isinstance(result, Failure)
   ```

3. **Default exclude_paths** → Must include .venv, __pycache__, .pytest_cache

4. **AST symbol extraction** → Use tree.body, not ast.walk() for top-level only

5. **CLI function size** → Extract helpers to keep under 50 lines

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.3 - the law |
| CLAUDE.md | Development guide for this project |
| docs/DESIGN.md | Technical design with architecture details |
| docs/AGENTS.md | Role definitions (Implementer, Reviewer, Adversary) |
| docs/VISION.md | Philosophy and motivation |

## Next Steps (Phase 2)

1. Implement core/references.py - Reference counting
2. Implement core/formatter.py - Output formatting
3. Add `invar map` command - Symbol map generation
4. Add `invar sig` command - Signature extraction

## Architecture Notes

```
Core receives STRING content, not file paths.
Shell reads files → passes content to Core → formats output.

src/invar/
├── core/           # Pure logic, no I/O, has contracts
├── shell/          # I/O operations, returns Result
└── templates/      # Files for invar init
```

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
