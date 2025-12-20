# Invar

[![PyPI version](https://badge.fury.io/py/python-invar.svg)](https://badge.fury.io/py/python-invar)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Don't hope AI code is correct. Know it.**

---

## The Problem

```
You: Write a function to calculate averages
AI: Here's the code...
You: Looks good... (reads 50 lines)... I think it's correct?
     ↑
     This is hoping, not knowing
```

AI coding assistants generate plausible code. But "plausible" isn't "correct". You end up:
- Reading every line AI writes (slower than writing yourself)
- Finding bugs in production (AI is confident, not accurate)
- Building technical debt faster than ever

## The Insight

You already believe in tests. You already believe in contracts. You already believe in clean architecture.

**Invar just applies these to AI output.**

```python
# AI writes this:
@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def calculate_average(items: list[float]) -> float:
    """
    >>> calculate_average([1.0, 2.0, 3.0])
    2.0
    >>> calculate_average([])  # Edge case
    Traceback (most recent call last):
        ...
    PreConditionError: ...
    """
    return sum(items) / len(items)
```

Now you **know**:
- Empty list? Contract catches it at runtime.
- Wrong result? Doctest fails immediately.
- AI forgot an edge case? You see it in the contract, not in production.

## Quick Start

### 1. Install

```bash
pip install python-invar
```

### 2. Initialize your project

```bash
cd your-project
invar init
```

This creates `INVAR.md` (protocol for AI) and `CLAUDE.md` (project rules).

### 3. Tell your AI to follow the protocol

**Claude Code:** Reads `CLAUDE.md` automatically.

**Other tools:** Add to system prompt:
> Follow the Invar protocol in INVAR.md. Write @pre/@post contracts and doctests for all functions.

### 4. Let AI write code with contracts

```python
# AI writes code in src/core/ (pure logic, no I/O)
@pre(lambda x, y: y != 0)
def divide(x: float, y: float) -> float:
    """
    >>> divide(10, 2)
    5.0
    """
    return x / y
```

### 5. Verify mechanically

```bash
# Run Guard - catches architectural violations
invar guard

# Output example:
# src/core/math.py
#   WARN :15 Function 'calculate' has no @pre or @post contract
#     → Add: @pre(lambda x, y: x >= 0 and y >= 0)
#     → Patterns: x >= 0 | x > 0 | x != 0, y >= 0 | y > 0 | y != 0
#
# Contract coverage: 85% (17/20 functions)

# Run tests - catches logic errors
pytest --doctest-modules
```

**You don't read AI code line by line. Tools tell you what's wrong.**

## What Gets Verified

| Check | What It Catches |
|-------|-----------------|
| `@pre`/`@post` required | AI forgot to think about boundaries |
| No I/O in Core | AI mixed business logic with file operations |
| Files < 500 lines | AI created a god-module |
| Functions < 50 lines | AI wrote unmaintainable code |
| No empty contracts | AI wrote `@pre(lambda: True)` to comply formally |
| No partial contracts | AI checked one param but ignored others |

## For Experienced Programmers

You're skeptical. Good. Here's what Invar actually is:

**Not magic:** Contracts are checked at runtime. Doctests are executed. Guard does static analysis. No AI involved in verification.

**Not new ideas:** Design-by-contract (Meyer, 1986). Pure/impure separation (functional programming). Executable specifications (doctests). Invar just enforces them.

**Not just for AI:** Code written with Invar conventions is better whether AI or human wrote it. Contracts document boundaries. Doctests prove behavior. Separation enables testing.

**The difference:** When AI writes code, you verify mechanically instead of reading manually.

## For Existing Projects

No reorganization needed. Configure patterns:

```toml
# pyproject.toml
[tool.invar.guard]
core_patterns = ["**/domain/**", "**/models/**"]
shell_patterns = ["**/api/**", "**/cli/**", "**/db/**"]
```

## Commands

```bash
invar guard              # Verify architecture rules
invar guard --changed    # Only git-modified files (fast feedback)
invar guard --agent      # JSON output for CI/automation
invar rules              # List all rules with explanations
invar map                # Symbol map with reference counts
invar sig module.py      # Extract function signatures
```

## Honest Limitations

**Invar catches:**
- Missing contracts (AI forgot boundaries)
- Empty/tautological contracts (`lambda: True`, `x == x`)
- I/O in pure code (architectural violations)
- Size violations (complexity indicators)

**Invar cannot catch:**
- Semantically wrong but syntactically valid contracts
- Dynamic imports, `eval()`, runtime tricks
- Whether the contract matches business requirements

**You still need:** Domain expertise to review contract correctness. Invar tells you contracts exist and aren't empty. You judge if they're right.

## Proof It Works

Invar verifies itself:

```bash
git clone https://github.com/tefx/invar
cd invar
pip install -e ".[dev]"
invar guard
# → Contract coverage: 78% (71/90 functions)
# → Guard passed.
```

## When to Use

**Good fit:**
- AI-assisted development with real business logic
- Teams that want AI speed without AI chaos
- Projects maintained over months/years

**Skip it:**
- One-off scripts
- Throwaway prototypes
- Projects under 500 lines

## Learn More

| Document | Purpose |
|----------|---------|
| [INVAR.md](./INVAR.md) | Protocol for AI agents (88 lines) |
| [docs/VISION.md](./docs/VISION.md) | Design philosophy |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical architecture |

---

**The bottom line:** You already verify human code with tests. Invar lets you verify AI code the same way—contracts, doctests, architecture rules. Stop reading AI output line by line. Let tools tell you what's wrong.

## License

MIT
