# Invar: Technical Design

> **Prerequisite:** Read [vision.md](./vision.md) for philosophy.
>
> **Design Principle:** Agent-Native Execution, Human-Directed Purpose. See [vision.md](./vision.md).
>
> **Mechanism Guides:** See [reference/](./reference/) for detailed technical documentation.

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

### The Six Laws

```
┌────────────────────────────────────────────────────────────────┐
│ LAW 1: SEPARATION                                              │
│ Pure logic (Core) and I/O (Shell) must be physically separate  │
├────────────────────────────────────────────────────────────────┤
│ LAW 2: CONTRACT COMPLETE                                       │
│ Define COMPLETE, RECOVERABLE boundaries before implementation  │
│ Complete = uniquely determines implementation (Clover)         │
│ Recoverable = guides fixes when violations occur (Pel)         │
├────────────────────────────────────────────────────────────────┤
│ LAW 3: CONTEXT ECONOMY                                         │
│ Read map → signatures → implementation (only if needed)        │
├────────────────────────────────────────────────────────────────┤
│ LAW 4: DECOMPOSE FIRST                                         │
│ Break complex tasks into sub-functions before implementing     │
│ Implement leaves first, then compose (Parsel: +75%)            │
├────────────────────────────────────────────────────────────────┤
│ LAW 5: VERIFY REFLECTIVELY                                     │
│ If fail: Reflect (why?) → Fix → Verify again                   │
│ Don't just fix—understand first (Reflexion: +11%)              │
├────────────────────────────────────────────────────────────────┤
│ LAW 6: INTEGRATE FULLY                                         │
│ Verify all feature paths connect correctly                     │
│ Local correctness ≠ global correctness (DX-07 post-mortem)     │
└────────────────────────────────────────────────────────────────┘
```

### The USBV Workflow (DX-32)

```
  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │UNDERSTAND│ ▶ │ SPECIFY  │ ▶ │  BUILD   │ ▶ │ VALIDATE │
  └──────────┘   └──────────┘   └──────────┘   └──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
    Intent         Contract       Implement      Verify
    Inspect        Design         Compose        Integrate
    Constraints    Test Cases                    Reflect
```

**Key insight:** Inspect before Contract — understand existing code before writing interfaces.

### Visible Checkpoints (3)

For complex tasks, show 3 checkpoints in TodoList:

**[UNDERSTAND]** — User verifies intent and context
```
□ Task intent clearly stated
□ Codebase context examined (invar sig, invar map)
□ Edge cases and constraints identified
□ Classified as Core or Shell
```

**[SPECIFY]** — User approves contracts before implementation
```
□ @pre AND @post decorators defined (complete contract)
□ Docstring has Examples (>>> normal, boundary, edge)
□ Self-test: Can this contract regenerate the function?
□ Complex task decomposed into sub-functions
□ Three-way consistency: Code ↔ Contract ↔ Doctests
```

**[VALIDATE]** — User confirms correctness
```
□ invar guard passes
□ If violations: reflected on WHY before fixing
□ Integration tested (if applicable)
```

**BUILD is internal work** — not shown in TodoList (no user decision needed).

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
| Size | File > 500 lines | ERROR |
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
max_file_lines = 500
max_function_lines = 50

# Required for Core
require_contracts = true
require_doctests = true

# I/O modules forbidden in Core (static import check only)
forbidden_imports = [
    "os", "sys", "socket", "requests", "urllib",
    "subprocess", "shutil", "io", "pathlib"
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
      - run: pip install invar-tools
      - run: invar guard --strict
        # --strict: treat warnings as errors
```

> **Tip:** Use `uvx invar-tools guard` locally to run without installing.

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

## MCP Server (DX-16)

Invar provides an MCP (Model Context Protocol) server for AI agent integration.

### Tools

| Tool | Purpose | Replaces |
|------|---------|----------|
| `invar_guard` | Smart Guard verification (static + doctests) | `pytest`, `crosshair` |
| `invar_sig` | Show function signatures with @pre/@post | Reading entire files |
| `invar_map` | Symbol map with reference counts | `grep` for definitions |

### Configuration

`invar init` creates `.mcp.json` at project root with auto-detected execution method:

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

**MCP method priority:**
1. `uvx` (recommended - isolated environment, always latest)
2. `command` (if `invar` is in PATH)
3. `python` (fallback to current interpreter)

### Agent Instructions

The MCP server provides `instructions` to enforce tool usage:
- Check-In requirement (display guard status + top entry points in first message)
- Tool substitution rules (use MCP tools instead of Bash commands)
- Task completion definition

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
3. Built-in defaults                    # Fallback
```

**invar.toml Format:**

```toml
# invar.toml - standalone configuration

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 500
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
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

    if (deprecated := project_root / ".invar/config.toml").exists():
        warn_deprecated(deprecated)

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
invar init              # Interactive mode with menus
invar init --claude     # Auto-select Claude Code, skip prompts
invar init --preview    # Show what would be done (dry run)
invar uninstall         # Remove Invar from project (preserves user content)
invar uninstall --dry-run  # Preview what would be removed
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

### Phase 3: Guard Enhancement ✅ Complete

**Goal:** Enhance verification for better self-dogfooding during Invar development.

**Deliverables:**
- [x] Function-internal import detection (not just top-level)
- [x] Impure function call detection (datetime.now, random.*, open, print)
- [x] Code line count excluding docstrings/comments
- [x] `invar guard --strict-pure` mode
- [x] New `core/purity.py` module

**Value:** Catch common pureness violations; better line count accuracy

### Phase 4: Perception ✅ Complete

**Deliverables:**
- [x] `invar map` command (with AST-based reference analysis)
- [x] `invar sig` command
- [x] JSON output for agent consumption
- [x] core/references.py, core/formatter.py, shell/commands/perception.py

**Value:** Context compression for large projects

### Phase 5: Guard Refinement ✅ Complete

**Deliverables:**
- [x] Shell Result validation (warn when Shell functions don't return Result)
- [x] Unified rule signatures
- [x] RuleConfig as Pydantic model

**Value:** Self-consistency, cleaner codebase

### Phase 6: Verification Completeness ✅ Complete

**Goal:** Fix critical gaps in what Guard can verify.

**Deliverables:**
- [x] Class method extraction in parser.py
- [x] Contract/size/doctest rules applied to methods
- [x] Purity checks (internal imports, impure calls) for methods
- [x] `exclude_doctest_lines` config option

### Phase 7: Agent-Native Foundation ✅ Complete

**Goal:** Detect Agent-specific failure modes.

**Deliverables:**
- [x] Empty contract detection (`@pre(lambda: True)`)
- [x] Redundant type detection (isinstance-only when typed)
- [x] Concrete fix suggestions with lambda skeletons

**New files:** `core/contracts.py`, `core/suggestions.py`

### Phase 8: Agent Efficiency ✅ Complete

**Goal:** Optimize for Agent iteration speed.

**Deliverables:**
- [x] `--changed` mode (git-modified files only)
- [x] `--agent` mode (JSON output with fix instructions)
- [x] @pre param mismatch detection

**New files:** `shell/git.py`

### Phase 9: Release ✅ Complete

**Goal:** Enable adoption by other projects.

**Deliverables:**
- [x] PyPI release (`pip install invar-tools` / `pip install invar-runtime`)
- [x] Documentation (README, VISION, consolidated docs)
- [x] CI templates (GitHub Actions)

### Phase 10: Agent-Native Advanced (Long-term)

**Goal:** Full Agent-native architecture.

**Rule Engine:**
- Rules YAML化 - Machine-readable with priorities
- Rule conflict resolution
- USBV phase precheck command

**Config & Profiles:**
- Config profiles ("strict", "standard", "relaxed" presets)
- Configurable impure list (user-defined)

**Guard Enhancements:**
- `invar guard --explain` (show classification reasons)
- Per-zone size limits (Core: 50, Shell: 80)
- Transitive impurity detection

### Phase 11: Language-Agnostic Protocol (LX-05) ✅ Complete

**Goal:** Support multiple programming languages.

**Deliverables:**
- [x] Language-agnostic INVAR.md templates
- [x] TypeScript contract examples (Zod schemas)
- [x] Language detection in templates
- [x] Template variables for language-specific content

### Phase 12: TypeScript Tooling (LX-06) ✅ Complete

**Goal:** Verification for TypeScript projects.

**Deliverables:**
- [x] TypeScript guard support (`guard_ts.py`)
- [x] Zod schema verification
- [x] JSDoc doctest extraction and execution
- [x] Hypothesis/property testing for TypeScript

### Phase 13: Extension Skills (LX-07) ✅ Complete

**Goal:** Optional specialized skills for quality assurance.

**Deliverables:**
- [x] `invar skill` CLI command
- [x] Skill registry and templates
- [x] `/security` and `/acceptance` extension skills
- [x] Skill isolation options (--quick, --standard, --deep)

---

## Dependencies

**invar-runtime (lightweight):**
```
deal >= 4.0           # Contracts engine
returns >= 0.20       # Result type
```

**invar-tools (includes invar-runtime):**
```
typer >= 0.9          # CLI framework
rich >= 13.0          # Pretty output
pydantic >= 2.0       # Validation
hypothesis >= 6.0     # Property testing
crosshair-tool        # Symbolic verification
mcp                   # Model Context Protocol
```

**Development:**
```
pytest >= 7.0
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

### Package Structure (v1.0+)

Invar uses a two-package architecture:

| Package | Size | Purpose |
|---------|------|---------|
| `invar-runtime` | ~3MB | Runtime contracts (`@pre`, `@post`, `must_use`, `invariant`) |
| `invar-tools` | ~100MB | Development tools (guard, map, sig, MCP server) |

```
invar-runtime (PyPI)
└── src/invar_runtime/
    ├── contracts.py      # @pre/@post, Contract class
    ├── decorators.py     # @must_use, @strategy, @skip_property_test
    ├── invariant.py      # Loop invariants
    └── resource.py       # @must_close

invar-tools (PyPI)
├── src/invar/
│   ├── core/             # Parser, rules, models
│   ├── shell/            # CLI, file system
│   ├── mcp/              # MCP server
│   └── templates/        # Files copied on init
└── (depends on invar-runtime)
```

### Distribution Channels

| Channel | Content | Target Users |
|---------|---------|--------------|
| **PyPI invar-tools** | CLI tool + templates | Developers using AI |
| **PyPI invar-runtime** | Runtime contracts | Projects using contracts |
| **uvx** | No-install execution | Quick usage |
| **GitHub** | Source + dev docs | Contributors |

### Installation Options

```bash
# Recommended: use without installing (always latest)
uvx invar-tools guard
uvx invar-tools init --claude

# Or install globally
pip install invar-tools

# For projects using contracts at runtime
pip install invar-runtime
```

### `invar init` Behavior

```bash
$ uvx invar-tools init --claude

✓ Added [tool.invar.guard] to pyproject.toml
✓ Created INVAR.md (Invar Protocol)
✓ Created CLAUDE.md (customize for your project)
✓ Created src/core/
✓ Created src/shell/
✓ Created .invar/context.md (context management)
✓ Created .mcp.json (MCP server config)
✓ Ran claude /init
```

### Version Strategy

Protocol and tool versions are separate:

```
INVAR.md v5.0        # Protocol version (MAJOR.MINOR)
invar-tools 1.0.2    # Tool version (semver)
invar-runtime 1.0.2  # Runtime version (semver)
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
