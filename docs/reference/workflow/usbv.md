# USBV: The Four-Phase Development Workflow

> **"Inspect before Contract. Depth varies naturally. Iterate when needed."**

## Quick Reference

```
U - Understand : Intent, Inspect (invar sig/map), Constraints
S - Specify    : @pre/@post contracts, Design decomposition, Doctests
B - Build      : Implement leaves first, Compose
V - Validate   : invar guard. Review Gate if triggered. Reflect → iterate
```

**Key insight:** Inspect comes BEFORE Contract. Depth varies based on resistance encountered.

## Phase 1: UNDERSTAND

> **"Know what and why before specifying how."**

### Activities

1. **Intent** - What does the task require?
   - New function, modification, or bug fix?
   - Is this Core or Shell?
   - What is the expected behavior?

2. **Inspect** - What exists in the codebase?
   ```bash
   invar sig <file>      # See existing contracts
   invar map --top 10    # Find entry points
   ```
   - Understand patterns used in the codebase
   - Find similar functionality
   - Identify integration points

3. **Constraints** - Edge cases? Limits?
   - Empty inputs, boundary values
   - Error conditions
   - Performance requirements

### Example

```
Task: "Add function to calculate average of a list"

UNDERSTAND:
- Intent: New function returning average of numbers
- Inspect: $ invar sig src/core/calc.py
  - Found existing `sum_values()` helper
  - Pattern: functions return primitives, not Result
- Constraints:
  - Empty list → error (not None)
  - Single element → return that element
  - Very large numbers → use float for precision
```

### Exit Criteria

- Can articulate what the function should do
- Know where it fits in codebase
- Identified main edge cases

## Phase 2: SPECIFY

> **"Define complete contracts and design before implementing."**

### Activities

1. **Contract** - Write @pre/@post that uniquely determine behavior
   ```python
   @pre(lambda items: len(items) > 0)
   @post(lambda result: min(items) <= result <= max(items))
   def average(items: list[float]) -> float:
       ...
   ```

2. **Design** - Decompose into sub-functions
   - List functions (name + purpose)
   - Identify dependencies
   - Order: leaves first

3. **Test Cases** - Doctests covering key cases
   ```python
   """
   >>> average([1.0, 2.0, 3.0])
   2.0
   >>> average([5.0])
   5.0
   >>> average([])
   Traceback (most recent call last):
       ...
   deal.PreContractError: ...
   """
   ```

### Self-Test for Completeness

Ask: **"Can these contracts regenerate the function?"**

If someone sees only @pre, @post, and doctests - can they write the exact same implementation?

### Contract Checklist

- [ ] `@pre` excludes all invalid inputs
- [ ] `@post` verifies all required properties
- [ ] Doctests cover: normal, edge, error cases
- [ ] Three-way consistency: code ↔ contracts ↔ doctests

See [Contract Completeness](../contracts/contract-complete.md) for details.

### Exit Criteria

- Contract is complete (could someone else implement from it?)
- Sub-function decomposition clear
- Doctests cover key cases

## Phase 3: BUILD

> **"Write code to pass your doctests."**

### Activities

1. **Implement Leaves** - Smallest units first (no dependencies)
2. **Compose** - Combine into complete feature
3. **Incremental Verify** - Run doctests after each function

### The Contract is the Specification

At this point, you have complete contracts and doctests. Implementation is filling in the body:

```python
@pre(lambda items: len(items) > 0)
@post(lambda result: min(items) <= result <= max(items))
def average(items: list[float]) -> float:
    """
    >>> average([1.0, 2.0, 3.0])
    2.0
    """
    return sum(items) / len(items)  # ← Implementation
```

### Implementation Guidelines

1. **Stay within contracts** - Don't add behavior not specified
2. **Follow the design** - Implement in planned order
3. **Keep it simple** - The contract tells you what's needed
4. **Run doctests frequently** - Catch issues early

### Exit Criteria

- All doctests pass
- No obvious code smells
- Follows existing patterns

## Phase 4: VALIDATE

> **"Confirm correctness. Iterate if needed."**

### Run Smart Guard

```bash
invar guard           # Full verification
invar guard --changed # Only modified files
```

### Verification Pipeline

```
invar guard
├─ Static analysis (rules)
├─ Doctests (examples)
├─ CrossHair (symbolic proof)
└─ Hypothesis (property testing)
```

### Review Gate (DX-31)

If guard outputs `review_suggested` warning, invoke independent review:

```bash
# Guard detected conditions requiring review
WARNING: review_suggested - Consider independent /review sub-agent

# Invoke independent reviewer
/review
```

**Trigger conditions:**
- Escape hatches >= 3 (`@invar:allow` markers)
- Contract coverage < 50% in Core files
- Security-sensitive paths detected

**Why?** Independent review catches issues that automated verification cannot:
- Architectural concerns
- Escape hatch justification validity
- Security implications

After review, address findings and re-run guard.

### Iteration Triggers

When validation fails, return to the appropriate phase:

| Issue Found | Return To |
|-------------|-----------|
| Logic error in code | BUILD |
| Missing edge case | SPECIFY (add doctest) |
| Contract incomplete | SPECIFY (strengthen @pre/@post) |
| Misunderstood requirement | UNDERSTAND |
| Review finds architectural issue | UNDERSTAND (re-examine design) |
| Review finds unjustified escape | SPECIFY (remove or justify) |

### Reflective Process

**Don't just fix symptoms.** Follow the reflective process:

1. **Reflect:** Why did it fail?
   - Is the contract wrong?
   - Is the implementation wrong?
   - Is the design flawed?

2. **Return:** Go back to appropriate phase
   - Not just "fix and retry"
   - Address root cause

3. **Validate:** Confirm the fix
   - Run `invar guard` again
   - Check for regressions

### Exit Criteria

- Guard passes (0 errors)
- Warnings addressed in touched files
- Review Gate satisfied (if triggered)
- Integration works (if applicable)

## Depth Adjustment Signals

The framework is self-balancing. These signals indicate where to focus:

| Signal | Meaning | Action |
|--------|---------|--------|
| Contract hard to write | UNDERSTAND incomplete | Go deeper in Inspect |
| Don't know where code goes | UNDERSTAND incomplete | More Inspect |
| Doctests keep failing | SPECIFY incomplete | Refine contract |
| Guard finds contract issues | SPECIFY incomplete | Strengthen @pre/@post |
| Implementation unclear | SPECIFY incomplete | Better decomposition |
| Integration fails | BUILD incomplete | Check interfaces |
| Review Gate triggered | Quality risk detected | Invoke /review |

**Key Insight:** Don't classify tasks. Notice where resistance is and adjust.

## Task Type Emphasis

Same 4 phases, different depth:

| Task Type | U | S | B | V |
|-----------|---|---|---|---|
| Pure algorithm | Shallow | **Deep** | Normal | **Deep** |
| Feature addition | **Deep** | Normal | Normal | Normal |
| Bug fix | **Deep** | Shallow | Shallow | **Deep** |
| Refactoring | Normal | Shallow | **Deep** | Normal |

## Anti-Patterns

### 1. Contract Before Inspect

```
BAD:  Intent → Contract → ... (reinvent the wheel)
GOOD: Intent → Inspect → Contract → ...
```

Contracts should be informed by existing code patterns.

### 2. Fix Symptoms

```
BAD:  Validate fails → Change code until it passes
GOOD: Validate fails → Reflect (why?) → Return to phase → Fix root cause
```

Symptom fixes create fragile code.

### 3. Batch Verification

```
BAD:  Implement everything → Validate once at end
GOOD: Implement function → Validate → Next function → Validate
```

Small iterations catch issues early.

## Complete Example

```
Task: Add function to find the most common element

1. UNDERSTAND
   - Intent: Find mode (most frequent element) in a list
   - Inspect: $ invar sig src/core/stats.py
     - No existing mode function
     - Pattern: similar to median()
   - Constraints: empty list error, tie returns any, single element

2. SPECIFY
   @pre(lambda items: len(items) > 0)
   @post(lambda result: result in items)
   @post(lambda result: items.count(result) >= items.count(x) for all x)

   Doctests:
   >>> mode([1, 2, 2, 3])
   2
   >>> mode([1])
   1

   Design:
   - count_occurrences(items) → dict[T, int]  # Helper (leaf)
   - mode(items) → T                           # Main

3. BUILD
   def mode(items):
       counts = count_occurrences(items)
       return max(counts, key=counts.get)

4. VALIDATE
   $ invar guard --changed
   ✓ Static: passed
   ✓ Doctests: 3/3 passed
   ✓ CrossHair: proved
   ✓ Hypothesis: 100 examples passed
```

## See Also

- [Session Start](./session-start.md) - Check-In protocol
- [Contract Completeness](../contracts/contract-complete.md) - Writing complete contracts
- [Pre/Post Contracts](../contracts/pre-post.md) - Contract syntax
- [Smart Verification Routing](../verification/smart-routing.md) - How verification works
