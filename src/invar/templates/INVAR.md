# The Invar Protocol v3.4

> **"Trade structure for safety."**

This is the operating manual for AI Coding Agents in Invar-enabled projects.

**What this is:** A structured methodology for writing reliable code through contracts, separation, and verification.

**What this is NOT:** Magic. You still need to think carefully.

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                       THE FOUR LAWS                             │
├─────────────────────────────────────────────────────────────────┤
│  1. SEPARATION    Core (pure) and Shell (I/O) are separate      │
│  2. CONTRACT      Define boundaries before implementation       │
│  3. CONTEXT       Read map → signatures → code (only if needed) │
│  4. VERIFY        Run tests after every change                  │
├─────────────────────────────────────────────────────────────────┤
│  Core:   Pure logic, NO I/O, @pre/@post REQUIRED                │
│  Shell:  I/O handling, Result[T, E] REQUIRED, @pre/@post opt.   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. The Four Laws

### Law 1: Separation

**Core and Shell must be physically separate.**

| Zone | Path | Contains | Rules |
|------|------|----------|-------|
| **Core** | `src/core/` | Pure business logic | No I/O, deterministic |
| **Shell** | `src/shell/` | I/O adapters | Returns Result, handles chaos |

```
     ┌─────────────┐
     │    Shell    │  ← Entry points, I/O
     └──────┬──────┘
            │ imports
            ▼
     ┌─────────────┐
     │    Core     │  ← Pure logic, contracts
     └─────────────┘

RULE: Core NEVER imports from Shell.
```

**Forbidden in Core:** `os`, `sys`, `socket`, `requests`, `subprocess`, `shutil`, `io`, `pathlib`

### Law 2: Contract First

**Define boundaries before implementation.**

Contract requirements differ by zone:

| Zone | Contract Type | Required |
|------|--------------|----------|
| **Core** | @pre/@post + doctest | ✅ Required |
| **Shell** | Result[T, E] + types | ✅ Required |
| **Shell** | @pre/@post | Optional |

**Core Example:**
```python
from deal import pre, post

@pre(lambda items, tax_rate: len(items) > 0)
@pre(lambda items, tax_rate: 0 <= tax_rate <= 1)
@post(lambda result: result >= 0)
def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
    """
    Examples:
        >>> calculate_total([Item(price=Decimal("100"))], Decimal("0.1"))
        Decimal('110.00')
    """
    ...
```

**Shell Example:**
```python
from returns.result import Result, Success, Failure

def load_config(project_root: Path) -> Result[Config, str]:
    """Load config from file. Result type IS the contract."""
    if not project_root.exists():
        return Failure(f"Path not found: {project_root}")
    return Success(Config(...))
```

**Why the difference?**
- Core is deterministic: @pre/@post can validate invariants
- Shell handles chaos: Result type expresses "might fail" contract
- Shell's @pre would check path validity, but that requires I/O

**Critical:** Lambda must accept ALL function parameters. See [Pitfall #1](#pitfall-1-deal-pre-signature).

### Law 3: Context Economy

**Read map → signatures → implementation (only if needed).**

| Level | What to Read | When |
|-------|--------------|------|
| 1 | `invar map` output | First, to understand structure |
| 2 | Signatures + contracts | Understanding dependencies |
| 3 | Full implementation | Only when modifying |

### Law 4: Verify Immediately

**Run tests after every change. No exceptions.**

```bash
pytest --doctest-modules
```

---

## 2. ICIV Workflow

```
Intent → Contract → Implementation → Verify
```

### Checkpoints by Zone

| Step | Core | Shell |
|------|------|-------|
| **Intent** | Classified as Core | Classified as Shell |
| **Contract** | @pre/@post + doctest | Result[T, E] + types |
| **Implementation** | < 50 lines, no I/O | < 50 lines, returns Result |
| **Verify** | pytest + invar guard | pytest + invar guard |

**After Intent:** Classified as Core or Shell
**After Contract (Core):** @pre/@post defined, doctests written
**After Contract (Shell):** Result type defined, type annotations complete
**After Implementation:** Code < 50 lines per function (refactor if exceeded)
**After Verify:** All tests pass, `invar guard` passes

---

## 3. Libraries

### 3.1 Contracts (deal)

```python
from deal import pre, post

@pre(lambda amount, rate: amount >= 0)
@pre(lambda amount, rate: 0 <= rate <= 1)
@post(lambda result: result >= 0)
def apply_discount(amount: float, rate: float) -> float:
    return amount * (1 - rate)
```

<a id="pitfall-1-deal-pre-signature"></a>
**Pitfall #1: @pre lambda signature**
```python
# ❌ WRONG: lambda only takes first parameter
@pre(lambda x: x >= 0)
def divide(x: int, y: int) -> float: ...

# ✅ CORRECT: lambda must match ALL parameters
@pre(lambda x, y: x >= 0)
def divide(x: int, y: int) -> float: ...
```

### 3.2 Result Types (returns)

```python
from returns.result import Result, Success, Failure

def load_config(path: str) -> Result[Config, str]:
    try:
        return Success(Config.parse(Path(path).read_text()))
    except FileNotFoundError:
        return Failure(f"Config not found: {path}")
```

**Pitfall #2: Checking Result type**
```python
result = load_config(path)

# ❌ WRONG: No is_failure() method
if result.is_failure(): ...

# ✅ CORRECT: Use isinstance
if isinstance(result, Failure):
    error = result.failure()

# ✅ ALSO CORRECT: Pattern matching
match result:
    case Failure(error): ...
    case Success(value): ...
```

### 3.3 Data Models (pydantic)

```python
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    product_id: str = Field(..., pattern=r'^[A-Z]{2}\d{6}$')
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
```

**Pydantic + Contract synergy:**
- Pydantic validates data shape
- Contracts validate business logic

---

## 4. Testing

### Doctest (Always)

```python
def calculate_discount(amount: Decimal, rate: Decimal) -> Decimal:
    """
    Examples:
        >>> calculate_discount(Decimal("100"), Decimal("0.1"))
        Decimal('90.00')
        >>> calculate_discount(Decimal("0"), Decimal("0.5"))
        Decimal('0.00')
    """
```

### Property Tests (Optional)

```python
if __debug__:
    from hypothesis import given, strategies as st

    @given(amount=st.decimals(min_value=0, max_value=1e6, allow_nan=False))
    def test_discount_non_negative(amount):
        assert calculate_discount(amount, Decimal("0.1")) >= 0
```

---

## 5. Gray Areas

Some operations don't fit cleanly into Core vs Shell.

**Logging:** Return structured data, log in Shell
```python
# Core: Return errors
def validate(data) -> Result[Output, list[Error]]: ...

# Shell: Log at boundary
if isinstance(result, Failure):
    logger.warning(f"Validation failed: {result.failure()}")
```

**Time/Random/Config:** Inject as parameter
```python
# Core: Accept as parameter
def is_expired(expiry: datetime, now: datetime) -> bool: ...

# Shell: Inject
expired = is_expired(token.expiry, datetime.now())
```

**Decision Rule:** Is it deterministic? YES → Core, NO → Shell (or inject)

---

## 6. Configuration

### Configuration Sources

Invar looks for configuration in this order:
1. `pyproject.toml` `[tool.invar.guard]` (standard Python projects)
2. `invar.toml` `[guard]` (standalone, no pyproject.toml needed)
3. Built-in defaults

### pyproject.toml

```toml
[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", ".venv", "venv", "__pycache__", ".git"]

# Pattern-based classification (optional, takes priority over paths)
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**"]
```

### invar.toml (Alternative)

For projects without pyproject.toml:

```toml
[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
# ... same options as above
```

**Pitfall #3: Missing exclusions**
```toml
# ❌ WRONG: Will scan thousands of third-party files
exclude_paths = ["tests"]

# ✅ CORRECT: Exclude all non-project code
exclude_paths = ["tests", ".venv", "venv", "__pycache__", ".git"]
```

**Pitfall #4: Function size includes docstrings**
```python
# ⚠️ The 50-line limit counts EVERYTHING: code + docstring + comments
# Good doctests can push functions over the limit

# ✅ SOLUTION: Extract helper functions when exceeded
def _helper(x):  # Move logic to helper
    ...

def main_function(x):
    """Extensive doctest examples here."""
    return _helper(x)
```

### CLI Commands

```bash
invar guard [path]       # Check architecture rules
invar guard --strict     # Warnings as errors
invar guard --json       # JSON output
invar init               # Initialize project (auto-detect config location)
invar init --dirs        # Always create src/core, src/shell
invar init --no-dirs     # Skip directory creation (for existing projects)
```

---

## 7. Honest Limitations

**Invar CAN:**
- Catch static import violations
- Check decorator presence
- Enforce file/function size limits

**Invar CANNOT:**
- Detect dynamic imports or `eval`
- Verify contract semantics (`@pre(lambda x: True)` passes)
- Force agents to follow protocol
- Replace engineering judgment

---

## 8. Commit Practices

> One ICIV cycle = one commit

- Commit when tests pass (enforces Law 4)
- Commit before trying something risky
- Each commit does ONE thing
- Delete code, don't comment it out

**Message format:** Start with verb (Add, Fix, Update, Remove)

---

## 9. Optional: Role-Based Review

For security-critical projects, explicit role-switching can improve code quality.

| Role | Mindset | When to Use |
|------|---------|-------------|
| **Implementer** | Constructive | Default. Follow ICIV, build features |
| **Reviewer** | Critical | Architecture changes, public API changes |
| **Adversary** | Destructive | User input handling, auth, financial code |

**Decision flow:**
```
Security-critical or untrusted input?
├── Yes → Adversary review
└── No → Architecture or API change?
    ├── Yes → Reviewer review
    └── No → Implementer + automated checks
```

For full role definitions and prompts, see `docs/AGENTS.md`.

---

## 10. Optional: Context Management

For long sessions or complex projects, maintain `.invar/context.md` to preserve information across context summarization.

### When to Update

| Event | Action |
|-------|--------|
| Major task completed | Update current state |
| Design decision made | Log decision + rationale |
| Pitfall discovered | Add to lessons learned |
| Session ending | Summarize key context |

### File Structure

```
.invar/
├── context.md      # Current state, lessons, key context
└── decisions.md    # Design decisions with rationale (optional)
```

### context.md Template

```markdown
# Project Context
*Last updated: YYYY-MM-DD*

## Current State
- Phase: [current phase]
- Working on: [current task]
- Blockers: [any blockers]

## Lessons Learned
1. [pitfall] → [solution]

## Key Files
- [file]: [purpose]
```

**Recovery:** At session start, read `.invar/context.md` to restore project context.

---

## Appendix: Complete Example

### Core Module

```python
"""src/core/pricing.py"""
from decimal import Decimal
from pydantic import BaseModel, Field
from deal import pre, post


class PriceBreakdown(BaseModel):
    subtotal: Decimal = Field(..., ge=0)
    tax: Decimal = Field(..., ge=0)
    total: Decimal = Field(..., ge=0)


@pre(lambda amount, tax_rate: amount >= 0)
@pre(lambda amount, tax_rate: 0 <= tax_rate <= 1)
@post(lambda result: result.total >= 0)
def calculate_price(amount: Decimal, tax_rate: Decimal) -> PriceBreakdown:
    """
    Calculate price with tax.

    Examples:
        >>> calculate_price(Decimal("100"), Decimal("0.1"))
        PriceBreakdown(subtotal=Decimal('100'), tax=Decimal('10.00'), total=Decimal('110.00'))
    """
    tax = (amount * tax_rate).quantize(Decimal("0.01"))
    return PriceBreakdown(subtotal=amount, tax=tax, total=amount + tax)
```

### Shell Module

```python
"""src/shell/invoice_service.py"""
from pathlib import Path
from decimal import Decimal
from returns.result import Result, Success, Failure
from src.core.pricing import calculate_price, PriceBreakdown


def process_invoice(path: str) -> Result[PriceBreakdown, str]:
    """Load and process an invoice file."""
    file_path = Path(path)
    if not file_path.exists():
        return Failure(f"Invoice not found: {path}")

    try:
        data = json.loads(file_path.read_text())
        result = calculate_price(
            Decimal(str(data['amount'])),
            Decimal(str(data['tax_rate']))
        )
        return Success(result)
    except (KeyError, ValueError) as e:
        return Failure(f"Invalid invoice: {e}")
```

---

*Version 3.3 | Designed for AI Coding Agents*
