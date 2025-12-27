# Rules

Show all Invar rule definitions with detection capabilities and hints.

---

## Behavior

Execute `invar rules` and display:
- All rule names (for use with `@invar:allow`)
- What each rule detects
- What each rule cannot detect
- Hints for fixing violations

---

## When to Use

- Before using `@invar:allow` escape hatch
- To understand why Guard flagged a violation
- To learn available rules and their severity
- To decide if an escape is appropriate

---

## Execution

```bash
invar rules
```

Output is JSON with 21 rules covering:
- **size**: file_size, function_size
- **contracts**: missing_contract, empty_contract, param_mismatch, postcondition_scope_error
- **purity**: forbidden_import, impure_call
- **shell**: shell_result, entry_point_too_thick, shell_pure_logic, shell_too_complex
- **docs**: missing_doctest, review_suggested

---

## Common Escape Hatches

| Rule | Example | Justification |
|------|---------|---------------|
| `shell_result` | Framework callback | Signature fixed by framework |
| `entry_point_too_thick` | Complex setup | Cannot delegate further |
| `forbidden_import` | Core test fixtures | Test-only imports |

Usage:
```python
# @invar:allow shell_result: Flask endpoint signature fixed
def api_handler(): ...
```

---

## Report Format

Present rules in a readable table:

```
## Invar Rules Catalog

| Rule | Severity | Detects |
|------|----------|---------|
| file_size | error | File exceeds max_file_lines limit |
| missing_contract | error | Core function without @pre/@post |
| ... | ... | ... |
```

---

Now run `invar rules` and present the catalog.
