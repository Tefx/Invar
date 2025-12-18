# Invar

> **Trade structure for safety.**

Invar is an AI-native software engineering framework that combines design-by-contract with architectural enforcement. It provides both a methodology (the Invar Protocol) and tools to enforce it.

## The Four Laws

```
1. SEPARATION    Core (pure) and Shell (I/O) are separate
2. CONTRACT      Define boundaries before implementation
3. CONTEXT       Read map → signatures → code (only if needed)
4. VERIFY        Run tests after every change
```

## Installation

```bash
pip install invar
```

For development with contracts and result types:

```bash
pip install invar[dev]  # includes deal, returns, hypothesis
```

## Quick Start

### Initialize a new project

```bash
invar init
```

This creates:
- `INVAR.md` - Protocol document for AI agents
- `CLAUDE.md` - Project development guide
- `src/core/` - Directory for pure business logic
- `src/shell/` - Directory for I/O adapters
- `.invar/context.md` - Context management for long sessions
- `[tool.invar.guard]` section in `pyproject.toml`

### Check architecture rules

```bash
invar guard              # Check current directory
invar guard --strict     # Treat warnings as errors
invar guard --json       # Output as JSON
```

## Project Structure

Invar enforces a Core/Shell architecture:

```
src/
├── core/           # Pure logic, NO I/O
│   ├── models.py   # Pydantic models
│   ├── rules.py    # Business logic with @pre/@post
│   └── ...
│
└── shell/          # I/O adapters
    ├── cli.py      # Command line interface
    ├── api.py      # HTTP handlers
    └── ...
```

**Rule:** Core NEVER imports from Shell. Dependencies flow inward only.

## Example

### Core (pure logic with contracts)

```python
# src/core/pricing.py
from decimal import Decimal
from deal import pre, post

@pre(lambda amount, tax_rate: amount >= 0)
@pre(lambda amount, tax_rate: 0 <= tax_rate <= 1)
@post(lambda result: result >= 0)
def calculate_total(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """
    Calculate total with tax.

    Examples:
        >>> calculate_total(Decimal("100"), Decimal("0.1"))
        Decimal('110.00')
    """
    tax = (amount * tax_rate).quantize(Decimal("0.01"))
    return amount + tax
```

### Shell (I/O with Result types)

```python
# src/shell/invoice.py
from pathlib import Path
from returns.result import Result, Success, Failure
from src.core.pricing import calculate_total

def process_invoice(path: str) -> Result[Decimal, str]:
    """Load invoice and calculate total."""
    file_path = Path(path)
    if not file_path.exists():
        return Failure(f"File not found: {path}")

    data = json.loads(file_path.read_text())
    total = calculate_total(
        Decimal(data["amount"]),
        Decimal(data["tax_rate"])
    )
    return Success(total)
```

## Configuration

In `pyproject.toml`:

```toml
[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "subprocess"]
exclude_paths = ["tests", ".venv"]
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `invar guard` | Check architecture rules |
| `invar guard --strict` | Warnings as errors |
| `invar guard --json` | JSON output |
| `invar init` | Initialize project |
| `invar version` | Show version |

## Documentation

| Document | Purpose |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol for AI agents |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical design |
| [docs/VISION.md](./docs/VISION.md) | Philosophy |
| [docs/AGENTS.md](./docs/AGENTS.md) | Role definitions (optional) |

## Honest Limitations

**Invar CAN:**
- Catch static import violations
- Check decorator presence (@pre/@post)
- Enforce file/function size limits

**Invar CANNOT:**
- Detect dynamic imports (`__import__`, `eval`)
- Verify contract semantics (`@pre(lambda x: True)` passes)
- Replace engineering judgment

## License

MIT
