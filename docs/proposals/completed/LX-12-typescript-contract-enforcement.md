# LX-12: TypeScript Contract Enforcement Strategy

**Status:** Archived (Merged into LX-15)
**Created:** 2026-01-04
**Archived:** 2026-01-04
**Superseded By:** [LX-15: TypeScript Guard Parity](../LX-15-typescript-guard-parity.md)

> **Note:** This proposal has been merged into LX-15 for unified tracking.
> - Phase 2 (Strict Mode) → LX-15 Phase 3.1
> - Phase 3 (Risk-Based Intelligence) → LX-15 Phase 3.2

---

**Original Priority:** Medium (Strategic decision affecting TS adoption)
**Original Depends On:** LX-06 (TypeScript Tooling Support)

## Executive Summary

Decide contract enforcement policy for TypeScript: should Invar require 100% Zod schema coverage (matching Python's @pre/@post requirement), or use a softer approach with coverage statistics and recommendations?

**Current State:** LX-06 Phase 1-3 implemented with "recommended" mode (80% coverage target, warnings not errors).

**Key Question:** Should TypeScript Core functions be required to have Zod schemas like Python Core functions require @pre/@post?

---

## Problem Statement

### Tension: Consistency vs. Ecosystem

**Python Approach (Proven):**
```python
# ❌ ERROR: Missing contract
def calculate(x: int) -> int:
    return x * x

# ✅ REQUIRED
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    return x * x
```

**TypeScript Current (LX-06):**
```typescript
// ⚠️ WARNING: Weak contract (coverage drops to 75%)
function calculate(x: number): number {
  return x * x;
}

// ✅ RECOMMENDED
const InputSchema = z.object({ x: z.number().positive() });
function calculate(input: z.infer<typeof InputSchema>): number {
  const { x } = InputSchema.parse(input);
  return x * x;
}
```

**Dilemma:** Enforce 100% like Python? Or stay flexible for TS ecosystem?

---

## Analysis: Enforcing 100% Coverage

### Advantages

#### 1. Cross-Language Consistency

| Rule | Python | TypeScript (Enforced) |
|------|--------|----------------------|
| Core = Pure | ✅ | ✅ |
| Core = Contracts | ✅ @pre/@post | ✅ Zod |
| Missing Contract | ❌ Error | ❌ Error |

**Benefits:**
- Simpler mental model: "Core always has contracts"
- Docs consistency: `.invar/examples/contracts.{py,ts}` identical philosophy
- Agent instructions simpler: No "Python strict, TS loose" confusion

#### 2. True Runtime Safety

```typescript
// Type system can't catch this
function processPayment(amount: number) {
  // amount could be: -100, NaN, Infinity, 1e308
  database.deduct(amount);  // 💥 Money bug
}

// Zod catches it
const AmountSchema = z.number().positive().finite().max(1000000);
function processPayment(amount: z.infer<typeof AmountSchema>) {
  const validated = AmountSchema.parse(amount);  // Throws on NaN, negative
  database.deduct(validated);  // ✅ Safe
}
```

**Value:**
- Prevents `NaN`, `Infinity`, negative numbers in financial code
- Runtime validation catches what compile-time can't
- Safety boundary for external data (API, user input)

#### 3. Blind Spot Elimination

**Current (Warnings):**
```
⚠️ Blind Spot: processPayment (CRITICAL)
   Risk: Handles money with no validation
   Suggested: z.number().positive().max(1000000)
```

**Enforced:**
```
✓ All Core functions have contracts
  Zero blind spots
```

#### 4. Forces Best Practices

- Developers write Zod schemas BEFORE implementation (like Python @pre/@post)
- Team consistency: Everyone follows same pattern
- Knowledge transfer: New devs see contracts everywhere

### Disadvantages

#### 1. Ecosystem Incompatibility (Critical Issue)

**TypeScript Mainstream:**
```typescript
// 99% of TypeScript code looks like this
function calculateTotal(items: Item[]): number {
  return items.reduce((sum, i) => sum + i.price, 0);
}
```

**Invar Would Require:**
```typescript
const ItemsSchema = z.array(ItemSchema).min(1);
const TotalSchema = z.number().nonnegative();

function calculateTotal(items: z.infer<typeof ItemsSchema>): z.infer<typeof TotalSchema> {
  const validated = ItemsSchema.parse(items);
  const result = validated.reduce((sum, i) => sum + i.price, 0);
  return TotalSchema.parse(result);
}
```

**Conflicts:**
- Popular libraries (React, Express, Prisma) don't use Zod
- Community best practices don't mandate runtime validation
- Forces non-idiomatic code on TS developers

#### 2. Zod is Third-Party Dependency

**Python:**
```python
from deal import pre, post  # Invar provides this
```

**TypeScript:**
```typescript
import { z } from "zod";  # 900KB external dependency
```

**Risks:**
- Zod could be replaced (io-ts, valibot, typebox gaining traction)
- Locks users into specific validation library
- What if Zod development stalls?

**Comparison:**

| Library | Size | Speed | Invar Lock-in? |
|---------|------|-------|----------------|
| zod | 58KB | 1x | ✅ Yes (if enforced) |
| valibot | 12KB | 15x faster | ❌ No (modular) |
| typebox | 45KB | 100x faster | ❌ No (JSON Schema) |

#### 3. Developer Experience Degradation

**Code Bloat:**

| Metric | Before Zod | After Zod | Ratio |
|--------|------------|-----------|-------|
| Lines of code | 5 | 12-15 | 2.4-3x |
| Cognitive load | Low | Medium | - |
| Refactor friction | Low | High | - |

**Example:**
```typescript
// Simple function becomes verbose
// Before (5 lines)
function add(a: number, b: number): number {
  return a + b;
}

// After (13 lines)
const AddInput = z.object({
  a: z.number().finite(),
  b: z.number().finite()
});
type AddInput = z.infer<typeof AddInput>;

function add(input: AddInput): number {
  const { a, b } = AddInput.parse(input);
  return a + b;
}
```

#### 4. TypeScript Philosophy Conflict

**TypeScript Design:**
> "TypeScript is JavaScript with syntax for types." — Anders Hejlsberg

**Core Principles:**
- Types erased at runtime (zero-cost abstraction)
- Gradual typing (opt-in strictness)
- JavaScript superset (runs everywhere)

**Invar Zod Enforcement:**
- Runtime validation required (cost > 0)
- All-or-nothing for Core (no gradual)
- Requires build step (Zod bundling)

**Community Reaction:**
- "This isn't TypeScript anymore, it's a different language"
- "Why validate twice? TypeScript already checked it"
- "Feels like Java, not JavaScript"

#### 5. Performance Cost

```typescript
// Hot path: Called 1M times
function calculateDiscount(price: number, rate: number): number {
  // Zod parse overhead: ~2-5μs per call
  const { price, rate } = InputSchema.parse({ price, rate });
  return price * (1 - rate);
}

// Total overhead: 2-5 seconds for 1M calls
```

**Impact:**
- Zod is optimized but not zero-cost
- Real-time systems (games, trading) affected
- Needs escape hatch: `@invar:allow performance`

**Benchmark:**

| Operation | TypeScript Native | + Zod Parse | Overhead |
|-----------|-------------------|-------------|----------|
| Simple math | 10ns | 2-5μs | 200-500x |
| Object access | 50ns | 2-5μs | 40-100x |

#### 6. Migration Barrier

**Scenario:** Existing 10K-line TypeScript codebase

**Current (Recommended):**
```
invar guard
⚠️ Contract coverage: 65% (target: 80%)
  Suggested improvements: [list of 20 functions]
  → Can adopt gradually
```

**Enforced:**
```
invar guard
❌ FAILED: 47 Core functions missing Zod schemas
  → Must fix ALL before passing
  → Blocks adoption
```

**Consequence:**
- "All or nothing" prevents gradual adoption
- Contradicts Invar's "incremental quality" philosophy
- Users try Invar, hit wall, abandon

---

## Solution Options

### Option A: Enforce 100% (Python Parity)

```toml
# .invar/config.toml
[guard.typescript]
require_contracts = true
min_coverage = 100.0
```

**Pros:**
- ✅ Consistent with Python
- ✅ Maximum safety
- ✅ Clear rules for agents

**Cons:**
- ❌ Ecosystem friction
- ❌ Migration barrier
- ❌ Performance cost

**Verdict:** Best for greenfield Invar-first projects

### Option B: Keep Recommended (Current)

```toml
[guard.typescript]
require_contracts = false
min_coverage = 80.0  # Warning, not error
```

**Pros:**
- ✅ Ecosystem-friendly
- ✅ Gradual adoption
- ✅ Respects TS philosophy

**Cons:**
- ❌ Inconsistent with Python
- ❌ Blind spots remain
- ❌ Agent confusion (when to enforce?)

**Verdict:** Best for brownfield adoption

### Option C: Configurable Strictness (Recommended)

```toml
[guard.typescript]
contract_policy = "strict"  # strict | recommended | optional

# strict mode (Python parity)
[guard.typescript.strict]
require_contracts = true
min_coverage = 100.0

# recommended mode (default)
[guard.typescript.recommended]
require_contracts = false
min_coverage = 80.0
warn_on_blind_spots = true

# optional mode (exploratory)
[guard.typescript.optional]
require_contracts = false
min_coverage = 0.0
report_only = true
```

**Pros:**
- ✅ User choice
- ✅ Gradual path: optional → recommended → strict
- ✅ Supports both greenfield and brownfield

**Cons:**
- ⚠️ More complex configuration
- ⚠️ Agents need clear guidance on which mode

**Verdict:** Best overall flexibility

### Option D: Risk-Based Enforcement

Only enforce contracts on high-risk functions:

```toml
[guard.typescript]
contract_policy = "risk-based"

enforce_contracts_for = [
  "**/payment/**/*.ts",       # Money handling
  "**/auth/**/*.ts",          # Authentication
  "**/*Security*.ts",         # Security-critical
  "**/*Crypto*.ts",           # Cryptography
]

enforce_for_patterns = [
  ".*[Pp]ayment.*",
  ".*[Aa]uth.*",
  ".*[Ss]ecurity.*",
]
```

**Auto-detection:**
```typescript
// Function signature analysis
function processPayment(amount: number) {  // ❌ REQUIRED (money keyword)
function calculateTotal(items: Item[]) {   // ⚠️ Recommended
```

**Pros:**
- ✅ Protects critical code
- ✅ Flexible for non-critical code
- ✅ Minimal migration burden

**Cons:**
- ⚠️ Need accurate risk detection
- ⚠️ Users may disagree on "high-risk"

**Verdict:** Best pragmatic compromise

### Option E: Agent-Specific Mode

Different rules for humans vs. AI agents:

```toml
[guard.typescript]
# Human development
contract_policy = "recommended"

# AI agent development
[guard.typescript.agent_mode]
contract_policy = "strict"
require_contracts = true
```

**Usage:**
```markdown
# .cursorrules
When YOU (the AI agent) write TypeScript Core code,
you MUST add Zod schemas. Use strict mode.
```

**Pros:**
- ✅ Humans: flexible
- ✅ Agents: strict (no bad habits)
- ✅ Best of both worlds

**Cons:**
- ⚠️ How to detect agent vs. human?
- ⚠️ Inconsistent codebase (human code loose, agent code strict)

**Verdict:** Interesting but complex

---

## Recommended Strategy

### Phase 1: Flexible Foundation (Current)

**Status:** ✅ Implemented in LX-06

```toml
[guard.typescript]
contract_policy = "recommended"
min_coverage = 80.0
warn_on_blind_spots = true
```

**Output:**
```
✓ Static: tsc PASS, eslint PASS
⚠️ Contracts: 75% coverage (target: 80%)
⚠️ Blind Spot: processPayment (CRITICAL)
   Suggested: z.object({ amount: z.number().positive() })
```

### Phase 2: Add Strict Mode (Optional)

**Timeline:** After user feedback (3-6 months)

```toml
[guard.typescript]
contract_policy = "strict"  # Opt-in
```

**Gate:** Only add if ≥5 users request it

### Phase 3: Risk-Based Intelligence (Future)

**Timeline:** 6-12 months

```toml
[guard.typescript]
contract_policy = "risk-based"
```

**Features:**
- ML-based risk detection (money, auth, security)
- Automatic blind spot prioritization
- Smart suggestions: "This function handles money, consider Zod"

---

## Performance Optimization Path

**Question for Next Discussion:** Can Zod runtime overhead be eliminated?

**Potential Approaches:**
1. **Compile-time validation** (Zod → TypeScript assertions)
2. **JIT optimization** (V8 inline caching)
3. **Conditional validation** (dev: validate, prod: skip)
4. **Partial validation** (validate once at boundary)

**Research Questions:**
- Can TypeScript compiler plugin insert Zod-equivalent checks?
- Can we detect "already validated" data flow and skip re-parse?
- Can build step pre-validate and strip Zod at runtime?

---

## Decision Matrix

| Scenario | Recommended Policy | Rationale |
|----------|-------------------|-----------|
| Greenfield Invar project | `strict` | No migration burden |
| Existing TS codebase | `recommended` | Gradual adoption |
| Financial/security code | `risk-based` + enforce | Critical safety |
| Performance-critical | `optional` + selective | Avoid overhead |
| AI agent development | `strict` | Prevent bad patterns |

---

## Success Criteria

### Must Have (Phase 1)

- [x] Recommended mode implemented (LX-06)
- [x] Coverage tracking (80% target)
- [x] Blind spot detection
- [x] Quality scoring (strong/medium/weak)

### Should Have (Phase 2)

- [ ] Strict mode available
- [ ] Config option: `contract_policy`
- [ ] Clear migration guide: recommended → strict
- [ ] User feedback: ≥5 requests for strict mode

### Nice to Have (Phase 3)

- [ ] Risk-based enforcement
- [ ] ML-based blind spot detection
- [ ] Performance optimization (see next discussion)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ecosystem pushback | High | Default to "recommended" |
| Zod dependency lock-in | Medium | Consider pluggable validators |
| Performance complaints | Medium | Research optimization (next) |
| Inconsistent adoption | Low | Clear docs + examples |

---

## Open Questions

### 1. Can Zod overhead be eliminated?

**Approaches to investigate:**
- TypeScript compiler plugin
- Build-time validation injection
- Conditional validation (dev vs. prod)
- Smart memoization

**Next:** Dedicated research discussion

### 2. Should we support alternative validators?

**Options:**
- Zod (current)
- Valibot (12KB, 15x faster)
- TypeBox (JSON Schema, 100x faster)
- io-ts (functional, mature)

**Trade-off:** Flexibility vs. consistency

### 3. What's the "right" default coverage target?

**Current:** 80%

**Alternatives:**
- 100% (Python parity)
- 90% (strict but realistic)
- 70% (relaxed)

**Research:** Survey TS community

---

## References

### Internal

- [LX-06: TypeScript Tooling](completed/LX-06-typescript-tooling.md)
- [LX-05: Language-Agnostic Protocol](completed/LX-05-language-agnostic-protocol.md)

### External

- [Zod Documentation](https://zod.dev/)
- [TypeScript Philosophy](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
- [Valibot Performance Comparison](https://valibot.dev/guides/benchmarks/)
- [TypeBox Benchmarks](https://github.com/sinclairzx81/typebox)

---

## Decision Log

### 2026-01-04: Proposal Created

**Context:** LX-06 Phase 1-3 complete with "recommended" mode. Need strategy for enforcement policy.

**Decision:**
1. Keep "recommended" as default (Phase 1)
2. Add "strict" mode if user demand (Phase 2)
3. Research performance optimization separately

**Rationale:**
- Ecosystem compatibility > Python parity
- Gradual adoption > all-or-nothing
- Prove value with recommendations before enforcing

**Next:** Discuss Zod performance optimization strategies
