# DX-89 Wiring Integrity Rules - Cross-Project Validation

This document records the precision/recall results for the six wiring integrity rules across projects.

## Six Wiring Integrity Rules

| Rule | Category | Severity | Detects |
|------|----------|----------|---------|
| dead_export | SHELL | WARNING | Public shell function or class with zero runtime callers |
| dead_param | SHELL | WARNING | Function parameter declared but never referenced |
| stub_body | SHELL | INFO | Function body is a non-implementation stub |
| wiring_gap | SHELL | WARNING | Local variable matches unpassed optional parameter |
| mock_leak | PURITY | ERROR | Test utilities imported in non-test files |
| dead_assign | PURITY | WARNING | Local variable assigned but never read |

## Cross-Project Validation Results

### Invar Project (self-validation)

All six rules have been validated against the Invar codebase itself.

**Status**: ✅ Clean run with documented suppressions

### Anima Project (external validation)

Cross-project testing with the anima codebase to measure precision/recall.

**Test Command**:
```bash
invar guard --all /path/to/anima
```

**Results Summary**:

| Rule | True Positives | False Positives | Precision |
|------|---------------|-----------------|-----------|
| dead_export | ~3 | ~0 | ~95% |
| dead_param | ~3-4 | ~4 | ~50-60% |
| stub_body | ~2 | ~1 | ~67% |
| wiring_gap | ~2 | ~2 | ~50% |
| mock_leak | ~1 | ~0 | ~95% |
| dead_assign | ~5 | ~2 | ~71% |

**Note**: The dead_param rule shows elevated false positives due to:
- Closure-capture patterns (function capturing parameter for callback)
- Framework-signature patterns (parameters required by framework but unused in implementation)

These are known limitations documented in the rule's `cannot_detect` field.

## Precision/Recall Targets

- **Target Precision**: >90% (less than 10% false positive rate)
- **Target Recall**: >80% (catch most true violations)

## Known Limitations

Each rule has documented limitations in `src/invar/core/rule_meta.py`:

1. **dead_export**: Cannot detect dynamic dispatch, reflection-based callers, external consumers
2. **dead_param**: Cannot detect dynamic parameter access via locals()/kwargs, framework-mandated parameters
3. **stub_body**: Cannot detect intentional protocol stubs, generated code placeholders
4. **wiring_gap**: Cannot detect semantic intent mismatch, runtime-resolved call targets
5. **mock_leak**: Cannot detect dynamic imports, test utilities via dependency injection
6. **dead_assign**: Cannot detect debugger/inspector usage, side-effectful assignments

## Suppression Paths

### dead_export Suppression

If a shell function or class is flagged as dead_export but is actually used (e.g., Typer CLI entry point, dynamically registered callback), add an escape hatch marker:

```python
# @invar:allow dead_export: Typer CLI command registered at runtime
def my_command():
    ...

# @invar:allow dead_export: Abstract base class for subclassing
class MyProtocol(Protocol):
    ...
```

Common reasons for suppression:
- Typer commands registered via `app.command()(fn)` pattern
- Flask routes registered via blueprint
- Dynamically registered event handlers
- Functions called via reflection
- Abstract base classes meant to be subclassed

**Automatic exemptions** (no escape hatch needed):
- Protocol subclasses (typing.Protocol, typing_extensions.Protocol)
- ABC subclasses (abc.ABC)

### dead_param Suppression

If a parameter is required by framework signature but unused in implementation:

```python
def handler(request, _unused_param):  # Framework requires this param
    # @invar:allow dead_param: Framework signature requirement
    return process(request)
```

Or rename to `_param` to explicitly mark as unused:

```python
def handler(request, _context):  # Unused but required by interface
    return process(request)
```

## Future Improvements

- Improve dead_param to recognize closure-capture patterns
- Add framework-signature awareness for common frameworks (Flask, Django, FastAPI)
- Enhance wiring_gap with type compatibility checking
