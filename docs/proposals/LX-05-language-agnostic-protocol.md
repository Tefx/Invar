# LX-05: Language-Agnostic Protocol Extraction

**Status:** ✅ Protocol Complete (Tooling → LX-06)
**Priority:** Medium
**Category:** Language/Agent eXtensions
**Created:** 2025-12-30
**Revised:** 2025-12-31
**Completed:** 2025-12-31
**Hotfix:** 2025-12-31 - Examples language-aware copy
**Based on:** LX-01 (feasibility), LX-04 (multi-agent), INVAR.md v5.0
**Depends on:** LX-04 completion ✅
**Successor:** [LX-06: TypeScript Tooling Support](LX-06-typescript-tooling.md)

---

## Completion Summary

### ✅ Completed (Phases 1-3)

| Component | Files | Status |
|-----------|-------|--------|
| Protocol templates (universal) | 8 | ✅ |
| Protocol templates (python) | 5 | ✅ |
| Protocol templates (typescript) | 5 | ✅ |
| CLAUDE.md templates | 7 | ✅ |
| Skills as Jinja templates | 4 | ✅ |
| Language detection | 1 | ✅ |
| `--language` CLI parameter | 1 | ✅ |
| `copy_dir_lang` manifest type | 1 | ✅ |
| TypeScript examples | 4 | ✅ |
| **Total** | **36 files** | ✅ |

### → Migrated to LX-06 (Phase 4)

TypeScript tooling implementation moved to dedicated proposal:

| Tool | LX-05 Plan | LX-06 Phase |
|------|------------|-------------|
| guard-ts | Phase 4 | Phase 1 (MVP) |
| sig-ts | Phase 4 | Phase 2 (tree-sitter + @invar/ts-analyzer) |
| map-ts | Phase 4 | Phase 2 |

See [LX-06: TypeScript Tooling Support](LX-06-typescript-tooling.md) for hybrid architecture design.

### ⚠️ Deferred (Phase 5 - Low Priority)

| Task | Status | Notes |
|------|--------|-------|
| README.md update | Deferred | Add after LX-06 MVP |
| CHANGELOG.md v1.9.0 | Deferred | Add after LX-06 MVP |
| docs/adapters/*.md | Deferred | Create with LX-06 |

---

## Executive Summary

Extract a language-agnostic version of the Invar protocol and skills that can be applied to any programming language. The core insight: **80% of Invar's value is in workflow and agent discipline, not Python-specific tools**.

---

## Hotfix: Language-Aware Examples (2025-12-31)

### Problem

After `invar init --language=typescript` or auto-detection of TypeScript project:
- INVAR.md correctly renders TypeScript content (Zod schemas, etc.)
- CLAUDE.md correctly renders TypeScript critical rules
- **But `.invar/examples/` still contains Python files** (contracts.py, core_shell.py)

### Root Cause

Manifest uses `copy_dir` which blindly copies the Python examples:
```toml
".invar/examples/" = { src = "examples/", type = "copy_dir" }
```

### Solution

1. **Reorganize templates:**
   ```
   src/invar/templates/examples/
   ├── python/
   │   ├── contracts.py
   │   ├── core_shell.py
   │   └── workflow.md
   └── typescript/
       ├── contracts.ts
       ├── core_shell.ts
       └── workflow.md
   ```

2. **New manifest type `copy_dir_lang`:**
   ```toml
   ".invar/examples/" = { src = "examples/{language}/", type = "copy_dir_lang" }
   ```

3. **template_sync.py enhancement:**
   - Resolve `{language}` placeholder from SyncConfig
   - Copy language-specific directory

### Files Changed

| File | Change |
|------|--------|
| `src/invar/templates/examples/python/` | Move existing files |
| `src/invar/templates/examples/typescript/` | Create new |
| `src/invar/templates/manifest.toml` | Add `copy_dir_lang` |
| `src/invar/shell/commands/template_sync.py` | Handle `copy_dir_lang` |

---

## Problem Statement

### Current INVAR.md Content Analysis

| Section | Lines | Language-Specific | Universal |
|---------|-------|-------------------|-----------|
| Six Laws | 10 | 10% (@pre/@post mention) | 90% |
| Core/Shell | 40 | 60% (Python imports, syntax) | 40% |
| Contract Rules | 45 | 100% (Python lambda syntax) | 0% |
| Check-In | 15 | 0% | 100% |
| USBV Workflow | 25 | 10% (guard command) | 90% |
| Visible Workflow | 25 | 20% (Python examples) | 80% |
| Task Completion | 10 | 0% | 100% |
| Markers | 35 | 80% (Python decorators) | 20% |
| Commands | 15 | 100% (Python tools) | 0% |
| **Total** | ~220 | **~45%** | **~55%** |

**Conclusion:** Over half of INVAR.md is already language-agnostic conceptually.

### Skill Content Analysis

| Skill | Language-Specific | Universal |
|-------|-------------------|-----------|
| `/develop` | 15% (guard command refs) | 85% |
| `/investigate` | 5% (sig/map refs) | 95% |
| `/propose` | 0% | 100% |
| `/review` | 10% (guard refs) | 90% |

**Conclusion:** Skills are 90%+ language-agnostic.

## Proposed Architecture

### Layer 1: Universal Protocol (`invar-protocol`)

```
invar-protocol/
├── PROTOCOL.md              # Core methodology (language-agnostic)
│   ├── Six Laws             # Universal principles
│   ├── USBV Workflow        # Universal process
│   ├── Check-In/Final       # Session boundaries
│   ├── Visible Workflow     # Progress tracking
│   └── Task Completion      # Done criteria
│
├── ARCHITECTURE.md          # Core/Shell concepts
│   ├── Separation Principle # Pure vs I/O
│   ├── Decision Tree        # Universal (no language examples)
│   └── Size Limits          # Function/file guidelines
│
├── CONTRACTS.md             # Contract concepts (not syntax)
│   ├── Preconditions        # Input constraints concept
│   ├── Postconditions       # Output guarantees concept
│   ├── Invariants           # State consistency concept
│   └── Self-Test Rule       # "Can others implement from spec?"
│
├── skills/                  # Universal skill definitions
│   ├── develop.md           # USBV implementation skill
│   ├── investigate.md       # Research skill
│   ├── propose.md           # Decision facilitation
│   └── review.md            # Adversarial review
│
└── schema/                  # Format specifications
    ├── claude-md.schema.md  # CLAUDE.md structure
    ├── context.schema.md    # context.md structure
    └── skill.schema.md      # Skill file structure
```

### Layer 2: Language Adapters

```
invar-python/               # Current (refactored)
├── CONTRACTS-PYTHON.md     # @pre/@post lambda syntax
├── TOOLS-PYTHON.md         # guard, sig, map specifics
├── templates/
│   └── examples/           # Python code examples
└── runtime/                # invar_runtime package

invar-typescript/           # Future
├── CONTRACTS-TS.md         # Zod/io-ts patterns
├── TOOLS-TS.md             # ESLint, fast-check
└── templates/
    └── examples/           # TypeScript examples

invar-rust/                 # Future
├── CONTRACTS-RUST.md       # contracts crate, proptest
├── TOOLS-RUST.md           # clippy, cargo test
└── templates/
    └── examples/           # Rust examples
```

## Template Splitting Boundaries

### Current INVAR.md Structure Analysis

```
INVAR.md (~500 lines)
├── Header + Motto                    # 5 lines, universal
├── Six Laws                          # 15 lines, 90% universal
├── Core/Shell Architecture           # 80 lines, 60% Python
│   ├── Separation Principle          #   universal concept
│   ├── Decision Tree                 #   universal concept
│   ├── Examples                      #   Python code
│   └── Size Guidelines               #   universal numbers
├── Contract Rules                    # 100 lines, 95% Python
│   ├── @pre/@post Syntax             #   Python lambda
│   ├── Doctest Format                #   Python >>>
│   ├── Self-Test Rule                #   universal concept
│   └── Common Mistakes               #   Python-specific
├── Session Protocol                  # 30 lines, 100% universal
│   ├── Check-In                      #   universal
│   └── Final                         #   universal
├── USBV Workflow                     # 50 lines, 85% universal
│   ├── Phase Definitions             #   universal
│   └── Guard References              #   tool-specific
├── Visible Workflow                  # 25 lines, 100% universal
├── Task Completion                   # 20 lines, 100% universal
├── Markers                           # 40 lines, 100% Python
│   └── @escape_hatch, etc.           #   Python decorators
├── Tools Reference                   # 30 lines, 100% Python
│   └── guard, sig, map               #   Python CLI
└── Troubleshooting                   # 50 lines, 100% Python
```

### Recommended Split Structure

```
src/invar/templates/
├── protocol/                      # INVAR.md templates
│   ├── universal/
│   │   ├── header.md              # Motto, version
│   │   ├── six-laws.md            # Principles only
│   │   ├── architecture.md        # Concepts, decision tree (no code)
│   │   ├── contracts-concept.md   # What pre/post mean, self-test rule
│   │   ├── session.md             # Check-In/Final
│   │   ├── usbv.md                # Phases with {verification_tool}
│   │   ├── visible-workflow.md    # Progress tracking
│   │   └── completion.md          # Done criteria
│   ├── python/
│   │   ├── architecture-examples.md
│   │   ├── contracts-syntax.md
│   │   ├── markers.md
│   │   ├── tools.md
│   │   └── troubleshooting.md
│   ├── typescript/
│   │   └── ... (same structure)
│   └── INVAR.md.jinja
│
├── claude-md/                     # CLAUDE.md templates (NEW)
│   ├── universal/
│   │   ├── header.md
│   │   ├── check-in.md
│   │   └── workflow.md
│   ├── python/
│   │   ├── critical-rules.md      # @pre/@post examples
│   │   └── quick-reference.md     # Result[T, E], etc.
│   ├── typescript/
│   │   ├── critical-rules.md      # Zod examples
│   │   └── quick-reference.md
│   └── CLAUDE.md.jinja
│
├── skills/                        # Skills as templates (NEW)
│   ├── develop/SKILL.md.jinja     # {verification_tool} rendered
│   ├── review/SKILL.md.jinja
│   ├── investigate/SKILL.md.jinja
│   └── propose/SKILL.md.jinja
│
├── config/                        # .invar/ templates (NEW)
│   ├── context.md.jinja           # Already exists, needs language param
│   └── examples/
│       ├── python/
│       │   ├── contracts.py
│       │   ├── core_shell.py
│       │   └── workflow.md
│       └── typescript/
│           ├── contracts.ts
│           ├── core_shell.ts
│           └── workflow.md
│
└── commands/                      # Command templates (NEW)
    ├── audit.md.jinja             # Contract examples section
    └── guard.md                   # No templating needed
```

### Boundary Classification Rules

| Content Type | Belongs To | Example |
|--------------|------------|---------|
| Principles | Universal | "Separation means pure logic vs I/O" |
| Decision trees | Universal | "Does this function read files? → Shell" |
| Pseudocode | Universal | `PRECONDITION: x > 0` |
| Language syntax | Adapter | `@pre(lambda x: x > 0)` |
| Tool commands | Adapter | `invar_guard()` |
| Error patterns | Adapter | `Result[T, E]` usage |
| Numeric guidelines | Universal | 50 lines/500 lines limits |

### Split Examples

**Universal (architecture.md):**
```markdown
## Core/Shell Separation

| Zone | Purpose | Characteristics |
|------|---------|-----------------|
| Core | Pure logic | No I/O, deterministic |
| Shell | I/O operations | File/network access |

### Decision Tree
Does this function...
├─ Read/write files? → Shell
├─ Make network requests? → Shell
└─ None of the above? → Core

### Injection Pattern (Pseudocode)
FUNCTION is_expired(expiry, current_time):
    RETURN current_time > expiry
```

**Python Adapter (architecture-examples.md):**
```python
# core/validator.py - Pure logic
@pre(lambda text: len(text) > 0)
@post(lambda result: isinstance(result, bool))
def is_valid_email(text: str) -> bool:
    return "@" in text and "." in text.split("@")[1]

# shell/reader.py - I/O operations
def read_and_validate(path: Path) -> Result[bool, IOError]:
    try:
        text = path.read_text()
        return Success(is_valid_email(text))
    except IOError as e:
        return Failure(e)
```

---

## Code Examples Strategy

### Three-Layer Example Architecture

| Layer | Location | Content | Purpose |
|-------|----------|---------|---------|
| **L1: Pseudocode** | Universal files | Abstract patterns | Concept explanation |
| **L2: Syntax snippets** | Adapter inline | 3-10 line examples | Syntax demonstration |
| **L3: Complete implementations** | .invar/examples/ | Full files | Reference patterns |

### Example Type Classification

| Example Type | Lines | Current Location | Recommended |
|--------------|-------|------------------|-------------|
| Concept explanation | 1-3 | INVAR.md inline | → Universal pseudocode |
| Syntax demo | 3-10 | INVAR.md inline | → Adapter inline |
| Full implementation | 10-50 | .invar/examples/ | → Adapter examples/ |
| Workflow demo | 50+ | .invar/examples/workflow.md | → Adapter examples/ |

### .invar/examples/ Structure

```
.invar/examples/           # Installed based on language parameter
├── core-example.md        # Language-specific Core patterns
├── shell-example.md       # Language-specific Shell patterns
└── workflow.md            # Language-specific USBV workflow

# Template selection:
# --language=python → copies from templates/examples/python/
# --language=typescript → copies from templates/examples/typescript/
```

---

## Other Documentation Analysis

### Documentation Split Requirements (Revised after Audit)

| Document | Split Needed | Reason |
|----------|--------------|--------|
| **CLAUDE.md** | 🔴 Yes | Critical Rules section has Python examples |
| **Skills (SKILL.md)** | 🔴 Yes | Must be rendered templates, not runtime placeholders |
| **.invar/context.md** | 🔴 Yes | Core/Shell rules, Task Router have Python syntax |
| **.invar/examples/** | ✅ Yes | Fully language-specific |
| **Commands (audit.md)** | ⚠️ Minor | Contract examples section only |
| **Commands (guard.md)** | ✅ No | Tool name universal, internal dispatch |
| **AGENT.md** | ✅ No | Generic agent instructions |

### Detailed Audit Results

#### CLAUDE.md Critical Section (Python-specific)
```markdown
<!--invar:critical-->
| **Core** | `@pre/@post` + doctests, NO I/O imports |  ← Python
| **Shell** | Returns `Result[T, E]` from `returns` library |  ← Python

### Contract Rules (CRITICAL)
@pre(lambda x: x >= 0)  ← Python lambda syntax
```

#### context.md.jinja (Python-specific content)
```markdown
### Core/Shell Separation
- **Core**: @pre/@post + doctests  ← Python
- **Shell**: Result[T, E]  ← Python

## Task Router
| Write code in `core/` | `.invar/examples/contracts.py` |  ← .py files
| Add `@pre`/`@post` contracts | ...  ← Python decorators
```

#### audit.md (Contract examples only)
```markdown
## Review Checklist
### A. Contract Semantic Value
- Bad: `@pre(lambda x: isinstance(x, int))`  ← Python
- Good: `@pre(lambda x: x > 0 and x < MAX_VALUE)`  ← Python
```

#### guard.md (No changes needed)
- `invar_guard()` tool handles language detection internally
- Rule names in report format are examples, not prescriptive

### Skills Placeholder Strategy

Current skills reference Python tools directly:

```markdown
# /develop SKILL.md (current)
Run `invar_guard()` to verify...
Use `invar_sig` to see contracts...
```

Universal skills with placeholders:

```markdown
# /develop SKILL.md (universal)
Run `{verification_tool}` to verify...
Use `{signature_tool}` to see contracts...
```

Template rendering replaces placeholders:

| Placeholder | Python | TypeScript |
|-------------|--------|------------|
| `{verification_tool}` | `invar_guard()` | `guard-ts` |
| `{signature_tool}` | `invar_sig` | `sig-ts` |
| `{map_tool}` | `invar_map` | `map-ts` |
| `{contract_decorator}` | `@pre/@post` | `Zod schema` |

---

## Universal Protocol Content

### PROTOCOL.md (Draft)

```markdown
# The Invar Protocol (Universal)

> **"Trade structure for safety."**

## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Pure logic / I/O physically separate |
| 2. Contract Complete | Preconditions + Postconditions + Examples uniquely determine implementation |
| 3. Context Economy | Overview → Signatures → Code (only read what's needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct; verify all paths |

## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Activities |
|-------|---------|------------|
| UNDERSTAND | Know what and why | Intent, Inspect existing code, Constraints |
| SPECIFY | Define boundaries | Preconditions, Postconditions, Examples |
| BUILD | Write code | Implement leaves, Compose |
| VALIDATE | Confirm correctness | Run verification, Review if needed |

**Key:** Inspect before Contract. Contracts before Code.

## Session Protocol

### Check-In (Required)

Your first message MUST display:
```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

### Final (Required)

Your last message for implementation tasks MUST display:
```
✓ Final: verification PASS | <summary>
```

## Visible Workflow

For complex tasks (3+ functions), show checkpoints:
```
□ [UNDERSTAND] Task, context, constraints
□ [SPECIFY] Contracts and design decomposition
□ [VALIDATE] Verification results, integration status
```

## Task Completion

A task is complete only when ALL conditions met:
- Check-In displayed
- Intent explicitly stated
- Contracts written before implementation
- Final displayed with passing verification
- User requirement satisfied

## Contract Concepts

### Precondition
Constraints on inputs that must be true before function executes.
```
PRECONDITION: input_value > 0 AND input_value < 100
```

### Postcondition
Guarantees about outputs that must be true after function executes.
```
POSTCONDITION: result >= 0
```

### Self-Test Rule
> "Can someone else write the exact same function from just the contracts + examples?"

If yes → Contracts are complete.
If no → Add more constraints or examples.
```

### ARCHITECTURE.md (Draft)

```markdown
# Core/Shell Architecture (Universal)

## Separation Principle

| Zone | Purpose | Characteristics |
|------|---------|-----------------|
| **Core** | Pure logic | No I/O, deterministic, testable |
| **Shell** | I/O operations | File/network/time access, error handling |

## Decision Tree

```
Does this function...
│
├─ Read or write files? ──────────────→ Shell
├─ Make network requests? ────────────→ Shell
├─ Access current time? ──────────────→ Shell OR inject as parameter
├─ Generate random values? ───────────→ Shell OR inject as parameter
├─ Print output? ─────────────────────→ Shell (return data instead)
├─ Access environment? ───────────────→ Shell
│
└─ None of the above? ────────────────→ Core
```

## Injection Pattern

Instead of accessing impure values directly, inject them as parameters:

```
# Core: receives 'current_time' as parameter (pure)
function is_expired(expiry, current_time):
    return current_time > expiry

# Shell: calls with actual time
expired = is_expired(token.expiry, get_current_time())
```

## Size Guidelines

| Component | Recommended Limit | Rationale |
|-----------|-------------------|-----------|
| Function body | ~50 lines | Comprehensible unit |
| File | ~500 lines | Manageable module |
| Entry point | ~15 lines | Thin delegation layer |
```

### skills/develop.md (Universal Draft)

```markdown
# /develop Skill (Universal)

> **Mindset:** CONTRACTS before code — no exceptions.

## Scope Boundaries

**This skill IS for:** Implementing features, Fixing bugs, Modifying existing code
**This skill is NOT for:** Exploring unclear requirements → /investigate first

## Entry Actions

1. Read context file for project state
2. Understand the task requirements

## USBV Phases

### UNDERSTAND (Phase 1)
- What exactly needs to be done?
- Review existing code structure
- Identify constraints and dependencies

### SPECIFY (Phase 2)
- Write preconditions and postconditions BEFORE implementation
- Add examples for expected behavior
- Design function decomposition if complex

### BUILD (Phase 3)
- Follow the contracts from SPECIFY
- Implement leaf functions first
- Compose into larger functions

### VALIDATE (Phase 4)
- Run verification tool
- Fix any failures
- Show Final summary

## New Function Gate (MANDATORY)

| Check | If NO → Action |
|-------|----------------|
| Contract shown in SPECIFY phase? | STOP. Return to SPECIFY. |
| Example written? | STOP. Write example first. |

## Exit Criteria

- Verification passes
- Final displayed
- User requirement satisfied
```

## Language Adapter Specification

### Contract Syntax Mapping

| Concept | Python | TypeScript | Rust | Go |
|---------|--------|------------|------|-----|
| **Precondition** | `@pre(lambda x: x > 0)` | `@Pre(x => x > 0)` or Zod | `#[pre(x > 0)]` | `// @pre: x > 0` |
| **Postcondition** | `@post(lambda r: r >= 0)` | `@Post(r => r >= 0)` | `#[post(ret >= 0)]` | `// @post: ret >= 0` |
| **Example** | Doctest `>>>` | JSDoc `@example` | `/// # Examples` | `// Example:` |
| **Pure/IO split** | `core/` vs `shell/` | Same or `pure/` | Same | Same |
| **Error type** | `Result[T, E]` | `Result<T, E>` | `Result<T, E>` | `(T, error)` |

### Verification Tool Mapping

| Layer | Python | TypeScript | Rust | Go |
|-------|--------|------------|------|-----|
| **Static** | Ruff, mypy | ESLint, tsc | Clippy | go vet |
| **Examples** | pytest doctest | Jest/Vitest | cargo test --doc | go test |
| **Property** | Hypothesis | fast-check | proptest | gopter |
| **Symbolic** | CrossHair | N/A | KLEE/MIRI | N/A |

### Adapter Interface

```
LanguageAdapter:
  - detect(path) → bool           # Is this a {language} project?
  - verify(path, options) → Result  # Run verification
  - signatures(file) → Signature[]  # Extract contracts
  - symbols(path) → SymbolMap       # Build reference map
  - patterns() → PatternDefs        # Core/Shell patterns
```

## Critical Analysis: Agent Compliance

### File Scattering Impact

**Question:** Will splitting protocol into multiple files hurt agent compliance?

**Analysis:**

| Scenario | Agent Behavior | Risk |
|----------|---------------|------|
| Single INVAR.md (current) | Agent reads on Check-In | ✅ Low - always discovers |
| Split into docs/protocol/*.md | Agent must navigate directory | ⚠️ Medium - may miss files |
| 7+ scattered files | Agent reads selectively | ❌ High - incomplete context |

**Key Insight:** Agents don't proactively explore file systems. They read what's referenced or what's in obvious locations (INVAR.md, CLAUDE.md).

### Recommended Architecture

**Source separation for maintainers, merged output for agents:**

```
Source (maintainer view):          Output (agent view):
├── protocol/                      ├── INVAR.md  ← Single file
│   ├── universal/                 │   (generated from template)
│   │   ├── six-laws.md           └── ...
│   │   ├── usbv.md
│   │   └── session.md
│   ├── python/
│   │   ├── contracts.md
│   │   └── tools.md
│   └── INVAR.md.jinja  ← Composition template
```

**Template Composition:**

```jinja
{# INVAR.md.jinja #}
{% include "protocol/universal/header.md" %}
{% include "protocol/universal/six-laws.md" %}

{% if language == "python" %}
{% include "protocol/python/core-shell.md" %}
{% include "protocol/python/contracts.md" %}
{% elif language == "typescript" %}
{% include "protocol/typescript/core-shell.md" %}
{% include "protocol/typescript/contracts.md" %}
{% endif %}

{% include "protocol/universal/session.md" %}
{% include "protocol/universal/usbv.md" %}

{% if language == "python" %}
{% include "protocol/python/tools.md" %}
{% endif %}
```

**Benefits:**
1. **Maintainers** edit focused, small files
2. **Agents** get single, comprehensive INVAR.md
3. **No compliance risk** - output identical to current structure

---

## Init Command Changes

### Language Detection

```python
SUPPORTED_LANGUAGES = ["python"]
FUTURE_LANGUAGES = ["typescript", "rust", "go"]

def detect_language(path: Path) -> str:
    """Auto-detect project language from marker files."""
    if (path / "pyproject.toml").exists():
        return "python"
    if (path / "tsconfig.json").exists():
        return "typescript"
    if (path / "Cargo.toml").exists():
        return "rust"
    if (path / "go.mod").exists():
        return "go"
    return "python"  # default
```

### New CLI Parameter

```python
def init(
    path: Path = typer.Argument(...),
    claude: bool = typer.Option(False, "--claude"),
    pi: bool = typer.Option(False, "--pi"),
    language: str = typer.Option(
        None,
        "--language",
        help="Target language (auto-detected if not specified)"
    ),
) -> None:
    # Auto-detect if not specified
    if language is None:
        language = detect_language(path)
    
    if language in FUTURE_LANGUAGES:
        console.print(f"[yellow]Warning:[/yellow] {language} support is experimental")
```

### Template Rendering

```python
sync_config = SyncConfig(
    syntax="cli",
    language=language,  # NEW: Pass to template
    inject_project_additions=...,
)
```

---

## TypeScript Implementation Plan

### Tool Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Contracts | Zod | Runtime validation, schema inference |
| Result Type | neverthrow | `Result<T, E>` for Shell functions |
| Static | tsc + ESLint | Type checking + linting |
| Tests | Vitest | Fast, ESM-native testing |
| Property | fast-check | Property-based testing |
| Doctest | vite-plugin-doctest | Inline examples |

### Contract Syntax

```typescript
// Python equivalent:
// @pre(lambda x: x > 0)
// @post(lambda result: result >= 0)

import { z } from 'zod';

// TypeScript with Zod:
const CalculateInput = z.object({
  principal: z.number().positive(),
  rate: z.number().min(0).max(1),
  years: z.number().int().positive(),
});

const CalculateOutput = z.number().nonnegative();

function calculate(input: z.infer<typeof CalculateInput>): number {
  const validated = CalculateInput.parse(input);
  const result = validated.principal * (1 + validated.rate) ** validated.years;
  return CalculateOutput.parse(result);
}
```

### Core/Shell Pattern

```typescript
// core/interest.ts - Pure logic
export function compoundInterest(
  principal: number,
  rate: number,
  years: number
): number {
  return principal * Math.pow(1 + rate, years);
}

// shell/calculator.ts - I/O operations
import { Result, ok, err } from 'neverthrow';
import { compoundInterest } from '../core/interest';

export function calculateFromInput(
  input: unknown
): Result<number, ValidationError> {
  const parsed = CalculateInput.safeParse(input);
  if (!parsed.success) {
    return err(new ValidationError(parsed.error));
  }
  return ok(compoundInterest(
    parsed.data.principal,
    parsed.data.rate,
    parsed.data.years
  ));
}
```

### Guard Implementation

```typescript
// invar-guard-ts pseudocode
async function guard(options: GuardOptions): Promise<GuardResult> {
  const results = await Promise.all([
    runTypeCheck(),      // tsc --noEmit
    runLinter(),         // eslint with invar rules
    runTests(),          // vitest run
    runPropertyTests(),  // vitest with fast-check
  ]);
  
  return aggregateResults(results);
}
```

### Sig/Map Implementation

```
Option A: tree-sitter-typescript
- Fast, battle-tested parser
- Extract function signatures with Zod schemas
- Build symbol reference map

Option B: TypeScript Compiler API
- Native AST access
- More accurate type inference
- Heavier dependency
```

**Recommendation:** Start with tree-sitter for speed, add TS Compiler API for advanced features.

---

## Implementation Plan

### Phase 1: Template Refactoring ✅ COMPLETE

| Day | Task | Output | Status |
|-----|------|--------|--------|
| 1 | Split INVAR.md universal sections | `protocol/universal/*.md` (8 files) | ✅ |
| 2 | Create Python adapter fragments | `protocol/python/*.md` (5 files) | ✅ |
| 3 | Create INVAR.md.jinja template | Composition template | ✅ |
| 4 | Split CLAUDE.md into templates | `claude-md/universal/*.md` + `python/*.md` | ✅ |
| 5 | Convert skills to templates | `skills/*.jinja` (4 files) | ✅ |
| 6 | Update context.md.jinja | Add language parameter | ✅ |
| 7 | Template audit.md | Contract examples section | ✅ |
| 8 | Update template_sync.py | Render all templates with language | ✅ |

**Files Created (28 files):**
```
src/invar/templates/
├── protocol/                          # INVAR.md (14 files)
│   ├── universal/ (8 files)
│   ├── python/ (5 files)
│   └── INVAR.md.jinja
│
├── claude-md/                         # CLAUDE.md (8 files) - NEW
│   ├── universal/
│   │   ├── header.md
│   │   ├── check-in.md
│   │   └── workflow.md
│   ├── python/
│   │   ├── critical-rules.md
│   │   └── quick-reference.md
│   └── CLAUDE.md.jinja
│
├── skills/                            # Skills (4 files) - NEW
│   ├── develop/SKILL.md.jinja
│   ├── review/SKILL.md.jinja
│   ├── investigate/SKILL.md.jinja
│   └── propose/SKILL.md.jinja
│
└── commands/                          # Commands (1 file) - NEW
    └── audit.md.jinja
```

**Files Modified (3 files):**
```
src/invar/templates/config/context.md.jinja  # Add language conditionals
src/invar/shell/commands/template_sync.py    # Render all templates
src/invar/core/sync_helpers.py               # SyncConfig.language
```

### Phase 2: Init Enhancement ✅ COMPLETE

| Day | Task | Output | Status |
|-----|------|--------|--------|
| 1 | Add `detect_language()` | Auto-detection logic | ✅ |
| 2 | Add `--language` parameter | CLI option | ✅ |
| 3 | Update SyncConfig | Language field | ✅ |
| 4 | Template rendering with language | Jinja context | ✅ |
| 5 | Tests + documentation | Test coverage | ✅ |

**Files Modified:**
- `src/invar/shell/commands/init.py` ✅
- `src/invar/core/sync_helpers.py` ✅
- `src/invar/shell/commands/template_sync.py` ✅

### Phase 3: TypeScript Skeleton ✅ COMPLETE

| Day | Task | Output | Status |
|-----|------|--------|--------|
| 1-2 | Create TS protocol fragments | `protocol/typescript/*.md` | ✅ |
| 3-4 | Create TS example files | contracts.ts, core_shell.ts, functional.ts | ✅ |
| 5 | Hotfix: copy_dir_lang | Language-aware examples | ✅ |

**Files Created:**
```
src/invar/templates/protocol/typescript/   ✅
├── architecture-examples.md
├── contracts-syntax.md
├── markers.md
├── tools.md
└── troubleshooting.md

src/invar/templates/examples/typescript/   ✅
├── contracts.ts
├── core_shell.ts
├── functional.ts
├── workflow.md
└── README.md
```

### Phase 4: TypeScript Tools → MIGRATED TO LX-06

> **Note:** This phase has been migrated to [LX-06: TypeScript Tooling Support](LX-06-typescript-tooling.md).
> LX-06 provides a more comprehensive hybrid architecture (Python orchestration + targeted Node components).

| Original Task | LX-06 Location |
|---------------|----------------|
| guard-ts (tsc + eslint + vitest) | LX-06 Phase 1 |
| sig-ts (tree-sitter) | LX-06 Phase 2 (@invar/ts-analyzer) |
| map-ts (symbol references) | LX-06 Phase 2 |

### Phase 5: Validation ⚠️ DEFERRED

Deferred until LX-06 MVP completion:

| Task | Status | Dependency |
|------|--------|------------|
| Test on real TS project | Pending | LX-06 Phase 1 |
| README.md update | Pending | LX-06 Phase 1 |
| CHANGELOG.md v1.9.0 | Pending | LX-06 Phase 1 |
| docs/adapters/*.md | Pending | LX-06 Phase 2 |

**LX-05 Protocol: Complete. LX-06 Tooling: In Progress.**

---

## File Change Summary

| Phase | Create | Modify | Delete | Total |
|-------|--------|--------|--------|-------|
| 1. Template Refactoring | 28 | 3 | 0 | 31 |
| 2. Init Enhancement | 0 | 4 | 0 | 4 |
| 3. TypeScript Skeleton | 12 | 2 | 0 | 14 |
| 4. TypeScript Tools | 3 | 2 | 0 | 5 |
| 5. Validation | 4 | 1 | 1 | 6 |
| **Total** | **47** | **12** | **1** | **60** |

### Detailed File List

**Phase 1: Create (28 files):**
```
# INVAR.md - Universal Protocol (8 files)
src/invar/templates/protocol/universal/header.md
src/invar/templates/protocol/universal/six-laws.md
src/invar/templates/protocol/universal/architecture.md
src/invar/templates/protocol/universal/contracts-concept.md
src/invar/templates/protocol/universal/session.md
src/invar/templates/protocol/universal/usbv.md
src/invar/templates/protocol/universal/visible-workflow.md
src/invar/templates/protocol/universal/completion.md

# INVAR.md - Python Adapter (5 files)
src/invar/templates/protocol/python/architecture-examples.md
src/invar/templates/protocol/python/contracts-syntax.md
src/invar/templates/protocol/python/markers.md
src/invar/templates/protocol/python/tools.md
src/invar/templates/protocol/python/troubleshooting.md

# INVAR.md - Composition (1 file)
src/invar/templates/protocol/INVAR.md.jinja

# CLAUDE.md - Universal (3 files)
src/invar/templates/claude-md/universal/header.md
src/invar/templates/claude-md/universal/check-in.md
src/invar/templates/claude-md/universal/workflow.md

# CLAUDE.md - Python (2 files)
src/invar/templates/claude-md/python/critical-rules.md
src/invar/templates/claude-md/python/quick-reference.md

# CLAUDE.md - Composition (1 file)
src/invar/templates/claude-md/CLAUDE.md.jinja

# Skills as Templates (4 files)
src/invar/templates/skills/develop/SKILL.md.jinja
src/invar/templates/skills/review/SKILL.md.jinja
src/invar/templates/skills/investigate/SKILL.md.jinja
src/invar/templates/skills/propose/SKILL.md.jinja

# Commands (1 file)
src/invar/templates/commands/audit.md.jinja
```

**Phase 1: Modify (3 files):**
```
src/invar/templates/config/context.md.jinja  # Add language conditionals
src/invar/shell/commands/template_sync.py    # Render all templates with language
src/invar/core/sync_helpers.py               # SyncConfig.language field
```

**Phase 3: Create (12 files):**
```
# TypeScript INVAR.md Adapter (5 files)
src/invar/templates/protocol/typescript/architecture-examples.md
src/invar/templates/protocol/typescript/contracts-syntax.md
src/invar/templates/protocol/typescript/markers.md
src/invar/templates/protocol/typescript/tools.md
src/invar/templates/protocol/typescript/troubleshooting.md

# TypeScript CLAUDE.md Adapter (2 files)
src/invar/templates/claude-md/typescript/critical-rules.md
src/invar/templates/claude-md/typescript/quick-reference.md

# TypeScript Examples (5 files)
src/invar/templates/examples/typescript/contracts.ts
src/invar/templates/examples/typescript/core_shell.ts
src/invar/templates/examples/typescript/functional.ts
src/invar/templates/examples/typescript/workflow.md
src/invar/templates/examples/typescript/README.md
```

**Phase 4: Create (3 files):**
```
# TypeScript Tools
src/invar/adapters/typescript/guard.py
src/invar/adapters/typescript/sig.py
src/invar/adapters/typescript/map.py
```

**Phase 2: Modify (4 files):**
```
src/invar/shell/commands/init.py       # detect_language(), --language
src/invar/core/sync_helpers.py         # SyncConfig.language field
src/invar/shell/commands/template_sync.py  # Jinja context
src/invar/shell/cli.py                 # CLI help text
```

**Phase 5: Create (4 files):**
```
docs/adapters/python.md
docs/adapters/typescript.md
docs/protocol/universal.md
CHANGELOG.md (v2.0.0 section)
```

**Phase 5: Modify (1 file):**
```
README.md                              # Multi-language support
```

**Phase 5: Delete (1 file):**
```
src/invar/templates/INVAR.md           # Replaced by INVAR.md.jinja
```

---

## Version Milestones

| Version | Content | Timeline |
|---------|---------|----------|
| v1.8.1 | Template refactoring (INVAR.md, CLAUDE.md, skills) | Week 1-2 |
| v1.9.0 | `--language` parameter, TS protocol docs | Week 3 |
| v2.0.0-beta | TypeScript tools (guard, sig, map) | Week 4-5 |
| v2.0.0 | Validated, documented release | Week 6 |

**Total: 6 weeks** (extended from 5 due to additional template work)

## Benefits

| Benefit | Description |
|---------|-------------|
| **Broader Applicability** | Protocol useful beyond Python (TS, Rust, Go) |
| **Clearer Separation** | Universal concepts vs language-specific tooling |
| **Easier Onboarding** | Learn concepts first, then syntax |
| **Community Adapters** | Others can create language support |
| **Agent Portability** | Same USBV workflow for any language |
| **No Compliance Risk** | Single INVAR.md output preserves agent behavior |
| **Maintainer Experience** | Small, focused source files |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-abstraction | Medium | Keep Python path as primary; TS validates universality |
| Maintenance burden | Low | Universal docs stable; only adapters change |
| Template complexity | Medium | Comprehensive tests for template rendering |
| Agent confusion | Low | Output identical to current INVAR.md structure |
| TS tool quality | High | Phase 5 validation on real project before release |

---

## Success Criteria

### Phase 1-2 (v1.9.0) ✅ COMPLETE
- [x] Template refactoring produces identical INVAR.md output
- [x] `--language` parameter works for Python
- [x] No regressions in existing Python workflow

### Phase 3 (TypeScript Protocol) ✅ COMPLETE
- [x] TypeScript protocol docs readable without Python knowledge
- [x] TypeScript example files (contracts.ts, core_shell.ts, functional.ts)
- [x] Language-aware examples installation (copy_dir_lang)

### Phase 4 (TypeScript Tools) → LX-06
- [ ] guard-ts runs tsc + eslint + vitest successfully → LX-06 Phase 1
- [ ] sig-ts extracts Zod schemas as contracts → LX-06 Phase 2
- [ ] map-ts builds symbol reference counts → LX-06 Phase 2

### Phase 5 (Validation) ⚠️ DEFERRED
- [ ] At least 1 real TypeScript project validates workflow → After LX-06
- [ ] Documentation complete for both languages → After LX-06
- [x] Existing Python users see no breaking changes
- [ ] Community feedback incorporated → After LX-06

---

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Single file vs split? | **Single output, split source** | Agents need single INVAR.md; maintainers need focused files |
| Skills generic? | **Yes, with tool placeholders** | `{verification_tool}` renders to `invar_guard` or `guard-ts` |
| CLAUDE.md sections? | **No change needed** | CLAUDE.md references INVAR.md; adapts automatically |
| Python migration? | **Yes, use template composition** | Consistency across languages; no user-facing changes |

---

## Open Questions (Remaining)

1. **NPM package name?** `invar-ts`, `@invar/typescript`, or `invar-tools-ts`?
2. **Monorepo or separate?** Keep TS tools in same repo or new `invar-typescript` repo?
3. **ESLint plugin?** Create `eslint-plugin-invar` for contract linting rules?

## Appendix: Universal Contract Examples (Pseudocode)

```
// PSEUDOCODE - Not tied to any language

FUNCTION calculate_discount(price, rate):
    PRECONDITION: price > 0 AND 0 <= rate <= 1
    POSTCONDITION: result >= 0

    EXAMPLE: calculate_discount(100, 0.2) → 80.0
    EXAMPLE: calculate_discount(100, 0) → 100.0  // Edge: no discount

    RETURNS: price * (1 - rate)

// Self-test: Can you implement this from just the spec above?
// If yes → Contract is complete.
```

---

*LX-05 builds on LX-01 feasibility analysis and LX-04 multi-agent infrastructure.*
