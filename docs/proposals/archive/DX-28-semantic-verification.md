# DX-28: Semantic Verification Mechanisms

> **"Catch logic bugs that type-correct code hides."**

**Status:** ✅ Complete (P0/P1 implemented, P2 merged to DX-38)
**Archived:** 2025-12-25

## Resolution

| Priority | Description | Resolution |
|----------|-------------|------------|
| P0 | Core relational contracts | ✅ Implemented |
| P1 | Skip abuse prevention, FormatSpec | ✅ Implemented |
| P2 | Contract quality rules | → Merged to **DX-38** Tier 4 |
| P2 | Bidirectional testing | → Implementation detail (no separate proposal needed) |
| P2 | CrossHair @relates integration | → Implementation detail (no separate proposal needed) |

## Implemented Components (P0/P1)

| Component | Location | Description |
|-----------|----------|-------------|
| `@relates` decorator | `runtime/src/invar_runtime/relations.py` | Input-output relational contracts |
| `@relates_multi` decorator | `runtime/src/invar_runtime/relations.py` | Multi-argument relational contracts |
| `RelationViolation` exception | `runtime/src/invar_runtime/relations.py` | Exception for contract violations |
| `FormatSpec` classes | `src/invar/core/format_specs.py` | Base classes for format specifications |
| `CrossHairOutputSpec` | `src/invar/core/format_specs.py` | CrossHair output format specification |
| Hypothesis strategies | `src/invar/core/format_strategies.py` | Format-driven property testing strategies |
| `invar mutate` command | `src/invar/shell/mutate_cmd.py` | Mutation testing CLI integration |
| `MutationResult` class | `src/invar/shell/mutation.py` | Mutation testing result model |
| `skip_without_reason` rule | `src/invar/core/contracts.py` | Guard warns when @skip_property_test lacks justification |
| `@skip_property_test(reason)` | `runtime/src/invar_runtime/decorators.py` | Enhanced to require reason string |

### Pending

| Component | Priority | Description |
|-----------|----------|-------------|
| Contract quality rules | P2 | Guard rules for contract completeness (filter_dual_coverage, parser_format_test, etc.) |
| Bidirectional testing | P2 | `BidirectionalSpec` framework |
| CrossHair integration | P2 | Symbolic verification of `@relates` |

### Skip Abuse Prevention (Dec 2024)

The `@skip_property_test` decorator now requires a reason string. Guard enforces this via the `skip_without_reason` rule.

**Valid skip reasons:**
- `no_params: Function has no parameters to test`
- `strategy_factory: Returns Hypothesis strategy, not testable data`
- `external_io: Requires database/network/filesystem`
- `non_deterministic: Output depends on time/random state`

```python
# ✅ Good - with reason
@skip_property_test("no_params: Zero-parameter function")
def get_constant() -> int:
    return 42

# ❌ Bad - Guard warns
@skip_property_test
def my_func(): ...

@skip_property_test()
def my_func(): ...
```

## Problem Statement

### The Bug That Escaped

A bug in `prove.py` went undetected through all verification layers:

```python
# BUG: Logic inverted - excludes what it should include
counterexamples = [
    line.strip()
    for line in stdout.split("\n")
    if line.strip() and "error" not in line.lower()  # ← "not in" is wrong
]
```

CrossHair output format: `file.py:92: error: IndexError when calling func('')`

The bug **excluded** all actual counterexamples because they contain "error".

### Why It Wasn't Caught

| Layer | What It Checked | Why It Missed |
|-------|-----------------|---------------|
| Static Analysis | Types, imports, size | No logic analysis |
| `@post(lambda r: isinstance(r, list))` | Return type | Content not verified |
| Doctests | Example cases | No counterexample format test |
| CrossHair | Contract satisfaction | Contract incomplete |
| Hypothesis | Property satisfaction | Property incomplete |

**Root Cause:** All layers verified that code satisfies its specification, but the specification itself was incomplete.

### The Bug Class

This represents a broader class: **Type-Correct, Semantically-Wrong (TCSW)** bugs.

Characteristics:
- Types are correct
- Structure is correct
- Logic is inverted/wrong
- Common path works, edge cases fail
- Existing tests don't cover the failing path

Examples:
- `in` vs `not in`
- `==` vs `!=`
- `>` vs `>=`
- `and` vs `or`
- Filter includes vs excludes

## Goals

1. **Systematic Detection**: Mechanisms that catch TCSW bugs automatically
2. **Specification Completeness**: Ensure contracts capture full semantics
3. **Coverage Visibility**: Know when verification is incomplete
4. **Low Friction**: Integrate into existing workflow without overhead

## Non-Goals

- Replacing existing verification (additive, not replacement)
- 100% bug prevention (defense in depth, not silver bullet)
- Changing the Core/Shell architecture

## Proposed Mechanisms

### Mechanism 1: Relational Contracts

**Problem:** Current `@pre`/`@post` only access input or output, not both.

**Solution:** Add `@relates` decorator for input-output relationships.

```python
from invar_runtime import relates

@pre(lambda stdout: isinstance(stdout, str))
@post(lambda result: isinstance(result, list))
@relates(lambda stdout, result:
    (": error:" in stdout.lower()) <= (len(result) > 0),
    "If input contains errors, output must be non-empty")
def extract_counterexamples(stdout: str) -> list[str]:
    ...
```

**Implementation:**

```python
# invar_runtime/relations.py

from functools import wraps
from typing import Callable, Any

def relates(
    relation: Callable[[Any, Any], bool],
    message: str = ""
) -> Callable:
    """
    Decorator asserting input-output relationship.

    The relation function receives (input_args, result) and must return True.
    CrossHair can verify this symbolically.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Capture first positional arg as primary input
            primary_input = args[0] if args else None
            if not relation(primary_input, result):
                raise RelationViolation(
                    f"Relation violated: {message}\n"
                    f"Input: {primary_input!r}\n"
                    f"Output: {result!r}"
                )
            return result

        # Preserve for CrossHair analysis
        wrapper.__relates__ = (relation, message)
        return wrapper
    return decorator

class RelationViolation(AssertionError):
    """Raised when input-output relation is violated."""
    pass
```

**Verification:** CrossHair can verify `@relates` by treating it as a postcondition that has access to captured inputs.

### Mechanism 2: Format-Driven Property Testing

**Problem:** Hypothesis uses random strings, missing format-specific bugs.

**Solution:** Define format specifications as strategies.

```python
# src/invar/core/format_specs.py

from dataclasses import dataclass
from hypothesis import strategies as st
from typing import Protocol

class FormatSpec(Protocol):
    """Protocol for format specifications."""

    def strategy(self) -> st.SearchStrategy:
        """Return Hypothesis strategy generating valid instances."""
        ...

    def matches(self, value: str) -> bool:
        """Check if value matches this format."""
        ...

@dataclass
class CrossHairOutputSpec:
    """Specification for CrossHair output format."""

    @staticmethod
    def counterexample_line() -> st.SearchStrategy[str]:
        """Generate a single counterexample line."""
        file_path = st.from_regex(r"[a-z_/]+\.py", fullmatch=True)
        line_num = st.integers(min_value=1, max_value=1000)
        error_type = st.sampled_from([
            "AssertionError", "IndexError", "ValueError",
            "TypeError", "KeyError", "AttributeError"
        ])
        func_name = st.from_regex(r"[a-z_][a-z0-9_]*", fullmatch=True)
        args = st.from_regex(r"[a-z_]*='[^']*'", fullmatch=True) | st.just("")

        return st.builds(
            lambda f, l, e, fn, a: f"{f}:{l}: error: {e} when calling {fn}({a})",
            file_path, line_num, error_type, func_name, args
        )

    @staticmethod
    def strategy() -> st.SearchStrategy[str]:
        """Generate complete CrossHair output."""
        return st.lists(
            CrossHairOutputSpec.counterexample_line(),
            min_size=0, max_size=5
        ).map(lambda lines: "\n".join(lines))

    @staticmethod
    def matches(value: str) -> bool:
        """Check if value matches CrossHair output format."""
        if not value.strip():
            return True  # Empty is valid (no errors)
        return all(
            ": error:" in line.lower()
            for line in value.strip().split("\n")
            if line.strip()
        )
```

**Usage in Tests:**

```python
# tests/properties/test_counterexample_extraction.py

from hypothesis import given
from invar.core.format_specs import CrossHairOutputSpec

@given(stdout=CrossHairOutputSpec.strategy())
def test_extraction_count_matches(stdout: str):
    """Number of extracted counterexamples equals lines with ': error:'"""
    result = extract_counterexamples(stdout)
    expected = sum(1 for line in stdout.split("\n")
                   if line.strip() and ": error:" in line.lower())
    assert len(result) == expected

@given(stdout=CrossHairOutputSpec.strategy())
def test_extraction_preserves_content(stdout: str):
    """Each counterexample line is preserved in output."""
    result = extract_counterexamples(stdout)
    for r in result:
        assert ": error:" in r.lower()
        assert r in stdout
```

### Mechanism 3: Bidirectional Testing

**Problem:** Parser tests only go input→output, missing format mismatches.

**Solution:** Test both directions: generate→parse and parse→validate.

```python
# src/invar/core/bidirectional.py

from dataclasses import dataclass
from typing import Generic, TypeVar, Callable

T = TypeVar('T')
S = TypeVar('S')

@dataclass
class BidirectionalSpec(Generic[T, S]):
    """
    Specification for bidirectional testing.

    T: Structured type (e.g., list of CounterexampleLine)
    S: Serialized type (e.g., str)
    """
    generate: Callable[[], T]      # Generate structured data
    render: Callable[[T], S]       # Structured → Serialized
    parse: Callable[[S], T]        # Serialized → Structured
    equivalent: Callable[[T, T], bool]  # Compare structured data

    def test_roundtrip(self, iterations: int = 100) -> list[str]:
        """
        Test that parse(render(x)) ≈ x

        Returns list of failures.
        """
        failures = []
        for i in range(iterations):
            original = self.generate()
            serialized = self.render(original)
            parsed = self.parse(serialized)
            if not self.equivalent(original, parsed):
                failures.append(
                    f"Iteration {i}:\n"
                    f"  Original: {original}\n"
                    f"  Serialized: {serialized}\n"
                    f"  Parsed: {parsed}"
                )
        return failures

# Example usage
counterexample_spec = BidirectionalSpec(
    generate=lambda: [generate_counterexample() for _ in range(random.randint(0, 5))],
    render=lambda ces: "\n".join(ce.render() for ce in ces),
    parse=lambda s: parse_counterexamples(s),
    equivalent=lambda a, b: len(a) == len(b) and all(
        a[i].function == b[i].function for i in range(len(a))
    )
)
```

### Mechanism 4: Contract Quality Rules

**Problem:** No enforcement that contracts are complete.

**Solution:** Add Guard rules checking contract quality.

```python
# src/invar/core/rules_contract_quality.py

"""
Contract quality rules for semantic verification.

DX-28: Detect incomplete contracts that may miss logic bugs.
"""

from invar.core.models import FileInfo, Violation, Severity, Symbol

def check_filter_dual_coverage(file_info: FileInfo, config) -> list[Violation]:
    """
    Rule: filter_dual_coverage

    Filter expressions (`if x in y` or `if x not in y`) must have
    doctests covering both True and False branches.

    Detects: Missing branch coverage in filter logic
    """
    violations = []

    for symbol in file_info.symbols:
        if not symbol.has_doctest:
            continue

        # Check for filter patterns in source
        source = _get_symbol_source(file_info, symbol)
        has_in_filter = _has_pattern(source, r'\bif\b.*\bin\b')
        has_not_in_filter = _has_pattern(source, r'\bif\b.*\bnot\s+in\b')

        if has_in_filter or has_not_in_filter:
            # Verify doctests cover both branches
            if not _has_dual_branch_coverage(symbol.docstring):
                violations.append(Violation(
                    rule="filter_dual_coverage",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Filter in '{symbol.name}' needs doctests for both matching and non-matching cases",
                    suggestion="Add doctests showing: (1) input that matches filter, (2) input that doesn't match"
                ))

    return violations

def check_parser_format_test(file_info: FileInfo, config) -> list[Violation]:
    """
    Rule: parser_format_test

    Functions parsing strings (using split, regex, 'in' checks) must have
    doctests using realistic input formats.

    Detects: Parser tests with synthetic data missing real format
    """
    violations = []

    for symbol in file_info.symbols:
        source = _get_symbol_source(file_info, symbol)

        # Detect string parsing patterns
        is_parser = any([
            _has_pattern(source, r'\.split\('),
            _has_pattern(source, r're\.(match|search|findall)'),
            _has_pattern(source, r'for\s+\w+\s+in\s+\w+\.split'),
        ])

        if is_parser and symbol.has_doctest:
            # Check if doctests use realistic format
            if not _doctest_has_realistic_format(symbol.docstring):
                violations.append(Violation(
                    rule="parser_format_test",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Parser '{symbol.name}' should have doctests with realistic input format",
                    suggestion="Add doctest using actual format the parser will receive in production"
                ))

    return violations

def check_extraction_empty_test(file_info: FileInfo, config) -> list[Violation]:
    """
    Rule: extraction_empty_test

    Functions returning lists from string extraction must have doctests
    for both empty and non-empty inputs.

    Detects: Missing empty-input handling tests
    """
    violations = []

    for symbol in file_info.symbols:
        # Check if function returns list and takes string input
        if not _returns_list(symbol) or not _takes_string_input(symbol):
            continue

        if symbol.has_doctest:
            has_empty_test = _doctest_has_pattern(symbol.docstring, r'>>>\s*\w+\(["\']["\']')
            has_nonempty_test = _doctest_has_pattern(symbol.docstring, r'>>>\s*\w+\(["\'][^"\']+["\']')

            if not has_empty_test or not has_nonempty_test:
                violations.append(Violation(
                    rule="extraction_empty_test",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Extraction function '{symbol.name}' needs empty and non-empty input doctests",
                    suggestion="Add: (1) doctest with empty string input, (2) doctest with typical non-empty input"
                ))

    return violations

def check_relational_contract(file_info: FileInfo, config) -> list[Violation]:
    """
    Rule: relational_contract_suggested

    Functions with string parsing that return collections should consider
    using @relates to specify input-output relationship.

    Detects: Missing relational contracts on complex transformations
    """
    violations = []

    for symbol in file_info.symbols:
        source = _get_symbol_source(file_info, symbol)

        # Complex transformation: string input, collection output, uses filtering
        is_complex_transform = (
            _takes_string_input(symbol) and
            _returns_collection(symbol) and
            (_has_pattern(source, r'\bif\b.*\bin\b') or
             _has_pattern(source, r'for.*if'))
        )

        has_relates = '@relates' in source

        if is_complex_transform and not has_relates:
            # Check if existing contracts specify input-output relationship
            has_io_contract = _contracts_reference_input_and_output(symbol)

            if not has_io_contract:
                violations.append(Violation(
                    rule="relational_contract_suggested",
                    severity=Severity.INFO,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Consider @relates for '{symbol.name}' to specify input-output relationship",
                    suggestion="Add @relates(lambda input, output: <relationship>) to catch logic inversions"
                ))

    return violations
```

### Mechanism 5: Mutation Testing Integration

**Problem:** Tests pass but don't catch logic inversions.

**Solution:** Integrate mutation testing to detect undertested code.

```python
# src/invar/shell/mutation.py

"""
Mutation testing integration for Invar.

DX-28: Detect undertested code by checking if mutations break tests.
"""

import subprocess
from pathlib import Path
from dataclasses import dataclass
from returns.result import Result, Success, Failure

@dataclass
class MutationResult:
    """Result of mutation testing."""
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    score: float  # killed / total
    survivors: list[str]  # Descriptions of surviving mutants

def run_mutation_testing(
    target: Path,
    test_command: str = "python -m pytest",
    mutations: list[str] | None = None
) -> Result[MutationResult, str]:
    """
    Run mutation testing on target file.

    Uses mutmut for mutation generation and test execution.

    Args:
        target: File to mutate
        test_command: Command to run tests
        mutations: Specific mutation types to test (default: all)

    Returns:
        MutationResult with score and surviving mutants
    """
    try:
        # Run mutmut
        cmd = [
            "mutmut", "run",
            "--paths-to-mutate", str(target),
            "--runner", test_command,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Parse results
        return Success(_parse_mutmut_results(result.stdout))

    except subprocess.TimeoutExpired:
        return Failure("Mutation testing timed out (10 min)")
    except FileNotFoundError:
        return Failure("mutmut not installed. Run: pip install mutmut")
    except Exception as e:
        return Failure(f"Mutation testing error: {e}")

# Priority mutations for logic bugs
LOGIC_MUTATIONS = [
    ("in", "not in"),
    ("not in", "in"),
    ("==", "!="),
    ("!=", "=="),
    (">", ">="),
    (">=", ">"),
    ("<", "<="),
    ("<=", "<"),
    ("and", "or"),
    ("or", "and"),
    ("True", "False"),
    ("False", "True"),
]
```

**CLI Integration:**

```bash
# New command
invar mutate src/invar/shell/prove.py

# Output
Mutation Testing Report
=======================
Target: src/invar/shell/prove.py
Mutants: 45 total, 42 killed, 3 survived
Score: 93.3%

⚠️  Surviving Mutants (undertested code):
  Line 184: `in` → `not in` SURVIVED
    → Filter logic may have inverted behavior undetected by tests

  Line 203: `> 0` → `>= 0` SURVIVED
    → Boundary condition not tested

  Line 215: `and` → `or` SURVIVED
    → Boolean logic not fully tested

Suggestion: Add tests that would fail if these mutations were applied.
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

1. **Add `@relates` decorator to invar_runtime**
   - Implement `relates()` decorator
   - Integrate with CrossHair verification
   - Add doctests and documentation

2. **Create format specification framework**
   - Define `FormatSpec` protocol
   - Implement `CrossHairOutputSpec`
   - Add to `invar.core.format_specs`

### Phase 2: Rules (Week 2-3)

3. **Implement contract quality rules**
   - `filter_dual_coverage`
   - `parser_format_test`
   - `extraction_empty_test`
   - `relational_contract_suggested`

4. **Add rules to Guard**
   - Register in `check_all_rules()`
   - Add to RULE_META
   - Update documentation

### Phase 3: Testing (Week 3-4)

5. **Create property test templates**
   - Format-driven strategies
   - Bidirectional test patterns
   - Example implementations

6. **Integrate mutation testing**
   - Add `invar mutate` command
   - Parse mutmut results
   - Generate actionable reports

### Phase 4: Documentation (Week 4)

7. **Update ICIDIV workflow**
   - Add semantic verification checklist
   - Document `@relates` usage
   - Add format spec examples

8. **Create mechanism documentation**
   - `docs/mechanisms/verification/semantic-contracts.md`
   - `docs/mechanisms/verification/format-testing.md`
   - `docs/mechanisms/verification/mutation-testing.md`

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `runtime/src/invar_runtime/relations.py` | `@relates` decorator |
| `src/invar/core/format_specs.py` | Format specification framework |
| `src/invar/core/rules_contract_quality.py` | Contract quality rules |
| `src/invar/core/bidirectional.py` | Bidirectional testing framework |
| `src/invar/shell/mutation.py` | Mutation testing integration |
| `docs/mechanisms/verification/semantic-contracts.md` | Documentation |

### Modified Files

| File | Changes |
|------|---------|
| `runtime/src/invar_runtime/__init__.py` | Export `relates` |
| `src/invar/core/rules.py` | Import contract quality rules |
| `src/invar/core/rule_meta.py` | Add new rule metadata |
| `src/invar/shell/cli.py` | Add `mutate` command |
| `INVAR.md` | Update ICIDIV with semantic verification |

## Success Metrics

### Quantitative

| Metric | Target |
|--------|--------|
| TCSW bugs caught by new rules | > 80% of introduced bugs |
| Contract quality rule violations in existing code | < 10 after fixes |
| Mutation score on Core modules | > 90% |
| Format-driven property tests | 100% coverage of parsers |

### Qualitative

- Developers naturally write `@relates` for complex transformations
- Format specs become standard practice for string parsing
- Mutation testing runs in CI for critical paths
- TCSW bug class becomes rare in code reviews

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `@relates` adds complexity | Make it optional, suggest via INFO rule |
| Mutation testing is slow | Run only on changed files, cache results |
| Too many new warnings | Phase rollout: INFO → WARNING over time |
| Format specs are tedious | Provide generators for common formats |

## Alternatives Considered

### 1. Dependent Types
Full dependent type system (like Idris) would catch these bugs at compile time.
**Rejected:** Too large a change, not compatible with Python ecosystem.

### 2. Formal Specification Languages
Using TLA+ or Alloy for specifications.
**Rejected:** Steep learning curve, separate from code.

### 3. Only Mutation Testing
Rely solely on mutation testing to find gaps.
**Rejected:** Reactive (finds gaps after the fact), doesn't guide writing better contracts.

## References

- [CrossHair Documentation](https://crosshair.readthedocs.io/)
- [Hypothesis Strategies](https://hypothesis.readthedocs.io/en/latest/data.html)
- [Mutation Testing with mutmut](https://mutmut.readthedocs.io/)
- [Property-Based Testing in Practice](https://fsharpforfunandprofit.com/posts/property-based-testing/)

## Appendix: Example Transformation

### Before DX-28

```python
def extract_counterexamples(stdout: str) -> list[str]:
    """Extract counterexamples from CrossHair output."""
    return [
        line.strip()
        for line in stdout.split("\n")
        if line.strip() and "error" not in line.lower()  # BUG: inverted
    ]
```

### After DX-28

```python
from invar_runtime import relates

@pre(lambda stdout: isinstance(stdout, str))
@post(lambda result: isinstance(result, list))
@relates(
    lambda stdout, result: (": error:" in stdout.lower()) <= (len(result) > 0),
    "Input with errors must produce non-empty output"
)
def extract_counterexamples(stdout: str) -> list[str]:
    """
    Extract counterexample lines from CrossHair output.

    CrossHair format: "file.py:10: error: AssertionError when calling func(...)"

    Examples:
        >>> extract_counterexamples("")
        []
        >>> extract_counterexamples("file.py:10: error: AssertionError when calling foo('')")
        ["file.py:10: error: AssertionError when calling foo('')"]
        >>> extract_counterexamples("All contracts verified")
        []
        >>> len(extract_counterexamples("a.py:1: error: E1\\nb.py:2: error: E2"))
        2
    """
    if not stdout or not stdout.strip():
        return []
    return [
        line.strip()
        for line in stdout.split("\n")
        if line.strip() and ": error:" in line.lower()
    ]
```

The `@relates` contract would have caught the original bug because:
1. Input `"file.py:10: error: IndexError..."` contains `": error:"`
2. With buggy code, output would be `[]` (empty)
3. Relation `(True) <= (False)` → `False` → Contract violation!
