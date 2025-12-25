# Severity Level Design

Invar uses three severity levels with distinct principles and behaviors.

## Overview

| Level | Behavior | Principle |
|-------|----------|-----------|
| **ERROR** | Blocks (exit 1) | Correctness or architecture broken |
| **WARNING** | Blocks with `--strict` | Quality degraded, may be false positive |
| **INFO** | Never blocks | Suggestion, requires human judgment |

## Exit Code Logic

```python
if errors > 0:           return 1  # Always blocks
if strict and warnings:  return 1  # --strict blocks
return 0                           # Pass
```

---

## ERROR - Must Fix

### Principle

**Code cannot work correctly OR architecture is broken.**

An ERROR means:
- The code will fail at runtime, OR
- The code cannot be verified, OR
- Architectural boundaries are violated

### Classification Criteria

| Criterion | Example |
|-----------|---------|
| Runtime failure certain | `param_mismatch` - lambda params wrong |
| Verification impossible | `missing_contract` - no @pre/@post |
| Architecture violated | `forbidden_import` - Core has I/O |
| Hard limit exceeded | `file_size` - unmaintainable |

### Current ERROR Rules (9)

| Rule | Rationale |
|------|-----------|
| `file_size` | >500 lines is unmaintainable |
| `missing_contract` | Cannot verify without contracts |
| `empty_contract` | Tautology is worse than missing |
| `param_mismatch` | Will crash at runtime |
| `forbidden_import` | Breaks Core purity |
| `impure_call` | Breaks Core purity |
| `shell_result` | Architecture: Shell must return Result |
| `entry_point_too_thick` | Architecture: Entry points must be thin |
| `shell_complexity_debt` | Accumulated debt must be addressed |

### Escape Hatches

Only **architecture rules** support escape (where context matters):

```python
# @invar:allow shell_result: Legacy API compatibility
def legacy_endpoint():
    return {"status": "ok"}  # Can't return Result

# @invar:allow entry_point_too_thick: Complex CLI orchestration
@app.command()
def guard(...):
    ...  # 100+ lines justified
```

**Correctness rules have no escape** - `param_mismatch` will crash, period.

---

## WARNING - Should Fix

### Principle

**Code works but quality is degraded. Detection may have false positives.**

A WARNING means:
- Code functions correctly
- But maintainability/quality suffers
- Or the detection is heuristic-based

### Classification Criteria

| Criterion | Example |
|-----------|---------|
| Quality degradation | `function_size` - harder to understand |
| Approaching limit | `file_size_warning` - 80% of max |
| Heuristic detection | `shell_pure_logic` - string matching |
| Potential issue | `must_use_ignored` - may be intentional |

### Current WARNING Rules (6)

| Rule | Rationale |
|------|-----------|
| `file_size_warning` | Early warning, not yet a problem |
| `function_size` | Complex algorithms may need long functions |
| `must_use_ignored` | Detection has blind spots (cross-module) |
| `internal_import` | May be needed for circular imports |
| `shell_pure_logic` | May be orchestration logic |
| `missing_doctest` | Not all functions need examples |

### Why Not ERROR?

#### `shell_pure_logic`

Detection uses string matching for I/O patterns:

```python
IO_INDICATORS = [".read(", "open(", "Path(", ...]

def has_io_operations(source: str) -> bool:
    return any(indicator in source for indicator in IO_INDICATORS)
```

**Blind spots:**
- `self.client.fetch()` - indirect I/O
- `flask.request.json` - framework I/O
- `User.query.filter()` - ORM I/O

**False positives are common** - orchestration functions coordinate I/O modules without doing I/O directly.

#### `missing_doctest`

Doctests are **illustrative**, not **prescriptive**:

```
Contracts: DEFINE what is correct (@pre/@post)
Doctests:  SHOW examples of correctness
```

A function can be verified via contracts + CrossHair without doctests. Making this ERROR would create busywork for trivial functions.

### Handling Warnings

1. **Daily development**: Warnings don't block
2. **CI/strict mode**: `invar guard --strict` blocks on warnings
3. **Best practice**: Fix warnings in files you modify

---

## INFO - May Ignore

### Principle

**Suggestion only. May not be a problem. Requires human judgment.**

An INFO means:
- Individual instance is minor
- May be intentional or justified
- Accumulation may indicate systemic issue

### Classification Criteria

| Criterion | Example |
|-----------|---------|
| Often intentional | `redundant_type_contract` - expected when forcing contracts |
| Context-dependent | `shell_too_complex` - complexity may be justified |
| Accumulation matters | 5+ complexity warnings → ERROR |

### Current INFO Rules (2)

| Rule | Rationale |
|------|-----------|
| `redundant_type_contract` | Expected behavior, default OFF |
| `shell_too_complex` | Single instance is minor |

### Escalation Mechanism

INFO rules can escalate to ERROR when accumulated:

```
shell_too_complex (INFO) × 5 → shell_complexity_debt (ERROR)
```

This enforces "Fix-or-Explain" at project level without blocking individual changes.

---

## Design Principles Summary

### 1. ERROR = Certain Problem

```
Detection confidence: 100%
False positive rate: 0%
Action required: Always
```

### 2. WARNING = Probable Problem

```
Detection confidence: High but not certain
False positive rate: Low but possible
Action required: In files you modify
```

### 3. INFO = Possible Problem

```
Detection confidence: Variable
False positive rate: Expected
Action required: At your discretion
```

### 4. Escape Hatches

```
ERROR (architecture): @invar:allow + reason
ERROR (correctness): No escape
WARNING: Semantic markers or severity_overrides
INFO: Semantic markers (prevent escalation)
```

### 5. Agent-Native Default

```
Default: ERROR blocks, WARNING warns
--strict: ERROR + WARNING block
Rationale: Agent shouldn't be blocked by legacy warnings
```

---

## Quick Reference

### When to use each level

| Situation | Level |
|-----------|-------|
| Will crash at runtime | ERROR |
| Cannot verify correctness | ERROR |
| Breaks architecture boundary | ERROR |
| Exceeds hard limit | ERROR |
| Heuristic detection | WARNING |
| Quality concern | WARNING |
| Style suggestion | INFO |
| Often intentional | INFO |

### Markers

| Marker | Level | Purpose |
|--------|-------|---------|
| `# @invar:allow <rule>: <reason>` | ERROR | Escape with justification |
| `# @shell_orchestration: <reason>` | WARNING | Mark as coordination logic |
| `# @shell_complexity: <reason>` | INFO | Prevent escalation |
| `# @shell:entry` | N/A | Mark as custom entry point |
