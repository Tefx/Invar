# Invar Project Context

*Last updated: 2025-12-27*

<!-- DX-58: Slimmed context for efficient Check-In (~150 lines) -->

## Key Rules (Quick Reference)

<!-- DX-54: Rules summary for long conversation resilience -->

### Core/Shell Separation
- **Core** (`**/core/**`): @pre/@post + doctests, NO I/O imports
- **Shell** (`**/shell/**`): Result[T, E] return type

### USBV Workflow
1. Understand → 2. Specify (contracts first) → 3. Build → 4. Validate

### Verification
- `invar_guard()` = static + doctests + CrossHair + Hypothesis
- Final must show: `✓ Final: guard PASS | ...`

## Task Router (DX-62)

| If you are about to... | STOP and read first |
|------------------------|---------------------|
| Write code in `core/` | `.invar/examples/contracts.py` |
| Write code in `shell/` | `.invar/examples/core_shell.py` |
| Add `@pre`/`@post` contracts | `.invar/examples/contracts.py` |
| Use functional patterns | `.invar/examples/functional.py` |
| Implement a feature | `.invar/examples/workflow.md` |

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
- Am I following USBV workflow?
- Did I run guard before claiming "done"?

---

## Current State

- **PyPI:** `invar-tools` + `invar-runtime` v1.3.0
- **Protocol:** v5.0 (USBV workflow, DX-58 critical section)
- **Status:** Feature complete, zero technical debt
- **Recent:** DX-57 (hooks proposal), DX-58 (document structure optimization)
- **Blockers:** None

## Active Work

See [docs/proposals/](../docs/proposals/) for planned changes.

**Current focus:** DX-57/DX-58 implementation

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

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Example-Driven Learning** - Abstract rules don't teach; concrete code examples do
4. **Skip Requires Justification** - Each @skip_property_test needs explicit reason
5. **Review Gate as Conditional Step** - Review should be automatic trigger, not manual
6. **Process Visibility vs Task Completion** - Need explicit visibility checkpoints
7. **Enforcement Timing Matters** - Pre-commit blocks effective; PreToolUse hooks too late
8. **Tools Exist ≠ Tools Used** - Habit overrides methodology
9. **Performance Enables Adoption** - Fast tools get used more
10. **Session Context > Async Feedback** - Problems caught during session beat CI feedback

---

## Tool Priority

| Task | Primary | Fallback |
|------|---------|----------|
| See contracts | `invar sig` | — |
| Find entry points | `invar map --top` | — |
| Find specific symbol | Serena `find_symbol` | `invar map` + grep |
| Verify | `invar guard` | — |

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
| 1.3.0 | 2025-12 | Rule detection, template sync (DX-56), protocol v5.0 |
| 1.0.2 | 2025-12 | Dual licensing: Apache-2.0 + GPL-3.0 + CC-BY-4.0 |
| 1.0.0 | 2025-12 | Package split (invar-runtime + invar-tools) |
| 0.8.0 | 2025-12 | Simplified verification levels (4→2) |
| 0.7.0 | 2025-12 | Zero technical debt (75→0 warnings) |

---

## Documentation Structure (DX-11)

| File | Owner | Edit? |
|------|-------|-------|
| src/invar/templates/ | **SSOT** | Yes (templates are source) |
| INVAR.md | Sync | No (`invar dev sync`) |
| CLAUDE.md | Sync + User | Regions only |
| .invar/context.md | User | Yes (this file) |
| .invar/examples/ | Sync | `invar dev sync` |

**Version Flow:** `templates/` → Invar project (via `invar dev sync`, syntax=mcp) AND → User projects (via `invar init/update`, syntax=cli)

---

<!-- ARCHIVE: Full session history in .invar/archive/ -->

*Update this file when: completing phases, making design decisions, releasing versions.*
