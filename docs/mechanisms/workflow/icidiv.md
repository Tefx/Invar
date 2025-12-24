# ICIDIV: The Six-Step Development Workflow

> **"Contract before Implement. Verify after every change. No exceptions."**

## Quick Reference

```
I - Intent    : Understand task, classify Core/Shell, list edge cases
C - Contract  : Write @pre/@post + doctests BEFORE code
I - Inspect   : invar sig for contracts, invar map for entry points
D - Design    : Decompose into sub-functions, leaves first
I - Implement : Write code to pass your doctests
V - Verify    : invar guard. If fail: reflect → fix → verify
```

**Required order.** Each step builds on the previous.

## Step 1: Intent

> **"What? Core or Shell? Edge cases?"**

### Questions to Answer

1. **What does the task require?**
   - New function, modification, or bug fix?
   - What is the expected behavior?

2. **Is this Core or Shell?**
   - **Core:** Pure logic, calculations, transformations
   - **Shell:** I/O, files, network, CLI

3. **What are the edge cases?**
   - Empty inputs, boundary values
   - Error conditions
   - Unusual but valid scenarios

### Example

```
Task: "Add function to calculate average of a list"

Intent:
- What: New function returning average of numbers
- Where: Core (pure calculation, no I/O)
- Edge cases:
  - Empty list → error or None?
  - Single element → return that element
  - All same values → return that value
  - Very large numbers → precision?
```

### Output

Clear statement of:
- What needs to be done
- Classification (Core/Shell)
- Known edge cases

## Step 2: Contract

> **"Write COMPLETE @pre/@post + doctests BEFORE code."**

### This is the Critical Step

Contracts come BEFORE implementation. They are the specification.

### Write Contracts First

```python
from deal import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: min(items) <= result <= max(items))
def average(items: list[float]) -> float:
    """
    Calculate arithmetic mean of a list.

    >>> average([1.0, 2.0, 3.0])
    2.0
    >>> average([5.0])
    5.0
    >>> average([])
    Traceback (most recent call last):
        ...
    deal.PreContractError: ...
    """
    ...  # Implementation comes later
```

### Self-Test for Completeness

Ask: **"Can these contracts regenerate the function?"**

If someone sees only:
- `@pre(lambda items: len(items) > 0)`
- `@post(lambda result: ...)`
- Doctests

Can they write the exact same implementation?

### Contract Checklist

- [ ] `@pre` excludes all invalid inputs
- [ ] `@post` verifies all required properties
- [ ] Doctests cover: normal, edge, error cases
- [ ] Three-way consistency: code ↔ contracts ↔ doctests

See [Contract Completeness](../contracts/contract-complete.md) for details.

## Step 3: Inspect

> **"Understand before modifying."**

### Use Invar Perception Tools

```bash
# See existing contracts
invar sig <file>

# See specific function
invar sig <file>::<function>

# Find entry points
invar map --top 10
```

### Why Inspect?

1. **Avoid reinventing** existing functionality
2. **Understand patterns** used in the codebase
3. **Find integration points** for new code
4. **Preserve consistency** with existing style

### Example Session

```bash
$ invar sig src/myapp/core/calc.py
calc.py:
  average(items: list[float]) -> float
    @pre: len(items) > 0
    @post: min(items) <= result <= max(items)

  median(items: list[float]) -> float
    @pre: len(items) > 0
    @post: result in sorted(items) or ...
```

**Insight:** "There's already an `average` function. Do I need another?"

## Step 4: Design

> **"Decompose into sub-functions. Leaves first."**

### Decomposition Principle

Complex tasks should be broken into smaller functions:

```
main_task()
├── subtask_1()
│   ├── helper_a()  ← Implement first (leaf)
│   └── helper_b()  ← Implement first (leaf)
└── subtask_2()
    └── helper_c()  ← Implement first (leaf)
```

### Leaves First

Implement helper functions before the functions that use them:
1. No dependencies = easier to test
2. Build up = fewer integration issues
3. Each step is verifiable

### Example Design

```
Task: Parse and validate user configuration

Design:
1. validate_field(name, value) → bool
   - Leaf function, no dependencies
2. parse_json(content: str) → dict
   - Uses standard library only
3. validate_config(data: dict) → Result[Config, list[str]]
   - Uses validate_field
4. load_config(path: Path) → Result[Config, str]
   - Shell function, uses parse_json + validate_config

Implementation order: 1 → 2 → 3 → 4
```

### Design Output

- List of functions with names and purposes
- Dependencies between functions
- Implementation order

## Step 5: Implement

> **"Write code to pass your doctests."**

### The Contract is the Specification

At this point, you have:
- Complete contracts (`@pre`, `@post`)
- Doctests with expected behavior
- Design with sub-functions

Implementation is filling in the body:

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

## Step 6: Verify

> **"invar guard. If fail: reflect → fix → verify."**

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

### When Verification Fails

**Don't just fix symptoms.** Follow the reflective process:

1. **Reflect:** Why did it fail?
   - Is the contract wrong?
   - Is the implementation wrong?
   - Is the design flawed?

2. **Fix:** Address root cause
   - Not just the symptom
   - Consider related code

3. **Verify:** Confirm the fix
   - Run `invar guard` again
   - Check for regressions

### Example Failure

```
ERROR: PostContractError in average()
  Counterexample: items=[-1.0, -2.0, -3.0]
  result=-2.0 but min(items)=-3.0, max(items)=-1.0
  Expected: -3.0 <= -2.0 <= -1.0
```

**Reflect:** The postcondition is wrong for negative numbers!

**Fix:** The postcondition `min(items) <= result <= max(items)` is actually correct. The average of `[-1, -2, -3]` is `-2`, which is between `-3` and `-1`. Wait... the error says `-3.0 <= -2.0 <= -1.0` which is `True`. Let me re-read...

Actually, this would pass. A real failure might be if we had a bug like:
```python
return sum(items)  # Forgot to divide!
```

**Verify:** Run `invar guard` again after fixing.

## Anti-Patterns

### 1. Code Before Contract

```
BAD:  Intent → Implement → "Add contracts later"
GOOD: Intent → Contract → ... → Implement
```

Contracts written after code are documentation, not specification.

### 2. Skip Inspect

```
BAD:  Intent → Contract → Implement (reinvent the wheel)
GOOD: Intent → Contract → Inspect → ...
```

You may duplicate existing functionality.

### 3. Fix Symptoms

```
BAD:  Verify fails → Change code until it passes
GOOD: Verify fails → Reflect (why?) → Fix root cause → Verify
```

Symptom fixes create fragile code.

### 4. Batch Verification

```
BAD:  Implement everything → Verify once at end
GOOD: Implement function → Verify → Next function → Verify
```

Small iterations catch issues early.

## Complete Example

```
Task: Add function to find the most common element

1. INTENT
   - What: Find mode (most frequent element) in a list
   - Where: Core (pure logic)
   - Edge cases: empty list, tie, single element

2. CONTRACT
   @pre(lambda items: len(items) > 0)
   @post(lambda result: result in items)
   @post(lambda result: items.count(result) >= items.count(x) for all x)

   Doctests:
   >>> mode([1, 2, 2, 3])
   2
   >>> mode([1])
   1
   >>> mode([1, 1, 2, 2])  # Tie - return any
   1  # or 2

3. INSPECT
   $ invar sig src/core/stats.py
   - No existing mode function
   - Pattern: similar to median()

4. DESIGN
   - count_occurrences(items) → dict[T, int]  # Helper
   - mode(items) → T                           # Main

5. IMPLEMENT
   def mode(items):
       counts = count_occurrences(items)
       return max(counts, key=counts.get)

6. VERIFY
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
