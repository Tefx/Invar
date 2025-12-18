# Invar: Technical Design

> **Prerequisite:** Read [VISION.md](./VISION.md) for philosophy.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INVAR SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Protocol   │  │  Perception  │  │    Guard     │          │
│  │  (INVAR.md)  │  │  (Map, Sig)  │  │  (Enforce)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                   │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────┐           │
│  │              External Integrations               │           │
│  │  deal │ returns │ pydantic │ hypothesis │ pytest │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Protocol (INVAR.md)

### Purpose

The Protocol is a document that defines how agents should work. It provides significant value with zero dependencies.

### The Four Laws

```
┌────────────────────────────────────────────────────────────────┐
│ LAW 1: SEPARATION                                              │
│ Pure logic (Core) and I/O (Shell) must be physically separate  │
├────────────────────────────────────────────────────────────────┤
│ LAW 2: CONTRACT FIRST                                          │
│ Define boundaries before implementation                         │
├────────────────────────────────────────────────────────────────┤
│ LAW 3: CONTEXT ECONOMY                                         │
│ Read map → signatures → implementation (only if needed)        │
├────────────────────────────────────────────────────────────────┤
│ LAW 4: VERIFY IMMEDIATELY                                      │
│ Unit + integration + self-check (invar guard)                   │
└────────────────────────────────────────────────────────────────┘
```

### The ICIDV Workflow

```
  ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
  │  I  │ ▶ │  C  │ ▶ │  I  │ ▶ │  D  │ ▶ │  I  │ ▶ │  V  │
  │ntent│   │ontr.│   │nsp. │   │sign │   │mpl. │   │erify│
  └─────┘   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘
     │         │         │         │         │         │
     ▼         ▼         ▼         ▼         ▼         ▼
  Classify  Define    Check     Plan     Write     Unit+
  Core/Shell bounds   sizes    extract   code     Integ.
```

### Checkpoints

Each step has a checkpoint the agent must pass:

**After Intent:**
```
□ Read map or project structure
□ Identified affected symbols
□ Classified as Core or Shell
```

**After Contract:**
```
□ All parameters have type hints
□ @pre/@post decorators defined
□ Docstring has Examples (>>>)
□ Considered edge cases: empty, zero, negative, large
```

**After Implementation:**
```
□ Code is explicit (no **kwargs, no eval)
□ Function < 50 lines, File < 300 lines
□ Full type annotations
```

**After Verify:**
```
□ pytest passes (including doctests)
□ Property tests found no counterexamples
□ invar guard passes (if installed)
```

---

## Component 2: Perception

### Purpose

Provide agents with compressed, high-signal context for large codebases.

### 2.1 Map Generator

**Input:** Project root directory
**Output:** Symbol map with reference counts and contracts

**Algorithm:**

```
Phase 1: Discovery
├── Walk directory tree
├── Filter: *.py, exclude __pycache__, tests, .venv, etc.
└── Build file list

Phase 2: Extraction (per file)
├── Parse AST (skip files with syntax errors, log warning)
├── Extract symbols: functions, classes, methods
├── Extract metadata: signature, docstring, decorators
└── Detect contracts (@pre, @post from deal)

Phase 3: Reference Analysis (AST-based)
├── For each file, walk AST to find:
│   ├── Name nodes (variable references)
│   ├── Call nodes (function calls)
│   └── Attribute nodes (method calls)
├── Match references to known symbols
├── Exclude self-references (same file, definition line)
└── Build reference map: symbol → count

Phase 4: Ranking & Formatting
├── Sort symbols by reference count (descending)
├── Apply display rules:
│   ├── refs > 10: Full signature + docstring + contract
│   ├── refs 3-10: Signature + contract summary
│   └── refs < 3: Name only (collapsible)
└── Generate output (human or JSON)
```

**Note on Reference Counting:**
- Uses AST analysis, not string matching (avoids false positives from comments/strings)
- Cannot detect dynamic calls (`getattr`, `__import__`)
- Cross-module references require import resolution

**Output Format (Human):**

```
📁 src/core/pricing.py (156 lines, 8 functions)
  🔥 calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal  [refs: 47]
     │ "Calculate order total with tax."
     │ @pre: len(items) > 0, 0 <= tax_rate <= 1
     │ @post: result >= 0
     │
     ├─ _apply_discount(price, rate) -> Decimal  [refs: 12]
     └─ _round_currency(amount) -> Decimal  [refs: 8]

  ƒ validate_line_item(item: RawItem) -> Result[LineItem, Error]  [refs: 23]
     "Validate a single line item."
```

**Output Format (JSON for agents):**

```json
{
  "project": "/path/to/project",
  "generated": "2024-12-18T10:00:00Z",
  "files": [
    {
      "path": "src/core/pricing.py",
      "lines": 156,
      "symbols": [
        {
          "name": "calculate_total",
          "kind": "function",
          "line": 42,
          "signature": "(items: list[Item], tax_rate: Decimal) -> Decimal",
          "docstring": "Calculate order total with tax.",
          "contracts": {
            "pre": ["len(items) > 0", "0 <= tax_rate <= 1"],
            "post": ["result >= 0"]
          },
          "refs": 47
        }
      ]
    }
  ],
  "summary": {
    "total_files": 24,
    "total_lines": 3420,
    "total_symbols": 156,
    "hottest": ["calculate_total", "validate_order", "process_payment"]
  }
}
```

### 2.2 Signature Extractor

**Purpose:** Extract just signatures + contracts for a specific file/symbol.

**Use case:** Agent needs to understand a dependency without reading full implementation.

```bash
invar sig src/core/pricing.py
invar sig src/core/pricing.py::calculate_total
```

**Output:**

```python
# src/core/pricing.py - Signatures only

@pre(lambda items: len(items) > 0)
@pre(lambda tax_rate: 0 <= tax_rate <= 1)
@post(lambda result: result >= 0)
def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
    """Calculate order total with tax."""
    ...

def validate_line_item(item: RawItem) -> Result[LineItem, ValidationError]:
    """Validate a single line item."""
    ...
```

---

## Component 3: Guard

### Purpose

Enforce architecture rules. **Prompts can be ignored; Guard cannot.**

### 3.1 Rules Engine

**Rule Categories:**

| Category | Rules | Severity |
|----------|-------|----------|
| Architecture | Core cannot import I/O modules | ERROR |
| Architecture | Shell functions should return Result | WARNING |
| Contracts | Public Core functions need @pre or @post | WARNING |
| Contracts | Contracts need doctest examples | WARNING |
| Size | File > 300 lines | ERROR |
| Size | Function > 50 lines | WARNING |
| Style | No **kwargs in Core | WARNING |

### 3.2 Honest Limitations

**Guard CAN detect:**
- Static `import` and `from ... import` statements
- Decorator presence (`@pre`, `@post`)
- File and function line counts
- Missing type annotations

**Guard CANNOT detect:**
- Dynamic imports: `__import__('os')`
- Method calls on allowed imports: `Path('/tmp').write_text()`
- Semantic quality of contracts: `@pre(lambda x: True)` passes
- Runtime behavior

**Configuration (pyproject.toml):**

```toml
[tool.invar.guard]
# Directory classification
core_paths = ["src/core", "src/domain"]
shell_paths = ["src/shell", "src/api", "src/cli"]

# Size limits
max_file_lines = 300
max_function_lines = 50

# Required for Core
require_contracts = true
require_doctests = true

# I/O modules forbidden in Core (static import check only)
forbidden_imports = [
    "os", "sys", "socket", "requests", "urllib",
    "subprocess", "shutil", "io"
]

# Paths to exclude from checking
exclude_paths = ["tests", "scripts", "migrations"]
```

### 3.3 Violation Report

```
$ invar guard

Invar Guard Report
==================

❌ ERROR: src/core/pricing.py
   Line 15: Imports 'os' (forbidden in Core)

❌ ERROR: src/core/validation.py
   File has 342 lines (max: 300)

⚠️  WARNING: src/core/utils.py
   Line 45: Function 'parse_date' missing @pre or @post

⚠️  WARNING: src/core/models.py
   Line 78: Function 'validate' has no doctest examples

Summary: 2 errors, 2 warnings
Exit code: 1 (errors found)

Note: Guard performs static analysis only. Dynamic imports and
runtime behavior are not checked.
```

### 3.4 CI Integration

```yaml
# .github/workflows/invar.yml
name: Invar Guard

on: [push, pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install invar
      - run: invar guard --strict
        # --strict: treat warnings as errors
```

---

## Component 4: Testing Strategy

### Philosophy

Tests serve multiple purposes:
1. **Documentation** - Show how to use the code
2. **Verification** - Prove correctness
3. **Regression** - Catch future breakage
4. **Specification** - Define expected behavior

Different test types serve different purposes.

### 4.1 Doctest (Recommended for All)

**Purpose:** Documentation + simple verification
**Location:** In docstrings

```python
def calculate_discount(amount: Decimal, rate: Decimal) -> Decimal:
    """
    Apply discount rate to amount.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_discount(Decimal("100"), Decimal("0.1"))
        Decimal('90.00')
        >>> calculate_discount(Decimal("100"), Decimal("0"))
        Decimal('100.00')
        >>> calculate_discount(Decimal("0"), Decimal("0.5"))
        Decimal('0.00')
    """
```

**Conventions:**
- Include: normal case, zero case, boundary case
- Keep examples simple and focused
- Run with: `pytest --doctest-modules`

### 4.2 Property Tests

**Purpose:** Edge case discovery, specification
**Location:** Choose based on project preference

**Option A: Inline (Agent-friendly)**

```python
# In source file, after function definition
if __debug__:
    from hypothesis import given, strategies as st

    @given(
        amount=st.decimals(min_value=0, max_value=1e6, allow_nan=False),
        rate=st.decimals(min_value=0, max_value=1, allow_nan=False)
    )
    def test_discount_properties(amount, rate):
        result = calculate_discount(amount, rate)
        assert result >= 0
        assert result <= amount
```

**Pros:**
- Test and code in same file (no context switch)
- Modification triggers test update awareness
- Removed in production with `python -O`

**Cons:**
- Requires pytest configuration
- Files become longer
- Less common in Python ecosystem

**Required configuration for inline tests:**
```toml
[tool.pytest.ini_options]
python_files = ["*.py"]
python_functions = ["test_*"]
testpaths = ["src"]
```

**Option B: Separate Directory (Convention-friendly)**

```
tests/
├── core/
│   ├── test_pricing.py
│   └── test_validation.py
└── conftest.py
```

**Pros:**
- Follows pytest conventions
- Source files stay short
- Standard tooling works out of box

**Cons:**
- Context switch between files
- Risk of forgetting to update tests
- Agent needs to access multiple files

### 4.3 Recommended Strategy

```toml
[tool.invar]
# Choose test style: "inline" or "separate"
test_style = "inline"  # Default: agent-friendly
```

| Test Type | Location | Purpose |
|-----------|----------|---------|
| Doctest | Docstring | Documentation, simple cases |
| Property (inline) | Source file | Core function specification |
| Property (separate) | tests/ | Complex multi-module tests |
| Integration | tests/integration/ | Cross-module, I/O tests |

---

## Component 5: Core/Shell Gray Areas

### The Problem

Real-world code doesn't always fit cleanly into Core vs Shell.

### Practical Guidelines

**Logging:**
```python
# Core: Use structured return values, not logging
def validate(data: Input) -> Result[Output, list[ValidationError]]:
    errors = []
    if not data.name:
        errors.append(ValidationError("name", "required"))
    # Return errors instead of logging them

# Shell: Log at the boundary
result = validate(data)
if result.is_failure():
    logger.warning(f"Validation failed: {result.failure()}")
```

**Configuration:**
```python
# Core: Accept config as parameter
def calculate_tax(amount: Decimal, tax_rates: TaxConfig) -> Decimal:
    ...

# Shell: Load and inject config
config = load_config("tax_rates.toml")  # I/O here
result = calculate_tax(amount, config)  # Pure call
```

**Current Time:**
```python
# Core: Accept time as parameter
def is_expired(expiry: datetime, now: datetime) -> bool:
    return now > expiry

# Shell: Inject current time
expired = is_expired(token.expiry, datetime.now())
```

**Random Values:**
```python
# Core: Accept random value as parameter
def select_winner(participants: list[str], random_index: int) -> str:
    return participants[random_index % len(participants)]

# Shell: Generate and inject
import secrets
winner = select_winner(participants, secrets.randbelow(len(participants)))
```

### Decision Framework

```
┌─────────────────────────────────────────────────────────────┐
│              Is this operation deterministic?                │
│                                                             │
│  YES (same input → same output)  │  NO (external state)    │
│              ↓                   │           ↓              │
│           CORE                   │        SHELL             │
│                                  │                          │
│  Examples:                       │  Examples:               │
│  - Math operations               │  - File I/O              │
│  - Data transformation           │  - Network calls         │
│  - Validation logic              │  - Database queries      │
│  - Business rules                │  - Current time          │
│                                  │  - Random generation     │
└─────────────────────────────────────────────────────────────┘
```

---

## CLI Design

```bash
# Perception
invar map [path]              # Generate map (human format)
invar map [path] --json       # Generate map (JSON format)
invar map [path] --top 10     # Show top 10 most-referenced symbols
invar sig <file>              # Extract signatures
invar sig <file>::<symbol>    # Extract specific symbol

# Guard
invar guard [path]            # Run architecture checks
invar guard --strict          # Treat warnings as errors
invar guard --json            # Output as JSON for tooling

# Utilities
invar init                    # Initialize INVAR.md and config
invar version                 # Show version
```

---

## File Structure for Invar-enabled Projects

```
project/
├── pyproject.toml            # Invar + tool configuration
├── INVAR.md                  # Protocol document (for agents)
│
├── src/
│   ├── core/                 # CORE - Pure logic
│   │   ├── __init__.py
│   │   ├── models.py         # Pydantic models
│   │   ├── pricing.py        # Business logic + inline tests
│   │   └── validation.py     # Validation rules
│   │
│   └── shell/                # SHELL - I/O adapters
│       ├── __init__.py
│       ├── api.py            # HTTP handlers
│       ├── database.py       # DB operations
│       └── files.py          # File operations
│
└── tests/
    ├── integration/          # Cross-module tests
    └── e2e/                  # End-to-end tests
```

---

## Phase 2 Design: Adoption Improvements

### Configuration Sources

**Problem:** Requiring pyproject.toml excludes scripts, notebooks, and legacy projects.

**Solution:** Support multiple configuration sources with priority:

```
Priority (highest to lowest):
1. pyproject.toml [tool.invar.guard]    # Standard Python projects
2. invar.toml [guard]                   # Standalone config
3. .invar/config.toml [guard]           # Context directory
4. Built-in defaults                    # Fallback
```

**invar.toml Format:**

```toml
# invar.toml - standalone configuration

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests"]
exclude_paths = ["tests", ".venv"]

# Pattern-based classification (optional)
core_patterns = []
shell_patterns = []
```

**Config Loading Algorithm:**

```python
def load_config(project_root: Path) -> RuleConfig:
    # Try sources in priority order
    if (pyproject := project_root / "pyproject.toml").exists():
        config = parse_pyproject(pyproject)
        if config:
            return config

    if (invar_toml := project_root / "invar.toml").exists():
        return parse_invar_toml(invar_toml)

    if (invar_config := project_root / ".invar/config.toml").exists():
        return parse_invar_toml(invar_config)

    return RuleConfig()  # defaults
```

### Pattern-based Classification

**Problem:** Requiring src/core and src/shell directories forces project restructuring.

**Solution:** Support glob patterns for flexible classification.

**Configuration:**

```toml
[tool.invar.guard]
# Option 1: Path-based (default, for new projects)
core_paths = ["src/core"]
shell_paths = ["src/shell"]

# Option 2: Pattern-based (for existing projects)
core_patterns = [
    "**/domain/**",
    "**/models/**",
    "**/services/internal/**",
    "**/core/**"
]
shell_patterns = [
    "**/api/**",
    "**/views/**",
    "**/cli/**",
    "**/handlers/**",
    "**/services/external/**"
]

# Exclude from all checking
exclude_patterns = ["**/legacy/**", "**/generated/**"]
```

**Classification Priority:**

```
1. Explicit exclude_patterns    → Skip file entirely
2. core_patterns match          → Classify as Core
3. shell_patterns match         → Classify as Shell
4. core_paths contains file     → Classify as Core
5. shell_paths contains file    → Classify as Shell
6. Neither                      → Uncategorized (no Core/Shell rules applied)
```

**Pattern Matching Rules:**

- Uses glob syntax (fnmatch)
- `**` matches any directory depth
- Patterns are relative to project root
- First match wins (patterns checked before paths)

### Flexible invar init

**Updated Behavior:**

```bash
$ invar init

# Step 1: Detect config location
pyproject.toml exists?
├── Yes → Add [tool.invar.guard] to pyproject.toml
└── No  → Create invar.toml

# Step 2: Create protocol files
├── Create INVAR.md (always)
├── Create CLAUDE.md (always)
└── Create .invar/context.md (always)

# Step 3: Create directories (optional)
Create src/core and src/shell? [Y/n]
├── Yes → Create directories with __init__.py
└── No  → Skip (user will use patterns)
```

**CLI Options:**

```bash
invar init              # Interactive, asks about directories
invar init --dirs       # Always create src/core, src/shell
invar init --no-dirs    # Never create directories
invar init --config-only # Only add config, no INVAR.md/CLAUDE.md
```

---

## Implementation Phases

### Phase 1: Protocol + Guard (MVP) ✅ Complete

**Deliverables:**
- INVAR.md template
- `invar guard` command
- Basic pyproject.toml configuration
- `invar init` command

**Value:** Architecture enforcement, contract checking

### Phase 2: Adoption ✅ Complete

**Goal:** Lower barriers for existing projects to adopt Invar.

**Deliverables:**
- [x] Multiple configuration sources (pyproject.toml, invar.toml)
- [x] Pattern-based Core/Shell classification
- [x] Flexible `invar init` (works without pyproject.toml)

**Value:** Zero-refactor adoption for existing projects

### Phase 3: Guard Enhancement

**Goal:** Enhance verification for better self-dogfooding during Invar development.

**Rationale:** By improving guard now, we get immediate feedback while developing subsequent phases.

**Deliverables:**
- Function-internal import detection (not just top-level)
- Impure function call detection:
  - Time: `datetime.now()`, `datetime.utcnow()`, `time.time()`
  - Random: `random.random()`, `random.randint()`, `random.choice()`
  - I/O: `open()`, `print()`, `input()`
- Code line count excluding docstrings/comments
- `invar guard --strict-pure` mode (new checks as WARNING)

**Value:** Catch common pureness violations; better line count accuracy

**Technical approach:**
```python
# AST visitor to detect impure calls
IMPURE_CALLS = {
    ('datetime', 'now'), ('datetime', 'utcnow'),
    ('time', 'time'), ('random', 'random'),
    ('', 'open'), ('', 'print'), ('', 'input'),
}

def check_impure_calls(tree: ast.AST) -> list[Violation]:
    """Walk AST and flag calls to known impure functions."""
    ...

# Separate code lines from docstring/comment lines
def count_code_lines(source: str) -> tuple[int, int]:
    """Returns (code_lines, docstring_comment_lines)."""
    ...
```

### Phase 4: Perception

**Deliverables:**
- `invar map` command (with AST-based reference analysis)
- `invar sig` command
- JSON output for agent consumption

**Value:** Context compression for large projects

### Phase 5: Polish

**Deliverables:**
- Documentation (usage guide)
- CI templates
- PyPI release

### Phase 6: Advanced Verification (Long-term)

**Goal:** Enable explicit pureness declarations with validation.

**Deliverables:**
- Global variable modification detection
- Support `# invar: pure` comment annotation
- Validate declared pure functions don't call impure functions
- Show pureness status in `invar map` output

**Configuration:**
```toml
[tool.invar.guard]
# Require explicit purity annotations in Core
require_pure_annotations = false  # default: false, opt-in
```

**Value:** Explicit intent + automated verification

---

## Dependencies

**Runtime:**
```
typer >= 0.9          # CLI framework
rich >= 13.0          # Pretty output
tomli >= 2.0          # TOML parsing (Python < 3.11)
```

**Recommended (not required):**
```
deal >= 4.0           # Contracts
returns >= 0.20       # Result type
pydantic >= 2.0       # Validation
```

**Development:**
```
pytest >= 7.0
hypothesis >= 6.0
mypy >= 1.0
ruff >= 0.1
```

---

## Bootstrap Strategy

Invar itself follows Invar principles:

```
src/invar/
├── core/           # Pure logic (AST parsing, rule checking)
│   ├── parser.py   # Parse Python files, extract symbols
│   ├── rules.py    # Rule definitions and checking
│   └── models.py   # Pydantic models for symbols, violations
│
└── shell/          # I/O (file system, CLI)
    ├── cli.py      # Typer commands
    ├── fs.py       # File system operations
    └── config.py   # Configuration loading
```

Invar v1.0 is written with human oversight. Once stable, Invar helps maintain itself.

### Lessons Learned from Bootstrap

When Invar was used to check itself, several issues were discovered:

| Issue | Root Cause | Fix |
|-------|------------|-----|
| `returns` API misuse | No usage examples in docs | Added Common Pitfalls section |
| `deal` @pre signature mismatch | Examples only showed single-param functions | Added multi-param example |
| .venv scanned (1800 files) | Default excludes too narrow | Expanded default exclude list |
| Class methods flagged as functions | `ast.walk()` traversed all nodes | Changed to `tree.body` only |
| CLI functions too long | Typer declarations are verbose | Extracted helper functions |

**Key Insight:** Documentation examples should cover common edge cases, not just happy paths.

### Future Considerations

**Guard Improvements:**
1. **Separate code/docstring line counts**: Report `Function 'foo' has 55 lines (35 code, 20 docstring)`
2. **Per-zone limits**: Different `max_function_lines` for Core (50) vs Shell (80)
3. **`invar guard --explain`**: Show why each file was classified as Core/Shell
4. **Static contract validation**: Check @pre lambda signature matches function

**Init Improvements:**
5. **Smart framework detection**: Detect Django/Flask and suggest appropriate patterns
6. **Config validation**: Warn when core_patterns and shell_patterns overlap
7. **Path existence check**: Warn when configured paths don't exist

**IDE Integration:**
8. **Real-time feedback**: Show violations while coding
9. **Quick fixes**: Auto-extract helper functions when limit exceeded

---

## Distribution

### Package Structure

```
invar (PyPI package)
├── src/invar/
│   ├── core/             # Parser, rules, models
│   ├── shell/            # CLI, file system
│   └── templates/        # Files copied on init
│       ├── INVAR.md
│       ├── CLAUDE.md.template
│       └── context.md.template
└── (metadata)
```

### Distribution Channels

| Channel | Content | Target Users |
|---------|---------|--------------|
| **PyPI** | CLI tool + templates | Primary distribution |
| **GitHub** | Source + dev docs | Contributors |
| **GitHub Raw** | INVAR.md direct link | AI agents |

### `invar init` Behavior

```bash
$ invar init

✓ Added [tool.invar.guard] to pyproject.toml
✓ Created INVAR.md (Invar Protocol)
✓ Created CLAUDE.md (customize for your project)
✓ Created src/core/
✓ Created src/shell/
✓ Created .invar/context.md (context management)
```

### Version Strategy

Protocol and tool versions are separate:

```
INVAR.md v3.7        # Protocol version
invar 0.1.0          # Tool version (semver)
```

### File Roles

| File | In Package | Copied by Init | Purpose |
|------|------------|----------------|---------|
| INVAR.md | ✅ | ✅ | Protocol reference |
| CLAUDE.md.template | ✅ | ✅ (as CLAUDE.md) | Project guide |
| context.md.template | ✅ | ✅ (as .invar/context.md) | Context management |
| proposal.md.template | ✅ | ✅ (as .invar/proposals/TEMPLATE.md) | Protocol change proposals |
| AGENTS.md | ❌ | ❌ | Optional, in docs/ |
| DESIGN.md | ❌ | ❌ | Dev docs only |
| VISION.md | ❌ | ❌ | Dev docs only |
