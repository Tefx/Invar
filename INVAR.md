# The Invar Protocol v3.17

> **"Trade structure for safety."** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

## Core/Shell Architecture

| Zone | Location | Must Have | Example |
|------|----------|-----------|---------|
| **Core** | `src/*/core/` | `@pre`/`@post` contracts, doctests | Pure calculations, transformations |
| **Shell** | `src/*/shell/` | `Result[T, E]` return type | File I/O, network, CLI |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`, `datetime.now`, `random.*`

**Core receives data, not paths** — Shell reads files, passes content to Core.

## Contracts

Every Core function must have `@pre` or `@post`:

```python
from deal import pre, post

@pre(lambda x, y: x > 0 and y > 0)  # Lambda must match ALL parameters
def calculate(x: int, y: int) -> int:
    """
    Calculate something.

    >>> calculate(2, 3)
    5
    """
    return x + y
```

Guard provides hints and suggestions for violations. Use `invar guard --explain` for details.

## Size Limits

| Limit | Value | Warning |
|-------|-------|---------|
| File | 500 lines | 80% (400) |
| Function | 50 lines | — |

## Guard Commands

```bash
invar guard              # Check rules (shows hints for violations)
invar guard --changed    # Modified files only (shows file context)
invar guard --explain    # Detailed explanations and limitations
invar guard --agent      # JSON output with full context
invar guard --pedantic   # Show all violations including off-by-default
invar rules              # List all rules with severity and hints
```

## Workflow: ICIDV

Before implementing, follow **I**ntent → **C**ontract → **I**nspect → **D**esign → **V**erify:

```
□ Intent    — What are we trying to achieve?
□ Contract  — What inputs are invalid? What does output guarantee?
□ Inspect   — Check existing patterns (use: invar guard --changed)
□ Design    — If file > 400 lines, plan extraction first
□ Verify    — Run: invar guard && pytest --doctest-modules
```

## Configuration

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
max_file_lines = 500
max_function_lines = 50
```

## More Information

| Topic | Location |
|-------|----------|
| Full protocol details | [docs/INVAR-DETAILED.md](docs/INVAR-DETAILED.md) |
| Technical design | [docs/DESIGN.md](docs/DESIGN.md) |
| Project context | [.invar/context.md](.invar/context.md) |
| Rule metadata | `invar rules --json` |

---

*Protocol v3.17 — Phase 9.3 compression. Essential information preserved; details available via Guard hints and commands.*
