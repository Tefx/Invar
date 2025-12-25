# Language-Inspired Enhancements Proposal

**Date:** 2024-12-21
**Status:** Draft
**Author:** AI Assistant

## Summary

This proposal documents insights from three programming languages and three verification/validation tools, exploring how they can inform Invar's evolution:

1. **Idris** — Dependent types, type-driven development
2. **Dafny** — Verification-aware programming, SMT integration
3. **Move/Sui** — Resource types, linear types, abilities
4. **Hypothesis** — Property-based testing, automatic test generation
5. **CrossHair** — Symbolic execution, SMT-based verification
6. **Instructor** — LLM structured outputs, validation-driven self-correction

These tools share a common philosophy: **make incorrect code impossible to write, rather than catching errors at runtime**.

Notably, Instructor validates Invar's core approach by demonstrating that "validation errors with clear error messages" enable AI self-correction — exactly what Invar's Guard provides.

### Core Value Update

This research reveals a powerful verification pyramid available to Invar:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Invar Verification Pyramid                   │
│                                                                 │
│                         ┌─────────┐                             │
│                         │CrossHair│  Symbolic Proof             │
│                         │ (prove) │  "Holds for ALL inputs"     │
│                         └────┬────┘                             │
│                      ┌───────┴───────┐                          │
│                      │   Hypothesis  │  Property Testing        │
│                      │  (fuzz 100+)  │  "Tested 100+ inputs"    │
│                      └───────┬───────┘                          │
│                 ┌────────────┴────────────┐                     │
│                 │    deal @pre/@post      │  Runtime Checking   │
│                 │    (runtime check)      │  "This call passed" │
│                 └────────────┬────────────┘                     │
│            ┌─────────────────┴─────────────────┐                │
│            │          invar guard              │  Static Analysis│
│            │       (static analysis)           │  "Contracts OK" │
│            └───────────────────────────────────┘                │
│                                                                 │
│   Bottom → Top: Cost increases, Assurance strengthens           │
└─────────────────────────────────────────────────────────────────┘
```

Since Invar uses `deal` which supports both Hypothesis and CrossHair, we can leverage the full pyramid.

---

## Table of Contents

1. [Idris Analysis](#1-idris-analysis)
2. [Dafny Analysis](#2-dafny-analysis)
3. [Move/Sui Analysis](#3-movesui-analysis)
4. [Hypothesis Analysis](#4-hypothesis-analysis)
5. [CrossHair Analysis](#5-crosshair-analysis)
6. [Instructor Analysis](#6-instructor-analysis)
7. [Synthesis: Unified Insights](#7-synthesis-unified-insights)
8. [Proposed Enhancements](#8-proposed-enhancements)
9. [Evolution Roadmap](#9-evolution-roadmap)
10. [Implementation Priority](#10-implementation-priority)
11. [Benchmarking Strategy](#11-benchmarking-strategy)
12. [Tier 0 Development Plan](#12-tier-0-development-plan)
13. [Multi-Layer Purity Detection](#13-multi-layer-purity-detection)
14. [Tier 1 Development Plan](#14-tier-1-development-plan)

---

## 1. Idris Analysis

**Source:** https://www.idris-lang.org/
**Documentation:** https://idris2.readthedocs.io/

### 1.1 Core Philosophy

> "Types are tools for constructing programs... the more expressive the type is that we give up front, the more confidence we can have that the resulting program will be correct."

Idris practices **Type-Driven Development (TDD)** — write the type first, let the compiler guide implementation.

### 1.2 Key Features

#### Dependent Types

Types can depend on values. The classic example is length-indexed vectors:

```idris
data Vect : Nat -> Type -> Type where
   Nil  : Vect Z a
   (::) : a -> Vect k a -> Vect (S k) a
```

Operations preserve length relationships:

```idris
(++) : Vect n a -> Vect m a -> Vect (n + m) a
```

The type system guarantees that concatenating vectors of length n and m produces a vector of length n+m. No runtime check needed.

#### First-Class Types

Types can be computed and manipulated like any other value:

```idris
isSingleton : Bool -> Type
isSingleton True = Nat
isSingleton False = List Nat
```

This enables conditional types based on runtime values.

#### Bounded Indexing (Fin)

`Fin n` represents valid indices for a collection of size n:

```idris
index : Fin n -> Vect n a -> a
```

The type system ensures index validity — out-of-bounds access is a compile error, not a runtime exception.

#### Totality Checking

Idris can verify that functions:
- Handle all possible inputs (coverage)
- Always terminate (productivity)

This eliminates entire classes of bugs at compile time.

### 1.3 Insights for Invar

| Idris Feature | Invar Insight |
|---------------|---------------|
| Types as specifications | Contracts can evolve toward types |
| Type-driven development | Aligns with Contract-First (Law 2) |
| Fin n (bounded index) | Index contracts with static verification |
| First-class types | First-class contracts (composable, inheritable) |
| Totality checking | Coverage analysis for edge cases |
| Compile-time proofs | Subset of contracts can be statically verified |

#### Concrete Ideas

1. **Refinement Types as Contract Evolution**

```python
# Current Invar
@pre(lambda x: x > 0)
def sqrt(x: float) -> float: ...

# Future: Refinement type carries the contract
PositiveFloat = Annotated[float, Gt(0)]

def sqrt(x: PositiveFloat) -> float: ...  # @pre implicit
```

2. **Contract Composition (First-Class)**

```python
# Define reusable contract
NonEmpty = Contract(lambda x: len(x) > 0, "must be non-empty")
AllPositive = Contract(lambda x: all(i > 0 for i in x), "all elements positive")

# Compose contracts
@pre(NonEmpty & AllPositive)
def geometric_mean(items: list[float]) -> float: ...
```

3. **Bounded Index Types**

```python
# Type that guarantees valid index
ValidIndex = Annotated[int, Lambda(lambda i, arr: 0 <= i < len(arr))]

def get_item(arr: list[T], i: ValidIndex[arr]) -> T:
    return arr[i]  # No bounds check needed - type guarantees it
```

---

## 2. Dafny Analysis

**Source:** https://dafny.org/
**GitHub:** https://github.com/dafny-lang/dafny

### 2.1 Core Philosophy

> "Dafny makes rigorous verification an integral part of development, thus reducing costly late-stage bugs that may be missed by testing."

Dafny is a **verification-aware programming language** that uses an SMT solver (Z3) to automatically prove correctness.

### 2.2 Key Features

#### Pre/Post Conditions (requires/ensures)

```dafny
method Abs(x: int) returns (y: int)
  ensures y >= 0
  ensures x >= 0 ==> y == x
  ensures x < 0 ==> y == -x
{
  if x < 0 { y := -x; } else { y := x; }
}
```

This is exactly analogous to Invar's @pre/@post.

#### Loop Invariants

```dafny
method Sum(a: array<int>) returns (s: int)
  ensures s == sum(a[..])
{
  s := 0;
  var i := 0;
  while i < a.Length
    invariant 0 <= i <= a.Length
    invariant s == sum(a[..i])
  {
    s := s + a[i];
    i := i + 1;
  }
}
```

Loop invariants specify what must be true at every iteration. The verifier proves:
1. Invariant holds on loop entry
2. If invariant holds before iteration, it holds after
3. Invariant + loop exit condition implies postcondition

#### Termination Conditions

```dafny
function Fib(n: nat): nat
  decreases n  // Proves termination
{
  if n < 2 then n else Fib(n-2) + Fib(n-1)
}
```

The `decreases` clause specifies a value that decreases each recursive call, proving termination.

#### Ghost Code

```dafny
ghost var history: seq<int>  // Only for specification, not runtime
```

Ghost variables and functions exist only for verification — they're erased at compilation. This separates specification from implementation.

#### Automatic Verification with Z3

Dafny automatically discharges proof obligations using the Z3 SMT solver. Developers write specifications; the prover verifies them.

#### Multi-Language Compilation

Verified Dafny code compiles to:
- C#
- Java
- JavaScript
- Go
- Python

This proves that formal verification is compatible with practical deployment.

#### IDE Integration (LSP)

Real-time verification feedback in VS Code:
- Verification successes/failures shown as you type
- Counterexamples for failed proofs
- Instant feedback loop

### 2.3 Insights for Invar

| Dafny Feature | Invar Insight |
|---------------|---------------|
| requires/ensures | Already have @pre/@post |
| Loop invariants | **New: @invariant decorator** |
| Termination | Optional @terminates contract |
| Ghost code | Specification-only assertions |
| Z3 integration | Long-term: SMT verification |
| IDE integration | Guard as LSP server |
| Multi-target compilation | Verified Python remains Python |

#### Concrete Ideas

1. **@invariant Decorator for Loops**

```python
from invar import invariant

def sum_array(items: list[int]) -> int:
    """
    >>> sum_array([1, 2, 3])
    6
    """
    total = 0
    for i, item in enumerate(items):
        invariant(0 <= i <= len(items))
        invariant(total == sum(items[:i]))
        total += item
    return total
```

Or as a context manager:

```python
def sum_array(items: list[int]) -> int:
    total = 0
    with invariant(lambda: total >= 0):
        for item in items:
            if item > 0:
                total += item
    return total
```

2. **@terminates Contract**

```python
@terminates(variant=lambda n: n)  # n decreases each call
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

3. **Ghost Assertions (Specification-Only)**

```python
@ghost  # Only checked in verification, not at runtime
def sum_property(items: list[int], result: int) -> bool:
    return result == sum(items)

@post(ghost=sum_property)  # Expensive check only in verification
def optimized_sum(items: list[int]) -> int:
    ...
```

4. **Guard LSP Server**

```
Editor (VS Code/Cursor) ←→ Guard LSP ←→ Real-time contract checking
                              ↓
                    Inline diagnostics:
                    - Missing contracts
                    - Incomplete contracts
                    - Potential violations
```

---

## 3. Move/Sui Analysis

**Source:** https://docs.sui.io/concepts/sui-move-concepts
**Move Book:** https://move-book.com/

### 3.1 Core Philosophy

Move was designed for safe smart contract development where bugs can cost millions. It uses **linear types** and an **abilities system** to prevent entire classes of vulnerabilities.

> "Move's type system prevents resource mismanagement through language-level constraints rather than relying on developer discipline."

### 3.2 Key Features

#### The Abilities System

Every type in Move has a set of **abilities** that control what operations are allowed:

| Ability | Meaning |
|---------|---------|
| `copy` | Value can be duplicated |
| `drop` | Value can be discarded without explicit handling |
| `key` | Value can be used as a key in global storage |
| `store` | Value can be stored in global storage |

By default, custom types have NO abilities — they must be explicitly granted:

```move
struct Coin has store {
    value: u64
}
// Coin can be stored but NOT copied or dropped
// Must be explicitly transferred or destroyed
```

This prevents:
- **Double-spending**: Can't copy a coin
- **Lost assets**: Can't accidentally drop a coin
- **Unauthorized access**: Can't use without proper key

#### Linear Types (Resources)

A **linear type** must be used exactly once:
- Cannot be copied (no accidental duplication)
- Cannot be dropped (no accidental loss)
- Must be explicitly consumed

```move
struct Ticket {
    event_id: u64
}
// Ticket has no abilities - it's a linear type
// Must be explicitly used (entered) or destroyed (refunded)
```

#### Ownership and Scope

Move enforces strict ownership:

```move
let ticket = create_ticket();
transfer(ticket);  // Ownership transferred
// ticket no longer accessible - compiler error if used
```

#### Object Model (Sui)

Every on-chain object has a unique identifier (UID):

```move
struct NFT has key {
    id: UID,  // Required first field
    name: String,
}
```

The bytecode verifier ensures:
- New objects always get fresh UIDs
- UIDs are never reused
- Object identity is preserved

#### Bytecode Verification

Before deployment, Move bytecode is verified:
- Type safety
- Resource safety
- Memory safety
- Capability constraints

This is **mandatory** — unverified code cannot deploy.

### 3.3 Insights for Invar

| Move Feature | Invar Insight |
|--------------|---------------|
| copy ability | **@must_not_copy** for sensitive objects |
| drop ability | **@must_use** / **@must_close** |
| key ability | Access control contracts |
| store ability | Serialization contracts |
| Linear types | Ownership/transfer contracts |
| Object UID | Entity identity contracts |
| Bytecode verification | Guard = mandatory pre-commit |

#### Concrete Ideas

1. **@must_use Decorator**

Inspired by Move's lack of `drop` ability:

```python
@must_use("Result may contain error - handle it")
def parse_config(path: str) -> Result[Config, ParseError]:
    ...

# Usage
result = parse_config("config.yaml")  # Must be used
# Ignoring result triggers Guard warning
```

2. **@must_close Decorator**

For resources that require cleanup:

```python
@must_close
class DatabaseConnection:
    def query(self, sql: str) -> list: ...
    def close(self) -> None: ...

# Guard warns if connection might not be closed
conn = DatabaseConnection()
data = conn.query("SELECT *")
# Warning: DatabaseConnection may not be closed
```

3. **@transfer Decorator**

For ownership semantics:

```python
@transfer  # Marks ownership transfer
def send_payment(payment: Payment, recipient: Account) -> Receipt:
    """After this call, payment is consumed and cannot be reused."""
    ...

# Usage
payment = create_payment(100)
receipt = send_payment(payment, alice)
send_payment(payment, bob)  # Error: payment already transferred
```

4. **Abilities as Contracts**

```python
@abilities(copy=False, drop=False)
class CryptoKey:
    """Cryptographic key that must be explicitly destroyed."""
    def __init__(self, bits: bytes): ...
    def destroy(self) -> None: ...

# Guard enforces:
# - No assignment to multiple variables
# - Must call destroy() before scope exit
```

5. **Entity Identity Contract**

```python
@unique_id("id")  # First field must be unique identifier
class Order:
    id: UUID
    items: list[Item]
    total: Decimal

# Guard verifies:
# - id field exists and is first
# - id is never reassigned
# - id uniqueness within scope
```

---

## 4. Hypothesis Analysis

**Source:** https://github.com/HypothesisWorks/hypothesis
**Documentation:** https://hypothesis.readthedocs.io/

### 4.1 Core Philosophy

> "You write tests which should pass for all inputs in whatever range you describe, and let Hypothesis randomly choose which of those inputs to check - including edge cases you might not have thought about."

Hypothesis is a **property-based testing** (PBT) library for Python. Instead of writing individual test cases, you define properties that should hold for all valid inputs.

### 4.2 Key Features

#### Property-Based Testing

Traditional unit testing:
```python
def test_sort():
    assert sort([3, 1, 2]) == [1, 2, 3]
    assert sort([]) == []
    assert sort([1]) == [1]
    # Manual cases - easy to miss edge cases
```

Property-based testing:
```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.lists(st.integers()))
def test_sort(items):
    result = sort(items)
    assert len(result) == len(items)           # Length preserved
    assert all(result[i] <= result[i+1]        # Sorted
               for i in range(len(result)-1))
    assert set(result) == set(items)           # Same elements
```

Hypothesis generates hundreds of test cases, including edge cases you might not think of.

#### Strategies

Strategies describe how to generate test data:

```python
st.integers()                          # Any integer
st.integers(min_value=0, max_value=100)  # Bounded integer
st.text()                              # Unicode strings
st.lists(st.integers())                # List of integers
st.floats(allow_nan=False)             # Floats without NaN
st.from_type(MyClass)                  # Generate from type annotations
```

#### Shrinking

When a test fails, Hypothesis finds the **minimal failing example**:

```python
@given(st.lists(st.integers()))
def test_sum_positive(items):
    assert sum(items) >= 0  # Fails for negative numbers

# Hypothesis reports: Falsifying example: items=[-1]
# Not: items=[-2847, 3829, -12983, ...]
```

This makes debugging much easier.

#### Stateful Testing

Test sequences of operations (state machines):

```python
class DatabaseStateMachine(RuleBasedStateMachine):
    @rule(key=st.text(), value=st.integers())
    def insert(self, key, value):
        self.db.insert(key, value)

    @rule(key=st.text())
    def delete(self, key):
        self.db.delete(key)

    @invariant()
    def size_non_negative(self):
        assert self.db.size() >= 0
```

### 4.3 The Key Insight: Contracts = PBT Invariants

From [Hillel Wayne's analysis](https://www.hillelwayne.com/post/pbt-contracts/):

> **"Your code doesn't violate any contracts" counts as a PBT invariant.**

This means:

| Component | PBT Role |
|-----------|----------|
| @pre | Defines valid input space → Hypothesis strategy |
| @post | Property that must hold → Hypothesis assertion |
| Contract chaining | Nested contracts checked → Integration tests |

```python
# Traditional PBT - manually define invariant
@given(st.integers(), st.integers())
def test_add(a, b):
    result = add(a, b)
    assert result == a + b  # Manual invariant

# Contract-based - contract IS the invariant
@pre(lambda a, b: True)
@post(lambda result, a, b: result == a + b)
def add(a, b):
    return a + b

# Hypothesis automatically verifies: input satisfies @pre → output satisfies @post
```

**Contract Chaining = Integration Tests:**

```python
@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def sqrt(x):
    return x ** 0.5

@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def process(x):
    return sqrt(x + 1)  # sqrt's @pre is automatically checked!

# Testing process() with Hypothesis automatically tests sqrt()'s contracts too
```

### 4.4 Existing Tool Ecosystem

| Tool | Function | Invar Relevance |
|------|----------|-----------------|
| [deal.cases](https://deal.readthedocs.io/) | Generate tests from contracts | **Already available!** (Invar uses deal) |
| [hypothesis-auto](https://timothycrosley.github.io/hypothesis-auto/) | Tests from type annotations | Complements deal.cases |
| [icontract-hypothesis](https://github.com/mristin/icontract-hypothesis) | Infer strategies from @pre | Pattern to learn from |
| [Pydantic + Hypothesis](https://docs.pydantic.dev/hypothesis_plugin/) | Auto-support Pydantic models | Invar uses Pydantic |

### 4.5 Invar Already Has Hypothesis!

**Critical discovery:** Invar already has access to Hypothesis through its `deal` dependency:

```python
# Current Invar code
from deal import pre, post

@pre(lambda price: price > 0)
@pre(lambda discount: 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)

# Automatically generate Hypothesis tests!
import deal

test_discounted_price = deal.cases(discounted_price)
# This generates 100 test cases using Hypothesis under the hood
```

Running:
```bash
pytest  # Automatically runs the generated tests
```

### 4.6 Strategy Inference from Contracts

Like icontract-hypothesis, we can infer Hypothesis strategies from @pre:

| @pre Pattern | Inferred Strategy |
|--------------|-------------------|
| `lambda x: x > 0` | `st.integers(min_value=1)` or `st.floats(min_value=0, exclude_min=True)` |
| `lambda x: 0 <= x <= 100` | `st.integers(min_value=0, max_value=100)` |
| `lambda s: len(s) > 0` | `st.text(min_size=1)` |
| `lambda items: len(items) < 10` | `st.lists(..., max_size=9)` |
| `lambda x: x in ['a', 'b', 'c']` | `st.sampled_from(['a', 'b', 'c'])` |
| `lambda items: all(i > 0 for i in items)` | `st.lists(st.integers(min_value=1))` |

This is more efficient than rejection sampling (filter invalid inputs).

### 4.7 Insights for Invar

| Hypothesis Feature | Invar Insight |
|--------------------|---------------|
| Property-based testing | Contracts ARE properties |
| Strategies | Can be inferred from @pre |
| Shrinking | Minimal counterexamples for contract violations |
| Stateful testing | Test @invariant sequences |
| from_type() | Generate from Pydantic models |
| deal.cases | **Already available!** |

#### Proposed: `invar test` Command

```bash
invar test                    # Run deal.cases on all Core functions
invar test --count 1000       # 1000 test cases per function
invar test src/module.py      # Test specific file
invar test --seed 12345       # Reproducible tests
invar test --shrink           # Show minimal counterexamples
```

#### Proposed: Three-Way Consistency Verification

Use Hypothesis to verify Clover's principle:

```
           Hypothesis generates input
                    ↓
    ┌─────────────────────────────┐
    │   Three-Way Consistency     │
    │                             │
    │   @pre ←→ Code ←→ @post     │
    │            ↕                │
    │        Doctests             │
    └─────────────────────────────┘

1. Generate input satisfying @pre
2. Execute code
3. Verify @post holds
4. Verify result matches doctests
```

#### Proposed: Guard Integration

```python
# Guard could detect functions without Hypothesis coverage
def untested_function(x: int) -> int:
    ...

# Guard output:
# WARN: untested_function has contracts but no deal.cases test
#     → Add: test_untested_function = deal.cases(untested_function)
```

---

## 5. CrossHair Analysis

**Source:** https://github.com/pschanely/CrossHair
**Documentation:** https://crosshair.readthedocs.io/

### 5.1 Core Philosophy

> "CrossHair is an analysis tool for Python that blurs the line between testing and type systems."

CrossHair uses **symbolic execution** with the **Z3 SMT solver** to verify contracts. Unlike testing (which checks specific inputs), CrossHair attempts to **prove** contracts hold for ALL inputs or find a counterexample.

### 5.2 How It Works

```
Traditional Testing:  function(concrete_value) → check result
Hypothesis (PBT):     function(random_values × 100) → check results
CrossHair:            function(symbolic_value) → theorem proving → proof OR counterexample
```

CrossHair creates **symbolic proxy objects** that represent all possible values:

| Python Type | CrossHair Symbolic Type | Z3 Expression |
|-------------|-------------------------|---------------|
| `int` | `SymbolicInt` | `IntSort()` |
| `bool` | `SymbolicBool` | `BoolSort()` |
| `str` | `AnySymbolicStr` | `StringSort()` |
| `dict` | `SymbolicDict` | `ArraySort()` |
| `list` | `SymbolicList` | Sequence theory |

When code branches (e.g., `if x > 0`), CrossHair explores **both paths** and uses Z3 to determine which inputs reach each path.

### 5.3 Key Features

#### Symbolic Execution

```python
def abs(x: int) -> int:
    if x < 0:           # CrossHair explores both branches
        return -x       # Path 1: x < 0
    return x            # Path 2: x >= 0

# CrossHair internally:
# Path 1: constraint x < 0  → result = -x → verify postcondition
# Path 2: constraint x >= 0 → result = x  → verify postcondition
```

#### Contract Verification

CrossHair directly supports **deal** (which Invar uses!):

```python
from deal import pre, post

@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    return x ** 0.5

# Verify with CrossHair
$ crosshair check module.py
# ✓ sqrt: All contracts verified
```

#### Counterexample Generation

When a contract violation is found, CrossHair provides the **exact input** that breaks it:

```python
@pre(lambda x: x > 0)
@post(lambda result: result > 0)
def broken_sqrt(x: float) -> float:
    return x - 1  # Bug: fails for 0 < x <= 1

$ crosshair check module.py
# ERROR: broken_sqrt
#   @post(lambda result: result > 0) violated
#   Counterexample: x = 0.5
#   Result: -0.5 (not > 0)
```

#### Watch Mode

Continuous verification while coding:

```bash
$ crosshair watch ./src/invar/core

# Watching ./src/invar/core for changes...
# Analyzing parser.py... ✓
# Analyzing rules.py... ✓
# [File changed: contracts.py]
# Analyzing contracts.py...
#   ERROR: line 42 - postcondition violated
#   Counterexample: expression = ""
```

### 5.4 CrossHair vs Hypothesis

| Aspect | Hypothesis | CrossHair |
|--------|------------|-----------|
| **Method** | Random testing | Symbolic execution |
| **Guarantee** | Probabilistic ("tested N cases") | Deterministic ("proven" or counterexample) |
| **Speed** | Fast (100 tests in seconds) | Slow (may timeout on complex functions) |
| **Coverage** | Statistical sampling | Exhaustive path exploration |
| **Edge cases** | May miss rare inputs | Finds exact violating inputs |
| **Applicability** | Any Python code | Limited by Z3's capabilities |
| **Integration** | `deal.cases(func)` | `crosshair check module.py` |

**They are complementary:**
- Use Hypothesis for fast feedback during development
- Use CrossHair for thorough verification before release

### 5.5 Hypothesis + CrossHair Integration

**Major discovery:** Hypothesis supports CrossHair as a backend!

```python
from hypothesis import given, settings, strategies as st

@settings(backend="crosshair")  # Use symbolic execution
@given(st.integers())
def test_specific_value(x):
    assert x != 123456789  # CrossHair finds this immediately!

# With random testing: might take millions of attempts
# With CrossHair: finds x=123456789 in one symbolic execution
```

Installation:
```bash
pip install hypothesis-crosshair
```

### 5.6 deal + CrossHair Integration

Since Invar uses `deal`, CrossHair integration is **already available**:

```python
# Current Invar code (using deal)
from deal import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: result >= min(items))
def find_min(items: list[int]) -> int:
    return min(items)

# Verify symbolically - no test code needed!
$ crosshair check mymodule.py
```

CrossHair automatically:
1. Recognizes deal decorators
2. Generates symbolic inputs satisfying @pre
3. Verifies @post holds for all such inputs
4. Reports counterexamples if found

### 5.7 Insights for Invar

| CrossHair Feature | Invar Insight |
|-------------------|---------------|
| Symbolic execution | Prove contracts, don't just test them |
| Z3 integration | Formal verification for Python |
| deal support | **Already works with Invar code!** |
| Counterexamples | Exact inputs that violate contracts |
| Watch mode | Continuous verification during development |
| Hypothesis backend | Combine PBT speed with symbolic precision |

#### Proposed: `invar verify` Command

```bash
invar verify                     # Symbolic verification of all Core
invar verify src/module.py       # Verify specific file
invar verify --timeout 60        # Set per-function timeout
invar verify --watch             # Continuous watch mode
```

**Implementation:**
```python
# Thin wrapper around CrossHair
import subprocess

def verify(path: str, timeout: int = 30) -> VerifyResult:
    result = subprocess.run([
        "crosshair", "check", path,
        "--per_condition_timeout", str(timeout)
    ], capture_output=True)
    return parse_crosshair_output(result.stdout)
```

#### Proposed: Guard Integration

```python
# Guard could suggest CrossHair verification
def complex_algorithm(data: list[int]) -> int:
    ...

# Guard output:
# INFO: complex_algorithm has contracts
#     → Quick check: invar test (Hypothesis)
#     → Full verify: invar verify (CrossHair)
```

#### Proposed: CI/CD Integration

```yaml
# .github/workflows/verify.yml
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install crosshair-tool
      - name: Symbolic Verification
        run: crosshair check src/invar/core --per_condition_timeout 30
```

### 5.8 Limitations

CrossHair has important limitations to understand:

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Timeout** | Complex functions may not complete | Use `--per_condition_timeout` |
| **Z3 coverage** | Not all Python operations supported | Fall back to Hypothesis |
| **External I/O** | Can't verify code with side effects | Only verify Core (pure) functions |
| **Aliasing** | Mutable object aliasing issues | Prefer immutable patterns |
| **Floating point** | Z3 uses real arithmetic, not IEEE floats | Be cautious with float contracts |

**Best practice:** Use CrossHair for Core (pure) functions, Hypothesis for Shell functions.

---

## 6. Instructor Analysis

**Source:** https://github.com/567-labs/instructor
**Documentation:** https://python.useinstructor.com/

### 6.1 Core Philosophy

> "Pydantic as your LLM contract: prompt with the actual schema, validate every boundary, and turn ValidationErrors into structured retries."

Instructor is the most popular Python library for extracting **structured data from LLMs** (11k+ GitHub stars, 3M+ monthly downloads). It uses Pydantic models as "contracts" for LLM outputs and automatically retries when validation fails.

**The Key Insight** (from Instructor documentation):

> **"Instead of framing 'self-critique' or 'self-reflection' in AI as new concepts, we can view them as validation errors with clear error messages that the system can use to self-correct."**

This is **exactly** what Invar does with Guard — validation errors become self-correction opportunities.

### 6.2 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Instructor Feedback Loop                      │
│                                                                  │
│   User Request                                                   │
│        ↓                                                         │
│   LLM generates response                                         │
│        ↓                                                         │
│   Pydantic validates against model                               │
│        ↓                                                         │
│   ┌─────────────┐      ┌─────────────────────────────────────┐  │
│   │ Valid?  YES │ ──→  │ Return structured data               │  │
│   └─────────────┘      └─────────────────────────────────────┘  │
│        ↓ NO                                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Append error to conversation:                            │   │
│   │ "Please correct; errors: {validation_error}"             │   │
│   └─────────────────────────────────────────────────────────┘   │
│        ↓                                                         │
│   Retry (up to max_retries)                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Key Features

| Feature | Description | Invar Parallel |
|---------|-------------|----------------|
| **Pydantic Models** | Define expected output structure | @pre/@post define expected behavior |
| **Automatic Retries** | Validation fails → error fed back → retry | Guard fails → AI fixes → verify again |
| **llm_validator** | Use LLM to validate LLM outputs | Future: LLM validates contract quality? |
| **Hook System** | Events for completion, parsing, errors | Future: Guard verification hooks? |
| **Structured Errors** | ValidationError with specific fields | Guard violations with suggestions |

### 6.4 Conceptual Alignment with Invar

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Pydantic as Foundation                         │
│                                                                     │
│   ┌─────────────────────┐         ┌─────────────────────┐          │
│   │     Instructor      │         │       Invar         │          │
│   │                     │         │                     │          │
│   │  LLM → Data         │         │  LLM/Human → Code   │          │
│   │  Pydantic models    │         │  @pre/@post         │          │
│   │  validate outputs   │         │  validate behavior  │          │
│   │                     │         │                     │          │
│   │  retry + feedback   │         │  guard + feedback   │          │
│   │  = self-correction  │         │  = self-correction  │          │
│   └─────────────────────┘         └─────────────────────┘          │
│                                                                     │
│   Different domains, same principle: validation → feedback → fix   │
└─────────────────────────────────────────────────────────────────────┘
```

| Aspect | Instructor | Invar |
|--------|-----------|-------|
| **Domain** | LLM data extraction | Code quality |
| **Contract type** | Pydantic models | @pre/@post + doctests |
| **Validation** | Pydantic + llm_validator | Guard static analysis |
| **Feedback loop** | ValidationError → retry | Guard violations → fix |
| **Research basis** | Implicit (Reflexion-like) | Explicit (Law 5: Reflexion) |

### 6.5 Validation of Invar's Approach

Instructor's success (11k+ stars, 3M+ downloads) validates Invar's core principles:

1. **Contracts Enable Correctness**: Both libraries prove that explicit contracts (Pydantic models or @pre/@post) are more effective than hoping for correct outputs.

2. **Feedback Loops Work**: Instructor's retry mechanism mirrors Reflexion research — clear error messages enable self-correction. This validates Invar's Law 5.

3. **Pydantic is the Right Foundation**: Both libraries build on Pydantic, proving its power for contract-based validation.

4. **Structured Errors Beat Prompting**: Instructor explicitly states that structured validation errors are better than "prompt engineering hacks" — this aligns with Invar's philosophy of mechanical verification.

### 6.6 Insights for Invar

| Instructor Feature | Invar Insight |
|-------------------|---------------|
| Pydantic as contract | Validates @pre/@post approach |
| Retry with feedback | Validates Law 5 (Reflexion) |
| llm_validator | **Future: LLM-based contract quality checking** |
| Hook system | **Future: Guard verification hooks** |
| Structured errors | Guard already provides this via suggestions |

### 6.7 Future Inspiration

#### llm_validator Pattern

Could Invar use LLMs to validate contract quality?

```python
from invar import llm_contract_validator

# Validate that a contract is meaningful (not tautological)
@pre(llm_contract_validator("this precondition should constrain inputs meaningfully"))
@post(llm_contract_validator("this postcondition should guarantee useful properties"))
def my_function(x: int) -> int:
    ...
```

This could catch subtle issues that static analysis misses:
- Contracts that are technically valid but semantically weak
- Contracts that don't match the function's documented purpose
- Missing edge case considerations

#### Hook System

Could Invar have verification hooks for observability?

```python
from invar import Guard

guard = Guard()

# Register hooks
guard.on("file:start", lambda f: print(f"Checking {f}..."))
guard.on("violation:found", lambda v: log_to_metrics(v))
guard.on("check:complete", lambda r: send_report(r))

# Run with hooks
guard.check("src/")
```

Use cases:
- CI/CD integration with custom reporting
- Real-time IDE feedback
- Metrics collection for code quality dashboards

#### Structured Error Protocol

Instructor's error feedback could inspire a more structured Guard output:

```python
# Current Guard output (human-readable)
"WARN: missing_contract at line 42"

# Future: Structured protocol for AI agents
{
    "type": "violation",
    "rule": "missing_contract",
    "severity": "warning",
    "location": {"file": "module.py", "line": 42, "symbol": "my_func"},
    "fix": {
        "action": "add_decorator",
        "code": "@pre(lambda x: ...)\n@post(lambda result: ...)"
    },
    "context": "Function 'my_func' takes int, returns str"
}
```

This would make Guard more "agent-native" — exactly what Invar aims for.

### 6.8 Relationship Summary

**Direct Integration: Not Applicable**
- Instructor validates LLM *data outputs*
- Invar validates *code behavior*
- Different domains, no direct integration path

**Conceptual Validation: Very High**
- Instructor proves that "contracts + validation + retry" works at scale
- Validates Invar's core philosophy
- Confirms Pydantic as the right foundation

**Future Inspiration: Medium**
- llm_validator pattern for contract quality
- Hook system for observability
- Structured error protocol for AI agents

---

## 7. Synthesis: Unified Insights

### 7.1 The Common Principle

All six tools converge on the same fundamental insight:

> **"Make incorrect code impossible to write, rather than catching errors at runtime."**

| Tool | Mechanism |
|------|-----------|
| Idris | Type system strong enough that invalid programs don't type-check |
| Dafny | Verification built-in; invalid programs don't verify |
| Move | Abilities system; invalid operations are language-level errors |
| Hypothesis | Property-based testing; contracts become testable invariants |
| CrossHair | Symbolic execution; contracts proven for ALL inputs |
| Instructor | Validation errors + retry = AI self-correction at scale |

### 7.2 Invar's Position

```
Language-Level Safety ←─────────────────────────────────→ Runtime Checking
     Idris        Move        Dafny      Invar+Guard    Plain Python
  (type proofs)  (abilities)  (SMT)    (analysis+runtime)  (none)
```

**Invar's unique value:** Provide Dafny-level assurance without changing Python.

### 7.3 What Invar Already Has

| Concept | Source | Invar Implementation |
|---------|--------|---------------------|
| Pre-conditions | Dafny requires | @pre |
| Post-conditions | Dafny ensures | @post |
| Contract-first | Idris type-driven | Law 2: Contract Complete |
| Mandatory verification | Move bytecode verification | Guard pre-commit hook |
| Three-way consistency | Clover research | Guard checks |
| Property-based testing | Hypothesis | deal.cases (**already available!**) |
| Automatic test generation | hypothesis-auto | Through deal + type hints |
| Symbolic verification | CrossHair | crosshair check (**already available!**) |
| SMT-based proofs | Dafny/CrossHair | Through deal + CrossHair |
| Validation → feedback → fix | Instructor | Guard violations → AI fixes |

### 7.4 The Verification Spectrum

```
Level 3: Formal Proofs (SMT/Theorem Provers)
         - Full mathematical proof
         - Covers all inputs
         - High effort, highest assurance

Level 2: Static Verification
         - Type system + static analysis
         - Compile-time guarantees
         - Medium effort, high assurance

Level 1: Runtime Contracts + Static Analysis  ← INVAR CURRENT
         - @pre/@post checked at runtime
         - Guard analyzes statically
         - Low effort, good assurance

Level 0: No Verification
         - Trust the code
         - Hope tests cover everything
         - No effort, no assurance
```

### 7.5 The Core Formula

This research reveals a powerful verification pyramid:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Contracts + Testing + Proving = Complete Verification        │
│                                                                 │
│   Level 3: CrossHair   → Prove contracts for ALL inputs        │
│   Level 2: Hypothesis  → Test contracts with 100+ random inputs│
│   Level 1: deal        → Check contracts at runtime            │
│   Level 0: Guard       → Verify contracts exist and are valid  │
│                                                                 │
│   @pre  → Strategy (Hypothesis) / Constraint (CrossHair)       │
│   @post → Assertion (Hypothesis) / Proof goal (CrossHair)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why this matters:**

| Without Integration | With Integration |
|---------------------|------------------|
| Contracts need manual testing | Hypothesis automatically tests contracts |
| PBT needs manual invariants | Contracts ARE the invariants |
| Testing gives probabilistic coverage | CrossHair gives deterministic proof |
| Edge cases easily missed | CrossHair finds exact counterexamples |
| "Works on my machine" | "Proven correct for all inputs" |

**Invar's unique position:** We already have this through `deal` + Hypothesis + CrossHair!

### 7.6 Evolution Strategy

Invar can evolve **upward** through the verification pyramid:

1. **Current (Level 0-1):** Guard + Runtime contracts
2. **Immediate (Level 2):** Add `invar test` (Hypothesis via deal.cases) — **already available!**
3. **Near-term (Level 2+):** Add @invariant, @must_use, @must_close, strategy inference
4. **Medium-term (Level 3):** Add `invar verify` (CrossHair) — **already available via deal!**
5. **Long-term:** IDE integration, continuous verification, Hypothesis+CrossHair backend

This is an **additive** strategy — each level adds to, not replaces, the previous.

**Key insight:** Levels 2 and 3 are already available through deal's integrations!

---

## 8. Proposed Enhancements

### 8.1 New Contract Decorators

#### @invariant

**Source:** Dafny loop invariants
**Purpose:** Specify conditions that must hold throughout a loop

```python
from invar import invariant

def binary_search(arr: list[int], target: int) -> int:
    """
    >>> binary_search([1, 2, 3, 4, 5], 3)
    2
    """
    lo, hi = 0, len(arr)
    while lo < hi:
        invariant(0 <= lo <= hi <= len(arr))
        invariant(target not in arr[:lo])
        invariant(target not in arr[hi:])
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        elif arr[mid] > target:
            hi = mid
        else:
            return mid
    return -1
```

**Guard Integration:**
- Detect loops without invariants in complex functions
- Suggest invariant patterns based on loop structure
- Verify invariant consistency with pre/post conditions

#### @must_use

**Source:** Move drop ability (lack thereof)
**Purpose:** Ensure return values are not ignored

```python
from invar import must_use

@must_use("Error must be handled")
def validate(data: dict) -> Result[ValidData, list[Error]]:
    ...

# Guard warns:
validate(user_input)  # Return value ignored!
```

**Use Cases:**
- Result types that may contain errors
- Resource handles that need processing
- Critical status codes

#### @must_close

**Source:** Move resource semantics
**Purpose:** Ensure resources are properly cleaned up

```python
from invar import must_close

@must_close
class TempFile:
    def __init__(self, path: str): ...
    def write(self, data: bytes): ...
    def close(self): ...

# Guard analyzes control flow:
def process():
    f = TempFile("temp.dat")
    f.write(data)
    # Warning: TempFile may not be closed (missing f.close())
```

**Guard Integration:**
- Track resource creation points
- Analyze all exit paths (including exceptions)
- Suggest context manager pattern

#### @transfer

**Source:** Move ownership
**Purpose:** Mark ownership transfer semantics

```python
from invar import transfer

@transfer("token")
def spend(token: AuthToken, action: str) -> Receipt:
    """Token is consumed after this call."""
    ...

# Guard warns:
token = get_token()
spend(token, "read")
spend(token, "write")  # Error: token already transferred
```

### 8.2 Contract Composition

**Source:** Idris first-class types
**Purpose:** Reusable, composable contracts

```python
from invar import Contract, pre, post

# Define reusable contracts
NonEmpty = Contract(lambda x: len(x) > 0, "must be non-empty")
Sorted = Contract(lambda x: x == sorted(x), "must be sorted")
AllPositive = Contract(lambda x: all(i > 0 for i in x), "all elements > 0")

# Compose with operators
@pre(NonEmpty & Sorted)  # AND composition
def binary_search(arr: list[int], target: int) -> int:
    ...

@pre(NonEmpty | AllPositive)  # OR composition
def flexible_function(data: list[int]) -> int:
    ...

# Negate
@pre(~NonEmpty)  # Require empty
def initialize(container: list) -> None:
    ...
```

### 8.3 Refinement Types

**Source:** Idris dependent types
**Purpose:** Types that carry contracts

```python
from typing import Annotated
from invar import Gt, Lt, Between, NonEmpty

# Refinement type definitions
PositiveInt = Annotated[int, Gt(0)]
Percentage = Annotated[float, Between(0, 100)]
NonEmptyStr = Annotated[str, NonEmpty()]

# Usage - contracts implicit in types
@post(lambda result: result >= 0)
def sqrt(x: PositiveInt) -> float:  # No @pre needed
    return x ** 0.5

def apply_discount(price: PositiveInt, discount: Percentage) -> PositiveInt:
    return int(price * (1 - discount / 100))
```

**Guard Integration:**
- Recognize Annotated types with Invar constraints
- Verify constraint satisfaction at call sites
- Suggest refinement types when @pre patterns detected

### 8.4 Ghost Specifications

**Source:** Dafny ghost code
**Purpose:** Expensive specifications checked only in verification mode

```python
from invar import ghost, post

@ghost
def is_sorted(arr: list[int]) -> bool:
    """O(n) check - only for verification."""
    return all(arr[i] <= arr[i+1] for i in range(len(arr)-1))

@post(ghost_check=is_sorted)  # Only in INVAR_VERIFY=1 mode
def sort(arr: list[int]) -> list[int]:
    ...  # O(n log n) implementation
```

**Modes:**
- `INVAR_VERIFY=1`: Ghost checks enabled (development/CI)
- `INVAR_VERIFY=0`: Ghost checks skipped (production)

### 8.5 Termination Contracts

**Source:** Dafny decreases clauses
**Purpose:** Prove recursive functions terminate

```python
from invar import terminates

@terminates(variant=lambda n: n)  # n decreases each call
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

@terminates(variant=lambda tree: tree.depth())  # depth decreases
def traverse(tree: Tree) -> list:
    if tree.is_leaf():
        return [tree.value]
    return traverse(tree.left) + traverse(tree.right)
```

**Guard Integration:**
- Verify variant decreases on each recursive call
- Warn about potentially non-terminating recursion
- Suggest variant functions for recursive code

### 8.6 Hypothesis Integration (Immediate Value)

**Source:** Hypothesis + deal.cases
**Purpose:** Automatic property-based testing from contracts

This is unique because **it's already available** through Invar's `deal` dependency.

#### `invar test` Command

```bash
invar test                    # Run deal.cases on all Core functions
invar test --count 1000       # 1000 test cases per function
invar test src/module.py      # Test specific file
invar test --seed 12345       # Reproducible tests
invar test --shrink           # Show minimal counterexamples
```

**Implementation:**
```python
# Core functionality already exists in deal
import deal

def run_contract_tests(module_path: str, count: int = 100):
    """Find all contracted functions and run deal.cases on them."""
    for func in find_contracted_functions(module_path):
        test_func = deal.cases(func, count=count)
        test_func()  # Run the generated tests
```

#### Strategy Inference

Parse @pre lambdas to generate efficient Hypothesis strategies:

```python
from invar.core.strategies import infer_strategy

# Input: @pre(lambda x: 0 < x < 100)
# Output: st.integers(min_value=1, max_value=99)

strategy = infer_strategy("lambda x: 0 < x < 100", param_type=int)
```

**Pattern Recognition:**

| Pattern | Strategy |
|---------|----------|
| `x > N` | `st.integers(min_value=N+1)` |
| `x < N` | `st.integers(max_value=N-1)` |
| `N <= x <= M` | `st.integers(min_value=N, max_value=M)` |
| `len(x) > 0` | `st.text(min_size=1)` / `st.lists(..., min_size=1)` |
| `x in [a, b, c]` | `st.sampled_from([a, b, c])` |
| `all(i > 0 for i in x)` | `st.lists(st.integers(min_value=1))` |

#### Guard Integration

```python
# Guard warns about missing PBT coverage
def my_function(x: int) -> int:
    ...

# Guard output:
# INFO: my_function has contracts - consider adding PBT
#     → test_my_function = deal.cases(my_function)
#     → Or run: invar test src/module.py
```

### 8.7 CrossHair Integration (Immediate Value)

**Source:** CrossHair + deal
**Purpose:** Symbolic verification of contracts (prove for ALL inputs)

This is unique because **it's already available** through deal's CrossHair support.

#### `invar verify` Command

```bash
invar verify                     # Symbolic verification of all Core
invar verify src/module.py       # Verify specific file
invar verify --timeout 60        # Set per-function timeout
invar verify --watch             # Continuous watch mode
```

**Implementation:**
```python
# Thin wrapper around CrossHair
import subprocess

def verify(path: str, timeout: int = 30) -> VerifyResult:
    result = subprocess.run([
        "crosshair", "check", path,
        "--per_condition_timeout", str(timeout)
    ], capture_output=True)
    return parse_crosshair_output(result.stdout)
```

#### Verification Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Quick check | `invar test` | Fast feedback (Hypothesis) |
| Full verify | `invar verify` | Thorough proof (CrossHair) |
| Continuous | `invar verify --watch` | While coding |
| CI/CD | `invar verify --timeout 30` | Before merge |

#### Guard Integration

```python
# Guard suggests verification level
def complex_algorithm(data: list[int]) -> int:
    ...

# Guard output:
# INFO: complex_algorithm has contracts
#     → Quick: invar test (Hypothesis, ~1s)
#     → Full:  invar verify (CrossHair, ~30s)
```

---

## 9. Evolution Roadmap

### Phase 0: Hypothesis + CrossHair Integration (Immediate - Already Available!)

**Effort:** Very Low
**Impact:** Very High
**Timeline:** Now

| Feature | Source | Description |
|---------|--------|-------------|
| deal.cases | Hypothesis | Automatic PBT from contracts |
| `invar test` command | deal + Hypothesis | CLI wrapper for deal.cases |
| crosshair check | CrossHair | Symbolic verification of contracts |
| `invar verify` command | deal + CrossHair | CLI wrapper for CrossHair |
| Documentation | — | Educate users about verification pyramid |

**Implementation Notes:**
- deal.cases is already available through deal dependency
- crosshair check already works with deal contracts
- `invar test` and `invar verify` are thin wrappers
- Immediate value with minimal implementation effort

### Phase 1: Core Extensions (Short-term)

**Effort:** Low-Medium
**Impact:** High
**Timeline:** Can start immediately

| Feature | Source | Description |
|---------|--------|-------------|
| @invariant | Dafny | Loop invariants as runtime checks |
| @must_use | Move | Warn on ignored return values |
| @must_close | Move | Resource cleanup verification |
| Contract composition | Idris | &, |, ~ operators for contracts |
| Strategy inference | icontract-hypothesis | Parse @pre → Hypothesis strategy |

**Implementation Notes:**
- @invariant: Function that records and checks condition
- @must_use/@must_close: Guard static analysis rules
- Composition: Contract class with __and__, __or__, __invert__
- Strategy inference: AST parsing of lambda expressions

### Phase 2: Resource Safety (Medium-term)

**Effort:** Medium
**Impact:** Medium

| Feature | Source | Description | Status |
|---------|--------|-------------|--------|
| @must_close | Move | Resource cleanup verification | **Active** |

**Moved to Tier 3 (Impractical in Python):**
- ~~@transfer~~: Python's dynamic typing and aliasing make accurate static ownership tracking impractical (estimated <60% detection accuracy). Runtime patterns (explicit consume methods, context managers) provide sufficient coverage without false positives.

**Removed from Phase 2 (Agent-Native filtering):**
- ~~Refinement types~~: Redundant with @pre + Contract Composition (C3)
- ~~Guard LSP~~: Human UX feature, not Agent-Native
- ~~Ghost specifications~~: Agent needs maximum checking, not selective skipping

**Implementation Notes:**
- @must_close: Control flow analysis to track resource lifecycle

### Phase 3: Advanced Verification (Long-term)

**Effort:** High
**Impact:** Very High (for adopters)

| Feature | Source | Description |
|---------|--------|-------------|
| Static contract verification | Dafny | Prove contracts without execution |
| SMT integration | Dafny | Z3 for automatic proofs |
| Termination proofs | Dafny/Idris | Prove functions terminate |
| Linear type checking | Move | Full ownership tracking |
| @transfer | Move | Ownership transfer tracking (deferred from Tier 2) |

**Implementation Notes:**
- Would require significant research
- Could leverage existing tools (Z3, CrossHair)
- @transfer requires compiler-level support for accurate tracking; Python's dynamic nature limits static analysis accuracy to <60%
- Opt-in for projects needing highest assurance

---

## 10. Implementation Priority

### Prioritization Matrix

| Feature | Value | Effort | Priority | Status |
|---------|-------|--------|----------|--------|
| **`invar test` (Hypothesis)** | **Very High** | **Very Low** | **Tier 0** | Active |
| **`invar verify` (CrossHair)** | **Very High** | **Very Low** | **Tier 0** | Active |
| Multi-layer purity | High (Agent decision) | Medium | **Tier 1** | Active |
| @must_use | High (catches ignored errors) | Low | **Tier 1** | Active |
| @invariant | High (catches loop bugs) | Medium | **Tier 1** | Active |
| Contract composition | Medium (DRY) | Low | **Tier 1** | Active |
| Strategy inference | High (efficient PBT) | Medium | **Tier 1** | Active |
| @must_close | Medium (resource safety) | Medium | **Tier 2** | Active |
| ~~@transfer~~ | — | — | **Tier 3** | Deferred (impractical in Python) |
| ~~Refinement types~~ | — | — | — | Removed (redundant with C3) |
| ~~Guard LSP~~ | — | — | — | Removed (not Agent-Native) |
| ~~Ghost specs~~ | — | — | — | Removed (not Agent-Native) |
| ~~CLI-B: Counterexamples~~ | — | — | — | Merged into A2 |
| ~~CLI-C: Priority ranking~~ | — | — | — | Removed (Agent can sort) |
| ~~CLI-D: Impact analysis~~ | — | — | — | Removed (use Serena + pytest) |

**CLI Quick Win (Immediate):**
| TTY auto-detection | High (truly automatic) | Very Low (30 min) | **Immediate** | Active |

### Recommended First Steps

0. **Implement `invar test` + `invar verify`** — **Immediate value, already available!**

   **`invar test` (Hypothesis):**
   - Wraps deal.cases (which uses Hypothesis)
   - Automatic PBT from existing contracts
   - Fast feedback (~100 random tests)
   - Users get property-based testing TODAY

   **`invar verify` (CrossHair):**
   - Wraps crosshair check
   - Symbolic verification of contracts
   - Proves contracts for ALL inputs (or finds counterexample)
   - Users get formal verification TODAY

   **Both require no new dependencies** (deal already supports them)

1. **Implement @invariant** — Highest value for new features
   - Loops are bug-prone
   - Natural extension of @pre/@post
   - Clear semantics

2. **Implement @must_use** — Simple Guard rule
   - Static analysis only
   - No runtime component
   - Catches common bugs

3. **Implement Contract composition** — Enables reuse
   - Simple operator overloading
   - Makes contracts first-class
   - Foundation for future features

4. **Implement Strategy inference** — Better PBT efficiency
   - Parse @pre patterns to Hypothesis strategies
   - Avoids rejection sampling
   - Builds on `invar test`

---

## 11. Benchmarking Strategy

Validating Invar's effectiveness requires scientific measurement. This section outlines benchmarks that can be used immediately and a long-term plan for creating an Invar-specific benchmark.

### 11.1 Why Not SWE-bench Directly?

[SWE-bench](https://github.com/SWE-bench/SWE-bench) is the standard benchmark for evaluating AI on real-world software engineering tasks. However, it's not directly suitable for Invar:

| Challenge | Reason |
|-----------|--------|
| **Repositories lack contracts** | Django, Flask, scikit-learn don't use @pre/@post |
| **Goal mismatch** | SWE-bench measures "can you fix this bug?", Invar ensures "can you write correct code?" |
| **Adding contracts = scope creep** | Bug fixes shouldn't include unrelated contract additions |
| **Data leakage** | [33% of solutions come from issue descriptions](https://openai.com/index/introducing-swe-bench-verified/), >94% in training data |

**Conclusion**: Use SWE-bench methodology, not SWE-bench directly.

### 11.2 Directly Usable Benchmarks

#### CRUXEval — Code Understanding ⭐⭐⭐⭐⭐

**Source:** [Facebook Research / ICML 2024](https://github.com/facebookresearch/cruxeval)

[CRUXEval](https://crux-eval.github.io/) tests code reasoning with 800 Python functions:
- **CRUXEval-I**: Given output, predict input
- **CRUXEval-O**: Given input, predict output

**Why perfect for Invar?** This directly maps to @pre/@post + doctests!

```python
# CRUXEval task
def f(x):
    return x * 2 + 1
# Task: f(5) = ?  → 11

# Invar perspective
@pre(lambda x: isinstance(x, int))
@post(lambda result, x: result == x * 2 + 1)
def f(x):
    """
    >>> f(5)
    11
    """
    return x * 2 + 1
```

**Experiment Design:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Hypothesis: Contracts improve code understanding               │
│                                                                  │
│  Group A (Baseline): function code only                         │
│  Group B (Contracts): function code + @pre + @post              │
│                                                                  │
│  Task: Predict input/output                                      │
│  Metric: pass@1 difference                                       │
│                                                                  │
│  Expected: Group B outperforms Group A on boundary cases        │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation Time:** 1-2 days

#### EvalPlus (HumanEval+ / MBPP+) — Code Robustness ⭐⭐⭐⭐

**Source:** [EvalPlus / NeurIPS 2023](https://github.com/evalplus/evalplus)

[EvalPlus](https://evalplus.github.io/) extends test coverage by **80x** to measure code robustness:

> "By comparing scores before & after using EvalPlus tests, less drop means more rigorousness"

**Experiment Design:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Hypothesis: ICIDIV produces more robust code                   │
│                                                                  │
│  Group A (Code-First): "Write function to solve..."             │
│  Group B (ICIDIV): "First write @pre/@post, then implement..."  │
│                                                                  │
│  Metrics:                                                        │
│    - HumanEval pass@1 vs HumanEval+ pass@1                       │
│    - Drop = (HumanEval - HumanEval+) / HumanEval                 │
│    - Smaller drop = more robust code                             │
│                                                                  │
│  Expected Results:                                               │
│              HumanEval    HumanEval+    Drop                     │
│  Code-First     85%          65%        -20%                     │
│  ICIDIV         82%          72%        -10%  ← more robust      │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation Time:** 2-3 days

#### ClassEval — ICIDIV Workflow ⭐⭐⭐⭐

**Source:** [FudanSELab / ICSE 2024](https://github.com/FudanSELab/ClassEval)

[ClassEval](https://dl.acm.org/doi/10.1145/3597503.3639219) is class-level code generation:
- 100 classes, 410 methods
- 33.1 test cases per class average
- Tests Holistic, Incremental, Compositional strategies

**Perfect for testing ICIDIV's Design → Implement flow!**

**Experiment Design:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Hypothesis: Contract-First improves class-level quality        │
│                                                                  │
│  Group A (Default): Incremental generation, no contracts        │
│  Group B (ICIDIV):                                               │
│    1. Write class invariants                                     │
│    2. Write method @pre/@post before implementation              │
│    3. Implement methods                                          │
│    4. Run Guard before submission                                │
│                                                                  │
│  Metrics:                                                        │
│    - pass@1 (correctness)                                        │
│    - Method dependency handling success rate                     │
│    - Test coverage                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation Time:** 1-2 weeks

#### BigCodeBench — Complex Tasks ⭐⭐⭐

**Source:** [BigCode / ICLR 2025](https://github.com/bigcode-project/bigcodebench)

[BigCodeBench](https://bigcode-bench.github.io/) has 1,140 complex tasks:
- Average 5.6 library function calls per task
- 99% branch coverage in tests
- Human: 97%, Best LLM: ~60%

**Experiment:** Test if contracts help LLMs follow complex instructions.

### 11.3 Benchmark Comparison Matrix

| Benchmark | Invar Relevance | Implementation | Measures |
|-----------|-----------------|----------------|----------|
| **CRUXEval** | ⭐⭐⭐⭐⭐ | 1-2 days | Contracts → understanding |
| **EvalPlus** | ⭐⭐⭐⭐ | 2-3 days | ICIDIV → robustness |
| **ClassEval** | ⭐⭐⭐⭐ | 1-2 weeks | ICIDIV → class quality |
| **BigCodeBench** | ⭐⭐⭐ | 1 week | Contracts → complex tasks |
| **HumanEval Pro** | ⭐⭐⭐ | 3 days | Contracts → progressive reasoning |

### 11.4 Long-Term: Invar-bench

#### Motivation

Existing benchmarks don't directly measure contract-based development. We need a dedicated benchmark.

#### Existing Foundation

[Python-by-Contract Dataset](https://dl.acm.org/doi/10.1145/3540250.3558917) (ACM FSE 2022):
- **514 Python functions with contracts** (using icontract)
- Designed for evaluating contract tools
- Achieved 76% code coverage

This is the ideal foundation for Invar-bench!

#### Task Types

```
┌─────────────────────────────────────────────────────────────────┐
│                        Invar-bench                               │
│                                                                  │
│  T1: Contract Violation Fix                                      │
│      Given: Code + contracts + failing test                      │
│      Task:  Fix code to satisfy contracts                        │
│                                                                  │
│  T2: Contract Generation                                         │
│      Given: Code + docstring + tests                             │
│      Task:  Write @pre/@post that capture behavior               │
│                                                                  │
│  T3: Contract-Guided Bug Fix                                     │
│      Given: Code with contracts + bug report                     │
│      Task:  Fix without violating existing contracts             │
│                                                                  │
│  T4: ICIDIV Compliance                                           │
│      Given: Feature request                                      │
│      Task:  Write contracts first, then implementation           │
│      Eval:  Were contracts written before code?                  │
│                                                                  │
│  T5: Contract Quality                                            │
│      Given: Code with weak contracts                             │
│      Task:  Improve contracts to be more meaningful              │
│      Eval:  Contracts catch more edge cases                      │
└─────────────────────────────────────────────────────────────────┘
```

#### Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **Guard Pass Rate** | % of submissions with 0 Guard errors |
| **Test Pass Rate** | % of submissions passing all tests |
| **Contract Coverage** | % of functions with meaningful contracts |
| **Contract Quality** | Not tautological, catches edge cases |
| **ICIDIV Compliance** | Contracts written before implementation |
| **Regression Prevention** | Contracts catch future breaking changes |

#### Data Sources

| Source | Size | Use |
|--------|------|-----|
| [Python-by-Contract](https://jiyangzhang.github.io/assets/pdf/papers/PythonContract.pdf) | 514 functions | T1, T2, T3 tasks |
| Invar itself (src/invar/core) | 90+ functions | Real-world contract examples |
| [deal examples](https://github.com/life4/deal) | 100+ | Contract patterns |
| [icontract-hypothesis](https://github.com/mristin/icontract-hypothesis) | test cases | Contract + PBT integration |

#### Implementation Roadmap

```
Phase 1: Feasibility (1-2 weeks)
├── Download Python-by-Contract dataset
├── Convert to Invar format (@pre/@post from deal)
├── Create 10 manual tasks
├── Test with Claude Code + Invar
└── Evaluate results

Phase 2: Benchmark Construction (2-4 weeks)
├── Expand to 100+ tasks
├── Automated evaluation scripts
├── Baseline comparison (with/without Invar)
└── Statistical analysis

Phase 3: Publication (4-8 weeks)
├── Open-source Invar-bench
├── Community validation
├── Technical report / paper
└── Submit to academic venue (FSE, ICSE, etc.)
```

### 11.5 Quick-Start Evaluation Script

```python
"""
invar_benchmark_eval.py - Quick evaluation of Invar on CRUXEval
"""

from pathlib import Path
import json

def add_contracts_to_function(code: str) -> str:
    """
    Infer @pre/@post from function implementation.
    Uses Guard's analysis or LLM to generate contracts.
    """
    # Option 1: Use invar sig to extract patterns
    # Option 2: Use LLM to infer contracts
    # Option 3: Manual annotation for small datasets
    pass

def run_cruxeval_experiment():
    """
    Compare code understanding with/without contracts.
    """
    # Load CRUXEval dataset
    dataset = load_cruxeval()

    results = {
        "baseline": {"input": [], "output": []},
        "with_contracts": {"input": [], "output": []}
    }

    for task in dataset:
        # Baseline prompt
        baseline_prompt = f"""
Given this function:
```python
{task.code}
```
What is the output when called with input: {task.input}?
"""

        # Contract-enhanced prompt
        code_with_contracts = add_contracts_to_function(task.code)
        contract_prompt = f"""
Given this function with contracts:
```python
{code_with_contracts}
```
What is the output when called with input: {task.input}?
"""

        # Evaluate both (using Claude API)
        baseline_result = evaluate(baseline_prompt, task.expected_output)
        contract_result = evaluate(contract_prompt, task.expected_output)

        results["baseline"]["output"].append(baseline_result)
        results["with_contracts"]["output"].append(contract_result)

    # Report
    print("CRUXEval-O Results:")
    print(f"  Baseline:       {mean(results['baseline']['output']):.1%}")
    print(f"  With Contracts: {mean(results['with_contracts']['output']):.1%}")
    print(f"  Improvement:    {improvement:.1%}")

if __name__ == "__main__":
    run_cruxeval_experiment()
```

### 11.6 Expected Outcomes

| Experiment | Hypothesis | Expected Result |
|------------|------------|-----------------|
| CRUXEval + Contracts | Contracts improve understanding | +5-15% pass@1 on boundary cases |
| EvalPlus + ICIDIV | Contract-first → robust code | 50% less drop (HumanEval → HumanEval+) |
| ClassEval + ICIDIV | Contract-first → better classes | +10-20% pass@1 on complex classes |
| Invar-bench | Comprehensive evaluation | Baseline for future Invar improvements |

### 11.7 Academic Impact

Creating Invar-bench would:

1. **Fill a gap**: No existing benchmark for contract-based AI development
2. **Enable comparison**: Standard way to compare contract tools
3. **Bridge communities**: Connect SE (FSE, ICSE) with AI (NeurIPS, ICML)
4. **Validate claims**: Scientific evidence for Invar's Five Laws

**Potential venues:**
- FSE (Foundations of Software Engineering)
- ICSE (International Conference on Software Engineering)
- ASE (Automated Software Engineering)
- ISSTA (Software Testing and Analysis)

---

## 12. Tier 0 Development Plan

This section contains the detailed development plan for immediate-value features.

### 12.1 CrossHair Limitations Analysis

Before implementing `invar verify`, we must understand CrossHair's constraints.

#### Supported Features

| Category | Support Level | Notes |
|----------|---------------|-------|
| Built-in types | ✅ Full | int, str, bool, float, list, dict, set |
| User-defined classes | ✅ Full | Pure Python classes work well |
| Standard library (pure) | ✅ Full | collections, itertools, functools |
| Type hints | ✅ Full | Used for strategy inference |
| deal contracts | ✅ Full | @pre, @post, @ensure, @inv |

#### Unsupported / Limited Features

| Category | Support | Reason | Workaround |
|----------|---------|--------|------------|
| **C Extensions** | ❌ None | Cannot symbolically execute C code | Use plugins or fallback to Hypothesis |
| numpy | ❌ | C-based array operations | Plugin required |
| pandas | ❌ | Cython datetime conflicts | Plugin required |
| scipy | ❌ | C-based scientific computing | Plugin required |
| requests | ⚠️ | Side effects (network) | Mock or skip |
| **Non-deterministic** | ❌ | SMT requires determinism | |
| random.* | ❌ | Non-deterministic output | Use seed or skip |
| time.time() | ❌ | System state dependent | Skip |
| datetime.now() | ❌ | System state dependent | Skip |
| uuid.uuid4() | ❌ | Random generation | Skip |
| **Side Effects** | ❌ | Cannot verify I/O | |
| File I/O | ❌ | open(), Path.read_text() | Skip (Shell only) |
| Network | ❌ | requests, urllib | Skip (Shell only) |
| Database | ❌ | sqlite3, sqlalchemy | Skip (Shell only) |
| **Language Features** | ⚠️ | Partial support | |
| `x is y` | ⚠️ | Identity may not work correctly | Use `==` |
| Nested functions | ❌ | Skipped during analysis | Flatten |
| Generators in contracts | ⚠️ | Consumption issues | Avoid |

#### Why This Aligns with Invar

```
┌─────────────────────────────────────────────────────────────────┐
│              CrossHair limitations ∩ Invar Core rules           │
│                                                                  │
│  CrossHair cannot handle:          Invar Core forbids:          │
│  ├── C extensions (numpy)          ├── External dependencies    │
│  ├── File I/O                      ├── os, pathlib, open        │
│  ├── Network                       ├── requests, urllib         │
│  ├── Random                        ├── random.*                 │
│  ├── System time                   ├── datetime.now()           │
│  └── Side effects                  └── All I/O operations       │
│                                                                  │
│  Conclusion: If code follows Invar Core rules,                  │
│              CrossHair CAN verify it!                           │
│                                                                  │
│  Core (pure functions) → CrossHair ✅                           │
│  Shell (I/O functions) → Hypothesis only ⚠️                     │
└─────────────────────────────────────────────────────────────────┘
```

#### Fallback Strategy

```python
# invar verify behavior for unsupported code

def verify_function(func, file_info):
    """
    Attempt CrossHair verification with fallback.
    """
    if not file_info.is_core:
        # Shell functions: skip CrossHair, suggest Hypothesis
        return VerifyResult(
            status="skipped",
            reason="Shell function (I/O)",
            suggestion="Use 'invar test' for Shell functions"
        )

    if uses_unsupported_imports(func):
        # Core function with unsupported imports
        return VerifyResult(
            status="unsupported",
            reason=f"Uses {unsupported_import}",
            suggestion="Use 'invar test' or add CrossHair plugin"
        )

    try:
        # Attempt CrossHair verification
        result = crosshair_check(func, timeout=30)
        return VerifyResult(status="verified", details=result)
    except CrossHairError as e:
        # CrossHair failed, fall back to Hypothesis
        return VerifyResult(
            status="fallback",
            reason=str(e),
            suggestion="Falling back to 'invar test'"
        )
```

### 12.2 Development Tasks

#### A1: `invar test` Command

**Goal**: Wrap `deal.cases` for automatic property-based testing.

**Status**: Ready to implement

**Effort**: 0.5 days

**Tasks**:
```
□ 1. Add `test` command to cli.py
     ├── Parse arguments (path, count, seed, verbose)
     ├── Scan for Core files
     ├── Find functions with contracts
     └── Run deal.cases on each

□ 2. Handle edge cases
     ├── Functions with no contracts → skip
     ├── Import errors → warn and continue
     ├── Test failures → collect and report
     └── Timeout per function

□ 3. Output formatting
     ├── Progress indicator
     ├── Success/failure per function
     ├── Summary statistics
     └── JSON output for --agent mode

□ 4. Documentation
     ├── Command help text
     ├── INVAR.md update
     └── Examples in README
```

**Implementation Sketch**:
```python
@app.command()
def test(
    path: Path = typer.Argument(Path("."), help="Path to test"),
    count: int = typer.Option(100, "--count", "-n"),
    seed: int = typer.Option(None, "--seed", "-s"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    timeout: int = typer.Option(30, "--timeout", "-t"),
) -> None:
    """Run property-based tests from contracts."""
    import deal

    tested, passed, failed = 0, 0, []

    for file_info in scan_core_files(path):
        module = import_module(file_info.path)

        for symbol in file_info.symbols:
            if not symbol.contracts:
                continue

            func = getattr(module, symbol.name, None)
            if not callable(func):
                continue

            tested += 1
            try:
                test_func = deal.cases(func, count=count, seed=seed)
                with timeout_context(timeout):
                    test_func()
                passed += 1
                if verbose:
                    console.print(f"  ✓ {symbol.name}")
            except Exception as e:
                failed.append((symbol.name, str(e)))
                console.print(f"  ✗ {symbol.name}: {e}")

    console.print(f"\n{passed}/{tested} passed, {len(failed)} failed")
    raise typer.Exit(1 if failed else 0)
```

#### A2: `invar verify` Command

**Goal**: Wrap CrossHair for symbolic verification with graceful degradation.

**Status**: Ready to implement (requires crosshair-tool installation)

**Effort**: 0.5 days

**Tasks**:
```
□ 1. Add `verify` command to cli.py
     ├── Check CrossHair installation
     ├── Parse arguments (path, timeout, watch)
     ├── Filter to Core files only
     └── Run crosshair check

□ 2. Handle limitations gracefully
     ├── Shell files → skip with message
     ├── Unsupported imports → warn and skip
     ├── CrossHair errors → suggest invar test
     └── Timeout → partial results

□ 3. Output formatting
     ├── Per-function status (verified/failed/skipped/unsupported)
     ├── Counterexamples when found
     ├── Summary with fallback suggestions
     └── JSON output for --agent mode

□ 4. Optional dependency handling
     ├── crosshair-tool as optional dep in pyproject.toml
     ├── Helpful error if not installed
     └── pip install python-invar[verify] option

□ 5. Documentation
     ├── Limitations section
     ├── When to use test vs verify
     └── Plugin development guide (future)
```

**Implementation Sketch**:
```python
@app.command()
def verify(
    path: Path = typer.Argument(Path("."), help="Path to verify"),
    timeout: int = typer.Option(30, "--timeout", "-t"),
    watch: bool = typer.Option(False, "--watch", "-w"),
) -> None:
    """Symbolically verify contracts (Core functions only)."""

    # Check CrossHair installation
    if not is_crosshair_installed():
        console.print("[red]CrossHair not installed.[/red]")
        console.print("Install: pip install crosshair-tool")
        console.print("Or use: pip install python-invar[verify]")
        raise typer.Exit(1)

    # Collect Core files
    core_files = []
    shell_files = []

    for file_info in scan_project(path):
        if file_info.is_core:
            # Check for unsupported imports
            unsupported = check_unsupported_imports(file_info)
            if unsupported:
                console.print(f"[yellow]Skipping {file_info.path}:[/yellow] uses {unsupported}")
                continue
            core_files.append(file_info.path)
        else:
            shell_files.append(file_info.path)

    if shell_files:
        console.print(f"[dim]Skipping {len(shell_files)} Shell files (use 'invar test' for those)[/dim]")

    if not core_files:
        console.print("No verifiable Core files found.")
        return

    # Run CrossHair
    console.print(f"Verifying {len(core_files)} Core files...")

    cmd = ["crosshair", "check", *core_files,
           "--per_condition_timeout", str(timeout)]
    if watch:
        cmd.append("--watch")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print("[green]All contracts verified![/green]")
    else:
        console.print("[yellow]Some contracts could not be verified.[/yellow]")
        console.print("Try 'invar test' for probabilistic testing.")

    raise typer.Exit(result.returncode)

# Helper: Check for unsupported imports
UNSUPPORTED_IMPORTS = {
    "numpy", "pandas", "scipy", "sklearn",
    "tensorflow", "torch", "cv2",
    "requests", "httpx", "aiohttp",
    "random",  # Non-deterministic
}

def check_unsupported_imports(file_info) -> list[str]:
    """Return list of unsupported imports in file."""
    unsupported = []
    for imp in file_info.imports:
        module = imp.split(".")[0]
        if module in UNSUPPORTED_IMPORTS:
            unsupported.append(module)
    return unsupported
```

#### E1: CRUXEval Experiment

**Goal**: Validate that contracts improve LLM code understanding.

**Status**: Ready to start (research task, no code changes to Invar)

**Effort**: 2 days

**Tasks**:
```
□ 1. Setup (Day 1 morning)
     ├── Clone CRUXEval dataset
     ├── Select 100 function subset
     ├── Set up evaluation harness
     └── Configure Claude API access

□ 2. Contract annotation (Day 1 afternoon)
     ├── Write @pre/@post for 100 functions
     ├── Add doctest examples
     ├── Validate contracts with deal
     └── Store in structured format

□ 3. Experiment execution (Day 2 morning)
     ├── Run baseline (code only)
     ├── Run with contracts
     ├── Record all responses
     └── Score correctness

□ 4. Analysis (Day 2 afternoon)
     ├── Calculate pass@1 for both groups
     ├── Statistical significance test
     ├── Identify where contracts helped most
     └── Write up findings

□ 5. Documentation
     ├── Experiment methodology
     ├── Results summary
     ├── Add to proposal as evidence
     └── Consider blog post / paper
```

### 12.3 Verification Workflow

After Tier 0 completion, the recommended workflow is:

```
┌─────────────────────────────────────────────────────────────────┐
│                  Complete Verification Workflow                  │
│                                                                  │
│  Developer writes code + contracts                               │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  invar guard                                                ││
│  │  Static analysis: contracts exist, no forbidden imports     ││
│  └─────────────────────────────────────────────────────────────┘│
│         │ Pass                                                   │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  pytest --doctest-modules                                   ││
│  │  Run example-based tests from doctests                      ││
│  └─────────────────────────────────────────────────────────────┘│
│         │ Pass                                                   │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  invar test (Hypothesis)                                    ││
│  │  Property-based testing: 100+ random inputs                 ││
│  │  Works for: ALL functions with contracts                    ││
│  └─────────────────────────────────────────────────────────────┘│
│         │ Pass                                                   │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  invar verify (CrossHair) [Optional, Core only]             ││
│  │  Symbolic verification: prove for ALL inputs                ││
│  │  Works for: Core functions without C extensions             ││
│  │  Skips: Shell, numpy/pandas, non-deterministic              ││
│  └─────────────────────────────────────────────────────────────┘│
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Verification Complete                                      ││
│  │                                                             ││
│  │  Core functions: Mathematically proven ✓                    ││
│  │  Shell functions: Probabilistically tested ✓                ││
│  │  Unsupported: Best-effort with Hypothesis ✓                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 12.4 pyproject.toml Changes

```toml
[project.optional-dependencies]
# Existing
dev = ["pytest", "mypy", "ruff", ...]

# New: Verification extras
test = ["hypothesis>=6.0"]  # Usually already via deal
verify = ["crosshair-tool>=0.0.50"]
all = ["python-invar[test,verify]"]
```

### 12.5 Timeline

```
Week 1:
├── Day 1-2: Implement invar test
│   ├── Morning: Core implementation
│   ├── Afternoon: Edge cases + tests
│   └── Evening: Documentation
│
├── Day 3-4: Implement invar verify
│   ├── Morning: Core implementation
│   ├── Afternoon: Limitation handling
│   └── Evening: Documentation
│
└── Day 5: Integration
    ├── Update INVAR.md
    ├── Update CLAUDE.md
    └── Prepare release notes

Week 2:
├── Day 1-2: CRUXEval experiment
│   ├── Setup + annotation
│   └── Execution
│
├── Day 3: Analysis + writeup
│
└── Day 4-5: Release
    ├── v0.5.0 release
    ├── Blog post / announcement
    └── Community feedback collection
```

### 12.6 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| `invar test` coverage | 100% Core functions | Runs on all contracted functions |
| `invar verify` coverage | 80% Core functions | Skips only unsupported imports |
| CRUXEval improvement | +5% pass@1 | Contracts vs baseline |
| Documentation | Complete | All new commands documented |
| Tests | 90%+ coverage | New CLI commands tested |

### 12.7 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| deal.cases has bugs | Low | Medium | Pin deal version, report issues |
| CrossHair too slow | Medium | Low | Adjust default timeout, document |
| Too many unsupported imports | Medium | Medium | Clear skip messages, fallback to test |
| CRUXEval shows no improvement | Low | High | Analyze why, adjust methodology |
| Community adoption low | Medium | Medium | Write tutorials, examples |

---

## 13. Multi-Layer Purity Detection

**Proposal ID**: B4
**Priority**: Tier 1 (Short-term)
**Effort**: 3-4 days
**Dependencies**: None

### 13.1 Problem Statement

When code references a function from a third-party library, how can the agent determine if that function is pure?

```python
from pandas import DataFrame
from some_lib import process_data

@pre(lambda df: len(df) > 0)
@post(lambda result: result is not None)
def analyze(df: DataFrame) -> dict:
    return process_data(df)  # Is process_data pure?
```

Current Invar uses a **blacklist approach** in `purity.py`, but this has fundamental limitations:

| Approach | Problem |
|----------|---------|
| Blacklist | Cannot enumerate all impure functions |
| Whitelist | Too restrictive, cannot cover all libraries |
| Assume unknown = pure | Dangerous, misses violations |
| Assume unknown = impure | Too conservative, blocks valid code |

### 13.2 Solution: Multi-Layer Detection with Agent Decision Support

Instead of trying to make the tool omniscient, we provide rich context to help the agent decide.

```
┌─────────────────────────────────────────────────────────────┐
│              Purity Detection Pyramid (Revised)              │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Agent Decision Support                            │
│           Rich context output for agent judgment            │
│           (Agent IS the LLM — no separate API call)         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: User Configuration                                │
│           [tool.invar.purity] pure = ["lib.func"]           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Heuristic Analysis                                │
│           Name patterns, type patterns, docstring keywords  │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Known Impure (Built-in Blacklist)                 │
│           os, sys, open, requests, random.*, datetime.now   │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight**: The agent running `invar guard` is already an LLM. Instead of calling another LLM API, we provide enough context for the agent to decide directly.

### 13.3 Layer Details

#### Layer 1: Built-in Blacklist (Current)

```python
# src/invar/core/purity.py (existing)
FORBIDDEN_MODULES = {"os", "sys", "subprocess", "pathlib", ...}
FORBIDDEN_CALLS = {"open", "print", "input", ...}
```

#### Layer 2: Heuristic Analysis (New)

```python
# src/invar/core/purity_heuristics.py

@dataclass
class HeuristicResult:
    likely_pure: bool
    confidence: float  # 0.0 - 1.0
    hints: list[str]

# Name patterns suggesting impurity
IMPURE_NAME_PATTERNS = [
    r"^read_", r"^write_", r"^save_", r"^load_",
    r"^fetch_", r"^send_", r"^delete_", r"^update_",
    r"^connect_", r"^open_", r"^close_",
    r"^print_", r"^log_", r"^emit_",
    r"_to_file$", r"_to_disk$", r"_to_db$",
]

# Name patterns suggesting purity
PURE_NAME_PATTERNS = [
    r"^calculate_", r"^compute_", r"^parse_",
    r"^validate_", r"^transform_", r"^convert_",
    r"^is_", r"^has_", r"^get_",
    r"^from_", r"^to_",
]

# Type hints suggesting impurity
IMPURE_TYPE_HINTS = [
    # Return None with no mutable args → likely side effect
    (r"-> None$", "Returns None, suggests side effect"),
    # Path-like parameters
    (r": (Path|str).*path", "Has path parameter"),
    (r": (Path|str).*file", "Has file parameter"),
    # I/O types
    (r": (File|IO|Stream|Connection|Socket)", "Has I/O type"),
]

# Docstring keywords suggesting impurity
IMPURE_DOC_KEYWORDS = [
    "writes to", "reads from", "saves", "loads",
    "modifies", "mutates", "side effect",
    "file", "disk", "database", "network", "API",
    "sends", "receives", "connects",
]

def analyze_purity_heuristic(
    func_name: str,
    signature: str | None,
    docstring: str | None,
) -> HeuristicResult:
    """
    Guess purity based on heuristics.

    >>> analyze_purity_heuristic("read_csv", "def read_csv(path: str) -> DataFrame", "Load data from file")
    HeuristicResult(likely_pure=False, confidence=0.9, hints=["name: read_*", "param: path", "doc: 'Load'"])

    >>> analyze_purity_heuristic("calculate_sum", "def calculate_sum(a: int, b: int) -> int", "Add two numbers")
    HeuristicResult(likely_pure=True, confidence=0.7, hints=["name: calculate_*", "pure signature"])
    """
    hints = []
    impure_score = 0
    pure_score = 0

    # Check name patterns
    for pattern in IMPURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name pattern: {pattern}")
            impure_score += 2

    for pattern in PURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name suggests pure: {pattern}")
            pure_score += 1

    # Check type hints
    if signature:
        for pattern, reason in IMPURE_TYPE_HINTS:
            if re.search(pattern, signature):
                hints.append(reason)
                impure_score += 2

        # Returns non-None → more likely pure
        if "->" in signature and "None" not in signature:
            hints.append("Returns value (not None)")
            pure_score += 1

    # Check docstring
    if docstring:
        doc_lower = docstring.lower()
        for keyword in IMPURE_DOC_KEYWORDS:
            if keyword in doc_lower:
                hints.append(f"Docstring contains: '{keyword}'")
                impure_score += 1

    # Calculate result
    total = impure_score + pure_score
    if total == 0:
        return HeuristicResult(likely_pure=True, confidence=0.5, hints=["No indicators found"])

    likely_pure = pure_score > impure_score
    confidence = abs(pure_score - impure_score) / total

    return HeuristicResult(likely_pure, min(confidence, 0.9), hints)
```

#### Layer 3: User Configuration (New)

```toml
# pyproject.toml
[tool.invar.purity]
# User declares these as pure (override heuristics)
pure = [
    "pandas.DataFrame.groupby",
    "pandas.DataFrame.sort_values",
    "numpy.sum",
    "numpy.mean",
]

# User declares these as impure
impure = [
    "mylib.utils.cached_compute",  # Has memoization side effect
]
```

#### Layer 4: Agent Decision Support (New)

When purity cannot be determined, provide rich context for the agent:

```python
@dataclass
class UnknownPurityContext:
    """Rich context to help agent determine purity."""
    call_expr: str
    qualified_name: str
    location: str
    signature: str | None
    docstring: str | None
    heuristic: HeuristicResult
    similar_known: list[tuple[str, bool, str]]  # (name, is_pure, reason)

def format_for_agent(ctx: UnknownPurityContext) -> dict:
    """
    Format unknown purity with rich context for agent decision.
    Returns JSON structure for --agent mode.
    """
    return {
        "type": "unknown_purity",
        "call": ctx.call_expr,
        "function": ctx.qualified_name,
        "location": ctx.location,
        "context": {
            "signature": ctx.signature,
            "docstring": ctx.docstring[:200] if ctx.docstring else None,
            "heuristic": {
                "likely_pure": ctx.heuristic.likely_pure,
                "confidence": ctx.heuristic.confidence,
                "hints": ctx.heuristic.hints,
            },
            "similar_known": [
                {"name": n, "pure": p, "reason": r}
                for n, p, r in ctx.similar_known
            ],
        },
        "suggested_action": {
            "if_pure": f'[tool.invar.purity]\npure = ["{ctx.qualified_name}"]',
            "if_impure": "Move call to Shell layer",
        },
    }
```

### 13.4 Example Output

```
$ invar guard --agent

{
  "violations": [...],
  "unknown_purity": [
    {
      "type": "unknown_purity",
      "call": "df.groupby('category').agg({'value': 'sum'})",
      "function": "pandas.DataFrame.groupby",
      "location": "src/myapp/core/aggregator.py:42",
      "context": {
        "signature": "groupby(by, axis=0, ...) -> DataFrameGroupBy",
        "docstring": "Group DataFrame using a mapper or by columns.",
        "heuristic": {
          "likely_pure": true,
          "confidence": 0.65,
          "hints": [
            "Name suggests pure: group*",
            "Returns value (not None)",
            "No I/O keywords in docstring"
          ]
        },
        "similar_known": [
          {"name": "pandas.DataFrame.sort_values", "pure": true, "reason": "returns new DataFrame"},
          {"name": "pandas.DataFrame.filter", "pure": true, "reason": "returns subset"},
          {"name": "pandas.read_csv", "pure": false, "reason": "file I/O"}
        ]
      },
      "suggested_action": {
        "if_pure": "[tool.invar.purity]\npure = [\"pandas.DataFrame.groupby\"]",
        "if_impure": "Move call to Shell layer"
      }
    }
  ]
}
```

### 13.5 Agent Workflow Integration

```
Agent runs invar guard
        │
        ▼
Guard detects unknown purity
        │
        ▼
┌───────────────────────────────────────┐
│ Agent receives rich context:          │
│ - Function signature                  │
│ - Docstring                           │
│ - Heuristic analysis                  │
│ - Similar known functions             │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Agent reasoning (internal):           │
│                                       │
│ "pandas.DataFrame.groupby..."         │
│ - Returns DataFrameGroupBy (not None) │
│ - Similar to SQL GROUP BY             │
│ - sort_values is pure, this is too    │
│ - Heuristics say likely pure (65%)    │
│                                       │
│ Conclusion: This is PURE              │
└───────────────────────────────────────┘
        │
        ▼
Agent updates pyproject.toml:
  [tool.invar.purity]
  pure = ["pandas.DataFrame.groupby"]
        │
        ▼
Agent runs invar guard again
        │
        ▼
✓ All checks passed
```

### 13.6 Design Philosophy

This design follows the **Agent-Native** principle:

```
Tool provides information ──► Agent makes decisions
      (invar guard)              (Claude/GPT)

Tool's job:                  Agent's job:
├── Detect issues            ├── Understand context
├── Collect context          ├── Apply knowledge
├── Format output            ├── Make judgment
└── Suggest actions          └── Execute fix
```

**Key principle**: Don't make the tool do what the agent already can. The agent IS an LLM — leverage its knowledge directly instead of calling another LLM API.

### 13.7 Implementation Tasks

```
□ Phase 1: Heuristic Analysis (1 day)
  ├── Create src/invar/core/purity_heuristics.py
  ├── Implement name/type/docstring pattern matching
  ├── Add tests for heuristic accuracy
  └── Integrate with existing purity.py

□ Phase 2: User Configuration (0.5 day)
  ├── Add [tool.invar.purity] config parsing
  ├── Support pure = [...] and impure = [...] lists
  ├── Override heuristics with config
  └── Document in INVAR.md

□ Phase 3: Context Collection (1 day)
  ├── Extract signature/docstring from third-party modules
  ├── Build similar_known database for common libraries
  ├── Create UnknownPurityContext data structure
  └── JSON output for --agent mode

□ Phase 4: Integration (0.5 day)
  ├── Update guard command to use new purity detection
  ├── Add unknown_purity to violation output
  ├── Human-readable format for non-agent mode
  └── Documentation and examples

□ Phase 5: Known Purity Database (1 day)
  ├── Curate purity annotations for popular libraries
  │   ├── pandas (transformations vs I/O)
  │   ├── numpy (computations vs file ops)
  │   ├── json (loads/dumps vs load/dump)
  │   └── collections, itertools, functools
  ├── Ship as built-in resource
  └── Allow user contributions
```

### 13.8 Success Criteria

| Metric | Target |
|--------|--------|
| Heuristic accuracy | >80% on known functions |
| False positive rate | <5% (pure marked as impure) |
| False negative rate | <10% (impure marked as pure) |
| Agent decision success | >90% correct after viewing context |
| Configuration adoption | Users add 5+ entries on average |

### 13.9 Why This Matters for Agents

1. **Reduces False Alarms**: Without this, agents see many warnings for actually-pure functions, causing noise
2. **Enables Self-Service**: Agents can resolve purity questions without human intervention
3. **Builds Knowledge Over Time**: Config file accumulates purity decisions for the project
4. **Follows Agent-Native**: Provides information, lets agent decide

---

## 14. Tier 1 Development Plan

This section contains the detailed development plan for short-term features, to be implemented after Tier 0 completion.

### 14.1 Tier 1 Overview

| ID | Proposal | Source | Effort | Dependencies |
|----|----------|--------|--------|--------------|
| **C2** | @must_use | Move | 1-2 days | None |
| **B4** | Multi-Layer Purity Detection | Agent-Native | 3-4 days | None |
| **C1** | @invariant | Dafny | 2-3 days | None |
| **C3** | Contract Composition | Idris | 1-2 days | None |
| **C4** | Strategy Inference | icontract-hypothesis | 2-3 days | A1 (invar test) |

**Total Estimated Effort**: 10-14 days

### 14.2 C2: @must_use (Must-Use Return Values)

**Priority**: ★★★★★ (Highest ROI in Tier 1)
**Effort**: 1-2 days
**Dependencies**: None

#### Problem Statement

Ignored return values are one of the most common sources of bugs:

```python
def validate(data: dict) -> Result[ValidData, list[Error]]:
    """Validate input, returning errors if invalid."""
    ...

# Bug: Error silently ignored!
validate(user_input)
data = process(user_input)  # May crash later with confusing error
```

#### Design

```python
from invar import must_use

@must_use("Error must be handled")
def validate(data: dict) -> Result[ValidData, list[Error]]:
    ...

@must_use("Resource handle must be processed")
def allocate_buffer(size: int) -> Buffer:
    ...

# Guard detects and warns:
# WARNING: must_use_ignored at src/processor.py:42
#   Return value of validate() ignored
#   Hint: Error must be handled
```

#### Implementation

```python
# src/invar/core/must_use.py

from typing import TypeVar, Callable

F = TypeVar('F', bound=Callable)

def must_use(reason: str = "") -> Callable[[F], F]:
    """
    Mark function return value as must-use.
    Actual enforcement is in Guard static analysis.

    >>> @must_use("Error must be handled")
    ... def may_fail() -> Result[int, str]:
    ...     return Ok(42)
    >>> may_fail.__invar_must_use__
    'Error must be handled'
    """
    def decorator(func: F) -> F:
        func.__invar_must_use__ = reason or "Return value must be used"
        return func
    return decorator
```

```python
# src/invar/core/rules.py - New rule

def check_must_use(file_info: FileInfo) -> list[Violation]:
    """
    Detect ignored return values of @must_use functions.

    >>> # Given: @must_use def validate(): ...
    >>> # Code: validate(x)  # no assignment
    >>> check_must_use(file_info)
    [Violation(rule="must_use_ignored", ...)]
    """
    violations = []
    must_use_funcs = collect_must_use_functions(file_info)

    for call in find_all_calls(file_info.ast):
        func_name = get_call_target(call)

        if func_name in must_use_funcs:
            if not is_return_value_used(call):
                violations.append(Violation(
                    severity=Severity.WARNING,
                    rule="must_use_ignored",
                    message=f"Return value of {func_name}() ignored",
                    hint=must_use_funcs[func_name],
                    suggestion=generate_fix_suggestion(call, func_name),
                ))

    return violations

def is_return_value_used(call: ast.Call) -> bool:
    """
    Check if call's return value is used.

    Used: x = func(), if func():, return func(), other(func())
    Unused: func()  # standalone expression statement
    """
    parent = get_parent_node(call)

    if isinstance(parent, ast.Expr):
        return False  # Standalone expression → unused
    return True  # Conservative: assume used
```

#### Tasks

```
□ Phase 1: Core Implementation (0.5 day)
  ├── Create src/invar/core/must_use.py
  ├── Implement @must_use decorator
  ├── Add __invar_must_use__ attribute
  └── Unit tests for decorator

□ Phase 2: Guard Integration (0.5 day)
  ├── Add must_use_ignored rule to rules.py
  ├── Implement is_return_value_used() analysis
  ├── Collect @must_use functions from imports
  └── Integration tests

□ Phase 3: Cross-file Analysis (0.5 day)
  ├── Track @must_use across module boundaries
  ├── Handle from x import y patterns
  ├── Cache must_use metadata for performance
  └── Edge case tests

□ Phase 4: Documentation (0.5 day)
  ├── Update INVAR.md
  ├── Add examples to README
  ├── Document in invar rules output
  └── Add to RULE_META
```

#### Agent Value Analysis

| Scenario | Without @must_use | With @must_use |
|----------|-------------------|----------------|
| Error handling | Silent bug, crash later | Immediate warning |
| Resource management | Leaked resources | Explicit handling required |
| Debug time | Hours tracing back | Seconds to fix |

**Necessity**: ★★★★★ — Highest ROI. Simple implementation, catches extremely common bugs. Rust's #[must_use] proves this pattern's value.

### 14.3 C1: @invariant (Loop Invariants)

**Priority**: ★★★★
**Effort**: 2-3 days
**Dependencies**: None

#### Problem Statement

Loops are the most bug-prone constructs. Without invariants, debugging requires mentally simulating each iteration:

```python
def binary_search(arr: list[int], target: int) -> int:
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1  # Bug: should be mid + 1 only if mid != target
        else:
            hi = mid
    return lo if lo < len(arr) and arr[lo] == target else -1
```

#### Design

```python
from invar import invariant

def binary_search(arr: list[int], target: int) -> int:
    """
    >>> binary_search([1, 2, 3, 4, 5], 3)
    2
    >>> binary_search([1, 2, 3, 4, 5], 6)
    -1
    """
    lo, hi = 0, len(arr)

    while lo < hi:
        # Loop invariants: checked at start of each iteration
        invariant(0 <= lo <= hi <= len(arr))
        invariant(target not in arr[:lo])  # Already searched left
        invariant(target not in arr[hi:])  # Already searched right

        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        elif arr[mid] > target:
            hi = mid
        else:
            return mid

    return -1
```

#### Implementation

```python
# src/invar/core/invariant.py

import os

_INVAR_CHECK = os.environ.get("INVAR_CHECK", "1") == "1"

class InvariantViolation(Exception):
    """Raised when a loop invariant is violated."""
    pass

def invariant(condition: bool, message: str = "") -> None:
    """
    Assert loop invariant. Checked at runtime when INVAR_CHECK=1.

    Place at the START of loop body to check condition each iteration.

    >>> invariant(True)  # OK
    >>> invariant(False, "x must be positive")
    Traceback (most recent call last):
    InvariantViolation: Loop invariant violated: x must be positive
    """
    if _INVAR_CHECK and not condition:
        msg = f"Loop invariant violated: {message}" if message else "Loop invariant violated"
        raise InvariantViolation(msg)
```

```python
# src/invar/core/rules.py - New rule

def check_loop_invariant(symbol: Symbol) -> list[Violation]:
    """
    Detect complex loops without invariants.

    Complexity threshold:
    - Loop body > 5 lines
    - Nested loops
    - Multiple loop variables
    """
    violations = []

    for loop in find_loops(symbol.body):
        if is_complex_loop(loop) and not has_invariant_call(loop):
            violations.append(Violation(
                severity=Severity.INFO,
                rule="missing_loop_invariant",
                message=f"Complex loop without invariant at line {loop.lineno}",
                hint="Consider adding invariant() to document loop behavior",
                suggestion=suggest_invariant(loop),
            ))

    return violations

def suggest_invariant(loop: ast.While | ast.For) -> str:
    """Generate invariant suggestions based on loop structure."""
    suggestions = []
    loop_vars = extract_loop_variables(loop)

    for var in loop_vars:
        if looks_like_index(var):
            suggestions.append(f"invariant(0 <= {var} <= len(...))")
        elif looks_like_accumulator(var):
            suggestions.append(f"invariant({var} >= initial_value)")

    return "\n".join(suggestions) if suggestions else "invariant(condition)"
```

#### Tasks

```
□ Phase 1: Core Implementation (0.5 day)
  ├── Create src/invar/core/invariant.py
  ├── Implement invariant() function
  ├── Add INVAR_CHECK environment toggle
  └── Unit tests

□ Phase 2: Guard Detection (1 day)
  ├── Implement is_complex_loop() heuristic
  ├── Detect invariant() calls in loops
  ├── Add missing_loop_invariant rule
  └── Implement suggest_invariant()

□ Phase 3: Hypothesis/CrossHair Integration (0.5 day)
  ├── Verify invariant works with deal.cases
  ├── Test with CrossHair symbolic execution
  ├── Document interaction with verification tools
  └── Integration tests

□ Phase 4: Documentation (0.5 day)
  ├── Update INVAR.md with invariant section
  ├── Add binary_search example
  ├── Document when to use invariants
  └── Add to CLAUDE.md workflow
```

#### Agent Value Analysis

```
Without @invariant:
┌────────────────────────────────────────────────────────────┐
│  Test fails at iteration 47                                │
│  Agent: "Which variable went wrong? lo? hi? mid?"          │
│  → Multiple debug iterations                               │
│  → Trial-and-error fixes                                   │
└────────────────────────────────────────────────────────────┘

With @invariant:
┌────────────────────────────────────────────────────────────┐
│  InvariantViolation: 0 <= lo <= hi violated               │
│  At iteration 3: lo=5, hi=4                               │
│  Agent: "lo exceeded hi at iteration 3"                   │
│  → Immediate insight: mid calculation issue               │
│  → Single targeted fix                                    │
└────────────────────────────────────────────────────────────┘
```

**Necessity**: ★★★★ — High value for algorithmic code. Loops are where most bugs hide. Synergizes with Hypothesis (finds invariant-breaking inputs) and CrossHair (proves invariants hold).

### 14.4 C3: Contract Composition

**Priority**: ★★★
**Effort**: 1-2 days
**Dependencies**: None

#### Problem Statement

Repetitive contract definitions violate DRY:

```python
@pre(lambda arr: len(arr) > 0 and arr == sorted(arr))
def binary_search(arr, target): ...

@pre(lambda arr: len(arr) > 0 and arr == sorted(arr))
def find_median(arr): ...

@pre(lambda arr: len(arr) > 0 and arr == sorted(arr))
def interpolation_search(arr, target): ...
```

#### Design

```python
from invar import Contract, pre

# Define reusable contracts
NonEmpty = Contract(lambda x: len(x) > 0, "non-empty")
Sorted = Contract(lambda x: x == sorted(x), "sorted")
AllPositive = Contract(lambda x: all(i > 0 for i in x), "all positive")

# Compose with operators
SortedNonEmpty = NonEmpty & Sorted  # AND

@pre(SortedNonEmpty)
def binary_search(arr, target): ...

@pre(SortedNonEmpty)
def find_median(arr): ...

@pre(NonEmpty | AllPositive)  # OR
def flexible_function(data): ...

@pre(~NonEmpty)  # NOT (require empty)
def initialize(container): ...
```

#### Implementation

```python
# src/invar/core/contract.py

from dataclasses import dataclass
from typing import Callable, Any
import deal

@dataclass
class Contract:
    """
    Composable contract with &, |, ~ operators.

    >>> NonEmpty = Contract(lambda x: len(x) > 0, "non-empty")
    >>> Sorted = Contract(lambda x: x == sorted(x), "sorted")
    >>> combined = NonEmpty & Sorted
    >>> combined.check([1, 2, 3])
    True
    >>> combined.check([])
    False
    """
    predicate: Callable[[Any], bool]
    description: str

    def check(self, value: Any) -> bool:
        return self.predicate(value)

    def __and__(self, other: "Contract") -> "Contract":
        return Contract(
            predicate=lambda x: self.check(x) and other.check(x),
            description=f"({self.description} AND {other.description})"
        )

    def __or__(self, other: "Contract") -> "Contract":
        return Contract(
            predicate=lambda x: self.check(x) or other.check(x),
            description=f"({self.description} OR {other.description})"
        )

    def __invert__(self) -> "Contract":
        return Contract(
            predicate=lambda x: not self.check(x),
            description=f"NOT({self.description})"
        )

    def __call__(self, *args, **kwargs) -> bool:
        """Allow using as deal.pre predicate."""
        value = args[0] if args else list(kwargs.values())[0]
        return self.check(value)


def pre(*contracts: Contract):
    """
    Decorator accepting Contract objects.

    >>> @pre(NonEmpty & Sorted)
    ... def my_func(data): return data[0]
    """
    def combined(*args, **kwargs):
        value = args[0] if args else list(kwargs.values())[0]
        return all(c.check(value) for c in contracts)

    return deal.pre(combined)
```

```python
# src/invar/contracts/__init__.py - Standard Library

"""Standard contract library."""

from invar.core.contract import Contract

# Collections
NonEmpty = Contract(lambda x: len(x) > 0, "non-empty")
Sorted = Contract(lambda x: list(x) == sorted(x), "sorted")
Unique = Contract(lambda x: len(x) == len(set(x)), "unique")

# Numbers
Positive = Contract(lambda x: x > 0, "positive")
NonNegative = Contract(lambda x: x >= 0, "non-negative")
InRange = lambda lo, hi: Contract(lambda x: lo <= x <= hi, f"[{lo},{hi}]")
Percentage = InRange(0, 100)

# Strings
NonBlank = Contract(lambda s: s and s.strip(), "non-blank")

# Lists
AllPositive = Contract(lambda xs: all(x > 0 for x in xs), "all positive")
NoNone = Contract(lambda xs: None not in xs, "no None")
```

#### Tasks

```
□ Phase 1: Contract Class (0.5 day)
  ├── Create src/invar/core/contract.py
  ├── Implement Contract dataclass
  ├── Add __and__, __or__, __invert__
  └── Unit tests for operators

□ Phase 2: deal Integration (0.5 day)
  ├── Implement pre() wrapper
  ├── Ensure compatibility with deal.cases
  ├── Test with CrossHair
  └── Integration tests

□ Phase 3: Standard Library (0.5 day)
  ├── Create src/invar/contracts/__init__.py
  ├── Define common contracts
  ├── Document each contract
  └── Usage examples

□ Phase 4: Documentation (0.5 day)
  ├── Update INVAR.md
  ├── Add composition examples
  ├── Document standard library
  └── Add to CLAUDE.md
```

#### Agent Value Analysis

| Aspect | Without Composition | With Composition |
|--------|---------------------|------------------|
| Code duplication | High | None (DRY) |
| Readability | Lambda soup | Self-documenting names |
| Maintenance | Change N places | Change 1 place |
| Agent efficiency | Rewrite each time | Use standard library |

**Necessity**: ★★★ — Medium-high. Not critical for correctness, but significantly improves developer experience and code quality. Standard library enables Agent to write contracts faster.

### 14.5 C4: Strategy Inference

**Priority**: ★★★★
**Effort**: 2-3 days
**Dependencies**: A1 (invar test)

#### Problem Statement

Strict @pre constraints cause Hypothesis to reject most generated inputs:

```python
@pre(lambda x: 0 < x < 10)
@pre(lambda y: len(y) > 0 and all(c.isalpha() for c in y))
def process(x: int, y: str) -> str: ...

# Default Hypothesis:
# st.integers() → 99%+ rejected by @pre
# st.text() → 99%+ rejected by @pre
# Result: Only ~1% of tests are valid
```

#### Design

```python
# Automatic strategy inference from @pre

$ invar test --verbose

Analyzing process...
Inferred: x → integers(min_value=1, max_value=9)
Inferred: y → text(min_size=1, alphabet=ascii_letters)

Running 1000 tests...
Rejected: 0 (0%)
Passed: 1000 ✓
```

#### Implementation

```python
# src/invar/core/strategies.py

import ast
import re
from hypothesis import strategies as st
from typing import Any

# Pattern → Strategy mapping
PATTERNS = {
    # Numeric comparisons
    r"(\w+)\s*>\s*(\d+)": lambda m: {"min_value": int(m.group(2)) + 1},
    r"(\w+)\s*>=\s*(\d+)": lambda m: {"min_value": int(m.group(2))},
    r"(\w+)\s*<\s*(\d+)": lambda m: {"max_value": int(m.group(2)) - 1},
    r"(\w+)\s*<=\s*(\d+)": lambda m: {"max_value": int(m.group(2))},
    r"(\d+)\s*<\s*(\w+)\s*<\s*(\d+)": lambda m: {
        "min_value": int(m.group(1)) + 1,
        "max_value": int(m.group(3)) - 1
    },

    # Set membership
    r"(\w+)\s+in\s+\[([^\]]+)\]": lambda m: {
        "sampled_from": eval(f"[{m.group(2)}]")
    },

    # Length constraints
    r"len\((\w+)\)\s*>\s*(\d+)": lambda m: {"min_size": int(m.group(2)) + 1},
    r"len\((\w+)\)\s*>=\s*(\d+)": lambda m: {"min_size": int(m.group(2))},
    r"len\((\w+)\)\s*<\s*(\d+)": lambda m: {"max_size": int(m.group(2)) - 1},
}

def infer_strategy(
    pre_source: str,
    param_name: str,
    param_type: type
) -> st.SearchStrategy | None:
    """
    Parse @pre lambda to infer Hypothesis strategy.

    >>> infer_strategy("lambda x: 0 < x < 100", "x", int)
    integers(min_value=1, max_value=99)

    >>> infer_strategy("lambda x: x in ['a', 'b']", "x", str)
    sampled_from(['a', 'b'])
    """
    constraints = {}

    for pattern, extractor in PATTERNS.items():
        match = re.search(pattern, pre_source)
        if match and param_name in match.group(0):
            constraints.update(extractor(match))

    if not constraints:
        return None

    return build_strategy(constraints, param_type)

def build_strategy(constraints: dict, param_type: type) -> st.SearchStrategy:
    """Build Hypothesis strategy from extracted constraints."""

    if "sampled_from" in constraints:
        return st.sampled_from(constraints["sampled_from"])

    if param_type == int:
        return st.integers(
            min_value=constraints.get("min_value"),
            max_value=constraints.get("max_value"),
        )

    if param_type == str:
        return st.text(
            min_size=constraints.get("min_size", 0),
            max_size=constraints.get("max_size"),
        )

    if param_type == list:
        return st.lists(
            st.integers(),
            min_size=constraints.get("min_size", 0),
            max_size=constraints.get("max_size"),
        )

    return st.from_type(param_type)
```

```python
# src/invar/shell/cli.py - Enhanced test command

@app.command()
def test(
    path: Path = typer.Argument(Path(".")),
    count: int = typer.Option(100, "--count", "-n"),
    infer: bool = typer.Option(True, "--infer/--no-infer"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run property-based tests with strategy inference."""

    for file_info in scan_core_files(path):
        for symbol in file_info.symbols:
            if not symbol.contracts:
                continue

            func = get_function(file_info.path, symbol.name)
            strategies = {}

            if infer:
                for contract in symbol.contracts:
                    if contract.type == "pre":
                        for param in get_params(func):
                            strategy = infer_strategy(
                                contract.source,
                                param.name,
                                param.annotation
                            )
                            if strategy:
                                strategies[param.name] = strategy
                                if verbose:
                                    console.print(f"  Inferred: {param.name} → {strategy}")

            test_func = deal.cases(func, count=count, kwargs=strategies)
            test_func()
```

#### Tasks

```
□ Phase 1: Pattern Recognition (1 day)
  ├── Create src/invar/core/strategies.py
  ├── Implement PATTERNS dictionary
  ├── Parse common constraint patterns
  ├── Unit tests for each pattern

□ Phase 2: Strategy Building (0.5 day)
  ├── Implement build_strategy()
  ├── Support int, float, str, list types
  ├── Handle combined constraints
  └── Edge case tests

□ Phase 3: CLI Integration (0.5 day)
  ├── Add --infer flag to test command
  ├── Pass inferred strategies to deal.cases
  ├── Verbose output showing inferences
  └── Integration tests

□ Phase 4: Advanced Patterns (0.5 day)
  ├── all(x > 0 for x in ...) patterns
  ├── isinstance() patterns
  ├── Regex patterns
  └── Documentation
```

#### Agent Value Analysis

```
Without Strategy Inference:
┌────────────────────────────────────────────────────────────┐
│  @pre(lambda x: 1 <= x <= 10)                              │
│  def process(x: int): ...                                  │
│                                                            │
│  $ invar test --count 1000                                 │
│  Running... Rejected 990 samples (99%)                     │
│  Only 10 valid tests executed                              │
│                                                            │
│  Agent: "Tests passed but coverage is terrible"            │
└────────────────────────────────────────────────────────────┘

With Strategy Inference:
┌────────────────────────────────────────────────────────────┐
│  $ invar test --count 1000 --verbose                       │
│  Inferred: x → integers(min_value=1, max_value=10)        │
│  Running... Rejected 0 samples (0%)                        │
│  All 1000 tests executed                                   │
│                                                            │
│  Agent: "Full coverage, high confidence"                   │
└────────────────────────────────────────────────────────────┘
```

**Necessity**: ★★★★ — High value for testing. Without this, `invar test` has poor coverage on constrained functions. icontract-hypothesis proves this approach works.

### 14.6 Implementation Timeline

```
┌─────────────────────────────────────────────────────────────┐
│                 Tier 1 Implementation Timeline               │
│                                                              │
│  Week 1 (after Tier 0 completion):                          │
│  ├── Day 1-2: C2 @must_use                                  │
│  │   ├── Core decorator                                     │
│  │   ├── Guard rule                                         │
│  │   └── Documentation                                      │
│  │                                                          │
│  ├── Day 3-5: B4 Multi-Layer Purity                         │
│  │   ├── Heuristic analysis                                 │
│  │   ├── User configuration                                 │
│  │   └── Agent context output                               │
│  │                                                          │
│  Week 2:                                                    │
│  ├── Day 1-3: C1 @invariant                                 │
│  │   ├── Core function                                      │
│  │   ├── Guard detection                                    │
│  │   └── Verification tool integration                      │
│  │                                                          │
│  ├── Day 4-5: C3 Contract Composition                       │
│  │   ├── Contract class                                     │
│  │   └── Standard library                                   │
│  │                                                          │
│  Week 3:                                                    │
│  ├── Day 1-3: C4 Strategy Inference                         │
│  │   ├── Pattern recognition                                │
│  │   ├── Strategy building                                  │
│  │   └── CLI integration                                    │
│  │                                                          │
│  ├── Day 4-5: Integration & Release                         │
│  │   ├── Full test suite                                    │
│  │   ├── Documentation review                               │
│  │   └── v0.6.0 release                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 14.7 Success Criteria

| Feature | Metric | Target |
|---------|--------|--------|
| **C2 @must_use** | Bugs detected | >90% of ignored returns flagged |
| **B4 Purity** | False positive rate | <5% |
| **C1 @invariant** | Integration | Works with Hypothesis + CrossHair |
| **C3 Composition** | Standard library | 15+ predefined contracts |
| **C4 Inference** | Coverage improvement | >50% more valid test cases |

### 14.8 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| @must_use cross-file tracking complex | Medium | Low | Start with same-file, expand later |
| Heuristic false positives too high | Medium | Medium | Conservative defaults, user override |
| @invariant performance overhead | Low | Low | INVAR_CHECK=0 in production |
| Strategy inference incomplete | Medium | Low | Fall back to default strategies |
| Contract composition breaks deal | Low | High | Extensive integration tests |

### 14.9 Tier 1 Summary

| Proposal | Core Value | Agent Help | Necessity |
|----------|-----------|------------|-----------|
| **C2 @must_use** | Catch ignored returns | Direct problem pointing | ★★★★★ |
| **B4 Purity** | Third-party library handling | Decision context | ★★★★★ |
| **C1 @invariant** | Loop bug visibility | Precise error location | ★★★★ |
| **C3 Composition** | DRY contracts | Standard library | ★★★ |
| **C4 Inference** | Test efficiency | Automatic optimization | ★★★★ |

**Recommended Order**: C2 → B4 → C1 → C3 → C4

This order maximizes early value delivery while respecting dependencies (C4 requires A1 from Tier 0).

---

## 15. Tier 2 Development Plan

### 15.1 Tier 2 Overview

| ID | Proposal | Source | Effort | Dependencies | Status |
|----|----------|--------|--------|--------------|--------|
| **C5** | @must_close | Move | 2-3 days | None | **Active** |

**Total Estimated Effort**: 2-3 days

**Prerequisites**: Tier 1 completion not required (independent feature)

### 15.2 C5: @must_close (Resource Cleanup Verification)

#### Problem Statement

Agents frequently introduce resource leaks when:
1. Adding early return paths without cleanup
2. Missing exception handling that bypasses close() calls
3. Forgetting to close resources in conditional branches

Example buggy code:

```python
def process_file(path: str) -> str:
    f = open(path)
    if not f.readable():
        return ""  # BUG: f not closed
    content = f.read()
    f.close()
    return content
```

#### Design

```python
from invar import must_close

@must_close
class FileHandle:
    def __init__(self, path: str): ...
    def read(self) -> str: ...
    def close(self) -> None: ...

# Guard warning:
# [must_close] FileHandle may not be closed on line 4 (early return)
# Suggestion: Use context manager pattern:
#   with FileHandle(path) as f:
#       ...
```

#### Implementation

**Core Components** (in `src/invar/core/`):

```python
# core/resources.py

from dataclasses import dataclass
from typing import Set, List, Tuple

@dataclass
class CFGNode:
    """Control Flow Graph node."""
    id: int
    kind: str  # "entry", "exit", "return", "raise", "normal"
    line: int
    successors: List[int]
    predecessors: List[int]
    opens: Set[str]   # Resources opened at this node
    closes: Set[str]  # Resources closed at this node

@dataclass
class ResourceLeak:
    """Detected resource leak."""
    resource_type: str
    open_line: int
    leak_line: int
    leak_kind: str  # "early_return", "exception", "conditional"
    suggested_fix: str

def build_cfg(func_ast: ast.FunctionDef) -> List[CFGNode]:
    """
    Build control flow graph from function AST.

    @pre: func_ast is a valid FunctionDef node
    @post: result contains entry and exit nodes
    @post: all nodes are reachable from entry

    >>> import ast
    >>> code = "def f():\\n    x = 1\\n    return x"
    >>> tree = ast.parse(code).body[0]
    >>> cfg = build_cfg(tree)
    >>> len(cfg) >= 2  # At least entry and exit
    True
    """
    ...

def analyze_resource_paths(
    cfg: List[CFGNode],
    must_close_types: Set[str]
) -> List[ResourceLeak]:
    """
    Analyze all paths through CFG for unclosed resources.

    @pre: cfg is a valid control flow graph with entry/exit nodes
    @pre: must_close_types contains type names marked with @must_close
    @post: all returned leaks have valid line numbers

    >>> # Example: early return without close
    >>> # def f():
    >>> #     f = FileHandle()  # opens
    >>> #     if bad:
    >>> #         return  # leak!
    >>> #     f.close()
    >>> leaks = analyze_resource_paths(cfg, {"FileHandle"})
    >>> len(leaks) == 1
    True
    """
    ...
```

**Guard Rule** (in `src/invar/core/rules.py`):

```python
def check_must_close(file_info: FileInfo) -> List[Violation]:
    """
    Check that @must_close resources are closed on all paths.

    @pre: file_info contains valid AST
    @post: all violations have leak_line >= open_line
    """
    violations = []

    # 1. Find @must_close decorated classes
    must_close_types = find_must_close_types(file_info.source)

    # 2. For each function, build CFG and analyze
    for func in file_info.functions:
        cfg = build_cfg(func.ast_node)
        leaks = analyze_resource_paths(cfg, must_close_types)

        for leak in leaks:
            violations.append(Violation(
                rule_id="must_close",
                severity="WARNING",
                line=leak.leak_line,
                message=f"{leak.resource_type} may not be closed ({leak.leak_kind})",
                suggestion=leak.suggested_fix
            ))

    return violations
```

**Decorator** (in `src/invar/decorators.py`):

```python
def must_close(cls):
    """
    Mark a class as requiring explicit close() on all exit paths.

    Usage:
        @must_close
        class Connection:
            def close(self): ...

    Guard will warn if instances may not be closed.
    """
    cls._invar_must_close = True
    return cls
```

#### Tasks Breakdown

| Task | Effort | Description |
|------|--------|-------------|
| 1. CFG construction | 1 day | Build control flow graph from AST |
| 2. Path analysis | 0.5 day | DFS/BFS to find all paths to exit |
| 3. Resource tracking | 0.5 day | Track open/close along each path |
| 4. Guard rule | 0.5 day | Integrate into rules.py |
| 5. Tests + docs | 0.5 day | Coverage for edge cases |

**Total: 2-3 days**

#### Agent Value Analysis

| Aspect | Rating | Explanation |
|--------|--------|-------------|
| **Bug frequency** | ★★★★★ | Resource leaks are extremely common |
| **Detection accuracy** | ★★★★ | CFG analysis catches most cases |
| **Error clarity** | ★★★★★ | Points to exact leak location |
| **Fix guidance** | ★★★★★ | Suggests context manager pattern |
| **Automation** | ★★★★ | Static analysis, no runtime needed |

#### Edge Cases

1. **Nested resources**: Track each independently
2. **Conditional close**: Analyze both branches
3. **Exception paths**: `try/except/finally` handling
4. **Context managers**: Automatically satisfy @must_close
5. **Aliasing**: Conservative approach (warn on ambiguity)

#### Success Criteria

- [ ] Guard detects early return leaks
- [ ] Guard detects exception path leaks
- [ ] Guard suggests context manager pattern
- [ ] No false positives on proper cleanup
- [ ] Context managers recognized as valid

### 15.3 Tier 2 Summary

| Proposal | Core Value | Agent Help | Necessity |
|----------|-----------|------------|-----------|
| **C5 @must_close** | Resource leak prevention | Clear leak location + fix suggestion | ★★★★ |

**Note**: @transfer was evaluated and moved to Tier 3 due to Python's dynamic typing making accurate static ownership tracking impractical (<60% accuracy estimate).

---

## 16. CLI Agent-Friendliness Audit

This section audits the current Invar CLI commands for agent-friendliness and proposes improvements.

### 16.1 Current Command Audit

| Command | Human Mode | Agent Mode | Agent-Friendly? |
|---------|------------|------------|-----------------|
| `invar guard` | Pretty tables | `--agent` JSON with fixes | ✅ Good |
| `invar sig` | One-line signatures | `--json` with contracts | ✅ Good |
| `invar map` | Hot/Warm/Cold categories | `--json` with ref_count | ✅ Good |
| `invar rules` | Pretty table | `--json` with metadata | ✅ Good |
| `invar init` | Interactive prompts | No JSON mode | ⚠️ Needs work |
| `invar version` | Plain text | No JSON mode | ⚠️ Minor |

### 16.2 Detailed Analysis

#### invar guard --agent (Good Example)

```json
{
  "status": "passed",
  "summary": { "files_checked": 23, "errors": 0, "warnings": 56 },
  "fixes": [
    {
      "file": "src/invar/core/formatter.py",
      "line": 228,
      "rule": "internal_import",
      "severity": "warning",
      "message": "Function '_violation_to_fix' has internal imports: invar",
      "fix": {
        "action": "manual",
        "instruction": "Move imports to top of file or move function to Shell"
      },
      "rule_meta": {
        "category": "purity",
        "detects": "Import statement inside function body",
        "cannot_detect": ["Lazy imports for performance", "..."],
        "hint": "Move import to module top-level or justify with comment"
      }
    }
  ]
}
```

**Strengths:**
- Structured JSON with file, line, rule
- Fix instructions with action type
- Rule metadata including `cannot_detect` limitations
- Severity levels for prioritization

#### invar sig --json (Good Example)

```json
{
  "file": "src/invar/core/parser.py",
  "symbols": [
    {
      "name": "parse_source",
      "kind": "function",
      "line": 25,
      "signature": "(source: str, path: str) -> FileInfo | None",
      "docstring": "Parse Python source code...",
      "contracts": [{ "kind": "pre", "expression": "lambda source, path: ..." }]
    }
  ]
}
```

**Strengths:**
- Includes contracts (unique to Invar)
- Full docstrings with examples
- Line numbers for navigation

### 16.3 Deep Analysis: Agent Capability Assessment

Before proposing improvements, we must assess what modern AI agents (Claude, GPT-4) can already do:

| Capability | Agent Can Do? | Evidence |
|------------|---------------|----------|
| Remember `--agent` flag | ✅ Yes | CLAUDE.md guidance works |
| Filter by severity | ✅ Yes | Can parse JSON, use jq |
| Sort violations | ✅ Yes | Basic data manipulation |
| Find references | ✅ Yes | Serena's find_referencing_symbols |
| Detect breaking changes | ✅ Yes | pytest catches failures |

**Key Insight**: Many proposed improvements automate what agents already do well.

### 16.4 Revised Issue Assessment

| Issue | Original Severity | Revised Severity | Reasoning |
|-------|-------------------|------------------|-----------|
| No auto-detection | Medium | **Low** | Agent rarely forgets with CLAUDE.md |
| No counterexamples | High | **Medium** | Only 2/12 rules benefit |
| No priority ranking | Medium | **Low** | Agent can sort existing data |
| No dependency info | High | **Low** | Serena + pytest provide this |
| Missing commands | High | **High** | A1/A2 are genuinely needed |

### 16.5 Revised Improvement Proposals

#### ~~A. INVAR_MODE env var~~ → **TTY Auto-Detection** (Recommended)

**Problem with INVAR_MODE**: Requires configuration, adds complexity.

**Better Solution**: Detect if stdout is a TTY (interactive terminal).

```python
# In shell/cli.py
import sys

def get_output_mode() -> str:
    if not sys.stdout.isatty():  # Pipe or redirect
        return "json"
    return "text"
```

**Behavior:**
```bash
invar guard              # TTY → Human-readable
invar guard | jq         # Pipe → Auto JSON
invar guard > out.json   # Redirect → Auto JSON
```

**Effort**: 30 minutes
**Value**: ★★★★★ (truly automatic, no config needed)

#### ~~B. Counterexamples~~ → **Merged into A2 (invar verify)**

**Analysis**: Only 2 rules benefit from counterexamples:
- `missing_contract`: What input fails?
- `empty_contract`: Why is `lambda: True` insufficient?

**Better Approach**: When `invar verify` (CrossHair) finds a counterexample, include it in the violation output automatically.

```json
{
  "rule": "contract_violation",
  "counterexample": {
    "inputs": {"x": -1, "y": 0},
    "raises": "ZeroDivisionError"
  }
}
```

**Decision**: Not a separate feature. Part of A2 implementation.

#### ~~C. Priority ranking~~ → **Removed**

**Reasoning**: Agent can achieve the same result with existing data:

```python
# Agent's approach (already possible)
violations = guard_output["fixes"]
violations.sort(key=lambda v: (
    0 if v["severity"] == "error" else 1,
    -map_data.get(v["symbol"], {}).get("ref_count", 0)
))
```

**Decision**: Removed. Agent is capable enough.

#### ~~D. Impact analysis~~ → **Removed**

**Reasoning**:
1. Serena provides `find_referencing_symbols`
2. `pytest` catches breaking changes
3. `invar map` shows `ref_count`

**Decision**: Removed. Use existing tools.

### 16.6 Final Recommendations

| Original Proposal | Status | Action |
|-------------------|--------|--------|
| CLI-A: INVAR_MODE | **Replaced** | TTY auto-detection (30 min) |
| CLI-B: Counterexamples | **Merged** | Part of A2 (invar verify) |
| CLI-C: Priority ranking | **Removed** | Agent can sort |
| CLI-D: Impact analysis | **Removed** | Use Serena + pytest |

### 16.7 Retained Value: TTY Auto-Detection

**The only CLI improvement worth implementing:**

```python
# shell/cli.py
import sys

def is_agent_mode() -> bool:
    """Auto-detect agent mode based on TTY status."""
    # If stdout is not a TTY (pipe, redirect, subprocess), assume agent
    return not sys.stdout.isatty()
```

**Why this is Agent-Native:**
- Zero configuration required
- Works automatically in all agent contexts
- Humans still get pretty output in terminals
- True "default correct" behavior

### 16.8 Exit Code Specification (Retained)

| Code | Meaning | Agent Action |
|------|---------|--------------|
| 0 | All checks passed | Proceed |
| 1 | Errors found (blocks commit) | Fix errors first |
| 2 | Warnings only | Fix if touching those files |
| 3 | Configuration error | Check invar.toml |
| 4 | File not found | Verify paths |

### 16.9 Lessons Learned

**Don't underestimate agents.** Modern AI agents are highly capable:
- They can parse JSON and manipulate data
- They can use multiple tools together
- They can follow instructions in CLAUDE.md

**Focus on genuinely new capabilities**, not automation of existing ones:
- ✅ A1/A2 (invar test/verify): New verification capabilities
- ✅ C1-C5 (decorators): New contract expressiveness
- ❌ CLI-A/B/C/D: Automate what agents already do

---

## Appendix: Agent-Native Filtering Criteria

When evaluating proposals for Invar, we apply **Agent-Native filtering** to ensure features genuinely help AI agents:

### Inclusion Criteria

| Criterion | Description | Example |
|-----------|-------------|---------|
| **New capability** | Enables something agents couldn't do before | @must_use detects ignored returns |
| **Better error messages** | Helps agent understand and fix issues | Multi-layer purity provides context |
| **Reduces ambiguity** | Makes correct action clearer | @invariant pinpoints loop bugs |
| **Automation** | Agent can use without human intervention | Strategy inference auto-optimizes |

### Exclusion Criteria

| Criterion | Description | Example Removed |
|-----------|-------------|-----------------|
| **Human UX only** | Only improves human developer experience | ~~Guard LSP~~ (IDE integration) |
| **Syntax sugar** | Same capability, different syntax | ~~Refinement types~~ (= @pre + C3) |
| **Reduces checking** | Agent needs maximum error detection | ~~Ghost specs~~ (skips checks) |
| **IDE-dependent** | Requires graphical interface | ~~Real-time highlighting~~ |

### Removed Proposals

| Proposal | Reason | Alternative |
|----------|--------|-------------|
| D1: Refinement Types | Redundant with @pre + Contract Composition | Use C3 |
| D2: Ghost Specifications | Agent needs all checks, not selective | Use INVAR_CHECK=0 in production |
| D3: Guard LSP | Human IDE feature, not Agent-Native | Agents use CLI: `invar guard --agent` |

---

## Appendix: Conflict and Consistency Analysis

This section documents the systematic review of all active proposals for conflicts and inconsistencies.

### Active Proposals Summary

| Tier | ID | Proposal | Status |
|------|-----|----------|--------|
| Imm | CLI | TTY auto-detection | Active |
| 0 | A1 | invar test (Hypothesis) | Active |
| 0 | A2 | invar verify (CrossHair) + counterexamples | Active |
| 0 | E1 | CRUXEval experiment | Active |
| 1 | C1 | @invariant | Active |
| 1 | C2 | @must_use | Active |
| 1 | C3 | Contract Composition | Active |
| 1 | C4 | Strategy Inference | Active |
| 1 | B4 | Multi-Layer Purity | Active |
| 2 | C5 | @must_close | Active |

**Removed CLI proposals (Section 16.9 analysis):**
- ~~CLI-B: Counterexamples~~ → Merged into A2
- ~~CLI-C: Priority ranking~~ → Agent can sort existing data
- ~~CLI-D: Impact analysis~~ → Use Serena + pytest

### Inter-Proposal Conflict Analysis

| Proposal Pair | Relationship | Conflict? | Notes |
|---------------|--------------|-----------|-------|
| A1 ↔ A2 | Complementary | No | Hypothesis (probabilistic) + CrossHair (exhaustive) = complete coverage |
| C1 ↔ @pre/@post | Extends | No | @invariant for loops, @pre/@post for functions |
| C2 ↔ shell_result | Complementary | No | shell_result: return type. @must_use: caller handles it |
| C3 ↔ @pre/@post | Extends | No | Composition operators build on existing contracts |
| C4 ↔ A1 | Dependency | No | C4 optimizes A1, requires A1 first |
| B4 ↔ impure_call | Extends | No | B4 adds context to existing purity rules |
| C5 ↔ shell_result | Complementary | No | C5: resource lifecycle. shell_result: return type |
| C1 ↔ C3 | Compatible | No | @invariant can use composition: inv1 & inv2 |
| CLI (TTY) ↔ --agent | Supersedes | No | TTY detection makes --agent optional, not breaking |

**Result: No conflicts found between proposals.**

### Consistency with Existing Functionality

| Invar Feature | Proposal Impact | Consistent? |
|---------------|-----------------|-------------|
| Core/Shell separation | C5 applies to Shell (resources), C1/C2/C3 to Core (logic) | ✅ |
| @pre/@post contracts | C1/C3 extend expressiveness, C4 optimizes testing | ✅ |
| Guard rules | C2/C5/B4 add new rules in consistent format | ✅ |
| ICIDIV workflow | A1/A2 enhance Verify step, C1/C3 enhance Contract step | ✅ |
| Agent-Native design | All proposals are CLI-first with JSON output | ✅ |
| Law 5 (Verify Reflectively) | All proposals improve error messages and fix guidance | ✅ |

**Result: All proposals are consistent with existing Invar principles.**

### Implementation Dependencies

```
Immediate (Quick Win)
└── CLI: TTY auto-detection (no dependencies, 30 min)

Tier 0 (Independent)
├── A1: invar test ←──────────────────┐
├── A2: invar verify (includes counterexamples)
└── E1: CRUXEval                      │
                                      │
Tier 1                                │
├── C1: @invariant (independent)      │
├── C2: @must_use (independent)       │
├── C3: Contract Composition (independent)
├── C4: Strategy Inference ───────────┘
└── B4: Multi-Layer Purity (independent)

Tier 2
└── C5: @must_close (independent)
```

**Key Dependency:**
- C4 (Strategy Inference) requires A1 (invar test) to be implemented first

### Technical Clarifications Needed

| Item | Question | Recommendation |
|------|----------|----------------|
| Decorator source | Should @invariant/@must_use/@must_close extend deal or be invar-native? | Invar-native with deal compatibility |
| Guard categories | New categories for C2/C5/B4 rules? | Add "returns" (C2), "resources" (C5), extend "purity" (B4) |
| Naming convention | Consistent decorator naming? | ✅ Already consistent: lowercase with underscores |

### Conclusion

- **0 conflicts** between proposals
- **0 inconsistencies** with existing functionality
- **1 dependency** documented (C4→A1)
- **3 clarifications** identified for implementation phase
- **3 CLI proposals removed** (Section 16.9 analysis: Agent capable enough)

**Final active proposal count: 11** (down from 14 after CLI proposal review)

All proposals can proceed as planned.

---

## Appendix A: Tool Comparison

| Feature | Idris | Dafny | Move | Hypothesis | CrossHair | Instructor | Invar (current) | Invar (proposed) | Status |
|---------|-------|-------|------|------------|-----------|------------|-----------------|------------------|--------|
| Pre-conditions | Types | requires | - | (filter) | (constraint) | Pydantic | @pre | @pre | ✅ |
| Post-conditions | Types | ensures | - | (assert) | (prove) | Pydantic | @post | @post | ✅ |
| Loop invariants | - | invariant | - | @invariant | - | - | - | @invariant | Tier 1 |
| Termination | totality | decreases | - | - | - | - | - | ~~@terminates~~ | Tier 3 |
| ~~Ghost code~~ | - | ghost | - | - | - | - | - | - | Removed |
| Must-use returns | - | - | abilities | - | - | - | - | @must_use | Tier 1 |
| Resource safety | - | - | drop ability | - | - | - | - | @must_close | Tier 2 |
| ~~Ownership transfer~~ | - | - | abilities | - | - | - | - | ~~@transfer~~ | Tier 3 (impractical) |
| Property testing | - | - | - | @given | - | - | deal.cases | invar test | Tier 0 |
| Symbolic exec | - | - | - | (backend) | Yes | - | - | invar verify | Tier 0 |
| Shrinking | - | - | - | Yes | - | - | (via deal) | (via deal) | ✅ |
| Counterexamples | - | Yes | - | Yes | Yes | - | - | Yes | Tier 0 |
| Retry/feedback | - | - | - | - | - | **Yes** | - | (via Guard) | ✅ |
| Strategy inference | - | - | - | from_type | - | - | - | infer_strategy | Tier 1 |
| Contract composition | Types | - | - | - | - | - | - | & \| ~ operators | Tier 1 |
| Purity detection | (implicit) | (implicit) | abilities | - | - | - | blacklist | multi-layer | Tier 1 |
| ~~Refinement types~~ | Types | - | - | - | - | - | - | - | Removed |
| ~~Guard LSP~~ | - | LSP | - | - | - | - | - | - | Removed |
| Verification | Type check | Z3 | Bytecode | Runtime | Z3 (SMT) | Runtime | Guard | Guard + Z3 | ✅ |
| Guarantee | Proof | Proof | Proof | Probabilistic | Proof | Probabilistic | Static | Proof | — |
| Runtime | Compiled | Compiled | VM | Python | Python | Python | Python | Python | — |

## Appendix B: Research Connections

This proposal connects to our research foundation (see VISION.md):

| Research | Connection |
|----------|------------|
| Clover (contract completeness) | Refinement types express complete contracts |
| Reflexion (verbal reflection) | @invariant enables reflection on loop behavior |
| Parsel (decomposition) | Composed contracts support hierarchical design |
| AlphaCodium (test-first) | @ghost separates specification from implementation |
| Property-Based Testing | Contracts + Hypothesis = automatic integration tests |
| Hillel Wayne's insight | "Contracts are PBT invariants" validates our approach |
| CrossHair (symbolic execution) | Contracts + Z3 = formal proofs for ALL inputs |
| Dafny (SMT integration) | CrossHair brings Dafny-style verification to Python |
| Instructor (validation-retry) | "Validation errors = self-correction" validates Guard feedback loop |
| Instructor (llm_validator) | LLM-based validation could enhance contract quality checking |
| CRUXEval (code reasoning) | Input/output prediction maps to @pre/@post + doctests |
| EvalPlus (robustness) | Extended tests measure if contracts improve code quality |
| Python-by-Contract | 514 functions with contracts - foundation for Invar-bench |
| Agent-Native (Invar principle) | Multi-layer purity: tool provides context, agent decides (no extra LLM call) |
| Rust #[must_use] | Proven success: @must_use catches ignored returns |
| icontract-hypothesis | Strategy inference: parse @pre → efficient Hypothesis strategies |
| Idris first-class types | Contract composition: reusable, composable contracts with operators |

## Appendix C: References

### Languages
1. **Idris Language** — https://www.idris-lang.org/
2. **Idris 2 Documentation** — https://idris2.readthedocs.io/
3. **Dafny Language** — https://dafny.org/
4. **Dafny GitHub** — https://github.com/dafny-lang/dafny
5. **The Move Book** — https://move-book.com/
6. **Sui Move Concepts** — https://docs.sui.io/concepts/sui-move-concepts

### Testing & Verification Tools
7. **Hypothesis** — https://github.com/HypothesisWorks/hypothesis
8. **Hypothesis Documentation** — https://hypothesis.readthedocs.io/
9. **deal Library** — https://github.com/life4/deal
10. **deal Documentation** — https://deal.readthedocs.io/
11. **hypothesis-auto** — https://timothycrosley.github.io/hypothesis-auto/
12. **icontract-hypothesis** — https://github.com/mristin/icontract-hypothesis
13. **Pydantic Hypothesis Plugin** — https://docs.pydantic.dev/hypothesis_plugin/
14. **Z3 Theorem Prover** — https://github.com/Z3Prover/z3
15. **CrossHair (Python verifier)** — https://github.com/pschanely/CrossHair
16. **CrossHair Documentation** — https://crosshair.readthedocs.io/
17. **hypothesis-crosshair** — https://github.com/pschanely/hypothesis-crosshair

### LLM Structured Outputs
18. **Instructor** — https://github.com/567-labs/instructor
19. **Instructor Documentation** — https://python.useinstructor.com/
20. **PydanticAI** — https://ai.pydantic.dev/
21. **Pydantic LLM Integration** — https://pydantic.dev/articles/llm-intro

### Code Benchmarks
22. **SWE-bench** — https://github.com/SWE-bench/SWE-bench
23. **CRUXEval** — https://github.com/facebookresearch/cruxeval
24. **CRUXEval Paper (ICML 2024)** — https://crux-eval.github.io/
25. **EvalPlus (HumanEval+/MBPP+)** — https://github.com/evalplus/evalplus
26. **EvalPlus Leaderboard** — https://evalplus.github.io/leaderboard.html
27. **ClassEval** — https://github.com/FudanSELab/ClassEval
28. **ClassEval Paper (ICSE 2024)** — https://dl.acm.org/doi/10.1145/3597503.3639219
29. **BigCodeBench** — https://github.com/bigcode-project/bigcodebench
30. **HumanEval Pro / MBPP Pro** — https://github.com/CodeEval-Pro/CodeEval-Pro
31. **Python-by-Contract Dataset** — https://dl.acm.org/doi/10.1145/3540250.3558917

### Key Articles
32. **Property Tests + Contracts = Integration Tests** — https://www.hillelwayne.com/post/pbt-contracts/

---

*This proposal documents language and tool-inspired enhancements for future discussion. All proposals have been filtered through **Agent-Native criteria** — features that only improve human UX (Guard LSP), duplicate existing capabilities (Refinement Types), or reduce error detection (Ghost Specs) have been removed. Implementation should be incremental: Tier 0 (`invar test` + `invar verify`, 2 weeks), Tier 1 (@must_use, @invariant, etc., 3 weeks), Tier 2 (@must_close, @transfer pending). Section 12 provides the Tier 0 development plan, Section 13 introduces Multi-Layer Purity Detection, and Section 14 details Tier 1. The Appendix documents the Agent-Native filtering criteria applied to all proposals.*
