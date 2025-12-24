# Rule Mechanisms

Guard enforces architectural rules with configurable severity.

**See also:** [Severity Design](severity-design.md) for principles behind level assignments.

## Rule Categories

| Category | Purpose | Layer |
|----------|---------|-------|
| size | File and function limits | All |
| contracts | @pre/@post quality | Core |
| purity | I/O isolation | Core |
| shell | Architecture enforcement | Shell |
| docs | Documentation requirements | Core |

## All Rules

### Size Rules

| Rule | Severity | Escape | Description |
|------|----------|--------|-------------|
| `file_size` | ERROR | No | File exceeds `max_file_lines` |
| `file_size_warning` | WARNING | - | File at 80% of limit |
| `function_size` | WARNING | - | Function exceeds `max_function_lines` |

### Contract Rules

| Rule | Severity | Escape | Description |
|------|----------|--------|-------------|
| `missing_contract` | ERROR | No | Core function without @pre or @post |
| `empty_contract` | ERROR | No | Tautology like `@pre(lambda: True)` |
| `redundant_type_contract` | INFO | - | Contract only checks types |
| `param_mismatch` | ERROR | No | Lambda params don't match function |
| `must_use_ignored` | WARNING | - | @must_use return value ignored |

### Purity Rules

| Rule | Severity | Escape | Description |
|------|----------|--------|-------------|
| `forbidden_import` | ERROR | No | Core imports I/O library |
| `internal_import` | WARNING | - | Import inside function body |
| `impure_call` | ERROR | No | Call to datetime.now, random.*, etc. |

### Shell Rules (DX-22)

| Rule | Severity | Escape | Description |
|------|----------|--------|-------------|
| `shell_result` | **ERROR** | Yes | Shell function doesn't return Result |
| `entry_point_too_thick` | **ERROR** | Yes | Entry point exceeds `entry_max_lines` |
| `shell_pure_logic` | WARNING | Marker | Shell function has no I/O operations |
| `shell_too_complex` | INFO | Marker | Function exceeds `shell_max_branches` |
| `shell_complexity_debt` | ERROR | No | Project has ≥5 unaddressed complexity warnings |

### Documentation Rules

| Rule | Severity | Escape | Description |
|------|----------|--------|-------------|
| `missing_doctest` | WARNING | - | Core function without doctest examples |

## Escape Hatch Mechanism (DX-22)

### Unified Escape Syntax

For ERROR-level architecture rules (`shell_result`, `entry_point_too_thick`):

```python
# @invar:allow <rule>: <reason>
```

**Examples:**

```python
# @invar:allow shell_result: Legacy API returns raw dict for backward compat
def legacy_api_endpoint():
    return {"status": "ok"}  # Cannot return Result

# @invar:allow entry_point_too_thick: Main CLI orchestrates all verification phases
@app.command()
def guard(...):
    # 100+ lines of CLI orchestration
    ...
```

### Semantic Markers

For WARNING/INFO rules, use semantic markers that document intent:

| Marker | Rule | Purpose |
|--------|------|---------|
| `# @shell_complexity: <reason>` | `shell_too_complex` | Justify branches, prevent escalation |
| `# @shell_orchestration: <reason>` | `shell_pure_logic` | Mark as coordination function |
| `# @shell:entry` | Entry detection | Mark custom framework callback |

### Escape Principles

| Level | Escape Allowed? | Mechanism |
|-------|-----------------|-----------|
| ERROR (correctness) | **No** | Must fix - will crash or can't verify |
| ERROR (architecture) | **Yes** | `@invar:allow` with justification |
| WARNING | **No escape** | Use semantic markers or `severity_overrides` |
| INFO | **No escape needed** | Never blocks; use markers to prevent escalation |

## Fix-or-Explain Enforcement

### Escalation Mechanism

```
Individual: shell_too_complex → INFO (suggestion)
                    ↓
         ≥5 unaddressed (no @shell_complexity markers)
                    ↓
  Project: shell_complexity_debt → ERROR (blocks)
```

### Resolution Options

1. **Fix** - Reduce branches, extract to Core
2. **Explain** - Add `# @shell_complexity: <reason>` marker

## Severity Overrides

In `pyproject.toml`:

```toml
[tool.invar]
severity_overrides = { "redundant_type_contract" = "off" }
```

Options: `off`, `info`, `warning`, `error`

## Rule Exclusions

Exclude rules for specific file patterns:

```toml
[tool.invar]
rule_exclusions = [
    { pattern = "**/generated/**", rules = ["*"] },
    { pattern = "**/tests/**", rules = ["missing_contract"] },
]
```

## CLI Commands

```bash
invar rules              # List all rules
invar rules --json       # JSON format for agents
invar rules -c shell     # Filter by category
```
