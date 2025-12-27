# DX-60: Structured Rules SSOT

**Status:** Draft
**Created:** 2025-12-28
**Depends on:** DX-57 (Claude Code Hooks)
**Optimizes:** DX-57 Layer 3 token usage (~1,800t → ~600t)

## Problem Statement

### Current State (DX-57)

DX-57 implements full INVAR.md injection for protocol refresh in long conversations:

```
Message 25+: Inject full INVAR.md → ~1,800 tokens
50-message session: ~5,700 tokens total
```

**Trade-off accepted:** True SSOT with zero maintenance, but high token cost.

### Optimization Opportunity

Full INVAR.md (~1,800t) includes content not critical for refresh:
- License header (~80t)
- Configuration examples (~150t)
- Extended troubleshooting (~100t)
- Command list (agents already know)

A **generated subset (~600t)** can achieve:
- 95% rule coverage
- True SSOT (generated from same source)
- 67% token reduction

## Interim Optimization (Implemented)

Before full DX-60, INVAR.md now includes inline limits for agent usability:

```markdown
### Size Limits (Agent Quick Reference)

| Rule | Limit | Fix |
|------|-------|-----|
| `function_too_long` | **50 lines** | Extract helper |
| `file_too_long` | **500 lines** | Split by responsibility |
| `entry_point_too_thick` | **15 lines** | Delegate to Shell |
```

**Rationale:** Agents operate in bounded context. Cross-referencing Configuration section for limits increases token cost and error rate. Inline limits = self-contained, actionable rules.

**Trade-off:** Minor duplication (limits in Configuration + Troubleshooting). DX-60 eliminates this via generation.

## Goal

Maintain SSOT while reducing token cost:

| Metric | DX-57 | DX-60 |
|--------|-------|-------|
| Tokens per injection | ~1,800 | ~600 |
| 50-msg session cost | ~5,700 | ~2,000 |
| SSOT | ✅ | ✅ |
| Maintenance | Zero | Zero |

## Design

### 规则结构化

```yaml
# src/invar/templates/rules/tools.yaml
version: "5.0"
tool_substitution:
  - id: verify
    task: "Verify code"
    wrong: ["pytest", "crosshair"]
    correct: "invar_guard"
    priority: critical
  - id: structure
    task: "Read structure"
    wrong: ["Read(.py)"]
    correct: "invar_sig"
    priority: high
  - id: entrypoints
    task: "Find functions"
    wrong: ["Grep 'def'"]
    correct: "invar_map"
    priority: medium
```

```yaml
# src/invar/templates/rules/architecture.yaml
version: "5.0"
zones:
  core:
    location: "**/core/**"
    requirements:
      - "@pre/@post contracts"
      - "doctests"
      - "pure (no I/O)"
    forbidden_imports:
      - {module: "os", reason: "filesystem access"}
      - {module: "sys", reason: "system access"}
      - {module: "subprocess", reason: "process execution"}
      - {module: "pathlib", reason: "filesystem access"}
      - {module: "open", reason: "file I/O", type: "builtin"}
      - {module: "requests", reason: "network I/O"}
      - {module: "datetime.now", reason: "impure time", type: "attribute"}
  shell:
    location: "**/shell/**"
    requirements:
      - "Result[T, E] return type"
```

```yaml
# src/invar/templates/rules/contracts.yaml
version: "5.0"
rules:
  - id: lambda_signature
    priority: critical
    description: "Lambda must include ALL parameters"
    examples:
      wrong: |
        @pre(lambda x: x >= 0)
        def calc(x: int, y: int = 0): ...
      correct: |
        @pre(lambda x, y=0: x >= 0)
        def calc(x: int, y: int = 0): ...
    guard_rule: param_mismatch

  - id: post_scope
    priority: high
    description: "@post can only access 'result'"
    examples:
      wrong: |
        @post(lambda result: result > x)  # 'x' unavailable!
      correct: |
        @post(lambda result: result >= 0)
```

```yaml
# src/invar/templates/rules/workflow.yaml
version: "5.0"
usbv:
  - phase: UNDERSTAND
    purpose: "Know what and why"
    activities: ["Intent", "Inspect (sig/map)", "Constraints"]
  - phase: SPECIFY
    purpose: "Define boundaries"
    activities: ["@pre/@post BEFORE code", "Design decomposition", "Doctests"]
  - phase: BUILD
    purpose: "Write code"
    activities: ["Implement leaves", "Compose", "Frequent guard"]
  - phase: VALIDATE
    purpose: "Confirm correctness"
    activities: ["invar guard", "Review gate", "Reflect"]
```

```yaml
# src/invar/templates/rules/limits.yaml
version: "5.0"
size_limits:
  - id: function_too_long
    limit: 50
    unit: lines
    message: "Function exceeds {limit} lines"
    fix: "Extract helper: `_impl()` + main with docstring"
    configurable: max_function_lines
    note: "Doctest lines excluded from count"

  - id: file_too_long
    limit: 500
    unit: lines
    message: "File exceeds {limit} lines"
    fix: "Split by responsibility"
    configurable: max_file_lines
    note: "Doctest lines excluded from count"

  - id: entry_point_too_thick
    limit: 15
    unit: lines
    message: "Entry point exceeds {limit} lines"
    fix: "Delegate to Shell functions"
    configurable: entry_max_lines

complexity_limits:
  - id: shell_too_complex
    limit: 3
    unit: branches
    message: "Shell function has {count} branches (max: {limit})"
    fix: "Extract logic to Core, or add: # @shell_complexity: <reason>"
```

### 生成目标

```
rules/*.yaml
     │
     ├─→ INVAR.md           (~300 lines, 完整文档)
     ├─→ injection-full.md  (~600 tokens, 长对话注入)
     ├─→ injection-simple.md (~80 tokens, 检查点注入)
     ├─→ guard rules        (规则检测逻辑)
     └─→ skill hints        (技能文件中的规则引用)
```

### 模板示例

```jinja
{# INVAR.md.jinja - 完整文档 #}
{% set tools = load_rules('tools') %}
{% set arch = load_rules('architecture') %}
{% set contracts = load_rules('contracts') %}
{% set limits = load_rules('limits') %}

# The Invar Protocol v{{ tools.version }}

## Tool Selection

| Task | ❌ NEVER | ✅ ALWAYS |
|------|----------|----------|
{% for rule in tools.tool_substitution %}
| {{ rule.task }} | {{ rule.wrong | join(', ') }} | {{ rule.correct }} |
{% endfor %}

## Architecture

**Forbidden in Core:** {{ arch.zones.core.forbidden_imports | map(attribute='module') | join(', ') }}

## Size Limits (Agent Quick Reference)

| Rule | Limit | Fix |
|------|-------|-----|
{% for rule in limits.size_limits %}
| `{{ rule.id }}` | **{{ rule.limit }} {{ rule.unit }}** | {{ rule.fix }} |
{% endfor %}

*Doctest lines excluded from counts. Limits configurable in `pyproject.toml`.*

## Contract Rules

{% for rule in contracts.rules %}
### {{ rule.description }}

```python
# ❌ WRONG
{{ rule.examples.wrong }}
# ✅ CORRECT
{{ rule.examples.correct }}
```
{% endfor %}
```

```jinja
{# injection-full.md.jinja - 精简注入 #}
{% set tools = load_rules('tools') %}
{% set arch = load_rules('architecture') %}
{% set contracts = load_rules('contracts') | selectattr('priority', 'eq', 'critical') %}
{% set limits = load_rules('limits') %}

### Tools
{% for rule in tools.tool_substitution | selectattr('priority', 'in', ['critical', 'high']) %}
{{ rule.task }}: {{ rule.correct }} (NOT {{ rule.wrong[0] }})
{% endfor %}

### Size Limits
{% for rule in limits.size_limits %}
{{ rule.id }}: {{ rule.limit }} {{ rule.unit }}
{% endfor %}

### Core Forbidden
{{ arch.zones.core.forbidden_imports | map(attribute='module') | join(', ') }}

### Contracts
{% for rule in contracts %}
{{ rule.examples.correct | first_line }}
{% endfor %}
```

### 生成工具

```python
# src/invar/shell/commands/generate.py

@app.command()
def generate(
    target: str = typer.Argument(..., help="Target: all|invar|injection|guard"),
    check: bool = typer.Option(False, help="Check consistency without writing"),
) -> None:
    """Generate derived files from rules/*.yaml."""

    rules = RulesLoader.load_all()

    if target in ("all", "invar"):
        content = render_template("INVAR.md.jinja", rules=rules)
        if check:
            verify_matches(INVAR_PATH, content)
        else:
            INVAR_PATH.write_text(content)

    if target in ("all", "injection"):
        for variant in ("simple", "full"):
            content = render_template(f"injection-{variant}.md.jinja", rules=rules)
            OUTPUT_PATH.joinpath(f"injection-{variant}.md").write_text(content)
```

### CI 验证

```yaml
# .github/workflows/rules-consistency.yml
name: Rules Consistency Check

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check SSOT consistency
        run: |
          invar generate --check all
```

## Migration Path

### Phase 1: Extract Rules (DX-60a)
1. 从现有 INVAR.md 提取规则到 YAML
2. 创建 INVAR.md.jinja 模板
3. 验证生成内容与原始一致

### Phase 2: Injection Integration (DX-60b)
1. 创建 injection-*.md.jinja 模板
2. 修改 DX-57 hooks 使用生成内容
3. 添加版本校验

### Phase 3: Guard Integration (DX-60c)
1. Guard 规则检测逻辑引用 YAML
2. 规则 ID 统一 (YAML ↔ Guard ↔ 文档)
3. `invar rules` 输出从 YAML 生成

## File Changes

```
src/invar/templates/
├── rules/                      # NEW: 规则定义
│   ├── tools.yaml              # Tool substitution rules
│   ├── architecture.yaml       # Core/Shell zones
│   ├── contracts.yaml          # @pre/@post rules
│   ├── workflow.yaml           # USBV phases
│   ├── limits.yaml             # Size/complexity limits (NEW)
│   └── errors.yaml             # Common errors and fixes
│
├── protocol/
│   └── INVAR.md.jinja          # MODIFIED: 改为模板
│
└── hooks/
    ├── injection-simple.md.jinja   # NEW
    └── injection-full.md.jinja     # NEW

src/invar/core/
└── rules_loader.py             # NEW: YAML 加载和验证

src/invar/shell/commands/
└── generate.py                 # NEW: 生成命令
```

## Effort Estimate

| Phase | Scope | Complexity |
|-------|-------|------------|
| DX-60a | 规则提取 + INVAR.md 模板化 | Medium |
| DX-60b | 注入内容生成 | Low |
| DX-60c | Guard 集成 | Medium |

## Open Questions

1. **规则版本控制**: 如何处理协议版本升级时的规则变更?
2. **国际化**: 是否需要支持多语言规则描述?
3. **用户自定义**: 是否允许用户扩展规则?

## Evolution Path

```
DX-57 (Current)                    DX-60 (Future)
─────────────────                  ─────────────────
INVAR.md                           rules/*.yaml
    │                                   │
    ↓                              ┌────┴────┐
Hook embeds                        ↓         ↓
full content                   INVAR.md   injection.md
    │                          (generated)  (generated)
    ↓                               │         │
~1,800t/injection                   └────┬────┘
                                         ↓
                                   ~600t/injection
```

### Backward Compatibility

DX-60 changes only internal generation; external interface unchanged:
- `invar init --claude` still generates hooks
- Hook behavior identical (just smaller injection)
- INVAR.md still installed to projects

### When to Implement

Evaluate after DX-57 deployment:
- If token cost is acceptable → defer DX-60
- If token cost is problematic → prioritize DX-60a/b
- If Guard rule consistency issues emerge → include DX-60c

## Decision

待 DX-57 完成后评估实施优先级。

## References

- DX-57: Claude Code Hooks Integration (parent proposal)
- DX-16: Agent Tool Enforcement (enforcement analysis)
