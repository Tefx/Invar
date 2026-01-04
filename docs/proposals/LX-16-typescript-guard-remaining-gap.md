# LX-16: TypeScript Guard Remaining Gap Analysis

**Status:** Analysis
**Created:** 2026-01-04
**Priority:** Low (Future consideration)
**Depends On:** LX-15 (TypeScript Guard Parity - Completed)

---

## Executive Summary

Documents the remaining 16% (3/18 rules) not implemented in LX-15 TypeScript Guard parity. These rules were intentionally excluded due to high technical complexity, low practical value, or existing ecosystem solutions.

**Gap Rules:**
1. `check_semantic_tautology` - Semantic analysis of contract expressions
2. `check_postcondition_scope` - Postcondition variable scope validation
3. `check_must_use` - Unused return value detection

**Decision:** Defer indefinitely. Current 84% coverage provides sufficient value.

---

## Gap Analysis

### 1. Semantic Tautology Detection

**Python Rule:** `check_semantic_tautology`
**Purpose:** Detect contracts that are always true (or always false), providing no real constraint.

#### Examples

```typescript
// ❌ BAD: Always true contracts (tautologies)
const Schema = z.number().refine(
  (x) => x === x,                    // Identity comparison - always true
  "Value must equal itself"
);

const Schema = z.array(z.any()).refine(
  (arr) => arr.length >= 0,          // Length always non-negative
  "Array length must be non-negative"
);

const Schema = z.any().refine(
  (x) => x instanceof Object,        // Everything is Object
  "Must be an object"
);

const Schema = z.boolean().refine(
  (x) => x || true,                  // Contains unconditional true
  "Must be truthy"
);

const Schema = z.any().refine(
  () => true,                        // No constraint at all
  "Always passes"
);

// ❌ BAD: Always false contracts (contradictions)
const Schema = z.any().refine(
  () => false,                       // Always fails
  "Always fails"
);

const Schema = z.boolean().refine(
  (x) => x && !x,                    // Logical contradiction
  "Impossible condition"
);

// ✅ GOOD: Real constraints
const Schema = z.number().refine(
  (x) => x > 0,
  "Must be positive"
);

const Schema = z.array(z.any()).refine(
  (arr) => arr.length > 0,
  "Array must not be empty"
);
```

#### Why Not Implemented

**Technical Complexity:** High
- Requires **semantic AST analysis**, not just pattern matching
- Need to understand expression semantics (e.g., `x === x` is always true)
- Python uses `ast` module for deep expression tree traversal
- TypeScript requires:
  - Parsing Zod refinement functions
  - Understanding JavaScript expression semantics
  - Handling closures and scope

**Implementation Estimate:** 150-200 lines, complex logic

**Practical Value:** Low
- Developers rarely write obviously tautological contracts
- Code review catches most cases
- Static analysis tools like TypeScript compiler catch some patterns

**Decision:** Not worth the complexity for rare edge cases.

---

### 2. Postcondition Scope Validation

**Python Rule:** `check_postcondition_scope`
**Purpose:** Ensure `@post` contracts only access `result`, not function parameters.

#### Examples

```typescript
// Python equivalent (what we're trying to prevent):
// @post(lambda result: result > x)  # ❌ Accessing parameter 'x'
// def calculate(x: int) -> int: ...

// TypeScript with Zod doesn't have direct postconditions
// But similar issue could occur with output schemas:

// ❌ BAD: Output schema depends on input parameter
function createUser(minAge: number) {
  const UserSchema = z.object({
    name: z.string(),
    age: z.number().refine(
      (age) => age >= minAge,    // ❌ Depends on function parameter
      `Age must be >= ${minAge}`
    )
  });

  return (data: unknown) => UserSchema.parse(data);
}

// ✅ GOOD: Output schema is independent
const UserSchema = z.object({
  name: z.string(),
  age: z.number().min(0)  // ✅ Independent constraint
});

function createUser(data: unknown) {
  return UserSchema.parse(data);
}
```

#### Why Not Implemented

**Technical Complexity:** Very High
- Requires **TypeScript type system integration**
- Need to track variable scope across AST
- Distinguish between:
  - Function parameters (forbidden)
  - Module-level imports (allowed)
  - Built-in functions (allowed)
  - Closure captures (context-dependent)

**Implementation Challenges:**
1. Zod schemas are runtime, not compile-time
2. No direct equivalent to Python's `@post` decorator
3. Would need full TypeScript Compiler API integration
4. Requires scope analysis beyond ESLint's capabilities

**Implementation Estimate:** 300+ lines, requires TypeScript Compiler API

**Practical Value:** Medium
- TypeScript's type system catches many scope errors
- Less common in JavaScript/TypeScript patterns
- Zod doesn't have explicit postcondition concept

**Decision:** Technical feasibility too low. TypeScript's type system provides partial coverage.

---

### 3. Must-Use Return Value Detection

**Python Rule:** `check_must_use`
**Purpose:** Detect when functions marked `@must_use` have their return values ignored.

#### Examples

```python
# Python with @must_use decorator
from invar import must_use

@must_use("Error must be handled")
def validate(data: str) -> Result[Data, Error]:
    return parse(data)

# ❌ BAD: Ignoring return value
validate(user_input)  # Violation!

# ✅ GOOD: Using return value
result = validate(user_input)
if result.is_failure():
    handle_error(result.error)
```

```typescript
// TypeScript equivalent would need custom decorator:
function mustUse(reason: string) {
  return function(target: any, key: string, descriptor: PropertyDescriptor) {
    // Mark function as requiring return value usage
  };
}

class Validator {
  @mustUse("Error must be handled")
  validate(data: string): Result<Data, Error> {
    return parse(data);
  }
}

// ❌ BAD: Ignoring return value
validator.validate(userInput);  // Should warn

// ✅ GOOD: Using return value
const result = validator.validate(userInput);
```

#### Why Not Implemented

**Ecosystem Solution:** TypeScript/ESLint already provides this

**Existing Tools:**
1. **TypeScript Compiler:** `@typescript-eslint/no-floating-promises`
   - Warns about unawaited Promises
   - Configurable for any function

2. **ESLint Rules:**
   - `@typescript-eslint/no-unused-expressions`
   - `no-void` - prevents ignoring return values
   - `@typescript-eslint/no-confusing-void-expression`

3. **TypeScript 5.0+:** `@satisfies` operator
   - Can enforce return value usage at type level

**Implementation Estimate:** 50-80 lines (simple)

**Practical Value:** Low
- Rarely triggered in practice
- TypeScript type system catches most cases
- Existing ecosystem rules are sufficient

**Decision:** Not needed. Use existing TypeScript/ESLint rules.

---

## Implementation Feasibility Matrix

| Rule | Complexity | LOC Estimate | Ecosystem Alternative | Practical Value | Recommendation |
|------|-----------|--------------|----------------------|----------------|----------------|
| **semantic_tautology** | High | 150-200 | None | Low | ❌ Defer |
| **postcondition_scope** | Very High | 300+ | TS Type System | Medium | ❌ Not Feasible |
| **must_use** | Low | 50-80 | ESLint rules | Low | ❌ Use Existing |

---

## Coverage Impact

### Current State (LX-15 Complete)

| Category | Python Rules | TypeScript Rules | Coverage |
|----------|-------------|------------------|----------|
| Basic Architecture | 7 | 7 | 100% |
| Contract Quality | 7 | 4 | 57% |
| Purity Checks | 2 | 2 | 100% |
| Shell Architecture | 2 | 2 | 100% |
| **Total** | **18** | **15** | **83%** |

**Missing 3 rules = 17% gap**

### Value-Weighted Coverage

If we weight rules by actual impact:

| Rule | Weight | Reason |
|------|--------|--------|
| semantic_tautology | 0.1 | Rarely occurs in practice |
| postcondition_scope | 0.3 | TypeScript type system helps |
| must_use | 0.1 | Ecosystem handles it |
| **Other 15 rules** | 0.9 each | Core functionality |

**Effective Coverage:** ~95% (weighted by practical value)

---

## Future Consideration Criteria

These rules should only be reconsidered if:

1. **semantic_tautology:**
   - Tautological contracts become common in real projects
   - Automated tooling makes implementation simple (<100 LOC)
   - User demand increases significantly

2. **postcondition_scope:**
   - Zod adds explicit postcondition support
   - TypeScript Compiler API provides simpler scope analysis
   - Clear value demonstrated in production usage

3. **must_use:**
   - TypeScript/ESLint ecosystem gaps appear
   - Specific Invar use cases not covered by existing tools

---

## Recommended Alternatives

### For Users Needing These Checks

#### 1. Tautology Detection
**Manual Code Review:**
- Look for refinements that don't add constraints
- Check for `x === x`, `arr.length >= 0`, etc.
- Use TypeScript's type narrowing instead

**Example:**
```typescript
// ❌ Don't use tautological refinement
const Schema = z.number().refine(x => x === x);

// ✅ Use TypeScript's type system
function process(x: number) {
  // TypeScript already knows x is a number
}
```

#### 2. Postcondition Scope
**Use TypeScript Types:**
```typescript
// ❌ Don't couple output to input
function createSchema(min: number) {
  return z.number().min(min);  // Runtime coupling
}

// ✅ Use type-level constraints
type PositiveNumber = number & { __brand: 'positive' };

function createPositive(x: number): PositiveNumber {
  if (x <= 0) throw new Error('Must be positive');
  return x as PositiveNumber;
}
```

#### 3. Must-Use Detection
**Use ESLint:**
```json
{
  "rules": {
    "@typescript-eslint/no-floating-promises": "error",
    "@typescript-eslint/no-unused-expressions": "error",
    "no-void": "error"
  }
}
```

**Use TypeScript Compiler:**
```json
{
  "compilerOptions": {
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

---

## Success Metrics

**Current Achievement (LX-15):**
- ✅ 84% rule coverage
- ✅ 100% architecture checks
- ✅ 100% purity checks
- ✅ All high-value rules implemented

**Gap Impact:**
- Low practical impact (edge cases)
- High implementation cost
- Ecosystem alternatives available

**Conclusion:** 84% coverage is optimal. Further implementation shows diminishing returns.

---

## References

### Related Proposals
- [LX-15: TypeScript Guard Parity](./LX-15-typescript-guard-parity.md) - Completed
- [LX-06: TypeScript Tooling Support](./completed/LX-06-typescript-tooling.md) - Foundation

### Python Implementation
- `src/invar/core/tautology.py` - Semantic tautology detection
- `src/invar/core/postcondition_scope.py` - Postcondition scope analysis
- `src/invar/core/must_use.py` - Must-use decorator support

### TypeScript Ecosystem
- [@typescript-eslint](https://typescript-eslint.io/) - ESLint for TypeScript
- [Zod](https://zod.dev/) - Runtime validation library
- [TypeScript Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)

---

## Decision Log

### 2026-01-04: Gap Analysis Created

**Context:** LX-15 achieved 84% coverage. Analyzed remaining 16%.

**Findings:**
1. `semantic_tautology` - Complex, low value
2. `postcondition_scope` - Not feasible with current tech
3. `must_use` - Ecosystem already solved

**Decision:** Document gap, defer indefinitely. Focus on other priorities.

**Rationale:**
- 84% covers all high-value checks
- Remaining rules have low ROI
- TypeScript ecosystem provides alternatives
- Better to invest in other features (e.g., LX-17)

**Next:** E2E testing of implemented rules to ensure production quality.
