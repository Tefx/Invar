# The Invar Protocol v3.9

> **"Trade structure for safety."**

This is the operating manual for AI Coding Agents in Invar-enabled projects.

**What this is:** A structured methodology for writing reliable code through contracts, separation, and verification.

**What this is NOT:** Magic. You still need to think carefully.

---

## 0. Quick Start (Read This First)

**Core insight:** Separate what CAN fail (I/O) from what SHOULD NOT fail (logic).

### The One Rule That Matters Most

```
When you write a function, ask: "Can this fail for reasons outside my control?"
├── YES (file not found, network error, invalid input from outside)
│   └── Shell: returns Result[T, E]
└── NO (pure calculation, transformation, validation of known data)
    └── Core: has @pre/@post contracts
```

### Minimum Viable Knowledge

1. **Core** = pure functions, no I/O, must have `@pre`/`@post` decorators
2. **Shell** = I/O functions, must return `Result[T, E]`
3. **Run `invar guard` after every change** - it catches violations
4. **Keep functions under 50 lines** - including docstrings and comments!
5. **Core receives data, not paths** - Shell reads files, passes content to Core

### Quick Decision Guide

| Situation | Answer |
|-----------|--------|
| Function reads/writes files? | Shell |
| Function makes network requests? | Shell |
| Function gets current time? | Shell, or inject time as parameter |
| Function uses random values? | Shell, or inject seed as parameter |
| Function prints to console? | Shell |
| None of the above? | Probably Core |

### When Confused

- **Not sure Core vs Shell?** → If it touches files/network/time/random, it's Shell
- **Function too long?** → Extract helper function (see [Section 11.3](#113-troubleshooting))
- **Guard failing?** → See [Section 11.3: Troubleshooting](#113-troubleshooting)

### Session Start Protocol

**When starting work on ANY Invar project, ALWAYS:**

```
1. Read THIS project's INVAR.md (not from memory)
   └─ Each project may have different protocol version

2. Check CLAUDE.md for project-specific rules
   └─ Look for "Protocol Version: X.Y" in header

3. Read .invar/context.md if exists
   └─ Contains current state and lessons learned
```

**Why this matters:** If you work on multiple projects, each may use different protocol versions. The project's local INVAR.md is the **authoritative source** - not your training data or previous project's rules.

**Feature Discovery (preferred over version checking):**

Instead of checking version numbers, check document contents:

| To Know | Check For |
|---------|-----------|
| Uses ICIDV workflow? | "Intent → Contract → Inspect → Design" in Section 2 |
| Has governance? | Section 12 exists |
| Has versioning rules? | Section 12.6 exists |

This is more reliable because:
- Version numbers can be outdated
- INVAR.md content is definitive
- Works even if protocol was partially updated

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                       THE FOUR LAWS                             │
├─────────────────────────────────────────────────────────────────┤
│  1. SEPARATION    Core (pure) and Shell (I/O) are separate      │
│  2. CONTRACT      Define boundaries before implementation       │
│  3. CONTEXT       Read map → signatures → code (only if needed) │
│  4. VERIFY        Unit + integration + self-check (invar guard) │
├─────────────────────────────────────────────────────────────────┤
│  Core:   Pure logic, NO I/O, @pre/@post REQUIRED                │
│  Shell:  I/O handling, Result[T, E] REQUIRED, @pre/@post opt.   │
├─────────────────────────────────────────────────────────────────┤
│  Workflow: Intent → Contract → Inspect → Design → Impl → Verify │
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

Contract requirements differ by zone and visibility:

| Zone | Visibility | Contract Type | Required |
|------|------------|--------------|----------|
| **Core** | Public | @pre/@post + doctest | ✅ Required |
| **Core** | Private (`_`) | @pre/@post | Optional |
| **Shell** | Any | Result[T, E] + types | ✅ Required |
| **Shell** | Any | @pre/@post | Optional |

**Why private Core functions don't require contracts:**
- They are implementation details, not API boundaries
- The public function's contract covers the externally-visible behavior
- Simple delegation functions (`_impl`, `_helper`) add noise with redundant contracts
- You control all callers, so you can ensure correct usage

**When to add contracts to private functions anyway:**
- Complex algorithm with non-obvious invariants
- Performance-critical code where boundary conditions matter
- Functions likely to become public in the future

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

> **Key Insight: Result[T, E] IS the Contract**
>
> For Shell functions, you might wonder: "Where's my @pre/@post?"
>
> The `Result` type IS your contract:
> - `Result[Config, str]` says: "I might fail, and if I do, here's why"
> - This is more honest than @pre, because @pre would need I/O to validate
>
> Example: To check "file exists" in @pre, you'd need to read the filesystem.
> But reading the filesystem IS the I/O you're trying to handle.
> So just return `Failure("File not found")` instead.

### Law 3: Context Economy

**Read map → signatures → implementation (only if needed).**

| Level | What to Read | When |
|-------|--------------|------|
| 1 | Project structure (file tree) | First, to understand structure |
| 2 | Signatures + contracts | Understanding dependencies |
| 3 | Full implementation | Only when modifying |

> **Note:** `invar map` command is planned for Phase 4. Currently use IDE features or `tree` command for project overview.

### Law 4: Verify Immediately

**Run ALL verification after every change. No exceptions.**

```bash
# Unit tests (doctest)
pytest --doctest-modules

# Architecture check
invar guard

# Integration (if config options changed)
# Test: config file enables feature
# Test: CLI flag overrides config
```

**Three levels of verification:**

| Level | What | Catches |
|-------|------|---------|
| Unit | pytest --doctest-modules | Logic errors, contract violations |
| Architecture | invar guard | File size, forbidden imports, missing contracts |
| Integration | Manual or scripted | Config/CLI interaction bugs |

**Common miss:** Feature works with `--flag` but not when set in config file.
Always test both scenarios when adding config options.

---

## 2. ICIDV Workflow

```
Intent → Contract → Inspect → Design → Implement → Verify
```

### Checkpoints by Zone

| Step | Core | Shell |
|------|------|-------|
| **Intent** | Classified as Core | Classified as Shell |
| **Contract** | @pre/@post + doctest | Result[T, E] + types |
| **Inspect** | Check file sizes, signature patterns | Check file sizes, signature patterns |
| **Design** | Plan extraction if needed | Plan extraction if needed |
| **Implement** | < 50 lines, no I/O | < 50 lines, returns Result |
| **Verify** | pytest + invar guard + integration | pytest + invar guard + integration |

**After Intent:** Classified as Core or Shell
**After Contract (Core):** @pre/@post defined, doctests written
**After Contract (Shell):** Result type defined, type annotations complete
**After Inspect:** Know if files will exceed limits, know existing patterns
**After Design:** Extraction planned (if needed), signatures consistent
**After Implement:** Code < 50 lines per function (refactor if exceeded)
**After Verify:** All tests pass, `invar guard` passes, config scenarios tested

### Why Inspect and Design?

Experience shows that skipping these steps causes:
- **File size surprises** - Adding code only to find files exceed 300 lines
- **Signature inconsistency** - Creating wrapper functions to adapt mismatched signatures
- **Integration bugs** - Features work with CLI but not config files

**Inspect checklist:**
```
□ Target file current size? (if >200 lines, be careful)
□ How do similar functions look? (signature patterns)
□ Edge cases? (class methods, async, nested functions)
```

**Design checklist:**
```
□ Will file exceed 280 lines? → Plan extraction BEFORE coding
□ Does signature match existing? → Adapt to existing pattern
□ Config option added? → Plan integration test
```

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

**Invar CAN detect:**
- Static `import` statements (top-level and function-internal)
- Decorator presence (@pre, @post)
- File and function size violations
- Path-based and pattern-based Core/Shell classification
- Function-internal imports (`--strict-pure` mode)
- Common impure function calls: `datetime.now`, `random.*`, `open`, `print` (`--strict-pure` mode)

**Invar CANNOT detect:**
- Dynamic imports (`__import__`, `importlib`)
- I/O through dependency injection (e.g., passing file handle to Core)
- Contract semantic quality (`@pre(lambda x: True)` passes)
- Missing `Result[T, E]` return type in Shell functions (not yet implemented)
- Class method contracts (only checks top-level functions)
- Async function purity issues

**Planned improvements:**
- Shell contract validation (check for Result return type)
- Class method checking
- Configurable impure function list

**Always remember:** Guard assists but doesn't replace engineering judgment.

---

## 8. Commit Practices

> One ICIDV cycle = one commit

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
| **Implementer** | Constructive | Default. Follow ICIDV, build features |
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

## 11. Deep Dive

This section provides additional context for agents who want to understand the "why" behind the rules, or who need help with specific situations.

### 11.1 Design Rationale

#### Why physical separation (not just logical)?

**Short answer:** Makes testing trivial and bugs locatable.

**Long answer:**
- Core functions are deterministic → same input = same output
- This means: no mocks needed, no test fixtures, just call and assert
- When a Core function has a bug, the bug is IN that function (not in some external dependency)
- When a Shell function fails, you know it's I/O-related (network, filesystem, etc.)
- Physical separation (different directories) makes the boundary visible and enforceable

#### Why contracts BEFORE implementation?

**Short answer:** Prevents "I'll add tests later" syndrome.

**Long answer:**
- `@pre` documents what the function expects from callers
- `@post` documents what the function guarantees to callers
- Doctest provides executable examples that serve as documentation
- Writing these FIRST forces you to think about edge cases before coding
- Implementation becomes "fill in the blank" - much easier than "figure it all out"

#### Why 50-line limit?

**Short answer:** If you can't fit it in 50 lines, you don't understand it well enough.

**Long answer:**
- Forces decomposition into understandable units
- Each function fits in one screen → easier to review
- Smaller functions are easier to test in isolation
- **Important:** The 50 lines include EVERYTHING: code + docstrings + comments
- This is intentional: if your docstring is huge, your function is doing too much

#### Why Core receives data, not paths?

**Short answer:** Keeps Core pure and testable.

**Example:**
```python
# ❌ WRONG: Core receives path (requires I/O to use)
def parse_config(path: Path) -> Config:
    content = path.read_text()  # I/O in Core!
    return Config.parse(content)

# ✅ CORRECT: Core receives content (pure)
def parse_config(content: str) -> Config:
    return Config.parse(content)

# Shell handles the I/O
content = Path("config.toml").read_text()  # I/O in Shell
config = parse_config(content)  # Pure call
```

### 11.2 Decision Trees

#### Core vs Shell Classification

```
Does this function...
│
├─ Read or write files?
│  └─ YES → Shell
│
├─ Make network requests?
│  └─ YES → Shell
│
├─ Access current time (datetime.now)?
│  └─ YES → Shell, OR inject time as parameter to keep in Core
│
├─ Generate random values?
│  └─ YES → Shell, OR inject seed as parameter to keep in Core
│
├─ Print to console or log?
│  └─ YES → Shell (return data instead, let Shell log)
│
├─ Access environment variables?
│  └─ YES → Shell
│
└─ None of the above?
   └─ Core
```

#### Contract Type Selection

```
Is it in Core?
│
├─ YES
│  ├─ Add @pre for each input constraint
│  ├─ Add @post for each output guarantee
│  ├─ Add doctest with examples
│  └─ All three are REQUIRED
│
└─ NO (Shell)
   ├─ Return type MUST be Result[T, E]
   ├─ @pre/@post are OPTIONAL (usually skip them)
   └─ Why skip? Because @pre would need I/O to validate
      Example: @pre checking "file exists" requires reading filesystem
```

#### Function Too Long - What to Do?

```
Why is the function long?
│
├─ Long docstring with many examples?
│  └─ Extract implementation to _helper(), keep docstring in main function
│     def _calculate_impl(x, y): ...  # No docstring needed
│     def calculate(x, y):
│         """Long docstring here."""
│         return _calculate_impl(x, y)
│
├─ Many conditional branches?
│  └─ Extract each branch to a separate function
│     def handle_case_a(x): ...
│     def handle_case_b(x): ...
│     def main(x):
│         if condition_a: return handle_case_a(x)
│         if condition_b: return handle_case_b(x)
│
├─ Sequential steps?
│  └─ Extract each step to a separate function
│     def step1(x): ...
│     def step2(y): ...
│     def main(x):
│         y = step1(x)
│         return step2(y)
│
└─ Complex algorithm?
   └─ Break into phases, each phase = one function
```

### 11.3 Troubleshooting

#### "Function 'X' exceeds 50 lines (N)"

**Cause:** Function is too long (including docstring and comments).

**Solutions (in order of preference):**

1. **Extract helper function:**
   ```python
   # Before
   def process(data):
       # 60 lines of code...

   # After
   def _process_impl(data):
       # Implementation here (no docstring)

   def process(data):
       """Docstring with examples."""
       return _process_impl(data)
   ```

2. **Split into multiple functions** if doing multiple things

3. **Simplify** - maybe the function is doing too much

#### "Core file 'X' imports forbidden module 'Y'"

**Cause:** I/O module imported in Core file.

**Solutions:**

1. **Move the function to Shell** if it genuinely needs I/O

2. **Inject the dependency** if the function can be kept pure:
   ```python
   # ❌ Core importing datetime
   from datetime import datetime
   def is_expired(expiry):
       return datetime.now() > expiry  # IMPURE!

   # ✅ Inject current time
   def is_expired(expiry, now):  # 'now' passed by Shell
       return now > expiry  # PURE!
   ```

3. **Pass data instead of path:**
   ```python
   # ❌ Core importing pathlib
   from pathlib import Path
   def load_data(path):
       return parse(Path(path).read_text())

   # ✅ Shell passes content
   def load_data(content):  # Shell reads file first
       return parse(content)
   ```

#### "Function 'X' missing @pre or @post"

**Cause:** Core function lacks contract decorators.

**Quick fix template:**
```python
from deal import pre, post

@pre(lambda param1, param2: <precondition>)  # What caller must provide
@post(lambda result: <postcondition>)         # What function guarantees
def function_name(param1, param2):
    """
    Brief description.

    Examples:
        >>> function_name(valid_input1, valid_input2)
        expected_output
    """
    ...
```

**Common contract patterns:**
```python
# Non-null
@pre(lambda x, y: x is not None)

# Non-empty collection
@pre(lambda items, n: len(items) > 0)

# Non-negative number
@pre(lambda x, y: x >= 0)

# Returns non-null
@post(lambda result: result is not None)

# Returns non-empty
@post(lambda result: len(result) > 0)

# Returns within range
@post(lambda result: 0 <= result <= 100)
```

#### "Shell function should return Result"

**Cause:** Shell function doesn't return `Result[T, E]`.

**Fix:**
```python
from returns.result import Result, Success, Failure

# ❌ Before
def load_config(path: str) -> Config:
    return Config.parse(Path(path).read_text())

# ✅ After
def load_config(path: str) -> Result[Config, str]:
    try:
        return Success(Config.parse(Path(path).read_text()))
    except FileNotFoundError:
        return Failure(f"Config not found: {path}")
    except Exception as e:
        return Failure(f"Failed to load config: {e}")
```

---

## 12. Protocol Governance

> The protocol evolves through practice, but with discipline.

### 12.1 The Three Layers

The Invar methodology has three layers with different change rules:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 0: Immutable Core                                        │
│  ─────────────────────────────────────────────────────────────  │
│  • Core/Shell separation principle                              │
│  • Design-by-contract philosophy                                │
│  • "Can fail → Shell, Cannot fail → Core"                       │
│                                                                 │
│  Status: IMMUTABLE. Changing this = no longer Invar.            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Protocol Standard (this document)                     │
│  ─────────────────────────────────────────────────────────────  │
│  • INVAR.md implementation details                              │
│  • Workflow definitions (ICIDV)                                 │
│  • Verification requirements (Law 4)                            │
│                                                                 │
│  Status: HUMAN-APPROVED changes only.                           │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Project Adaptation                                    │
│  ─────────────────────────────────────────────────────────────  │
│  • CLAUDE.md project-specific rules                             │
│  • context.md lessons learned                                   │
│  • Project-specific patterns and pitfalls                       │
│                                                                 │
│  Status: Agent may evolve freely, but should document.          │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Change Rules

| Layer | Who Can Propose | Who Approves | Documentation |
|-------|-----------------|--------------|---------------|
| Layer 0 | Nobody | N/A | N/A |
| Layer 1 | Agent or Human | **Human only** | Proposal required |
| Layer 2 | Agent or Human | Self-approved | Should document |

### 12.3 Protocol Evolution Mode

Projects can configure how strictly they follow the protocol:

```toml
[tool.invar]
protocol_version = "3.9"           # Lock to specific version
protocol_evolution = "human-approved"  # Default mode
```

| Mode | Layer 1 Changes | Layer 2 Changes |
|------|-----------------|-----------------|
| `locked` | ❌ Forbidden | ✅ Allowed |
| `human-approved` | 🔒 Requires approval | ✅ Allowed |
| `open` | ✅ Allowed (not recommended) | ✅ Allowed |

**Default: `human-approved`** - Agent can propose Layer 1 changes, but human must explicitly approve.

### 12.4 Proposal Process

When Agent identifies a potential protocol improvement:

**Step 1: Document the Proposal**

Create `.invar/proposals/YYYY-MM-DD-title.md`:

```markdown
# Protocol Change Proposal

## Trigger
What problem or friction caused this proposal?

## Change
What specific change is proposed?

## Evidence
What experience supports this change?

## Layer
Is this Layer 1 (protocol) or Layer 2 (project)?

## Impact
What else needs to change if this is approved?
```

**Step 2: Wait for Approval (Layer 1 only)**

- Agent MUST NOT implement Layer 1 changes without human approval
- Agent SHOULD explicitly ask: "This is a Layer 1 change. Do you approve?"
- Human can: Approve / Reject / Modify

**Step 3: Implement and Document**

- Update relevant files
- Update version number (Layer 1 changes)
- Record in changelog

### 12.5 Review Cycle

After major milestones, consider a review:

```
Implement (ICIDV) → Review → Propose → (Approval) → Improve
```

**Trigger conditions:**
- Phase/milestone completion
- Significant friction encountered
- Major bug discovered

**Review questions:**
1. What worked well? Why?
2. What caused friction? Root cause?
3. What unexpected rework happened? How to prevent?
4. What's missing from current process?

**Outputs:**
- Updated Lessons Learned (Layer 2)
- Protocol change proposals (Layer 1, if needed)

### 12.6 Versioning Rules

The protocol uses semantic versioning aligned with the governance layers:

```
MAJOR.MINOR
  │     │
  │     └─ Layer 1 changes (protocol revisions)
  │
  └─ Protocol generation (Layer 0 defines this)
```

**Version Bump Rules:**

| Change Type | Version Impact | Example |
|-------------|----------------|---------|
| Layer 0 change | N/A (impossible) | Would create new protocol, not Invar |
| Layer 1 change | MINOR bump (+0.1) | v3.7 → v3.8 |
| Layer 2 change | No bump | Project-specific, not versioned |
| Typo/clarification | No bump | Editorial only |

**Backwards Compatibility:**

Within the same MAJOR version, all changes are **additive and compatible**:

| Scenario | Behavior |
|----------|----------|
| v3.6 project reads v3.7 docs | ✅ All v3.6 rules still apply |
| v3.8 project uses v3.6 tooling | ✅ Tools may lack new features, but work |
| v3.x project meets v2.x project | ⚠️ Different MAJOR = potentially incompatible |

**MAJOR Version Change Criteria:**

A new MAJOR version (e.g., v3.x → v4.x) would require:
1. Fundamental philosophy change (not just implementation details)
2. Breaking changes to Layer 1 that cannot be backwards-compatible
3. Community consensus (if protocol is widely adopted)

**Note:** Layer 0 is immutable, so a true MAJOR version change would effectively be a fork or successor protocol, not "Invar v4".

**Version in Config:**

```toml
[tool.invar]
protocol_version = "3.9"  # Documents which version this project implements
```

This is **declarative, not enforced** - it documents the project's target version for:
- Agent awareness (which features/rules apply)
- Tooling compatibility checks (future)
- Audit trail (which protocol version was followed)

### 12.7 Version History

| Version | Date | Layer | Key Changes |
|---------|------|-------|-------------|
| v3.9 | 2024-12-19 | L1 | Session Start Protocol, feature discovery |
| v3.8 | 2024-12-19 | L1 | Versioning rules, compatibility guarantees |
| v3.7 | 2024-12-19 | L1 | Protocol Governance, evolution controls |
| v3.6 | 2024-12-19 | L1 | ICIDV workflow, enhanced Law 4 |
| v3.5 | 2024-12-18 | L1 | Quick Start, Deep Dive sections |

---

*Version 3.9 | Designed for AI Coding Agents*
