## Troubleshooting (Python)

### Size Limits (Agent Quick Reference)

| Rule | Limit | Fix |
|------|-------|-----|
| `function_too_long` | **50 lines** | Extract helper: `_impl()` + main with docstring |
| `file_too_long` | **500 lines** | Split by responsibility |
| `entry_point_too_thick` | **15 lines** | Delegate to Shell functions |

*Doctest lines excluded from counts. Limits configurable in `pyproject.toml`.*

### Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `param_mismatch` error | Lambda missing params | Include ALL params (even defaults) |
| `shell_result` error | Shell func no Result | Add Result[T,E] or @invar:allow |
| `is_failure()` not found | Wrong Result check | Use `isinstance(result, Failure)` |

### Result Type Usage

```python
from returns.result import Result, Success, Failure

# Creating results
return Success(value)
return Failure(error)

# Checking results
if isinstance(result, Failure):
    handle_error(result.failure())
else:
    use_value(result.unwrap())

# Chaining
result.map(transform).bind(next_operation)
```
