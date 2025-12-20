# Invar

[![PyPI version](https://badge.fury.io/py/python-invar.svg)](https://badge.fury.io/py/python-invar)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Don't hope AI code is correct. Know it.**

You use AI to write code. How do you know it's correct?

- Read every line? Slower than writing it yourself
- Hope for the best? See you in production

Invar makes AI prove its code is correct.

---

## What It Looks Like

```python
@pre(lambda items: len(items) > 0)      # Empty list? Rejected at runtime
@post(lambda result: result >= 0)       # Result is always non-negative
def average(items: list[float]) -> float:
    """
    >>> average([1, 2, 3])              # Behavior is proven
    2.0
    """
    return sum(items) / len(items)
```

Contracts (`@pre`/`@post`) are checked at runtime. Violations fail immediately—no silent bugs.

---

## Quick Start

```bash
pip install python-invar
cd your-project
invar init
```

This creates `INVAR.md` (protocol), `CLAUDE.md` (project rules), and pre-commit hooks.

| AI Tool | Configuration |
|---------|---------------|
| Claude Code | Works automatically (reads CLAUDE.md) |
| Cursor | Settings → Rules → "Follow the INVAR.md protocol" |
| Others | Add "Follow the INVAR.md protocol" to system prompt |

---

## The Four Laws

| Law | Principle |
|-----|-----------|
| **1. Separation** | Pure logic (Core) and I/O (Shell) must be physically separate |
| **2. Contract First** | Define boundaries (`@pre`/`@post`) before implementation |
| **3. Context Economy** | Read map → signatures → implementation (only if needed) |
| **4. Verify Immediately** | Run `invar guard && pytest` after every change |

---

## The Workflow: ICIDIV

```
I ─── C ─── I ─── D ─── I ─── V
│     │     │     │     │     │
▼     ▼     ▼     ▼     ▼     ▼
Intent  Contract  Inspect  Design  Implement  Verify
```

**Example — You:** "Add a function to calculate discounted price"

**AI follows ICIDIV:**

| Step | AI does |
|------|---------|
| **Intent** | Core function (pure logic, no I/O) |
| **Contract** | `@pre`: price > 0, discount ∈ [0,1]. `@post`: result ≥ 0 |
| **Inspect** | `invar sig` — check existing patterns |
| **Design** | File size OK, no extraction needed |
| **Implement** | Write code with contracts and doctest |
| **Verify** | `invar guard && pytest` — all pass |

```python
@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)
```

```
git commit → pre-commit hook runs invar guard → ✓ Commit succeeds
```

Verification fails? AI sees the report, fixes it, verifies again.

---

## Why This Works

Contracts are written by AI, not by you. You don't review every one.

**Constraints produce quality:**

Without constraints, AI writes code that "looks right."
With constraints, AI must think through boundaries before writing—this thinking process itself reduces bugs.

**Verification creates a feedback loop:**

```
AI writes code → invar guard reports violations → AI fixes → verify again
```

AI can't ignore edge cases because Guard catches them.

---

## What It Guarantees

| Invar verifies | You judge |
|----------------|-----------|
| Contracts exist (boundaries were considered) | Whether contracts match business requirements |
| Contracts non-empty (not `@pre(lambda: True)`) | Whether edge cases are covered |
| Doctests pass | Whether critical scenarios are tested |
| Pure logic has no I/O (Law 1) | Whether business logic is correct |
| Files < 500 lines, functions < 50 lines | Whether code is well-structured |

Invar guarantees mechanical correctness. Business semantics still need your judgment—but that's far more efficient than reviewing every line.

---

## Runtime Overhead

Contracts are checked at runtime. Yes, there's overhead.

**In development:** Keep enabled. Overhead is negligible vs. catching bugs early.

**In production:**

```bash
DEAL_DISABLE=1 python your_app.py  # Disable all contract checking
```

Or keep enabled—contracts catch invalid inputs at system boundaries.

---

## For Experienced Programmers

You might ask: Isn't this just Design-by-Contract?

Yes. These aren't new ideas:

- Design-by-Contract (Meyer, 1986)
- Doctests (Python standard library)
- Pure/Impure separation (functional programming)

Invar applies them to AI output with automatic verification.

**The key shift**: Human code—you trust the author. AI code—you need mechanical verification.

---

## Command Reference

```bash
invar guard              # Check architecture rules
invar guard --changed    # Only git-modified files
invar guard --explain    # Detailed explanations
invar guard --agent      # JSON output for automation
invar rules              # List all rules
invar sig <file>         # Function signatures + contracts
invar map --top 10       # Most-referenced symbols
```

---

## Existing Projects

No restructuring needed. Configure which directories are pure logic vs I/O:

```toml
# pyproject.toml
[tool.invar.guard]
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**", "**/db/**"]
```

---

## Learn More

| Document | Content |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol for AI |
| [docs/VISION.md](./docs/VISION.md) | Design philosophy |
| [docs/INVAR-GUIDE.md](./docs/INVAR-GUIDE.md) | Detailed guide |

---

## License

MIT
