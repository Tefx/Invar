# Invar: Philosophy & Vision

> **"Trade structure for safety. The goal is not to make AI simpler, but to make AI output more reliable."**

---

## The Problem

When AI coding agents (Claude Code, Cursor, Copilot) write code, they face inherent limitations:

| Limitation | Nature | Consequence |
|------------|--------|-------------|
| **Stateless** | No persistent memory | Must re-learn project every session |
| **Token-bound** | Limited context window | Cannot "see" entire codebase |
| **Blind generation** | Cannot execute code | Cannot verify correctness during generation |
| **Happy-path bias** | Training data distribution | Systematically weak at edge cases |

These are **not bugs to fix**—they are fundamental properties of how language models work.

---

## The Insight

Traditional approaches try to make AI "smarter" through:
- Better prompts
- More training data
- Larger context windows

**Invar takes a different approach: provide structure that catches errors.**

This is NOT like accessibility design (previous analogy was flawed):
- Accessibility makes things SIMPLER for users
- Invar makes things MORE STRUCTURED (which is more complex)

**Honest framing:** Invar is a trade-off:
- You invest MORE upfront (contracts, separation, protocols)
- You get FEWER bugs and MORE maintainable code

**Invar is safety infrastructure, not simplification.**

---

## The Four Pillars

### 1. Contracts as Guardrails

Agents have blind spots for edge cases. Contracts force explicit boundary thinking.

```python
from deal import pre, post

@pre(lambda price: price >= 0)
@post(lambda result: result >= 0)
def calculate_discount(price, rate):
    ...
```

**Without contract:** Agent writes code, forgets edge cases, bugs emerge later.
**With contract:** Agent must declare boundaries upfront, catches issues early.

### 2. Maps as Compressed Context *(Planned - Phase 4)*

Agents cannot "see" large codebases. Maps will provide high-signal context.

```
Without Map: Agent reads 50 files to understand project
With Map:    Agent reads summary with key symbols and contracts
```

**Status:** Not yet implemented. Currently use IDE features, `tree`, or tools like Repomix for project overview.

### 3. Architecture as Sanctuary

I/O is chaos. Pure logic is testable. Physical separation creates a "clean room" for agents.

```
┌─────────────────────────────────┐
│           SHELL                 │  ← Chaos lives here (I/O, network, files)
│                                 │
│   ┌─────────────────────────┐   │
│   │         CORE            │   │  ← Agent sanctuary (pure, testable)
│   └─────────────────────────┘   │
└─────────────────────────────────┘
```

**Honest caveat:** The boundary is sometimes fuzzy. Logging, config, time—these require judgment calls.

### 4. Tools as Enforcement

Prompts are suggestions. Tools are laws.

Agents might forget prompt instructions. But `invar guard` will block non-compliant code in CI.

**Honest caveat:** Guard can only enforce what's statically detectable. Dynamic imports, runtime behavior—these bypass Guard.

---

## Design Principles

### Principle 1: Don't Reinvent Wheels

Mature libraries exist for:
- **Contracts:** deal
- **Result types:** returns
- **Validation:** pydantic
- **Testing:** pytest + hypothesis

Invar's role: **coordinate and add AI-specific value**, not replace.

### Principle 2: Gradual Adoption

```
Level 0: Protocol only (INVAR.md)     → Guidance, no enforcement
Level 1: + Guard                       → Architecture enforcement  ← Current
Level 2: + Map/Sig                     → Context compression       ← Planned
```

Each level adds value independently. Currently at Level 1.

### Principle 3: Human-AI Collaboration

Agents write code, but humans review. Design for both:

- Decorators (not asserts) for readability
- Structured errors for machine parsing
- Natural language docs for human understanding

### Principle 4: Honest Limitations

Invar cannot:
- Detect dynamic imports or eval()
- Guarantee semantic correctness of contracts
- Force agents to follow the protocol
- Replace good engineering judgment

Invar can:
- Catch common architectural violations
- Provide checkpoints for agent workflow (ICIDV)
- Enforce Core/Shell separation

Invar will (Phase 4):
- Compress codebase context via Maps

---

## Success Metrics

| Metric | What We Measure | Status |
|--------|-----------------|--------|
| Architecture violations | I/O in Core, missing contracts | ✅ Enforced by Guard |
| Contract coverage | Functions with explicit contracts | ✅ Aim for 80% in Core |
| Edge-case bugs | Bugs from unhandled boundaries | ✅ Reduced by contracts |
| Context efficiency | Tokens needed to understand code | ⏳ Phase 4 (Maps) |

---

## What Invar Is NOT

- **Not a type checker** → Use mypy
- **Not a linter** → Use ruff
- **Not a test framework** → Use pytest
- **Not a formal verifier** → Too heavy for daily work
- **Not magic** → Requires discipline and investment

Invar is a **methodology + AI-specific tools** that coordinates existing tools.

---

## The Invar Equation

```
Invar = Protocol + Guard + Perception* + Integrations

Protocol     = Methodology for human-AI collaboration (INVAR.md)
Guard        = Architecture enforcement (static analysis) ✅
Perception   = Map + Signature extraction (context compression) ⏳ Phase 4
Integrations = deal + returns + pydantic + hypothesis + pytest
```

---

## The Bootstrap Question

**Q: If Invar helps write correct code, how do you write Invar correctly?**

**A:** Invar v1.0 is written with human oversight, serving as the trusted foundation. Once established, Invar can help maintain and extend itself. This is not circular—it's how all tools bootstrap.

---

*"In the age of AI-generated code, the skill is not writing code—it's specifying what correct code looks like."*
