# LX-01: Multi-Language Invar Feasibility Assessment

**Status:** Draft
**Created:** 2025-12-27
**Series:** LX (Language eXtension) - New series for multi-language evolution

## Executive Summary

Evaluate the feasibility of evolving Invar from a Python-specific tool into a multi-language development protocol with language-specific adapters.

**Core Hypothesis:** Invar's primary value lies in its workflow and agent protocol (USBV, adversarial review, context management), not in specific Python tools. These concepts are language-agnostic and could benefit developers across all languages.

---

## Problem Statement

### Current State

Invar is tightly coupled to Python:

```
invar-tools/
├── Core verification: deal, CrossHair, Hypothesis
├── Static analysis: ruff
├── Code patterns: Python decorators, doctests
└── Result: Only Python developers can use Invar
```

### Missed Opportunity

The most valuable parts of Invar are universal concepts:

| Concept | Python Implementation | Universal Value |
|---------|----------------------|-----------------|
| USBV Workflow | TodoList convention | ★★★ Process discipline |
| Agent Protocol | CLAUDE.md, skills | ★★★ AI collaboration |
| Adversarial Review | /review skill | ★★★ Quality assurance |
| Contract-First | @pre/@post decorators | ★★☆ Design by Contract |
| Core/Shell | Pure functions vs I/O | ★★☆ Functional architecture |

### Strategic Question

> Can Invar evolve from "Python contract verification tool" to "Universal AI-assisted development protocol"?

---

## Current Architecture Analysis

### Coupling Assessment

#### Tightly Coupled to Python (Refactor Required)

| Component | Location | Coupling Type |
|-----------|----------|---------------|
| `deal` contracts | `invar_runtime` | Library dependency |
| CrossHair verification | `shell/prove/crosshair.py` | Tool integration |
| Hypothesis testing | `shell/prove/hypothesis.py` | Tool integration |
| Ruff linting | `shell/commands/guard.py` | Tool integration |
| AST parsing | `core/parser.py` | Language-specific |
| Doctest extraction | `core/doctest.py` | Format-specific |
| `@pre`/`@post` syntax | Templates, docs | Syntax-specific |

#### Language-Agnostic (Extractable)

| Component | Location | Portability |
|-----------|----------|-------------|
| USBV workflow | `INVAR.md`, skills | ★★★ Pure concept |
| Skill definitions | `.claude/skills/` | ★★★ Markdown format |
| Agent protocol | `CLAUDE.md` template | ★★★ Region-based |
| Context management | `.invar/context.md` | ★★★ Markdown format |
| Check-In/Final | Protocol definition | ★★★ Tool-agnostic concept |
| Proposal system | `docs/proposals/` | ★★★ Process convention |
| Severity definitions | Skill content | ★★★ Universal taxonomy |

#### Partially Coupled (Abstraction Possible)

| Component | Current | Abstraction Path |
|-----------|---------|------------------|
| `invar guard` | Python tools | Plugin interface |
| `invar sig` | Python AST | Language-specific parser |
| `invar map` | Python analysis | Language-specific analyzer |
| Core/Shell pattern | Python conventions | Pattern definition per language |

### Coupling Ratio

```
Total Components: ~30 significant modules

Tightly Coupled:    8 (27%) - Require rewrite per language
Language-Agnostic: 15 (50%) - Extract to core
Partially Coupled:  7 (23%) - Abstraction layer needed

Conclusion: 50%+ is already language-agnostic
```

---

## Target Architecture

### Vision: Invar 2.0

```
@invar/core                    # Language-Agnostic Protocol
├── protocol/
│   ├── usbv.md                # USBV workflow specification
│   ├── check-in.md            # Check-In/Final protocol
│   └── severity.md            # CRITICAL/MAJOR/MINOR definitions
├── agent/
│   ├── claude-md-spec.md      # CLAUDE.md structure specification
│   ├── skill-format.md        # Skill file format specification
│   └── routing-rules.md       # Workflow routing rules
├── templates/
│   ├── CLAUDE.md.jinja        # Base template (language placeholder)
│   ├── INVAR.md.jinja         # Protocol template
│   └── skills/                # Skill templates
└── config/
    ├── context-format.md      # context.md specification
    └── lessons-format.md      # Lessons learned format

@invar/python                  # Python Adapter (Current, Refactored)
├── contracts/
│   ├── deal_integration.py    # deal library wrapper
│   └── contract_parser.py     # @pre/@post extraction
├── verify/
│   ├── crosshair_runner.py    # CrossHair integration
│   ├── hypothesis_runner.py   # Hypothesis integration
│   └── doctest_runner.py      # Doctest execution
├── static/
│   └── ruff_runner.py         # Ruff integration
├── guard.py                   # Python-specific guard
├── sig.py                     # Python signature extraction
├── map.py                     # Python symbol mapping
└── patterns.py                # Core/Shell pattern definitions

@invar/typescript              # TypeScript Adapter (Future)
├── contracts/
│   ├── zod_integration.ts     # Zod schema validation
│   └── contract_parser.ts     # JSDoc/TypeDoc extraction
├── verify/
│   ├── fastcheck_runner.ts    # fast-check integration
│   └── vitest_runner.ts       # Vitest integration
├── static/
│   ├── eslint_runner.ts       # ESLint integration
│   └── tsc_runner.ts          # TypeScript compiler checks
├── guard.ts                   # TypeScript-specific guard
├── sig.ts                     # TypeScript signature extraction
├── map.ts                     # TypeScript symbol mapping
└── patterns.ts                # Pure/Effect pattern definitions

@invar/rust                    # Rust Adapter (Future)
├── contracts/
│   └── contracts_crate.rs     # contracts crate integration
├── verify/
│   └── proptest_runner.rs     # proptest integration
├── static/
│   └── clippy_runner.rs       # Clippy integration
├── guard.rs                   # Rust-specific guard
├── sig.rs                     # Rust signature extraction
├── map.rs                     # Rust symbol mapping
└── patterns.rs                # Result<T,E> pattern definitions
```

### Plugin Interface

```python
# @invar/core defines the interface
class LanguageAdapter(Protocol):
    """Interface that each language adapter must implement."""

    # Required
    def guard(self, path: Path, changed_only: bool) -> GuardResult:
        """Run verification for this language."""
        ...

    def extract_signatures(self, path: Path) -> list[Signature]:
        """Extract function/method signatures with contracts."""
        ...

    def build_symbol_map(self, path: Path) -> SymbolMap:
        """Build symbol reference map."""
        ...

    # Optional
    def get_patterns(self) -> dict[str, PatternDefinition]:
        """Return Core/Shell equivalent patterns for this language."""
        ...

    def get_contract_syntax(self) -> ContractSyntax:
        """Return contract syntax for templates."""
        ...
```

### Template Parameterization

```jinja
{# CLAUDE.md.jinja with language parameters #}
## Quick Reference

| Zone | Requirements |
|------|-------------|
{% if language == "python" %}
| Core | `@pre`/`@post` + doctests, pure (no I/O) |
| Shell | Returns `Result[T, E]` from `returns` library |
{% elif language == "typescript" %}
| Core | Zod schemas + property tests, pure (no side effects) |
| Shell | Returns `Effect<A, E, R>` or `Result<T, E>` |
{% elif language == "rust" %}
| Core | `#[pre]`/`#[post]` + property tests, pure |
| Shell | Returns `Result<T, E>` |
{% endif %}
```

---

## Feasibility Assessment

### Technical Feasibility

| Aspect | Difficulty | Notes |
|--------|------------|-------|
| Extract core protocol | Low | Mostly documentation |
| Define plugin interface | Medium | API design critical |
| Refactor Python adapter | Medium | Current code needs modularization |
| Create TypeScript adapter | Medium | Good tool ecosystem |
| Create Rust adapter | Low | Strong type system helps |
| MCP tool abstraction | Medium | Need language-agnostic interface |

### Language Ecosystem Readiness

| Language | Contracts | Property Testing | Static Analysis | Readiness |
|----------|-----------|------------------|-----------------|-----------|
| **Python** | deal ★★★ | Hypothesis ★★★ | ruff ★★★ | ★★★ Current |
| **TypeScript** | zod ★★☆ | fast-check ★★☆ | ESLint ★★★ | ★★☆ Good |
| **Rust** | contracts ★★☆ | proptest ★★★ | clippy ★★★ | ★★★ Excellent |
| **Go** | assertions ★☆☆ | gopter ★★☆ | go vet ★★☆ | ★★☆ Adequate |
| **Java** | JML ★☆☆ | jqwik ★★☆ | SpotBugs ★★☆ | ★★☆ Adequate |

### Effort Estimation

| Phase | Effort | Duration | Dependencies |
|-------|--------|----------|--------------|
| Phase 1: Protocol extraction | Low | 1-2 weeks | None |
| Phase 2: Plugin interface | Medium | 2-3 weeks | Phase 1 |
| Phase 3: Python refactor | Medium | 3-4 weeks | Phase 2 |
| Phase 4: TypeScript adapter | Medium | 4-6 weeks | Phase 3 |
| Phase 5: Community adapters | Ongoing | N/A | Phase 4 |

**Total for Python + TypeScript:** ~3-4 months

---

## Risk Analysis

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Abstraction too complex | Architecture failure | Start with 2 languages only |
| Feature parity impossible | User confusion | Define "core" vs "extended" features |
| Maintenance burden | Quality decline | Community ownership model |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| CrossHair has no equivalent | Reduced verification depth | Accept different verification levels |
| Contract syntax varies | Template complexity | Language-specific examples |
| Breaking changes | Existing users affected | Maintain Python compatibility |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low adoption of new adapters | Wasted effort | Start with high-demand languages |
| Documentation overhead | User confusion | Unified docs with language tabs |

---

## Success Criteria

### Phase 1 Success (Protocol Extraction)

- [ ] USBV workflow defined as standalone specification
- [ ] Skill format standardized with JSON schema
- [ ] CLAUDE.md structure documented as specification
- [ ] Language placeholder system designed

### Phase 2 Success (Plugin Interface)

- [ ] `LanguageAdapter` protocol defined
- [ ] Guard result format standardized
- [ ] Signature format standardized
- [ ] Symbol map format standardized

### Phase 3 Success (Python Refactor)

- [ ] Python adapter uses plugin interface
- [ ] All existing tests pass
- [ ] No breaking changes for users
- [ ] Clear separation: core vs python

### Phase 4 Success (TypeScript Adapter)

- [ ] `invar init` works for TypeScript projects
- [ ] `invar guard` runs ESLint + fast-check
- [ ] CLAUDE.md generated with TypeScript patterns
- [ ] At least 3 real TypeScript projects validated

### Overall Success

- [ ] Developer can use Invar workflow in Python OR TypeScript
- [ ] Same USBV discipline applies to both
- [ ] Agent protocol works identically
- [ ] Community interest in additional adapters

---

## Alternatives Considered

### A: Stay Python-Only

**Pros:** No refactoring, focused effort
**Cons:** Limited adoption, missed opportunity
**Verdict:** Short-term safe, long-term limiting

### B: Full Rewrite in Rust

**Pros:** Performance, single binary distribution
**Cons:** High effort, community barrier
**Verdict:** Too risky, unnecessary

### C: Protocol-First (Recommended)

**Pros:** Validates abstraction incrementally, low initial cost
**Cons:** Longer total timeline
**Verdict:** Best balance of risk and reward

---

## Recommendation

**Proceed with Phase 1 (Protocol Extraction).**

Reasons:
1. **Low cost:** Mostly documentation work
2. **High value:** Clarifies what Invar really is
3. **Reversible:** No breaking changes
4. **Validation:** Proves or disproves the hypothesis

### Immediate Next Steps

1. **LX-02:** USBV Workflow Specification
2. **LX-03:** Skill Format Specification
3. **LX-04:** CLAUDE.md Structure Specification
4. **LX-05:** Plugin Interface Design

### Decision Points

| After Phase | Decision |
|-------------|----------|
| Phase 1 | Continue to Phase 2? (Is spec valuable?) |
| Phase 2 | Continue to Phase 3? (Is interface practical?) |
| Phase 3 | Continue to Phase 4? (Is TypeScript worth it?) |

Each phase has a natural exit point if the approach proves unviable.

---

## Appendix A: Contract Syntax Comparison

### Python (Current)

```python
from deal import pre, post

@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    >>> calculate(10)
    100
    """
    return x * x
```

### TypeScript (Proposed)

```typescript
import { z } from 'zod';
import { fc } from 'fast-check';

// Contract via schema
const PositiveInt = z.number().int().positive();

/**
 * @pre x > 0
 * @post result >= 0
 */
function calculate(x: z.infer<typeof PositiveInt>): number {
    return x * x;
}

// Property test (equivalent to doctest)
test('calculate properties', () => {
    fc.assert(fc.property(
        fc.integer({ min: 1 }),
        (x) => calculate(x) >= 0
    ));
});
```

### Rust (Proposed)

```rust
use contracts::*;

/// Calculate the square of a positive number.
///
/// # Examples
/// ```
/// assert_eq!(calculate(10), 100);
/// ```
#[pre(x > 0)]
#[post(ret >= 0)]
fn calculate(x: i32) -> i32 {
    x * x
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn calculate_positive(x in 1i32..1000) {
            prop_assert!(calculate(x) >= 0);
        }
    }
}
```

---

## Appendix B: Feature Matrix

| Feature | Python | TypeScript | Rust | Core? |
|---------|--------|------------|------|-------|
| USBV Workflow | ✓ | ✓ | ✓ | Yes |
| Agent Protocol | ✓ | ✓ | ✓ | Yes |
| Check-In/Final | ✓ | ✓ | ✓ | Yes |
| Adversarial Review | ✓ | ✓ | ✓ | Yes |
| Preconditions | deal @pre | zod schemas | #[pre] | Concept |
| Postconditions | deal @post | return types | #[post] | Concept |
| Property Testing | Hypothesis | fast-check | proptest | Concept |
| Symbolic Execution | CrossHair | N/A | N/A | Extended |
| Static Analysis | ruff | ESLint+tsc | clippy | Adapter |
| Doctests | Python doctest | JSDoc examples | rustdoc | Adapter |

---

## Appendix C: Naming Considerations

### Package Names

| Option | Core | Python | TypeScript | Notes |
|--------|------|--------|------------|-------|
| A | `invar-core` | `invar-python` | `invar-typescript` | Clear |
| B | `@invar/core` | `@invar/python` | `@invar/ts` | Scoped |
| C | `invar` | `invar[python]` | `invar[ts]` | Extras |

**Recommendation:** Option A for clarity across package managers.

### Command Names

```bash
# Option 1: Subcommand per language
invar python guard
invar typescript guard
invar rust guard

# Option 2: Auto-detect (recommended)
invar guard  # Detects language from pyproject.toml/package.json/Cargo.toml

# Option 3: Separate binaries
invar-py guard
invar-ts guard
invar-rs guard
```

**Recommendation:** Option 2 (auto-detect) for best UX.

---

*Created as part of LX (Language eXtension) series.*
