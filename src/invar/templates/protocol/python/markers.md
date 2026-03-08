## Markers (Python)

### Entry Points

Entry points are framework callbacks (`@app.route`, `@app.command`) at Shell boundary.
- **Exempt** from `Result[T, E]` — must match framework signature
- **Keep thin** — delegate to Shell functions that return Result
  - Traditional callbacks: max **15** lines (`entry_max_lines`)
  - MCP tool handlers: max **35** lines (`entry_point_thresholds["mcp_tool"]`)

Auto-detected by decorators. For custom callbacks:

```python
# @shell:entry
def on_custom_event(data: dict) -> dict:
    result = handle_event(data)
    return result.unwrap_or({"error": "failed"})
```

### Shell Complexity

When shell function complexity is justified:

```python
# @shell_complexity: Subprocess with error classification
def run_external_tool(...): ...

# @shell_orchestration: Multi-step pipeline coordination
def process_batch(...): ...
```

### Architecture Escape Hatch

When rule violation has valid architectural justification:

```python
# @invar:allow shell_result: Framework callback signature fixed
def flask_handler(): ...
```

**Valid rule names for @invar:allow:**
- `shell_result` — Shell function without Result return type
- `entry_point_too_thick` — Entry point exceeds kind-specific limit (15 traditional / 35 MCP tool handlers)
- `forbidden_import` — I/O import in Core (rare, justify carefully)

Run `invar rules` for complete rule catalog with hints.
