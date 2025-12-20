# Phase 9 Development Reflection

*Created: 2025-12-20*
*Author: Claude (Agent perspective)*

## Overview

This document captures deep reflections from developing Phase 9 (Agent-Native Polish) of Invar. The goal is to identify remaining friction, fundamental tensions, and opportunities for improvement.

---

## Part 1: Concrete Pain Points Experienced

### 1.1 Contract Parameter Errors (Recurring)

**What happened:**
Multiple times during Phase 9, I wrote `@pre` contracts with wrong parameter counts:

```python
# ERROR: Function has 3 params, lambda has 2
@pre(lambda source, max_lines: isinstance(source, str) and max_lines > 0)
def analyze_file_context(source: str, path: str, max_lines: int = 500):
```

**Why it happened:**
- I see the function signature and mentally extract "important" params
- Default params (`max_lines=500`) feel "optional" so I skip them
- The `path` param seemed like metadata, not a constraint target

**Current mitigation:** Phase 8 added `param_mismatch` detection (ERROR level)

**What's still missing:**
- Detection happens AFTER I write the code
- No IDE-time feedback (LSP integration)
- No auto-generation of correct lambda skeleton in editor

**Proposal:** P15 - IDE/LSP integration for real-time contract validation

---

### 1.2 API Discovery Friction

**What happened:**
I frequently guessed wrong about Invar's own APIs:

```python
# WRONG: Assumed parse_source returns list[Symbol]
symbols = parse_source(source)
for s in symbols:
    if s.kind == SymbolKind.FUNCTION:  # Error: tuple has no .kind

# CORRECT: Returns FileInfo
file_info = parse_source(source, path)
symbols = file_info.symbols
```

```python
# WRONG: Assumed Symbol has .has_contract property
if symbol.has_contract:  # Error: no attribute

# CORRECT: Check contracts list
if len(symbol.contracts) > 0:
```

**Why it happened:**
- No IDE autocompletion in my context
- Reading source is expensive (tokens), so I guess
- Similar patterns in other codebases led to wrong assumptions

**What's still missing:**
- `invar sig` helps but requires knowing to use it
- No inline type hints in Guard output
- No "did you mean?" suggestions for API misuse

**Proposal:** P16 - API usage examples in docstrings + Guard check for common misuses

---

### 1.3 Core Import Restrictions (Cognitive Load)

**What happened:**
I kept trying to use forbidden imports in Core:

```python
# In core/inspect.py - WRONG
from pathlib import Path  # Forbidden!
path = Path(file_path)
```

**Why it happened:**
- `pathlib` is so natural for path operations
- The "why" isn't immediately clear (it's pure, why forbidden?)
- Workarounds require more thought (use string operations)

**Current mitigation:** Guard detects forbidden imports

**What's still missing:**
- Guard says WHAT is forbidden but not WHY or WHAT TO USE INSTEAD
- No suggestions for pure alternatives (`fnmatch` instead of `PurePath.match`)
- The rule feels arbitrary without explanation

**Proposal:** P17 - Forbidden import suggestions with pure alternatives

```
ERROR: 'pathlib' is forbidden in Core
  → Why: File path operations may access filesystem
  → Instead: Use string operations or fnmatch for patterns
  → Example: fnmatch.fnmatch(path, "*.py") instead of Path(path).match("*.py")
```

---

### 1.4 File Size Creep

**What happened:**
`core/rules.py` is at 483 lines (96% of limit). It grew gradually:
- Started small
- Each new rule added ~30-50 lines
- Warnings came too late to easily refactor

**Current mitigation:** P8 added 80% threshold warning

**What's still missing:**
- No guidance on HOW to split (which functions go together?)
- No tracking of growth rate (is this file growing faster than others?)
- Refactoring requires significant effort once large

**Proposal:** P18 - Module cohesion analysis

```
WARNING: core/rules.py at 96% capacity
  → Suggested split by function group:
    - size_rules.py: check_file_size, check_function_size (120 lines)
    - contract_rules.py: check_missing_contract, check_empty_contract, ... (200 lines)
    - purity_rules.py: check_forbidden_import, check_internal_import, ... (160 lines)
```

---

### 1.5 Doctest Line Inflation

**What happened:**
Good doctests push functions over 50 lines even when logic is small:

```python
def analyze_file_context(...):
    """
    Analyze a source file.

    Examples:
        >>> source = '''
        ... from deal import pre
        ... @pre(lambda x: x > 0)
        ... def positive(x: int) -> int:
        ...     return x * 2
        ... '''
        >>> ctx = analyze_file_context(source.strip(), "test.py", 500)
        >>> ctx.functions_total
        2
    """
    # Only 15 lines of actual logic, but function is 53 lines total
```

**Current mitigation:** `exclude_doctest_lines` config option

**What's still missing:**
- Default is OFF (should probably be ON)
- No visibility into doctest vs code line breakdown
- Tension: good docs vs size limits

**Proposal:** P19 - Doctest/code line split in warnings

```
WARNING: Function 'analyze_file_context' has 53 lines
  → Breakdown: 15 code + 38 doctest
  → Consider: exclude_doctest_lines = true in config
```

---

## Part 2: Fundamental Tensions Identified

### 2.1 Enforcement vs Enablement

**The tension:**
Invar tries to ENFORCE structure, but enforcement creates workarounds.

| Enforcement | Agent Response |
|-------------|----------------|
| Require @pre/@post | Write `@pre(lambda x: isinstance(x, str))` |
| Forbid os/sys | Import inside function, use subprocess |
| Limit file size | Split artificially, lose cohesion |

**The insight:**
Formal compliance ≠ Substantive compliance

Agents will find ways to satisfy rules without understanding intent. This is not malicious - it's optimization under constraints.

**Current mitigation:**
- `empty_contract` detection
- `redundant_type_contract` detection
- Hints explain "why"

**What's still missing:**
- Semantic validation of contract quality
- Incentives for good contracts (not just penalties for bad)
- Recognition of genuine edge cases where trivial contracts are correct

**Possible approaches:**
1. **Probabilistic scoring** - "This contract covers 30% of edge cases"
2. **Comparative analysis** - "Similar functions have richer contracts"
3. **Accept the limitation** - Some contracts WILL be trivial, focus on catching the worst

---

### 2.2 Static vs Semantic Analysis

**The tension:**
Guard is purely syntactic. It can detect:
- `@pre(lambda: True)` - obvious tautology
- `@pre(lambda x: True)` - ignores parameter

But it CANNOT detect:
- `@pre(lambda x: x == x)` - always true
- `@pre(lambda x: len(x) >= 0)` - always true for strings/lists
- `@pre(lambda x: isinstance(x, object))` - always true

**Why this matters:**
An agent trying to "formally comply" can write infinitely many tautologies that pass Guard.

**Current mitigation:** None (P7 proposed but complex)

**Possible approaches:**
1. **Pattern library** - Known tautology patterns
2. **Symbolic execution** - Prove condition is always true
3. **LLM-based scoring** - Use another model to judge contract quality
4. **Statistical analysis** - Contracts that never fail in tests are suspicious

**My recommendation:** Start with pattern library (P7), defer symbolic execution

---

### 2.3 Documentation vs Behavior

**The tension:**
Documentation doesn't change agent behavior. Only enforced mechanisms do.

| Approach | Agent Behavior |
|----------|----------------|
| "Read INVAR.md before coding" | Skipped (costs tokens) |
| "Follow ICIDV workflow" | Skipped (no enforcement) |
| "Check existing patterns" | Skipped (extra step) |

**Phase 9's insight:**
> "Don't force agent to read - show them automatically."

**What we did:**
- P14: Auto-show patterns in `--changed` mode
- P5: Auto-show hints with every violation
- P3: Embed rule metadata in output

**What's still missing:**
- ICIDV Intent/Design steps have no enforcement
- "Best practices" documentation is ignored
- No mechanism to ensure agent read context.md

**Possible approaches:**
1. **Accept the limitation** - Some steps can't be enforced
2. **Require explicit acknowledgment** - "Confirm you read the context" (annoying)
3. **Embed in output** - Show relevant context.md sections in Guard output
4. **Trust but verify** - Check code quality as proxy for process quality

---

### 2.4 Token Budget vs Information Completeness

**The tension:**
Every piece of information competes for context tokens.

| More info | Trade-off |
|-----------|-----------|
| Detailed protocol | Less room for code |
| Full error explanations | Less room for fixes |
| Complete API docs | Less room for implementation |

**Phase 9.3's approach:**
Compress INVAR.md from 1296 → 88 lines by:
- Moving details to separate files
- Letting tools provide info on-demand
- Keeping only essential concepts

**What's still missing:**
- No measurement of actual token usage
- No adaptive compression (show more when context is fresh)
- No prioritization (what's most important for current task?)

**Possible approaches:**
1. **Layered information** - Core concepts always, details on-demand
2. **Task-aware context** - Show different info for different tasks
3. **Progressive disclosure** - Start minimal, expand on request
4. **Agent-managed context** - Let agent decide what to keep

---

### 2.5 Self-Consistency (Invar Checking Itself)

**The tension:**
Invar's own code has violations that are hard to fix:

```
src/invar/core/rules.py at 96% capacity
src/invar/shell/cli.py multiple functions > 50 lines
Multiple warnings about missing contracts on helper functions
```

**The question:**
Should Invar be perfectly compliant with its own rules?

| Position | Argument |
|----------|----------|
| Yes | "Eat your own dogfood" - credibility |
| No | Rules are guidelines, not absolutes |
| Partial | Core rules yes, style rules flexible |

**Current state:**
- 0 errors (critical rules pass)
- 24 warnings (style rules have violations)
- Warnings are about helper functions and size limits

**My recommendation:**
1. Fix warnings that indicate real problems
2. Document intentional exceptions
3. Use as test case for rule tuning

---

## Part 3: Missing Capabilities

### 3.1 Proactive Guidance (Not Just Reactive Checking)

**Current state:**
Guard is reactive - it checks AFTER code is written.

**What's missing:**
Proactive guidance BEFORE or DURING coding:

```bash
# Before starting a task
invar plan "Add authentication to API"
> This will affect:
>   - src/core/auth.py (new file, recommend @pre for password validation)
>   - src/shell/api.py (add Result return types)
> Suggested contracts:
>   - Password: min length, complexity
>   - Token: non-empty, valid format
```

**Proposal:** P20 - `invar plan` command for pre-implementation guidance

---

### 3.2 Contract Inference

**Current state:**
Agent must manually write all contracts.

**What's missing:**
Automatic contract inference from:
- Doctests (if test passes with x=5, maybe @pre(lambda x: x > 0))
- Type hints (already done, but could be richer)
- Usage patterns (if always called with positive ints...)
- Similar functions (reuse contracts from related functions)

**Proposal:** P21 - `invar suggest` command for contract inference

```bash
invar suggest src/core/calc.py::compute
> Based on doctests:
>   @pre(lambda x, y: x > 0 and y > 0)  # All examples use positive
> Based on similar functions:
>   @post(lambda result: result >= 0)   # Like related_func()
```

---

### 3.3 Refactoring Support

**Current state:**
When file exceeds limit, agent must manually:
1. Identify what to extract
2. Create new module
3. Update all imports
4. Verify nothing broke

**What's missing:**
Automated refactoring assistance:

```bash
invar refactor src/core/rules.py --split-by-group
> Creating:
>   src/core/rules/size.py (check_file_size, check_function_size)
>   src/core/rules/contracts.py (check_missing_contract, ...)
>   src/core/rules/purity.py (check_forbidden_import, ...)
> Updating imports in 5 files...
> Done. Run 'invar guard' to verify.
```

**Proposal:** P22 - `invar refactor` command with safe transformations

---

### 3.4 Cross-Session Memory

**Current state:**
Each session starts fresh. Context recovery depends on:
- context.md (manually maintained)
- Conversation summary (when context overflows)

**What's missing:**
- Automatic learning from past sessions
- Tracking of recurring mistakes
- Project-specific patterns database

**Example:**
```
# .invar/memory.json
{
  "common_errors": [
    {"pattern": "@pre with wrong param count", "count": 5, "last": "2025-12-20"},
    {"pattern": "pathlib import in Core", "count": 3, "last": "2025-12-19"}
  ],
  "learned_patterns": [
    {"file": "core/*.py", "typical_contract": "@pre(lambda x: isinstance(x, ...))"}
  ]
}
```

**Proposal:** P23 - Session memory for recurring pattern detection

---

## Part 4: Prioritized Recommendations

### Immediate (Phase 10 Candidates)

| ID | Proposal | Impact | Effort | Rationale |
|----|----------|--------|--------|-----------|
| P17 | Forbidden import alternatives | High | Low | Reduces cognitive load |
| P19 | Doctest/code line split | Medium | Low | Better visibility |
| P7 | Semantic tautology detection | High | Medium | Catches formal compliance |

### Medium-term

| ID | Proposal | Impact | Effort | Rationale |
|----|----------|--------|--------|-----------|
| P18 | Module cohesion analysis | Medium | Medium | Guides refactoring |
| P20 | `invar plan` command | High | High | Proactive guidance |
| P15 | IDE/LSP integration | High | High | Real-time feedback |

### Long-term / Research

| ID | Proposal | Impact | Effort | Rationale |
|----|----------|--------|--------|-----------|
| P21 | Contract inference | High | Very High | Reduces manual work |
| P22 | Automated refactoring | Medium | Very High | Safe transformations |
| P23 | Session memory | Medium | High | Learning system |

---

## Part 5: Meta-Observations

### 5.1 The Value of Self-Reflection

Writing this reflection surfaced insights that wouldn't emerge from just "fixing bugs":
- Patterns across multiple incidents
- Fundamental tensions (not just symptoms)
- Gaps between intention and reality

**Recommendation:** Make reflection a regular practice, not just post-mortem.

### 5.2 Agent-Native Design Principles (Refined)

From Phase 9, these principles emerged:

1. **Automatic > Opt-in** - Features agents don't know about don't get used
2. **Default ON > Default OFF** - More checking is better
3. **Show, don't document** - Embed info in output, don't expect reading
4. **Mechanical work → Tool** - Free agent for reasoning
5. **Enforcement > Guidelines** - Unenforced rules are ignored
6. **Single source of truth** - Reduce duplication and drift

### 5.3 The Bootstrap Problem

Invar is a tool for agents, built by agents, checked by Invar.

This creates interesting dynamics:
- We experience our own friction points
- We can't easily step outside to evaluate objectively
- Improvements we make affect our own future development

**Implication:** Need external validation (human review, other agents, production usage)

---

## Conclusion

Phase 9 successfully implemented Agent-Native Polish, but revealed deeper challenges:

1. **Enforcement creates workarounds** - Formal vs substantive compliance tension
2. **Static analysis has limits** - Can't catch all tautologies
3. **Documentation is ignored** - Only automatic mechanisms work
4. **Token budget constrains information** - Must prioritize ruthlessly
5. **Self-dogfooding is valuable** - We feel our own pain points

The path forward:
1. Continue P7 (semantic validation) as highest-impact improvement
2. Add proactive guidance (P20) to shift from reactive to proactive
3. Consider IDE integration (P15) for real-time feedback
4. Maintain reflection practice to surface hidden friction

---

*This reflection is itself a demonstration of the ICIDV "Intent" step - understanding deeply before acting.*
