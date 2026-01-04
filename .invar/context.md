# Invar Project Context

*Last updated: 2026-01-04*

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

- **PyPI:** `invar-tools` v1.17.2 + `invar-runtime` v1.3.0
- **Protocol:** v5.0 (USBV workflow, DX-58 critical section)
- **Status:** Feature complete, TypeScript tooling production-ready
- **Recent:** DX-22 (Fix-or-Explain complexity), LX-06 (Unbundled eslint-plugin), DX-81 (Multi-agent init)
- **Blockers:** None

## Active Work

See [docs/proposals/](../docs/proposals/) for planned changes.

**Current focus:** LX-06 completed - TypeScript tools production-ready with unbundled distribution

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
8. **Enforcement Timing Matters** - Pre-commit blocks effective; PreToolUse hooks too late
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

## TypeScript Integration (DX-78)

**Status:** Complete and reviewed (2026-01-03)

### Architecture

- **Python wrapper:** `src/invar/shell/ts_compiler.py` (uses subprocess to call Node.js)
- **TypeScript tool:** `src/invar/node_tools/ts-query.js` (TypeScript Compiler API)
- **Python refs:** `src/invar/shell/py_refs.py` (jedi library)
- **CLI integration:** `perception.py`, `guard.py` (multi-language routing)
- **MCP integration:** `handlers.py`, `server.py` (invar_refs tool)

### Supported Commands

| Command | Python | TypeScript |
|---------|--------|------------|
| `invar sig <file>` | ✅ | ✅ |
| `invar map <path>` | ✅ | ✅ |
| `invar refs <file>::<symbol>` | ✅ (jedi) | ✅ (TS Compiler API) |

### Security Model

- **Single-shot subprocess:** Process starts, runs query, outputs JSON, exits
- **No orphan risk:** No persistent Node.js processes
- **Path validation:** All file paths validated before subprocess execution
- **JSON parsing:** Input validation with error handling

### Dependencies

- **Runtime:** Node.js + TypeScript package (peer dependency)
- **Python:** jedi library (required for Python refs)
- **Detection:** Automatic via tsconfig.json presence

### Known Limitations

- Requires tsconfig.json in project root
- TypeScript project must be compilable
- No support for decorator metadata yet

### Review History

- **2026-01-03:** Adversarial review completed
  - Fixed 4 critical TypeScript bugs (JSON parsing, null checks, I/O error handling, TOCTOU)
  - Fixed 5 major Python bugs (column hardcoding, missing markers, weak tests, dynamic types)
  - 32 integration tests passing
  - Guard: 0 errors, 0 warnings

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
| 1.15.0 | 2026-01 | Multi-agent init support (DX-81), checkbox selection UI |
| 1.14.0 | 2026-01 | Invar usage feedback collection (DX-79), anonymization tools |
| 1.12.0 | 2026-01 | TypeScript Compiler API integration (DX-78), multi-language refs |
| 1.9.0 | 2026-01 | Extension Skills (LX-07), TypeScript support (LX-05/06) |
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
| .invar/examples/ | Sync | `invar dev sync` |

**Version Flow:** `templates/` → Invar project (via `invar dev sync`, syntax=mcp) AND → User projects (via `invar init/update`, syntax=cli)

---

<!-- ARCHIVE: Full session history in .invar/archive/ -->

*Update this file when: completing phases, making design decisions, releasing versions.*
