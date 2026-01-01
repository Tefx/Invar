# LX-10: TypeScript Size Limit Adjustments

> **Status:** Draft
> **Created:** 2026-01-02
> **Complexity:** Low (config change + minor code)

---

## Problem

Current guard size limits are uniform across languages:
- `max_file_lines = 500`
- `max_function_lines = 50`

TypeScript code requires more lines than Python for equivalent functionality due to:

| Factor | Python | TypeScript | Overhead |
|--------|--------|------------|----------|
| Type annotations | Optional, inline | Required, often multi-line | +20-30% |
| Interface definitions | dataclass ~3 lines | interface ~10 lines | +30% |
| Zod schemas (contracts) | @pre/@post 1 line | z.object({...}) multi-line | +50% |
| JSX (React) | N/A | Significant | +50%+ |
| Destructuring/generics | Concise | Verbose | +10-20% |

### Example: Same Logic, Different Line Count

**Python (5 lines):**
```python
@pre(lambda data: len(data) > 0)
@post(lambda result: result is not None)
def process(data: dict) -> Result[User, str]:
    return Success(User(**data))
```

**TypeScript (15 lines):**
```typescript
const ProcessInput = z.object({
  id: z.string().min(1),
  name: z.string(),
});

const ProcessOutput = z.object({
  user: UserSchema,
});

function process(
  data: z.infer<typeof ProcessInput>
): Result<z.infer<typeof ProcessOutput>, string> {
  return ok({ user: data });
}
```

---

## Solution

Add language-specific size limit overrides.

### Proposed Defaults

| Limit | Python | TypeScript | Ratio |
|-------|--------|------------|-------|
| `max_file_lines` | 500 | 650 | 1.3x |
| `max_function_lines` | 50 | 65 | 1.3x |

The 1.3x multiplier accounts for type annotation overhead without encouraging bloated code.

---

## Configuration

### pyproject.toml (Python projects)

```toml
[tool.invar.guard]
max_file_lines = 500
max_function_lines = 50
```

### invar.config.json (TypeScript projects)

```json
{
  "guard": {
    "max_file_lines": 650,
    "max_function_lines": 65
  }
}
```

### Implementation

Option A: **Template-level defaults** (Recommended)
- Set different defaults in Python vs TypeScript templates
- No code changes to guard logic
- Each language's `invar.config.json` or `pyproject.toml` has appropriate defaults

Option B: **Guard-level language detection**
- Guard detects language and applies multiplier
- More complex, less transparent

**Recommendation: Option A** - simpler, more explicit, user can see/modify values.

---

## Implementation

### Phase 1: Update Templates

1. **TypeScript template** (`src/invar/templates/protocol/typescript/`):
   ```json
   // invar.config.json
   {
     "guard": {
       "max_file_lines": 650,
       "max_function_lines": 65
     }
   }
   ```

2. **Python template** (`src/invar/templates/protocol/python/`):
   - Keep current defaults (500/50)

### Phase 2: Documentation

Update INVAR.md and docs to mention language-specific recommendations.

---

## Alternatives Considered

### A. No Change
- **Pro:** Consistency across languages
- **Con:** TypeScript files constantly hit limits, encouraging escape hatches

### B. Higher Universal Limits (600/60)
- **Pro:** Simple
- **Con:** Python code quality may degrade

### C. Per-Zone Limits (Core vs Shell)
- Already mentioned in docs: Shell 80 vs Core 50
- Orthogonal to this proposal

---

## Risks

| Risk | Mitigation |
|------|------------|
| TypeScript code becomes bloated | 1.3x is conservative; monitor and adjust |
| Inconsistency confuses users | Document clearly in templates |

---

## Success Criteria

- [ ] TypeScript projects don't hit size limits for typical code
- [ ] Escape hatch usage for `file_size` decreases in TypeScript projects
- [ ] Python limits unchanged

---

## Timeline

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Update TypeScript template defaults | 0.5 day |
| 2 | Update documentation | 0.5 day |
| **Total** | | **1 day** |
