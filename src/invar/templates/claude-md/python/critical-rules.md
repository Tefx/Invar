<!--invar:critical-->
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
{% if syntax == "mcp" -%}
| **Verify** | `invar_guard` — NOT pytest, NOT crosshair |
{% else -%}
| **Verify** | `invar guard` — NOT pytest, NOT crosshair |
{% endif -%}
| **Core** | `@pre/@post` + doctests, NO I/O imports |
| **Shell** | Returns `Result[T, E]` from `returns` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

### Contract Rules (CRITICAL)

```python
# ❌ WRONG: Lambda must include ALL parameters
@pre(lambda x: x >= 0)
def calc(x: int, y: int = 0): ...

# ✅ CORRECT: Include defaults too
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# ❌ WRONG: @post cannot access parameters
@post(lambda result: result > x)  # 'x' not available!

# ✅ CORRECT: @post only sees 'result'
@post(lambda result: result >= 0)
```

<!--/invar:critical-->
