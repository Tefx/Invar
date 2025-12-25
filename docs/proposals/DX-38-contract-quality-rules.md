# DX-38: Contract Quality Rules

> **"A contract that constrains nothing, guarantees nothing."**

**Status:** Draft
**Created:** 2025-12-25
**Origin:** Extracted from DX-33 Option A
**Effort:** High
**Risk:** High (heuristics, false positives)

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

## Related

- DX-33: Verification Blind Spots Analysis (origin)
- `src/invar/core/contracts.py`: Existing redundancy detection
- `src/invar/core/tautology.py`: Semantic tautology detection
