# Invar Quick Guide

> Essential "why" and "how" for AI agents. Read after [INVAR.md](../INVAR.md).

---

## Why Core/Shell Separation?

**Short answer:** Makes testing trivial and bugs locatable.

| Property | Core | Shell |
|----------|------|-------|
| Deterministic | Yes (same input = same output) | No (depends on external state) |
| Testable | No mocks needed | Requires mocks/fixtures |
| Bug location | Bug is IN that function | Bug might be external |

**Core receives data, not paths:**
```python
# Wrong: Core receives path (requires I/O to use)
def parse_config(path: Path) -> Config:
    content = path.read_text()  # I/O in Core!
    return Config.parse(content)

# Correct: Core receives content (pure)
def parse_config(content: str) -> Config:
    return Config.parse(content)

# Shell handles the I/O
content = Path("config.toml").read_text()  # I/O in Shell
config = parse_config(content)  # Pure call
```

---

## Why Contracts Before Implementation?

1. **@pre** documents what the function expects from callers
2. **@post** documents what the function guarantees to callers
3. Writing these FIRST forces thinking about edge cases
4. Implementation becomes "fill in the blank"

---

## Decision Tree: Core vs Shell

```
Does this function...
│
├─ Read or write files? ──────────────────→ Shell
├─ Make network requests? ─────────────────→ Shell
├─ Access current time (datetime.now)? ────→ Shell OR inject as parameter
├─ Generate random values? ────────────────→ Shell OR inject as parameter
├─ Print to console? ──────────────────────→ Shell (return data, Shell logs)
├─ Access environment variables? ──────────→ Shell
│
└─ None of the above? ─────────────────────→ Core
```

---

## Handling Impure Operations in Core

**Pattern:** Inject impure values as parameters.

```python
# Time - inject as parameter
def is_expired(expiry: datetime, now: datetime) -> bool:  # 'now' passed by Shell
    return now > expiry

# Shell call:
expired = is_expired(token.expiry, datetime.now())

# Random - inject as parameter
def select_winner(participants: list[str], index: int) -> str:
    return participants[index % len(participants)]

# Shell call:
winner = select_winner(participants, secrets.randbelow(len(participants)))

# Config - inject as parameter
def calculate_tax(amount: Decimal, config: TaxConfig) -> Decimal:
    return amount * config.rate

# Shell call:
config = load_config("tax.toml")  # I/O here
tax = calculate_tax(amount, config)  # Pure call
```

---

## Function Too Long - What to Do

```
Why is it long?
│
├─ Long docstring with examples?
│  └─ Extract implementation to _helper(), keep docstring in main
│
├─ Many conditional branches?
│  └─ Extract each branch to separate function
│
├─ Sequential steps?
│  └─ Extract each step to separate function
│
└─ Complex algorithm?
   └─ Break into phases, each phase = one function
```

**Example:**
```python
# Before: 60 lines
def process(data):
    # 60 lines of code...

# After: split into helper + main
def _process_impl(data):
    # Implementation (no docstring needed)

def process(data):
    """Docstring with examples."""
    return _process_impl(data)
```

---

## Shell Result Warning - What to Do

```
Does this function do I/O?
│
├─ YES → Add Result[T, E]
│        return Success(value) or Failure("error message")
│
├─ NO, it's pure logic → Move to Core
│        (gains @pre/@post contracts)
│
└─ NO, it's a generator → Acceptable exception
         (yields items, doesn't fit Result pattern)
```

---

## Lambda Signature Pitfall

```python
# WRONG: Lambda only takes first parameter
@pre(lambda x: x >= 0)
def calculate(x: int, y: int = 0): ...

# CORRECT: Lambda must include ALL parameters (even defaults)
@pre(lambda x, y=0: x >= 0)
def calculate(x: int, y: int = 0): ...
```

Guard's `param_mismatch` rule catches this as ERROR.

---

## Meaningful Contracts

```python
# Redundant - type hints already check this
@pre(lambda x: isinstance(x, int))
def calc(x: int): ...

# Meaningful - checks business logic
@pre(lambda x: x > 0)
def calc(x: int): ...

# Meaningful - checks relationship between params
@pre(lambda start, end: start < end)
def process_range(start: int, end: int): ...
```

Guard's `empty_contract` and `redundant_type_contract` rules help catch these.

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Lambda wrong params | Runtime error | Match ALL function params |
| Result check | `is_failure()` not found | Use `isinstance(result, Failure)` |
| Missing exclusions | Scans .venv (thousands of files) | Add .venv to exclude_paths |
| File size surprise | Guard fails after "done" | Check size BEFORE adding code |

---

*This guide complements INVAR.md. For full philosophy, see [vision.md](./vision.md). For technical details, see [design.md](./design.md).*
