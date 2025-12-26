# DX-38: Contract Quality Rules

> **"A contract that constrains nothing, guarantees nothing."**

**Status:** Partial (Tier 1-2 Implemented)
**Created:** 2025-12-25
**Updated:** 2025-12-27
**Origin:** Extracted from DX-33 Option A, merged with DX-28 P2
**Effort:** High
**Risk:** High (heuristics, false positives)

## Implementation Status (2025-12-27)

| Tier | Status | Location |
|------|--------|----------|
| Tier 1 | ✅ Done | `src/invar/core/tautology.py` |
| Tier 2 | ✅ Done | `src/invar/core/contracts.py` + `utils.py` |
| Tier 3 | ⏸ Deferred | High false-positive risk |
| Tier 4 | ⏸ Deferred | Needs more research |

### Tier 1 Implementation
- `lambda x: True` → "contract always returns True (no constraint)"
- `lambda x: False` → "contract always returns False (contradiction)"
- `lambda: ...` → "contract has no parameters (doesn't validate inputs)"

### Tier 2 Implementation
- `redundant_type_contract` rule enabled by default (severity: warning)
- Detects `isinstance(x, T)` redundant with type annotation `x: T`

## Scope

This proposal covers TWO complementary aspects of contract quality:

| Aspect | Description | Origin |
|--------|-------------|--------|
| **Contract Weakness** | Contracts that constrain too little (tautologies, redundant) | DX-33 |
| **Contract Incompleteness** | Contracts that miss important behaviors (filters, parsers) | DX-28 |

## Problem Statement

Guard checks contract **presence** but not contract **quality**. Ceremonial contracts pass all checks but add zero value:

```python
# These all pass Guard, but are they meaningful?
@pre(lambda x: True)                      # Always true - useless
@pre(lambda x: isinstance(x, int))        # Redundant with type hint
@pre(lambda x: x is not None)             # Sometimes useful, sometimes not
@post(lambda result: True)                # Guarantees nothing
```

DX-31 adversarial review found multiple instances of weak contracts that verification tools cannot detect.

## The Core Challenge

> **"Tools verify what IS, not what SHOULD BE."**

Contract quality requires understanding programmer **intent**:
- Is `@pre(lambda x: x > 0)` meaningful? Depends on the function's purpose.
- Is `@pre(lambda x: isinstance(x, str))` redundant? Depends on whether type hints exist.

This is fundamentally a semantic judgment, not a syntactic check.

## Proposed Approach

### Tier 1: Obvious Violations (Low Risk)

Patterns that are almost always wrong:

```python
OBVIOUS_WEAK_PATTERNS = [
    "lambda.*: True",           # Tautology
    "lambda.*: False",          # Contradiction (will always fail)
    "lambda: .*",               # No parameters used
]
```

### Tier 2: Redundancy Detection (Medium Risk)

Contracts that duplicate type information:

```python
def is_redundant_with_type_hint(contract: str, signature: str) -> bool:
    """
    Detect: @pre(lambda x: isinstance(x, int)) when x: int exists.

    >>> is_redundant_with_type_hint("lambda x: isinstance(x, int)", "(x: int)")
    True
    """
```

### Tier 3: Semantic Analysis (High Risk - Future)

Patterns that **might** be weak:

```python
# These need context to judge
@pre(lambda x: len(x) > 0)        # Meaningful for strings, maybe not for lists?
@pre(lambda x: x is not None)     # Useful if Optional[T], redundant otherwise
@post(lambda r: r is not None)    # Same issue
```

### Tier 4: Contract Completeness (from DX-28 P2)

Contracts that miss important behavioral patterns:

#### filter_dual_coverage

Filter expressions (`if x in y` or `if x not in y`) must have doctests covering both branches.

```python
def check_filter_dual_coverage(file_info: FileInfo, config) -> list[Violation]:
    """
    Detect: Missing branch coverage in filter logic.

    >>> # Bad: only tests matching case
    >>> def extract(items):
    ...     '''>>> extract(["a", "b"])'''
    ...     return [x for x in items if "a" in x]

    >>> # Good: tests both branches
    >>> def extract(items):
    ...     '''>>> extract(["a", "b"])  # matching
    ...        >>> extract(["x", "y"])  # non-matching'''
    ...     return [x for x in items if "a" in x]
    """
```

#### parser_format_test

Functions parsing strings must have doctests using realistic input formats.

```python
def check_parser_format_test(file_info: FileInfo, config) -> list[Violation]:
    """
    Detect: Parser tests with synthetic data missing real format.

    >>> # Bad: synthetic input
    >>> def parse_error(s):
    ...     '''>>> parse_error("test")'''
    ...     return "error:" in s.lower()

    >>> # Good: realistic format
    >>> def parse_error(s):
    ...     '''>>> parse_error("file.py:10: error: IndexError")'''
    ...     return ": error:" in s.lower()
    """
```

#### extraction_empty_test

Functions returning lists from string extraction must test empty and non-empty inputs.

```python
def check_extraction_empty_test(file_info: FileInfo, config) -> list[Violation]:
    """
    Detect: Missing empty-input handling tests.

    >>> # Bad: only non-empty
    >>> def split_lines(s):
    ...     '''>>> split_lines("a\\nb")'''
    ...     return s.split("\\n")

    >>> # Good: both cases
    >>> def split_lines(s):
    ...     '''>>> split_lines("")
    ...        >>> split_lines("a\\nb")'''
    ...     return s.split("\\n")
    """
```

#### relational_contract_suggested

Complex transformations should consider `@relates` for input-output relationships.

```python
def check_relational_contract(file_info: FileInfo, config) -> list[Violation]:
    """
    Suggest @relates for functions with filtering transformations.

    >>> # Could benefit from @relates:
    >>> def extract_errors(stdout: str) -> list[str]:
    ...     return [l for l in stdout.split("\\n") if ": error:" in l]

    >>> # With @relates:
    >>> @relates(lambda stdout, result:
    ...     (": error:" in stdout) <= (len(result) > 0),
    ...     "Errors in input → non-empty output")
    >>> def extract_errors(stdout: str) -> list[str]:
    ...     return [l for l in stdout.split("\\n") if ": error:" in l]
    """
```

## Implementation Plan

### Phase 1: Obvious Violations Only

Add `contract_quality` rule that only flags Tier 1 patterns:

```python
def check_contract_quality(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Detect obviously weak contracts (Tier 1 only).

    Examples:
        >>> # Tautology - always warn
        >>> source = '@pre(lambda x: True)\\ndef f(x): pass'
        >>> check_contract_quality(parse(source), RuleConfig())
        [Violation(rule="weak_contract", ...)]
    """
```

**False positive risk:** Very low - these patterns are almost never intentional.

### Phase 2: Redundancy Detection

Add `redundant_type_contract` check:

```python
# Already exists in contracts.py - need to integrate with Guard output
def is_redundant_type_contract(expression: str, signature: str) -> bool:
    ...
```

**False positive risk:** Medium - some teams prefer explicit type checks.

### Phase 3: Semantic Suggestions (Future)

Instead of warnings, provide **suggestions**:

```
INFO: Contract @pre(lambda x: x is not None) may be redundant
      if 'x' has non-Optional type hint. Consider:
      - Remove if type system guarantees non-None
      - Keep if documenting intent explicitly
```

## Configuration

Allow teams to tune sensitivity:

```toml
[tool.invar.guard]
contract_quality = "strict"  # warn on Tier 1 + 2
# contract_quality = "permissive"  # warn on Tier 1 only
# contract_quality = "off"  # disable
```

## Success Criteria

- [ ] Phase 1: Flag `lambda: True` and similar tautologies
- [ ] Phase 2: Detect isinstance() redundant with type hints
- [ ] False positive rate < 5% on real codebases
- [ ] Clear documentation on what triggers warnings

## Open Questions

1. Should weak contracts be ERROR or WARNING?
2. How to handle intentional documentation contracts?
3. Should we auto-suggest stronger contracts?

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| High false positive rate | Start with Tier 1 only |
| Teams use explicit contracts intentionally | Configuration to disable |
| Complex AST analysis needed | Reuse existing `contracts.py` logic |

## Implementation Phases (Updated)

| Phase | Tier | Rules | Risk |
|-------|------|-------|------|
| 1 | Tier 1 | `weak_contract` (tautology) | Low |
| 2 | Tier 2 | `redundant_type_contract` | Medium |
| 3 | Tier 4a | `filter_dual_coverage`, `extraction_empty_test` | Medium |
| 4 | Tier 4b | `parser_format_test`, `relational_contract_suggested` | Medium |
| 5 | Tier 3 | Semantic analysis suggestions | High |

## Related

- DX-33: Verification Blind Spots Analysis (origin of Tier 1-3)
- DX-28: Semantic Verification Mechanisms (origin of Tier 4, archived)
- `src/invar/core/contracts.py`: Existing redundancy detection
- `src/invar/core/tautology.py`: Semantic tautology detection
- `runtime/src/invar_runtime/relations.py`: `@relates` decorator
