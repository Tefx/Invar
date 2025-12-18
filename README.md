# Invar

**Structure for AI-assisted development.**

---

## The Problem

AI coding agents (Claude Code, Cursor, Copilot) face inherent limitations:

| Limitation | Nature | Consequence |
|------------|--------|-------------|
| **Stateless** | No persistent memory | Must re-learn project every session |
| **Token-bound** | Limited context window | Cannot "see" entire codebase |
| **Blind generation** | Cannot execute code | Cannot verify during generation |
| **Happy-path bias** | Training data distribution | Systematically weak at edge cases |

These are **not bugs to fix**—they are fundamental properties of how language models work.

## The Insight

Traditional approaches try to make AI "smarter":
- Better prompts
- More training data
- Larger context windows

**Invar takes a different approach: provide structure that catches errors.**

You invest MORE upfront (contracts, separation, verification). You get FEWER bugs and MORE maintainable code.

> **Invar is safety infrastructure, not simplification.**

## The Four Pillars

### 1. Contracts as Guardrails

Agents have blind spots for edge cases. Contracts force explicit boundary thinking.

- **Without:** Agent writes code, forgets edge cases, bugs emerge later
- **With:** Agent declares boundaries upfront, issues caught early

### 2. Architecture as Sanctuary

I/O is chaos. Pure logic is testable. Separation creates a "clean room" for agents.

```
your-project/
├── core/           ← Pure logic (deterministic, testable, no I/O)
└── shell/          ← I/O operations (calls core/ for logic)
```

### 3. Maps as Compressed Context *(Phase 4)*

Agents cannot "see" large codebases. Maps will provide high-signal summaries.

- **Without:** Agent reads 50 files to understand project
- **With:** Agent reads summary with key symbols and contracts

> Not yet implemented. Currently use IDE features or tools like Repomix.

### 4. Tools as Enforcement

Prompts are suggestions. Tools are laws.

Agents might forget instructions. But `invar guard` blocks non-compliant code.

## Quick Start

### 1. Install

```bash
pip install invar
```

### 2. Initialize

```bash
cd your-project
invar init
```

Creates:
- `INVAR.md` — Protocol document (give this to your AI)
- `CLAUDE.md` — Project-specific rules
- `.invar/context.md` — Session continuity

### 3. Give Protocol to Your AI

**Claude Code:** Reads `CLAUDE.md` automatically.

**Other tools:** Add `INVAR.md` to system prompt or project knowledge.

### 4. Verify

```bash
invar guard              # Check structure
invar guard --strict     # Warnings as errors
```

## What Gets Enforced

| Rule | Purpose |
|------|---------|
| Core has no I/O imports | Business logic stays pure and testable |
| Functions < 50 lines | Forces decomposition into understandable units |
| Files < 300 lines | Prevents god-modules that know too much |
| Public functions have contracts | Explicit boundaries prevent misuse |
| No impure calls in Core | `datetime.now()`, `random()` break determinism |

## For Existing Projects

No need to reorganize. Use pattern-based classification:

```toml
# pyproject.toml
[tool.invar.guard]
core_patterns = ["**/domain/**", "**/models/**", "**/rules/**"]
shell_patterns = ["**/api/**", "**/cli/**", "**/db/**"]
```

## Honest Limitations

**Invar can:**
- Catch common architectural violations
- Provide checkpoints for agent workflow (ICIDV)
- Make violations visible in CI
- Enforce Core/Shell separation

**Invar cannot:**
- Detect dynamic imports or `eval()`
- Guarantee semantic correctness of contracts
- Force agents to follow the protocol
- Replace good engineering judgment

## Proof It Works

Invar enforces itself:

```bash
git clone https://github.com/tefx/invar
cd invar
invar guard --strict
# → 0 errors, 0 warnings
```

## When to Use Invar

**Good fit:**
- AI-assisted projects with real business logic
- Codebases maintained over months/years
- Teams that want AI productivity without AI chaos

**Skip it:**
- One-off scripts
- Throwaway prototypes
- Projects under 500 lines

## Learn More

| Document | Content |
|----------|---------|
| [INVAR.md](./INVAR.md) | Full protocol for AI agents |
| [docs/VISION.md](./docs/VISION.md) | Design philosophy |
| [docs/DESIGN.md](./docs/DESIGN.md) | Technical architecture |

---

*"In the age of AI-generated code, the skill is not writing code—it's specifying what correct code looks like."*

## License

MIT
