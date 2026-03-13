# Invar Project Context

*Last updated: 2026-01-04*

<!-- DX-58: Slimmed context for efficient startup status checks (~150 lines) -->

## Key Rules (Quick Reference)

<!-- DX-54: Rules summary for long conversation resilience -->

### Core/Shell Separation
- **Core** (`**/core/**`): @pre/@post + doctests, NO I/O imports
- **Shell** (`**/shell/**`): Result[T, E] return type

### Workflow
1. Understand → 2. Specify (contracts first) → 3. Build → 4. Validate

### Verification
- `invar_guard()` = static + doctests + CrossHair + Hypothesis
- Final should report: `guard PASS | ...`

## Task Router (DX-62)

| If you are about to... | STOP and read first |
|------------------------|---------------------|
| Write code in `core/` | `INVAR.md#core-vs-shell` |
| Write code in `shell/` | `INVAR.md#core-vs-shell` |
| Add `@pre`/`@post` contracts | `INVAR.md#contract-syntax-python` |
| Use functional patterns | `INVAR.md#core-example-python` |
| Implement a feature | `INVAR.md#usbv-workflow` |

**Rule:** Match found above? Read the file BEFORE writing code.

## Self-Reminder

<!-- DX-54: AI should re-read this file periodically -->

**When to re-read this file:**
- Starting a new task
- Completing a task (before moving to next)
- Conversation has been going on for a while (~15-20 exchanges)
- Unsure about project rules or patterns

**Quick rule check:**
- Am I in Core or Shell?
- Do I have @pre/@post contracts?
- Am I following the 4-phase workflow?
- Did I run guard before claiming "done"?

---

## Current State

 - **PyPI:** `invar-tools` v1.17.12 + `invar-runtime` v1.3.0
- **Protocol:** v5.0 (4-phase workflow, DX-58 critical section)
 - **Status:** Feature complete, Python-only surface stabilization in progress
 - **Recent:** DX-91 (Python-only simplification), DX-87 (Removed multi-agent init), v1.17.12 (Guard hardening)
- **Blockers:** None

## Active Work

See [docs/proposals/](../docs/proposals/) for planned changes.

**Current focus:** DX-91 Python-only cleanup and verification hardening

---

## Coverage Guarantee Matrix

Smart Guard (`invar guard`) runs multiple verification layers:

| Layer | Runs On | Catches |
|-------|---------|---------|
| **Static Analysis** | All Python files | Architecture violations, missing contracts |
| **Doctests** | Functions with `>>>` examples | Logic errors, edge cases |
| **CrossHair** | Functions with @pre/@post | Contract violations via symbolic execution |
| **Hypothesis** | Functions with @pre/@post | Contract violations via random testing |

### Function Coverage

| Function Has | Static | Doctests | CrossHair | Hypothesis |
|--------------|--------|----------|-----------|------------|
| @pre/@post + doctests | ✅ | ✅ | ✅ | ✅ |
| @pre/@post only | ✅ | ❌ | ✅ | ✅ |
| Doctests only | ✅ | ✅ | ❌ | ❌ |
| No contracts | ✅ | ❌ | ❌ | ❌ |

**Key Insight:** Doctests are the universal fallback. Every function should have at least one doctest.

---

## Lessons Learned (Recent)

<!-- DX-58: Keep last 10, archive older ones -->

1. **Reliability > Size Optimization** - ESLint unbundled (632 KB) beats bundled (50 KB) when architecture demands it
2. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
3. **Automatic > Opt-in** - Agents won't use flags they don't know about
4. **Example-Driven Learning** - Abstract rules don't teach; concrete code examples do
5. **Skip Requires Justification** - Each @skip_property_test needs explicit reason
6. **Review Gate as Conditional Step** - Review should be automatic trigger, not manual
7. **Process Visibility vs Task Completion** - Need explicit visibility checkpoints
8. **Enforcement Timing Matters** - Pre-commit blocks effective; hook enforcement timing matters
9. **Tools Exist ≠ Tools Used** - Habit overrides methodology
10. **Performance Enables Adoption** - Fast tools get used more

---

## Tool Priority

| Task | Primary | Fallback |
|------|---------|----------|
| See contracts | `invar sig` | — |
| Find entry points | `invar map --top` | — |
| Find specific symbol | Serena `find_symbol` | `invar map` + grep |
| Verify | `invar guard` | — |

---

## Legacy Notes

Historical integration notes were moved to archived proposal records.

---

## Release Process

**Do NOT use `twine upload` manually.** GitHub Actions handles PyPI publishing.

```bash
# 1. Update version in pyproject.toml
# 2. Commit and push
git add -A && git commit -m "Bump version to X.Y.Z" && git push

# 3. Create release (triggers automatic PyPI publish)
gh release create vX.Y.Z --title "vX.Y.Z - Title" --notes "..."
```

---

## Version History (Recent)

| Version | Date | Highlights |
|---------|------|------------|
| 1.17.0 | 2026-03 | Python-only surface, removed multi-agent init (DX-91) |
| 1.14.0 | 2026-01 | Invar usage feedback collection (DX-79), anonymization tools |
| 1.12.0 | 2026-01 | Compiler API integration (DX-78), multi-language refs |
| 1.9.0 | 2026-01 | Extension Skills (LX-07), language support foundation (LX-05/06) |
| 1.8.0 | 2025-12 | Claude hooks improvements, interactive init (DX-70) |
| 1.5.0 | 2025-12 | Language-agnostic protocol templates |
| 1.3.0 | 2025-12 | Rule detection, template sync (DX-56), protocol v5.0 |
| 1.0.0 | 2025-12 | Package split (invar-runtime + invar-tools) |

---

## Documentation Structure (DX-11)

| File | Owner | Edit? |
|------|-------|-------|
| src/invar/templates/ | **SSOT** | Yes (templates are source) |
| INVAR.md | Sync | No (`invar dev sync`) |
| CLAUDE.md | Sync + User | Regions only |
| .invar/context.md | User | Yes (this file) |
| .invar/context.md | User | Yes (this file) |

**Version Flow:** `templates/` → Invar project (via `invar dev sync`, syntax=mcp) AND → User projects (via `invar init/update`, syntax=cli)

---

<!-- ARCHIVE: Full session history in .invar/archive/ -->

*Update this file when: completing phases, making design decisions, releasing versions.*
