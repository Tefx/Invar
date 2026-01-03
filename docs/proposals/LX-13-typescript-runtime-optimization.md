# LX-13: TypeScript Runtime Validation Optimization

**Status:** Draft
**Created:** 2026-01-04
**Updated:** 2026-01-04
**Priority:** Medium (Performance improvement, not blocking)
**Depends On:** LX-06 (TypeScript Tooling), LX-12 (Contract Enforcement Strategy)

## Executive Summary

Investigate strategies to reduce or eliminate Zod runtime validation overhead (200-500x compared to native TypeScript). While complete elimination is impossible due to type erasure, **boundary validation patterns can reduce overhead by 80-90%**.

**Key Finding:** The bottleneck is not Zod itself, but **redundant validation** in call chains. Solution: validate once at system boundaries (Shell layer), trust internally (Core layer).

---

## Problem Statement

### Performance Cost (from LX-12)

```typescript
// Hot path: Called 1M times
function calculateDiscount(price: number, rate: number): number {
  // Zod parse overhead: ~2-5μs per call
  const { price, rate } = InputSchema.parse({ price, rate });
  return price * (1 - rate);
}

// Total overhead: 2-5 seconds for 1M calls
```

**Benchmark:**

| Operation | TypeScript Native | + Zod Parse | Overhead |
|-----------|-------------------|-------------|----------|
| Simple math | 10ns | 2-5μs | **200-500x** |
| Object access | 50ns | 2-5μs | 40-100x |

### Real-World Impact

**Scenarios where overhead matters:**

1. **High-frequency functions** (>10K calls/sec)
   - Real-time systems (games, trading bots)
   - Data processing pipelines
   - API gateways with heavy load

2. **Nested validation chains**
   ```typescript
   apiHandler(req)           // Parse 1
     → validateInput(data)   // Parse 2 (same data)
       → processPayment(tx)  // Parse 3 (same data)
         → ...
   ```
   **Problem:** Same data validated 3+ times

3. **Build-time overhead**
   - Test suites with thousands of validations
   - Development hot-reload cycles

### The Core Question

**Can Zod's runtime overhead be eliminated while maintaining Invar's safety guarantees?**

---

## Solution Analysis

### Option 1: Compile-Time Validation (TypeScript Plugin)

**Idea:** Transform Zod schemas into TypeScript assertions at compile time.

```typescript
// Source code
const InputSchema = z.object({ x: z.number().positive() });
function calc(input: z.infer<typeof InputSchema>) {
  const validated = InputSchema.parse(input);  // Runtime validation
  return validated.x * 2;
}

// After transformation (ideal)
function calc(input: { x: number }) {
  // TypeScript already validated types at compile time
  // No runtime parse() needed
  return input.x * 2;
}
```

**Technical Feasibility:**

✅ **Possible:**
- TypeScript supports Transformer Plugins
- Can extract type information from Zod schemas

❌ **Critical Flaw:**
- Compile-time types ≠ Runtime values
- `z.number().positive()` → TypeScript only checks `number` type
- **Cannot validate at compile time:** `x > 0` (semantic constraint)
- Edge cases (NaN, Infinity, negative) **must** be checked at runtime

**Example of the limitation:**

```typescript
const Schema = z.number().positive().finite().max(1000);

// TypeScript can check:
type T = number;  ✅ Compile-time

// TypeScript CANNOT check:
// - Is x > 0?           ❌ Runtime only
// - Is x !== NaN?       ❌ Runtime only
// - Is x <= 1000?       ❌ Runtime only
```

**Conclusion:**

Only ~30% of validation overhead can be eliminated (type checking).
Semantic constraints (~70%) still require runtime checks.

**Verdict:** ❌ Not sufficient as primary solution

---

### Option 2: Conditional Validation (Dev vs Prod)

**Idea:** Skip validation in production, assume inputs are trusted.

```typescript
const VALIDATE = process.env.NODE_ENV !== 'production';

function calc(input: InputSchema) {
  if (VALIDATE) {
    InputSchema.parse(input);  // Only in dev
  }
  return input.x * 2;
}
```

**Pros:**
- ✅ 100% overhead elimination in production
- ✅ Easy to implement
- ✅ Precedent: React's PropTypes (dev-only)

**Cons:**
- ❌ **No protection in production** (where it matters most)
- ❌ Diverges from Invar philosophy
- ❌ Risk: code passes dev but fails in prod

**Invar Philosophy Conflict:**

| Principle | Python @pre/@post | TypeScript (if conditional) |
|-----------|-------------------|----------------------------|
| Runtime safety | ✅ All environments | ❌ Dev only |
| Contracts as docs | ✅ Enforceable proof | ⚠️ Unenforced hints |
| Cross-language parity | ✅ Consistent | ❌ Inconsistent |

**Example of the risk:**

```typescript
// Dev: x = 10 (normal case, passes)
// Prod: x = -1 (edge case, no validation, silent failure)
@pre(lambda x: x > 0)  # Python: catches in prod
z.number().positive()  # TypeScript: skipped in prod?
```

**Conclusion:**

Conflicts with Invar's core safety guarantees.

**Verdict:** ⚠️ Only as opt-in escape hatch (like `@invar:allow performance`)

---

### Option 3: Boundary Validation Pattern (Recommended)

**Idea:** Validate once at system boundaries, trust data internally.

```typescript
// ===== BOUNDARY (Shell layer) =====
export async function apiHandler(req: Request) {
  const input = RequestSchema.parse(req.body);  // ← ONLY validation point
  return processPayment(input);  // Internal calls trust data
}

// ===== INTERNAL (Core layer) =====
function processPayment(data: PaymentData) {
  // No parse() — assume 'data' already validated
  return data.amount * 0.95;
}
```

**Type Safety with `Validated<T>`:**

```typescript
// Mark validated data at type level
type Validated<T> = T & { readonly __validated: unique symbol };

// Boundary function returns Validated<T>
function validate<T>(schema: z.Schema<T>, input: unknown): Validated<T> {
  return schema.parse(input) as Validated<T>;
}

// Internal functions require Validated<T>
function processPayment(data: Validated<PaymentData>) {
  // TypeScript enforces: data MUST come from validate()
  // Cannot accidentally pass unvalidated data
  return data.amount * 0.95;
}
```

**Visual Example:**

```
┌────────────────────────────────────────────────────────┐
│  HTTP Request → apiHandler                             │
│                                                        │
│  ✓ VALIDATE HERE (Shell boundary)                     │
│  ┌────────────────────────────────────────────┐       │
│  │ const input = InputSchema.parse(req.body); │       │
│  └────────────────────────────────────────────┘       │
│                                                        │
│  → processPayment(input)      [TRUST]                 │
│    → calculateFees(input)     [TRUST]                 │
│      → applyDiscount(input)   [TRUST]                 │
│        → finalizeTransaction  [TRUST]                 │
│                                                        │
│  ❌ NO redundant parse() calls                         │
└────────────────────────────────────────────────────────┘
```

**Overhead Reduction:**

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| 10-function call chain | 10 parses | 1 parse | **90%** |
| API with 5 handlers | 5 parses | 1 parse | **80%** |
| Single function | 1 parse | 1 parse | 0% |

**Perfect Alignment with Invar Architecture:**

| Layer | Responsibility | Validation |
|-------|---------------|------------|
| **Shell** | I/O boundaries | ✅ Validate external input |
| **Core** | Pure logic | ❌ Trust validated data |

**Pros:**
- ✅ 80-90% overhead reduction in typical codebases
- ✅ Type-safe (TypeScript enforces `Validated<T>`)
- ✅ Matches Invar's Core/Shell philosophy
- ✅ Still validates in production (safe)
- ✅ No library changes needed

**Cons:**
- ⚠️ Requires code refactoring to use `Validated<T>`
- ⚠️ Not applicable to functions that receive external input mid-chain

**Conclusion:**

**Best practical solution.** Reduces overhead dramatically while maintaining safety.

**Verdict:** ✅ **Primary recommendation**

---

### Option 4: Smart Memoization

**Idea:** Cache validation results to avoid re-parsing identical data.

```typescript
const validationCache = new WeakMap<object, boolean>();

function cachedParse<T>(schema: z.Schema<T>, input: T): T {
  if (validationCache.has(input)) {
    return input;  // Already validated
  }
  const result = schema.parse(input);
  validationCache.set(result, true);
  return result;
}
```

**When it works:**

| Input Type | Cacheable? | Example |
|------------|------------|---------|
| Same object reference | ✅ Yes | Config object reused |
| Primitive values | ❌ No | WeakMap limitation |
| New object, same content | ❌ No | Different reference |

**Reality Check:**

```typescript
// Scenario 1: Works
const config = { timeout: 5000 };
cachedParse(ConfigSchema, config);  // Parse
cachedParse(ConfigSchema, config);  // Cache hit ✅

// Scenario 2: Doesn't work (most common)
cachedParse(NumberSchema, 42);      // Error: primitives not cacheable ❌
cachedParse(DataSchema, req.body);  // Each request = new object ❌
```

**Overhead Analysis:**

- WeakMap lookup: ~50ns (vs 2-5μs parse)
- Savings: 98% **if cacheable**
- Problem: Most hot paths use primitives or new objects

**Conclusion:**

Limited applicability. Only works for specific patterns (reused config objects).

**Verdict:** ⚠️ Supplementary technique, not primary solution

---

### Option 5: Alternative Validators (Valibot, TypeBox)

**Performance Comparison (from LX-12):**

| Library | Size | Speed | Ecosystem |
|---------|------|-------|-----------|
| Zod | 58KB | 1x | Mature |
| **Valibot** | 12KB | **15x faster** | Emerging |
| **TypeBox** | 45KB | **100x faster** | JSON Schema |

**Why is Valibot faster?**

1. **Lazy parsing** — only validates accessed fields
2. **Tree-shakable** — loads only needed validators
3. **Functional design** — avoids class instantiation overhead

**Why is TypeBox faster?**

1. Generates JSON Schema
2. Uses **Ajv** (JIT-compiled validators)
3. Optimized for high-throughput scenarios

**Migration Example:**

```typescript
// Zod
const Schema = z.object({
  x: z.number().positive(),
  y: z.string().min(3)
});

// Valibot
import * as v from 'valibot';
const Schema = v.object({
  x: v.pipe(v.number(), v.minValue(1)),
  y: v.pipe(v.string(), v.minLength(3))
});

// TypeBox
import { Type } from '@sinclair/typebox';
const Schema = Type.Object({
  x: Type.Number({ minimum: 1 }),
  y: Type.String({ minLength: 3 })
});
```

**Integration Impact:**

**If LX-06/LX-12 locks into Zod:**
- ❌ High migration cost (rewrite all schemas)
- ❌ Breaking change for users

**If pluggable validators supported:**
- ✅ Users choose library (Zod/Valibot/TypeBox)
- ✅ Invar Guard adapts to detected library
- ⚠️ More complexity in implementation

**Conclusion:**

Technically feasible and high-impact for performance.

**Verdict:** ✅ Long-term strategy (6-12 months)

---

### Option 6: JIT Optimization (V8 Engine)

**Theory:** V8's optimizing compiler will inline hot code paths.

**Reality:**

```typescript
// Zod's internal structure
class ZodObject {
  parse(data) {
    for (const key in this.shape) {          // Dynamic iteration
      const validator = this.shape[key];     // Property access
      const result = validator.parse(data[key]);  // Polymorphic call
    }
  }
}
```

**Why V8 can't optimize:**

- **Megamorphic call sites** — `validator.parse()` has many implementations
- **Dynamic property access** — `this.shape[key]` prevents inlining
- **Complex branching** — Zod's parsing logic has many paths

**Optimization attempts:**

```typescript
// Hypothesis: Monomorphic version
const optimizedParse = (data) => {
  const x = parseNumber(data.x);  // Specific, not generic
  const y = parseString(data.y);
  return { x, y };
};
```

**Problem:** This is essentially **hand-writing validators**, defeating Zod's purpose.

**Conclusion:**

Cannot rely on V8 to optimize generic validation libraries.

**Verdict:** ❌ Not actionable

---

## Recommended Strategy

### Three-Phase Roadmap

```
Phase 1: Boundary Validation Patterns (Immediate)
  ↓
Phase 2: Performance Escape Hatches (3 months)
  ↓
Phase 3: Pluggable Validators (6-12 months)
```

---

### Phase 1: Boundary Validation Guidance (Immediate)

**Goal:** Educate users on optimal validation patterns.

**Implementation:**

**1. Documentation in `.invar/examples/typescript-contracts.md`:**

```markdown
## Performance Best Practices

### ✅ DO: Validate at Boundaries

\`\`\`typescript
// Shell layer (API handler)
export async function createUser(req: Request) {
  const input = CreateUserSchema.parse(req.body);  // ← VALIDATE
  return processUser(input);  // Core layer
}

// Core layer (pure logic)
function processUser(data: UserData) {
  // NO parse() — trust caller validated
  return {
    id: generateId(),
    name: data.name,
    email: data.email
  };
}
\`\`\`

### ❌ DON'T: Validate Internally

\`\`\`typescript
function processUser(data: unknown) {
  const validated = UserDataSchema.parse(data);  // ← REDUNDANT
  // Caller should have validated
}
\`\`\`
```

**2. Guard Detection:**

```python
# In invar/core/typescript_guard.py
def detect_redundant_validation(call_chain: list[FunctionCall]) -> list[Warning]:
    """Detect multiple parse() calls on same data flow."""
    warnings = []
    for i, call in enumerate(call_chain):
        if call.is_zod_parse():
            for prev_call in call_chain[:i]:
                if prev_call.is_zod_parse() and same_data_flow(call, prev_call):
                    warnings.append(
                        Warning(
                            code="redundant_validation",
                            message=f"Data already validated at {prev_call.location}",
                            suggestion="Use Validated<T> type to mark trusted data"
                        )
                    )
    return warnings
```

**3. Type Helper:**

```typescript
// Added to @invar/runtime-ts package
export type Validated<T> = T & { readonly __validated: unique symbol };

export function validate<T>(schema: z.Schema<T>, input: unknown): Validated<T> {
  return schema.parse(input) as Validated<T>;
}
```

**Deliverables:**
- [ ] Documentation in `.invar/examples/`
- [ ] Guard warning for redundant validation
- [ ] `Validated<T>` type helper in runtime package

**Timeline:** 1-2 weeks

---

### Phase 2: Performance Escape Hatches (3 months)

**Goal:** Allow opt-out for performance-critical code (like Python's `@invar:allow`).

**Syntax:**

```typescript
// @invar:allow performance
function hotPath(data: InputData) {
  // Skip validation, assume caller validated
  return data.x * data.y * data.z;
}
```

**Guard Rules:**

```python
@dataclass
class PerformanceEscapeHatch:
    function: str
    reason: str
    caller_validation: bool  # Must prove caller validates

def check_escape_hatch(node: FunctionNode) -> Result:
    if has_annotation(node, "@invar:allow performance"):
        # 1. Require documentation of why
        if not node.has_justification():
            return Failure("performance escape hatch requires justification")

        # 2. Verify caller has validation
        callers = find_callers(node)
        if not any(caller_validates(c) for c in callers):
            return Failure("no caller validates input to this function")

        return Success()
```

**Example:**

```typescript
/**
 * High-frequency calculation called 1M+ times per second.
 *
 * @invar:allow performance
 * Justification: Called from processOrders() which validates OrderSchema
 */
function calculateDiscount(price: number, qty: number): number {
  return price * qty * 0.95;  // No parse()
}

export function processOrders(req: Request) {
  const orders = OrderSchema.parse(req.body);  // ← Validation here
  return orders.map(o => calculateDiscount(o.price, o.qty));
}
```

**Deliverables:**
- [ ] `@invar:allow performance` syntax support
- [ ] Guard enforcement of justification + caller validation
- [ ] Documentation of when to use

**Timeline:** 2-3 months

---

### Phase 3: Pluggable Validators (6-12 months)

**Goal:** Support Zod, Valibot, TypeBox interchangeably.

**Configuration:**

```toml
# .invar/config.toml
[guard.typescript]
validator = "valibot"  # zod | valibot | typebox | auto
```

**Auto-detection:**

```python
def detect_validator(project_path: Path) -> str:
    """Detect which validator library is in use."""
    package_json = read_json(project_path / "package.json")
    deps = {**package_json.get("dependencies", {}),
            **package_json.get("devDependencies", {})}

    if "valibot" in deps:
        return "valibot"
    elif "@sinclair/typebox" in deps:
        return "typebox"
    elif "zod" in deps:
        return "zod"
    else:
        return "none"
```

**Adapter Interface:**

```python
class ValidatorAdapter(Protocol):
    def parse_schema(self, code: str) -> Schema: ...
    def extract_constraints(self, schema: Schema) -> list[Constraint]: ...
    def suggest_schema(self, type_info: TypeInfo) -> str: ...

class ZodAdapter(ValidatorAdapter): ...
class ValibotAdapter(ValidatorAdapter): ...
class TypeBoxAdapter(ValidatorAdapter): ...
```

**User Experience:**

```bash
# Project A uses Zod
$ invar guard
✓ Detected validator: zod
✓ Contract coverage: 85%

# Project B uses Valibot
$ invar guard
✓ Detected validator: valibot
✓ Contract coverage: 90% (15x faster validation)
```

**Deliverables:**
- [ ] Abstract validator interface
- [ ] Adapters for Zod, Valibot, TypeBox
- [ ] Auto-detection in Guard
- [ ] Migration guide (Zod → Valibot)

**Timeline:** 6-12 months

---

## Implementation Plan

### Phase 1 Detailed Tasks

| Task | File | Effort |
|------|------|--------|
| Write boundary pattern docs | `.invar/examples/typescript-performance.md` | 2 days |
| Add `Validated<T>` helper | `runtime-ts/src/validated.ts` | 1 day |
| Implement redundant validation detection | `core/typescript_guard.py` | 3 days |
| Add Guard warning output | `shell/guard_reporter.py` | 1 day |
| Unit tests | `tests/test_typescript_guard.py` | 2 days |

**Total: 1-2 weeks**

### Phase 2 Detailed Tasks

| Task | File | Effort |
|------|------|--------|
| Parse `@invar:allow performance` | `core/typescript_parser.py` | 2 days |
| Implement caller validation check | `core/typescript_guard.py` | 3 days |
| Add justification enforcement | `core/typescript_guard.py` | 2 days |
| Update Guard output format | `shell/guard_reporter.py` | 1 day |
| Documentation | `docs/guides/typescript-performance.md` | 2 days |
| Tests | `tests/test_escape_hatches.py` | 2 days |

**Total: 2-3 weeks**

### Phase 3 Detailed Tasks

| Task | File | Effort |
|------|------|--------|
| Design adapter interface | `core/validators/base.py` | 3 days |
| Implement Zod adapter | `core/validators/zod.py` | 3 days |
| Implement Valibot adapter | `core/validators/valibot.py` | 5 days |
| Implement TypeBox adapter | `core/validators/typebox.py` | 5 days |
| Auto-detection logic | `shell/validator_detection.py` | 2 days |
| Config integration | `core/config.py` | 2 days |
| Migration tooling | `shell/commands/migrate.py` | 5 days |
| Documentation | `docs/guides/validators.md` | 3 days |
| Tests | `tests/test_validators.py` | 5 days |

**Total: 1-2 months**

---

## Success Criteria

### Phase 1 Success Metrics

- [ ] Guard detects redundant validation with 95%+ accuracy
- [ ] `Validated<T>` pattern documented with 3+ examples
- [ ] User feedback: "I understand boundary validation pattern"

### Phase 2 Success Metrics

- [ ] `@invar:allow performance` accepted by 100% of users who try it
- [ ] Guard blocks unjustified escape hatches with zero false positives
- [ ] Performance-critical code paths reduced from 10 validations to 1

### Phase 3 Success Metrics

- [ ] Auto-detection works for 95%+ of TypeScript projects
- [ ] Valibot projects see 10-15x speedup in validation
- [ ] TypeBox projects see 50-100x speedup
- [ ] Migration guide success rate: 90%+ (users complete migration without errors)

---

## Performance Impact Estimates

### Baseline (Current)

```typescript
// Typical API handler with 5-function call chain
function apiHandler(req) {
  const data = Schema.parse(req.body);      // 5μs
  return processStep1(data);                // 5μs (re-parse)
}
function processStep1(data) {
  const validated = Schema.parse(data);     // 5μs
  return processStep2(validated);           // 5μs
}
// ... 3 more steps

// Total: 25μs per request
```

### After Phase 1 (Boundary Validation)

```typescript
function apiHandler(req) {
  const data = validate(Schema, req.body);  // 5μs (only validation)
  return processStep1(data);                // 0μs (trusted)
}
function processStep1(data: Validated<T>) {
  return processStep2(data);                // 0μs
}

// Total: 5μs per request (80% reduction)
```

### After Phase 3 (Valibot)

```typescript
// Same code, but using Valibot instead of Zod
function apiHandler(req) {
  const data = validate(Schema, req.body);  // 0.33μs (15x faster)
  return processStep1(data);                // 0μs
}

// Total: 0.33μs per request (93% reduction from baseline)
```

**Real-World Impact:**

| Scenario | Before | After P1 | After P3 | Improvement |
|----------|--------|----------|----------|-------------|
| 10K req/sec API | 250ms overhead | 50ms | 3.3ms | **98.7%** |
| Test suite (1M validations) | 25 sec | 5 sec | 0.33 sec | **98.7%** |
| Hot reload (dev) | 2 sec | 0.4 sec | 0.027 sec | **98.6%** |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users don't adopt boundary pattern | Medium | Medium | Guard warnings + clear docs |
| `Validated<T>` type pollution | Low | Low | Make opt-in, provide utilities |
| Valibot/TypeBox API changes | Medium | Low | Lock to stable versions |
| False positives in redundant detection | High | Medium | Conservative detection + escape hatch |
| Performance claims don't materialize | High | Low | Benchmark before Phase 3 |

---

## Open Questions

### 1. Should `Validated<T>` be enforced or optional?

**Enforced:**
```typescript
// Compiler error if you forget to validate
function processPayment(data: Validated<PaymentData>) { ... }

processPayment({ amount: 100 });  // ❌ Type error
processPayment(validate(Schema, input));  // ✅
```

**Optional:**
```typescript
// Just guidance, not enforced
function processPayment(data: PaymentData) { ... }
```

**Trade-off:** Safety vs friction

### 2. How to handle multi-source validation?

```typescript
// Data comes from TWO sources
function merge(dbData: DbUser, apiData: ApiUser) {
  // Both sources need validation
  // But they're different schemas
  // How to mark as "partially validated"?
}
```

### 3. Should Guard auto-fix redundant validation?

**Auto-fix:**
```typescript
// Before
function process(data: unknown) {
  const validated = Schema.parse(data);
}

// After (auto-fixed)
function process(data: Validated<UserData>) {
  // parse() removed
}
```

**Risk:** Breaking changes if caller doesn't validate

---

## References

### Internal

- [LX-06: TypeScript Tooling](completed/LX-06-typescript-tooling.md) — Guard implementation
- [LX-12: Contract Enforcement Strategy](LX-12-typescript-contract-enforcement.md) — Performance data
- [INVAR.md](../../INVAR.md) — Core/Shell architecture

### External

- [Zod Performance Discussion](https://github.com/colinhacks/zod/issues/1724)
- [Valibot Benchmarks](https://valibot.dev/guides/benchmarks/)
- [TypeBox Performance](https://github.com/sinclairzx81/typebox#performance)
- [V8 Optimization Killers](https://github.com/petkaantonov/bluebird/wiki/Optimization-killers)

---

## Decision Log

### 2026-01-04: Initial Proposal

**Context:** LX-12 identified 200-500x overhead as barrier to TypeScript adoption.

**Key Decisions:**

1. **Primary solution: Boundary validation pattern** (Phase 1)
   - Rationale: 80-90% reduction with minimal changes
   - Aligns with Invar's Core/Shell architecture

2. **Secondary: Pluggable validators** (Phase 3)
   - Rationale: Valibot/TypeBox offer 15-100x speedup
   - Future-proofs against validator library changes

3. **Rejected: Compile-time validation**
   - Rationale: TypeScript type erasure prevents semantic validation
   - Only 30% of overhead addressable

4. **Rejected: Conditional validation as default**
   - Rationale: Conflicts with Invar's safety guarantees
   - Only allowed as explicit escape hatch

**Next Steps:**
1. Prototype redundant validation detection (Phase 1)
2. Benchmark Valibot vs Zod in realistic scenarios
3. User research: Would pluggable validators add too much complexity?
