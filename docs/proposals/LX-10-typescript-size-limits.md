# LX-10: Language-Aware Layered Size Limits

> **Status:** Draft
> **Created:** 2026-01-02
> **Updated:** 2026-01-02
> **Complexity:** Medium (config model + rules logic + templates)

---

## Problem

### Issue 1: Uniform Limits Ignore Code Layer Differences

Current limits are uniform across all code:
- `max_file_lines = 500`
- `max_function_lines = 50`

But **Core** and **Shell** have fundamentally different characteristics:

| Layer | Characteristics | Current Compliance |
|-------|----------------|-------------------|
| **Core** | Pure functions, small, focused | 92.3% under 50 lines |
| **Shell** | CLI entry points, I/O, error handling | **76.4%** under 50 lines |
| **Tests** | Setup, fixtures, many assertions | Variable |

Data from Invar codebase analysis:
- Core: avg 27 lines/function, 7.7% exceed 50 lines
- Shell: avg 38 lines/function, **23.6% exceed 50 lines**
- 5 files exceed 500 lines with no escape hatches

### Issue 2: TypeScript Requires More Lines

TypeScript code requires ~30% more lines than Python for equivalent functionality:

| Factor | Python | TypeScript | Overhead |
|--------|--------|------------|----------|
| Type annotations | Optional, inline | Required, multi-line | +20-30% |
| Interface definitions | dataclass ~3 lines | interface ~10 lines | +30% |
| Zod schemas (contracts) | @pre/@post 1 line | z.object({...}) multi-line | +50% |
| JSX (React) | N/A | Significant | +50%+ |

---

## Solution

Implement **language-aware layered size limits**:

1. **Layer detection**: Determine if file is in core/shell/tests based on path
2. **Per-layer limits**: Different limits for each layer
3. **Per-language multiplier**: TypeScript gets 1.3x Python limits

### Proposed Limits

#### Python

| Layer | File Lines | Function Lines | Rationale |
|-------|-----------|----------------|-----------|
| **Core** | 500 | 50 | Pure functions should be small |
| **Shell** | 700 | 100 | CLI/IO naturally larger |
| **Tests** | 1000 | 200 | Test setup can be verbose |
| **Default** | 600 | 80 | Fallback for unclassified |

#### TypeScript (Python × 1.3)

| Layer | File Lines | Function Lines | Rationale |
|-------|-----------|----------------|-----------|
| **Core** | 650 | 65 | Type overhead |
| **Shell** | 910 | 130 | API routes, React components |
| **Tests** | 1300 | 260 | Test boilerplate |
| **Default** | 780 | 104 | Fallback |

---

## Design

### Layer Detection

```python
class CodeLayer(Enum):
    CORE = "core"
    SHELL = "shell"
    TESTS = "tests"
    DEFAULT = "default"

def detect_layer(file_path: str) -> CodeLayer:
    """
    Detect code layer from file path patterns.

    >>> detect_layer("src/myapp/core/logic.py")
    <CodeLayer.CORE: 'core'>
    >>> detect_layer("src/myapp/shell/cli.py")
    <CodeLayer.SHELL: 'shell'>
    >>> detect_layer("tests/test_foo.py")
    <CodeLayer.TESTS: 'tests'>
    >>> detect_layer("src/myapp/utils.py")
    <CodeLayer.DEFAULT: 'default'>
    """
    path_lower = file_path.replace("\\", "/").lower()

    if "/core/" in path_lower:
        return CodeLayer.CORE
    if "/shell/" in path_lower:
        return CodeLayer.SHELL
    if "/tests/" in path_lower or "/test/" in path_lower or "test_" in path_lower:
        return CodeLayer.TESTS
    return CodeLayer.DEFAULT
```

### Configuration Model

```python
class LayerLimits(BaseModel):
    """Size limits for a specific code layer."""
    max_file_lines: int = Field(ge=1)
    max_function_lines: int = Field(ge=1)

class RuleConfig(BaseModel):
    # Existing fields...

    # New: per-layer limits
    layer_limits: dict[str, LayerLimits] = Field(
        default_factory=lambda: {
            "core": LayerLimits(max_file_lines=500, max_function_lines=50),
            "shell": LayerLimits(max_file_lines=700, max_function_lines=100),
            "tests": LayerLimits(max_file_lines=1000, max_function_lines=200),
            "default": LayerLimits(max_file_lines=600, max_function_lines=80),
        }
    )

    def get_limits(self, layer: CodeLayer) -> LayerLimits:
        """Get limits for a layer, falling back to default."""
        return self.layer_limits.get(layer.value, self.layer_limits["default"])
```

### Configuration Format

#### Python (pyproject.toml)

```toml
[tool.invar.guard]
# These become "default" layer limits
max_file_lines = 600
max_function_lines = 80

# Optional: override specific layers
[tool.invar.guard.layers.core]
max_file_lines = 500
max_function_lines = 50

[tool.invar.guard.layers.shell]
max_file_lines = 700
max_function_lines = 100

[tool.invar.guard.layers.tests]
max_file_lines = 1000
max_function_lines = 200
```

#### TypeScript (invar.config.json)

```json
{
  "guard": {
    "max_file_lines": 780,
    "max_function_lines": 104,
    "layers": {
      "core": { "max_file_lines": 650, "max_function_lines": 65 },
      "shell": { "max_file_lines": 910, "max_function_lines": 130 },
      "tests": { "max_file_lines": 1300, "max_function_lines": 260 }
    }
  }
}
```

### Rules Update

```python
def check_file_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    layer = detect_layer(file_info.path)
    limits = config.get_limits(layer)

    if file_info.lines > limits.max_file_lines:
        return [Violation(
            rule="file_size",
            severity=Severity.ERROR,
            message=f"File has {file_info.lines} lines (max: {limits.max_file_lines} for {layer.value})",
            # ...
        )]
    # Warning threshold check...
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (2h)

| Task | File | Changes |
|------|------|---------|
| Add `CodeLayer` enum | core/models.py | New enum |
| Add `LayerLimits` model | core/models.py | New model |
| Add `detect_layer()` | core/utils.py | New function |
| Update `RuleConfig` | core/models.py | Add layer_limits field |
| Update `parse_guard_config()` | core/utils.py | Parse layers config |

### Phase 2: Rules Integration (1.5h)

| Task | File | Changes |
|------|------|---------|
| Update `check_file_size()` | core/rules.py | Use layer limits |
| Update `check_function_size()` | core/rules.py | Use layer limits |
| Update violation messages | core/rules.py | Show layer in message |

### Phase 3: Templates (1h)

| Task | File | Changes |
|------|------|---------|
| Update Python template | templates/protocol/python/ | Default layer limits |
| Update TypeScript template | templates/protocol/typescript/ | 1.3x layer limits |
| Update invar.config.json schema | templates/ | Add layers section |

### Phase 4: Documentation & Tests (1.5h)

| Task | File | Changes |
|------|------|---------|
| Update INVAR.md | INVAR.md | Document layered limits |
| Update rules reference | docs/reference/rules/ | Document layer behavior |
| Add unit tests | tests/core/ | Test layer detection, limits |

**Total: ~6 hours (1 day)**

---

## Migration

### Backward Compatibility

- Existing `max_file_lines` / `max_function_lines` become "default" layer
- Projects without `layers` config continue to work
- No breaking changes

### Recommended Migration

1. Remove `file_size` escape hatches that were due to Shell files
2. Verify Shell functions no longer trigger warnings
3. Optionally tighten Core limits further

---

## Alternatives Considered

### A. Pattern-Based Overrides

```toml
[tool.invar.guard.overrides]
"**/shell/**" = { max_file_lines = 700 }
"**/tests/**" = { max_file_lines = 1000 }
```

- **Pro:** More flexible
- **Con:** More complex config, harder to understand defaults

### B. Uniform Increase

Just raise limits to 600/80 for all code.

- **Pro:** Simple
- **Con:** Doesn't encourage Core purity

### C. Per-Language Only (Original LX-10)

Python 500/50, TypeScript 650/65.

- **Pro:** Simpler
- **Con:** Doesn't solve Shell layer issue

**Decision:** Layer-based (Option A) provides right balance of simplicity and correctness.

---

## Success Criteria

- [ ] Invar codebase passes guard without escape hatches for file_size
- [ ] Shell functions (guard, init) no longer trigger function_size warnings
- [ ] Core layer maintains strict 500/50 limits
- [ ] TypeScript projects have appropriate 1.3x limits
- [ ] Configuration is backward compatible

---

## Summary Table

| Language | Layer | File Lines | Function Lines |
|----------|-------|-----------|----------------|
| Python | Core | 500 | 50 |
| Python | Shell | 700 | 100 |
| Python | Tests | 1000 | 200 |
| Python | Default | 600 | 80 |
| TypeScript | Core | 650 | 65 |
| TypeScript | Shell | 910 | 130 |
| TypeScript | Tests | 1300 | 260 |
| TypeScript | Default | 780 | 104 |
