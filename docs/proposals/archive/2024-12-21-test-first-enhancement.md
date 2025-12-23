# Protocol Change Proposal: Test-First, Contract-as-Recovery, Hierarchical Decomposition, Reflective Verification & Contract Completeness

> Inspired by research showing: (1) test-first improves accuracy 19%→44%, (2) contracts enable auto-recovery, (3) hierarchical decomposition improves pass rates 75%+, (4) underspecified problems are unsolvable, (5) verbal reflection improves pass@1 from 80%→91%, (6) three-way consistency checking achieves 87% acceptance with zero false positives.

---

## Metadata

- **Date:** 2024-12-21
- **Author:** Agent (based on research paper analysis)
- **Status:** Draft
- **Layer:** L1 (Protocol)
- **References:**
  - [AlphaCodium: From Prompt Engineering to Flow Engineering](https://arxiv.org/abs/2401.08500) (2024)
  - [Pel: A Programming Language for Orchestrating AI Agents](https://arxiv.org/abs/2505.13453) (2025)
  - [Parsel: Algorithmic Reasoning with Language Models by Composing Decompositions](https://arxiv.org/abs/2212.10561) (2022, NeurIPS 2023)
  - [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770) (2023, ICLR 2024)
  - [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) (2023, NeurIPS 2023)
  - [Clover: Closed-Loop Verifiable Code Generation](https://arxiv.org/abs/2310.17807) (2023, CAV 2024)

---

## Trigger

### Problem 1: Contract and Implementation Coupled

Current ICIDIV workflow treats Contract and Implementation as closely coupled:

```
Current: Intent → Contract → Inspect → Design → Implement → Verify
                     ↓
         @pre/@post + doctests written together with code
```

**AlphaCodium research** demonstrates that **separating test generation from code generation** significantly improves accuracy:

> "Generating useful tests is easier than generating correct code. Generating tests only requires understanding the problem and basic reasoning—no need to fully 'solve' the problem."

### Problem 2: Contracts Viewed Only as Verification

Current view of contracts is one-dimensional:

```
Current: Contract → Verify → Report violation → Agent manually fixes
```

**Pel research** shows contracts have a second critical function—**recovery context**:

> "When an error occurs, the Helper Agent analyzes the discrepancy between the code and the expected usage (based on the docstring) and proposes a corrected code snippet."

The better the contract/doctest, the easier it is to auto-fix violations.

### Problem 3: Design Step Lacks Decomposition Guidance

Current Design step focuses only on file size:

```
Current: □ Design — If file > 400 lines, plan extraction first
```

**Parsel research** shows that **hierarchical decomposition** dramatically improves code generation:

> "Humans often start with a high-level algorithmic design and implement each part gradually. LLMs should mimic this approach."

The Design step should guide breaking complex tasks into sub-functions BEFORE implementation.

### Problem 4: Underspecified Problems Are Unsolvable

**SWE-bench research** evaluated LLMs on 2,294 real GitHub issues. The best model (Claude 2) solved only **1.96%**.

Key finding—what makes problems **unsolvable**:

> "Underspecified issue descriptions led to ambiguity on what the problem was and how it should be solved."

What makes problems **solvable**:
- Clear, specific descriptions
- Well-structured tests
- Reduced context complexity

**This validates Invar's entire approach:** Contracts eliminate ambiguity. Clear specs → Solvable problems.

### Problem 5: Verification Without Reflection

Current Verify step is mechanical:

```
Current: □ Verify — Run: invar guard && pytest
                   If violations: fix → verify again
```

**Reflexion research** shows that **explicit verbal reflection** dramatically improves outcomes:

> "Reflexion agents verbally reflect on task feedback signals, then maintain their reflective text in episodic memory to induce better decision-making in subsequent trials."

Result: HumanEval pass@1 improved from **80% (GPT-4) → 91% (with Reflexion)**.

The difference: Don't just fix—**understand WHY it failed** first.

### Problem 6: Contract Quality is Undefined

Current contracts have no quality metric beyond "exists":

```
Current: Has @pre or @post? ✓ Pass
         What's in the contract? (not checked)
```

**Clover research** introduces **completeness checking**:

> "To prevent annotations that are too trivial from being accepted, they test whether the annotations contain enough information to reconstruct functionally equivalent code."

A good contract should be **complete enough to regenerate the code**:

```python
# Weak contract (incomplete) - many implementations satisfy it
@pre(lambda x: x > 0)
def mystery(x: int) -> int:
    ...  # Could be x+1, x*2, x**2, anything

# Strong contract (complete) - only one implementation satisfies it
@pre(lambda x: x > 0)
@post(lambda x, result: result == x + 1)
def increment(x: int) -> int:
    """
    >>> increment(5)
    6
    """
    ...  # Must be: return x + 1
```

The Clover approach achieves **87% acceptance of correct code** while maintaining **zero false positives** (never accepting incorrect code).

---

## Proposed Changes

### Change 1: Test-First Emphasis

Expand the Contract step to explicitly require tests BEFORE implementation.

**Before:**
```markdown
## Contracts

Every Core function must have `@pre` or `@post`:

@pre(lambda x, y: x > 0 and y > 0)
def calculate(x: int, y: int) -> int:
    """
    >>> calculate(2, 3)
    5
    """
```

**After:**
```markdown
## Contracts (Test-First)

Before implementation, define:
1. **Preconditions** (@pre) - What inputs are invalid?
2. **Postconditions** (@post) - What does output guarantee?
3. **Edge Cases** (doctests) - At least 3 examples including boundaries

Writing tests is easier than writing code. Do this FIRST.

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)    # Normal case
    80.0
    >>> discounted_price(100, 0)      # Edge: no discount
    100.0
    >>> discounted_price(100, 1)      # Edge: full discount
    0.0
    >>> discounted_price(0.01, 0.5)   # Edge: minimal price
    0.005
    """
```

### Change 2: Contract-as-Recovery Philosophy

Add new section explaining contracts' dual purpose.

```markdown
## Why Contracts Matter

Contracts serve two purposes:

1. **Verification** - Catch violations before they become bugs
2. **Recovery** - When violations occur, contracts tell the Agent exactly
   what went wrong and how to fix it

A good contract is a repair manual for your code.

### The Verification-Recovery Loop

┌─────────────────────────────────────────────────────┐
│  Agent writes code with contracts                   │
│       ↓                                             │
│  invar guard finds violation                        │
│       ↓                                             │
│  Agent reflects: Why did this fail?                 │
│       ↓                                             │
│  Agent reads: contract + doctest + reflection       │
│       ↓                                             │
│  Agent fixes based on understanding                 │
│       ↓                                             │
│  Verify again → Clean                               │
└─────────────────────────────────────────────────────┘

Good contracts make the "fix" step trivial.
Reflection makes the fix more likely to be correct.
```

### Change 3: Hierarchical Decomposition in Design

Enhance the Design step to include task decomposition.

**Before:**
```markdown
□ Design — If file > 400 lines, plan extraction first
```

**After:**
```markdown
□ Design — Decompose into sub-functions, then check file size:
           1. List functions needed (name + one-line description)
           2. Identify dependencies (which calls which)
           3. Order: implement leaves first, then compose
           4. If file > 400 lines, plan extraction
```

**Example:**

Task: *"Implement shopping cart total calculation"*

```
Design decomposition:

calculate_cart_total(cart) → float
├── validate_cart_items(cart) → bool      # Check all items valid
├── get_item_subtotal(item) → float       # Price × quantity
├── apply_item_discount(item) → float     # Apply per-item discount
├── calculate_subtotal(cart) → float      # Sum of item subtotals
├── apply_cart_discount(subtotal) → float # Apply cart-level discount
└── add_tax(amount) → float               # Add applicable tax

Implementation order (leaves first):
1. validate_cart_items  — no dependencies
2. get_item_subtotal    — no dependencies
3. apply_item_discount  — no dependencies
4. add_tax              — no dependencies
5. calculate_subtotal   — uses get_item_subtotal, apply_item_discount
6. apply_cart_discount  — no dependencies
7. calculate_cart_total — uses all above
```

For each function: Contract → Implement → Verify, then compose.

### Change 4: Reflective Verification

Enhance the Verify step to include explicit reflection on failures.

**Before:**
```markdown
□ Verify — Run: invar guard && pytest --doctest-modules
           If violations: read contract → fix → verify again
```

**After:**
```markdown
□ Verify — Run: invar guard && pytest --doctest-modules
           If violations:
           1. Reflect: Why did this fail? What was misunderstood?
           2. Read: contract + doctest + error message
           3. Fix: based on reflection + contract
           4. Verify again
```

The key insight from Reflexion: **Don't just fix—understand first.**

### Change 5: Contract Completeness Philosophy

Add guidance on writing complete (not just present) contracts.

```markdown
## Contract Completeness

A good contract is **complete** when it uniquely determines the implementation.

### Self-Test for Completeness

Ask: "Given only my @pre/@post and doctests, could someone else write
the exact same function?"

- **Yes** → Contract is complete ✓
- **No** → Add more constraints or examples

### Three-Way Consistency

Your contract, docstring, and code must all align:

```
     Code
    /    \
   /      \
@pre/@post ←→ Docstring/Doctests
```

If any two conflict, there's a bug. Write all three to be consistent.

### Example: Incomplete vs Complete

```python
# INCOMPLETE: Many functions satisfy this
@pre(lambda x: x >= 0)
def process(x: int) -> int:
    """Process the input."""
    ...

# COMPLETE: Only one function satisfies this
@pre(lambda x: x >= 0)
@post(lambda x, result: result == x * 2)
def double(x: int) -> int:
    """
    Double the input value.

    >>> double(0)
    0
    >>> double(5)
    10
    >>> double(100)
    200
    """
    ...  # Must be: return x * 2
```

Complete contracts make verification stronger AND recovery easier.
```

---

## Evidence

### From AlphaCodium Paper (2024)

| Approach | GPT-4 Accuracy (pass@5) |
|----------|------------------------|
| Single prompt | 19% |
| AlphaCodium flow (test-first) | 44% |

**Key mechanisms:**
1. Self-reflection before coding
2. AI-generated test cases before implementation
3. Iterative verification against tests

### From Pel Paper (2025)

**REPeL Self-Healing Mechanism:**
```
Error occurs → Capture context (docstring + code) → Helper Agent analyzes
→ Proposes fix based on docstring → Auto-correct → Continue
```

**Key insight:** Docstrings/contracts are not just documentation—they're the context that enables automatic error recovery.

### From Parsel Paper (2022/2023)

| Benchmark | Improvement |
|-----------|-------------|
| APPS competition | **+75%** pass rate vs AlphaCode/Codex |
| HumanEval pass@1 | 67% → **85%** with auto-generated tests |
| Robotic planning | **2x** more likely to be accurate |

**Key mechanisms:**
1. Decompose task into hierarchical function descriptions
2. Use tests to validate each component
3. Search across implementation combinations
4. Compose verified components

**Key insight:**
> "Like human programmers, start with high-level design, then implement each part gradually."

### From SWE-bench Paper (2023/2024)

| Model | Real GitHub Issues Solved |
|-------|--------------------------|
| Claude 2 (best) | **1.96%** |
| Other SOTA models | < 2% |

**What makes problems unsolvable:**
- Underspecified issue descriptions
- Multi-file coordination complexity
- Overly specific/unrelated tests
- Long context requirements

**What makes problems solvable:**
- Clear, specific descriptions
- Well-structured, relevant tests
- Reduced context complexity
- Good repository maintenance

**Key insight:**
> "Underspecified issue descriptions led to ambiguity on what the problem was and how it should be solved."

**Invar's response:** Contracts (@pre/@post) and doctests eliminate ambiguity. Every function has a clear specification.

### From Reflexion Paper (2023)

| Approach | HumanEval pass@1 |
|----------|-----------------|
| GPT-4 (direct) | 80% |
| GPT-4 + Reflexion | **91%** |

**How it works:**
```
Attempt → Fail → Verbal reflection ("Why did this fail?")
→ Store reflection in memory → Next attempt uses reflection → Success
```

**Key mechanisms:**
1. Verbal reflection on failures (not just error messages)
2. Episodic memory of reflections
3. Use past reflections to inform future attempts

**Key insight:**
> "Reflexion agents verbally reflect on task feedback signals, then maintain their reflective text in episodic memory to induce better decision-making."

**Invar's application:** When verification fails, don't just read the error—reflect on WHY it failed. This reflection makes the fix more likely to be correct.

### From Clover Paper (2023/2024)

| Metric | Result |
|--------|--------|
| Correct code acceptance | **87%** |
| Incorrect code acceptance | **0%** (zero false positives) |
| Flawed programs discovered | 6 bugs in existing MBPP-DFY-50 dataset |

**How it works:**
```
Three-Way Consistency Check:

     Code
    /    \
   /      \
Annotations ←→ Docstrings

Six directional checks:
- anno-sound: Code satisfies annotations (formal verification)
- anno-complete: Annotations can regenerate code (completeness)
- anno↔doc: Annotations and docstrings are semantically equivalent
- code↔doc: Code and docstrings are consistent
```

**Key mechanisms:**
1. **Completeness check** - Contracts must be non-trivial (can regenerate code)
2. **Zero false positive policy** - Better to reject valid code than accept invalid code
3. **Triangular consistency** - All three artifacts must align

**Key insight:**
> "To prevent annotations that are too trivial from being accepted, they test whether the annotations contain enough information to reconstruct functionally equivalent code."

**Invar's application:**
- Contracts (@pre/@post) + doctests + code form a triangle
- A "complete" contract uniquely determines the implementation
- The self-test: "Could someone regenerate my function from just the contract?"

### Combined Insights

| Research | Key Finding | Invar Application |
|----------|-------------|-------------------|
| AlphaCodium | Test-first improves accuracy 2x+ | Write contracts/doctests BEFORE code |
| Pel | Contracts enable auto-recovery | Good contracts = easy fixes |
| Parsel | Decomposition improves pass rate 75%+ | Break task into sub-functions first |
| SWE-bench | Underspecified = unsolvable | Contracts eliminate ambiguity |
| Reflexion | Verbal reflection improves pass@1 by 11% | Reflect on failures before fixing |
| Clover | Three-way consistency, 87% accept, 0% false positive | Complete contracts + triangular consistency |
| **Combined** | Structure + Completeness + Reflection | Design → Contract (complete) → Implement → Reflect → Verify |

### Alignment with Invar

| Research Concept | Invar Equivalent | Status |
|------------------|------------------|--------|
| Pre-processing (understand problem) | Intent step | ✓ Aligned |
| Generate tests first | Contract step | ⚠️ Not explicit |
| Hierarchical decomposition | Design step | ⚠️ Not explicit |
| Iterative verification | Verify step | ✓ Aligned |
| Contract as recovery context | Guard hints | ⚠️ Could emphasize |
| Clear specifications | Contracts + Doctests | ✓ Core strength |
| Verbal reflection on failures | Verify step | ⚠️ Not explicit |
| Contract completeness | @pre + @post + doctests | ⚠️ No quality metric |
| Three-way consistency | Code ↔ Contract ↔ Doctest | ✓ Implicit (new emphasis) |
| Zero false positive policy | Guard strictness | ✓ Stricter enforcement |

---

## Specific Changes

### 1. INVAR.md Updates

**A. Enhance Contracts section:**

```markdown
## Contracts (Test-First)

> "Writing tests is easier than writing code. Do this FIRST."

Before implementation, define:
1. **Preconditions** (@pre) - What inputs are invalid?
2. **Postconditions** (@post) - What does output guarantee?
3. **Edge Cases** - At least 3 doctests including:
   - Normal case
   - Boundary values (0, 1, max, min)
   - Edge conditions

[code example with 4+ doctests]
```

**B. Add Why Contracts Matter section:**

```markdown
## Why Contracts Matter

Contracts serve two purposes:
1. **Verification** - Catch violations before they become bugs
2. **Recovery** - When violations occur, contracts guide the fix

The time you spend writing contracts is never wasted:
- Good contracts → Faster verification
- Good contracts → Easier fixes when things go wrong

Research shows: Underspecified problems are unsolvable (SWE-bench).
Contracts eliminate ambiguity. Clear specs → Solvable problems.
```

### 2. ICIDIV Workflow Enhancement

```markdown
## Workflow: ICIDIV

**I**ntent → **C**ontract → **I**nspect → **D**esign → **I**mplement → **V**erify

□ Intent    — What are we trying to achieve? List potential edge cases.

□ Contract  — Write @pre/@post AND doctests BEFORE implementation.
              Include: normal case, boundaries, edge conditions.
              These will guide both verification AND future fixes.

□ Inspect   — Run: invar sig <file>, invar map --top 10

□ Design    — Decompose task into sub-functions:
              1. List functions (name + description)
              2. Identify dependencies
              3. Order: leaves first, then compose
              4. If file > 400 lines, plan extraction

□ Implement — For each function (in dependency order):
              Write code to pass the doctests you already wrote

□ Verify    — Run: invar guard && pytest --doctest-modules
              If violations:
              1. Reflect: Why did this fail?
              2. Read: contract + doctest + error
              3. Fix based on understanding
              4. Verify again
```

### 3. docs/VISION.md Addition

Add new section:

```markdown
## Research Foundation

Invar's methodology is validated by recent AI code generation research:

### AlphaCodium (2024)
Test-first approach improved GPT-4 accuracy from 19% to 44%.
> "Generating tests is easier than generating code."

This validates Invar's Contract-First principle.

### Pel (2025)
Contracts/docstrings serve as recovery context for auto-fixing errors.
> "When an error occurs, the Agent analyzes the discrepancy between
> code and expected usage (based on docstring) to propose corrections."

This extends Invar's philosophy: contracts are both verification AND recovery tools.

### Parsel (2022/2023)
Hierarchical decomposition improved pass rates by 75%+ on competition problems.
> "Like human programmers, start with high-level design, then implement
> each part gradually."

This validates Invar's Design step: decompose before implement.

### SWE-bench (2023/2024)
Real-world GitHub issues reveal that underspecified problems are unsolvable.
Best model (Claude 2) solved only 1.96% of 2,294 real issues.
> "Underspecified issue descriptions led to ambiguity on what the problem
> was and how it should be solved."

This validates Invar's core insight: **Contracts eliminate ambiguity.**
- @pre/@post make expectations explicit
- Doctests provide concrete examples
- Clear specs → Solvable problems

### Reflexion (2023)
Verbal reflection on failures improved HumanEval pass@1 from 80% to 91%.
> "Reflexion agents verbally reflect on task feedback signals, then maintain
> their reflective text in episodic memory to induce better decision-making."

This enhances Invar's Verify step: **Don't just fix—understand why it failed first.**

### Clover (2023/2024)
Three-way consistency checking achieves 87% acceptance while maintaining zero false positives.
> "To prevent annotations that are too trivial from being accepted, they test whether
> the annotations contain enough information to reconstruct functionally equivalent code."

This introduces **contract completeness**: A good contract uniquely determines the implementation.

### Unified Insight

The research converges on a single principle:

**Structure before code. Completeness in contracts. Reflection before fix.**

1. **Design** - Decompose task into sub-functions
2. **Contract** - Write COMPLETE tests for each function (eliminates ambiguity)
3. **Implement** - Write code to pass the tests
4. **Verify** - If failure, reflect first, then fix

Time spent on structure pays dividends at every stage:
- During implementation → Clearer targets (complete contracts = one valid solution)
- During verification → Catch bugs early (three-way consistency)
- During recovery → Reflection + contracts guide fixes
- For solvability → Clear, complete specs make problems tractable
```

### 4. Optional: Guard Output Enhancement

Current:
```
ERROR: missing_contract at calculate() in math.py:15
  Hint: Add @pre/@post decorator
```

Enhanced:
```
ERROR: missing_contract at calculate() in math.py:15

  Hint: Add @pre/@post decorator. Example:

    @pre(lambda x, y: x > 0 and y > 0)
    @post(lambda result: result > 0)
    def calculate(x: int, y: int) -> int:
        """
        >>> calculate(2, 3)
        5
        """

  Good contracts make future violations easy to fix.
```

---

## Impact Analysis

- [x] INVAR.md sections affected
  - Contracts section: Add test-first emphasis
  - New section: Why Contracts Matter
  - Workflow section: Enhanced Design + Contract + Verify steps
- [x] CLAUDE.md updates needed
  - Development Workflow: Mirror INVAR.md changes
- [x] Template files to update
  - src/invar/templates/INVAR.md
  - src/invar/templates/CLAUDE.md.template
- [ ] Code changes required (optional)
  - Guard hints could be enhanced with more context
  - Optional rule: minimum doctest count
  - Optional rule: contract completeness hint
- [x] Other documentation
  - docs/VISION.md: Add Research Foundation section with 6 papers
  - GitHub Pages: Update with decomposition + reflection + completeness concepts

---

## Alternatives Considered

### 1. Add Cases as Separate Step (ICICDIV - 7 steps)

```
Intent → Contract → Inspect → Cases → Design → Implement → Verify
```

**Rejected because:**
- Adds cognitive overhead (7 vs 6 steps)
- Cases are naturally part of Contract thinking
- More steps != better (complexity cost)

### 2. Require Minimum Doctest Count in Guard

Add rule: `missing_edge_cases` - Warn if < 3 doctests.

**Deferred because:**
- Mechanical counting doesn't ensure quality
- Could add as optional rule later
- Start with documentation/process change first

### 3. Add Self-Reflection Step

AlphaCodium has explicit self-reflection. Add to Invar?

**Rejected because:**
- Intent step already covers this conceptually
- Adding more steps increases friction
- Can emphasize "list edge cases" within Intent instead

### 4. Implement Auto-Fix Like Pel's REPeL

Pel automatically fixes errors using docstring context.

**Deferred because:**
- Requires significant tooling changes
- Agent already does this manually via Guard hints
- Document the philosophy first, tooling can follow

### 5. Add Decomposition as Separate Step

Make decomposition its own step before Design.

**Rejected because:**
- Decomposition IS design—they shouldn't be separated
- Current ICIDIV structure is sufficient
- Enhanced Design step description achieves the goal

### 6. Add Reflection as Separate Step

Make reflection its own step after Verify.

**Rejected because:**
- Reflection is part of the Verify loop, not a separate step
- Only needed when verification fails
- Enhancing Verify step description is sufficient

---

## Approval

**For Layer 1 changes only:**

- [ ] Human has reviewed this proposal
- [ ] Human explicitly approves: _____________ (signature/date)

---

## Implementation Checklist

After approval:

- [ ] Update INVAR.md
  - [ ] Enhance Contracts section with test-first emphasis
  - [ ] Add "Why Contracts Matter" section (dual purpose + solvability)
  - [ ] Add "Contract Completeness" section
  - [ ] Add "at least 3 doctests" guideline
  - [ ] Enhance Design step with decomposition guidance
  - [ ] Enhance Verify step with reflection guidance
  - [ ] Update ICIDIV description with all changes
- [ ] Update version number (v3.20)
- [ ] Sync templates
  - [ ] src/invar/templates/INVAR.md
  - [ ] src/invar/templates/CLAUDE.md.template
- [ ] Update related documentation
  - [ ] CLAUDE.md
  - [ ] docs/VISION.md (add Research Foundation section with 6 papers)
  - [ ] docs/index.html (GitHub Pages)
- [ ] Optional: Enhance Guard hints
  - [ ] Contract completeness self-test hint
- [ ] Add to version history in context.md
- [ ] Commit with clear message
- [ ] Release new version

---

## Summary

### Core Changes

| Change | Source | ICIDIV Step | Impact |
|--------|--------|-------------|--------|
| Test-First emphasis | AlphaCodium | Contract | Write contracts/doctests BEFORE code |
| Contract-as-Recovery | Pel | Contract + Verify | Contracts guide fixes, not just verification |
| Hierarchical Decomposition | Parsel | Design | Break task into sub-functions first |
| Specs = Solvability | SWE-bench | Contract | Clear contracts make problems tractable |
| Reflective Verification | Reflexion | Verify | Reflect on failures before fixing |
| Contract Completeness | Clover | Contract | Complete contracts uniquely determine implementation |
| At least 3 doctests | Combined | Contract | Cover normal + boundaries + edges |

### Unified Philosophy

```
Structure before code. Completeness in contracts. Reflection before fix.

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Design: Break task into functions                         │
│      ↓                                                      │
│   Contract: Write COMPLETE tests for each function          │
│      ↓         (complete = uniquely determines impl)        │
│      ↓         (eliminates ambiguity → makes problem        │
│      ↓          solvable)                                   │
│      ↓                                                      │
│   Implement: Write code to pass tests (leaves first)        │
│      ↓                                                      │
│   Verify: If fail → Reflect (why?) → Fix → Verify again     │
│                                                             │
│   Three-way consistency: Code ↔ @pre/@post ↔ Doctests       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Research shows this approach:
- Improves accuracy 2x+ (AlphaCodium)
- Improves pass rates 75%+ (Parsel)
- Enables auto-recovery (Pel)
- Makes problems solvable (SWE-bench: clear specs vs 1.96% solve rate)
- Improves fix success (Reflexion: 80% → 91% with reflection)
- 87% accept, 0% false positive (Clover: complete contracts + consistency)
```

### Cost vs Benefit

**Cost:** Minimal (documentation changes, no new workflow steps)

**Benefit:**
- Validates Invar philosophy with research backing (6 papers)
- Makes "Design" step more actionable (decomposition)
- Makes "Contract" step's dual purpose clearer (verification + recovery)
- Introduces contract completeness as quality metric
- Makes "Verify" step more effective with reflection
- Explains WHY specs matter (solvability, not just verification)
- Provides concrete examples and guidance
