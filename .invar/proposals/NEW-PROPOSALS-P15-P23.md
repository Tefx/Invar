# New Proposals P15-P23: Phase 10+ Roadmap

*Created: 2025-12-20*
*Based on: Phase 9 Development Reflection*

---

## P15: IDE/LSP Integration

**Status:** Proposed
**Priority:** P2 (High impact, High effort)
**Phase:** 10+
**Affects:** Developer experience, Real-time feedback

### Problem

Contract errors are discovered AFTER code is written:

```python
# Agent writes this...
@pre(lambda source, max_lines: ...)  # Missing 'path' param
def analyze(source: str, path: str, max_lines: int): ...

# ...runs invar guard...
# ...sees error...
# ...fixes...
# ...runs guard again...
```

This reactive loop wastes time and context tokens.

### Solution

Language Server Protocol (LSP) integration for real-time feedback:

```
┌─────────────────────────────────────────────────────────┐
│ @pre(lambda source, max_lines: ...)                     │
│              ↑                                          │
│              └── ⚠️ Missing parameter 'path'            │
│                  Expected: lambda source, path, max_lines│
└─────────────────────────────────────────────────────────┘
```

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   VS Code    │────▶│  LSP Server  │────▶│  Invar Core  │
│   Extension  │◀────│  (invar-lsp) │◀────│  (rules.py)  │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
        │  Diagnostics      │  Real-time
        │  Code Actions     │  Analysis
        │  Hover Info       │
        ▼                   ▼
   ┌─────────────────────────────────────┐
   │  Editor shows:                      │
   │  - Squiggles under violations       │
   │  - Quick fixes in lightbulb menu    │
   │  - Hover shows rule explanation     │
   └─────────────────────────────────────┘
```

### Features

#### 1. Real-time Diagnostics

```python
# As you type, see immediately:

@pre(lambda x: True)  # ⚠️ Empty contract: condition is always true
def process(x: int, y: int) -> int:  # ⚠️ Missing param 'y' in @pre
    import os  # 🔴 Forbidden import in Core
    return x + y
```

#### 2. Code Actions (Quick Fixes)

```
💡 Quick Fix: Add missing parameter 'y'
   @pre(lambda x: True)
   →
   @pre(lambda x, y: <condition>)

💡 Quick Fix: Remove forbidden import
   import os
   →
   (deleted)

💡 Quick Fix: Add contract
   def process(...):
   →
   @pre(lambda x, y: <condition>)
   def process(...):
```

#### 3. Hover Information

```
┌─────────────────────────────────────────────────────────┐
│ @pre(lambda x, y: x > 0 and y > 0)                      │
│ ─────────────────────────────────────                   │
│ Precondition Contract                                   │
│                                                         │
│ Parameters: x, y                                        │
│ Validates: Both inputs must be positive                 │
│                                                         │
│ Rule: missing_contract                                  │
│ Docs: INVAR.md#contracts                                │
└─────────────────────────────────────────────────────────┘
```

### Implementation

#### Phase 1: Basic LSP Server

```python
# src/invar/lsp/server.py

from pygls.server import LanguageServer
from lsprotocol.types import Diagnostic, DiagnosticSeverity

class InvarLanguageServer(LanguageServer):
    def __init__(self):
        super().__init__("invar-lsp", "v1.0.0")

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    async def did_change(params):
        """Analyze document and publish diagnostics."""
        uri = params.text_document.uri
        content = server.workspace.get_document(uri).source

        # Reuse existing Invar analysis
        file_info = parse_source(content, uri)
        violations = check_all_rules(file_info, config)

        diagnostics = [
            Diagnostic(
                range=_line_to_range(v.line),
                message=v.message,
                severity=_severity_to_lsp(v.severity),
                source="invar",
                code=v.rule,
            )
            for v in violations
        ]

        server.publish_diagnostics(uri, diagnostics)
```

#### Phase 2: VS Code Extension

```json
// package.json
{
  "name": "invar-vscode",
  "displayName": "Invar",
  "description": "Core/Shell architecture enforcement",
  "categories": ["Linters", "Programming Languages"],
  "activationEvents": ["onLanguage:python"],
  "contributes": {
    "configuration": {
      "title": "Invar",
      "properties": {
        "invar.enable": { "type": "boolean", "default": true },
        "invar.strictPure": { "type": "boolean", "default": true }
      }
    }
  }
}
```

#### Phase 3: Code Actions

```python
@server.feature(TEXT_DOCUMENT_CODE_ACTION)
async def code_actions(params):
    """Provide quick fixes for violations."""
    diagnostics = params.context.diagnostics
    actions = []

    for diag in diagnostics:
        if diag.code == "param_mismatch":
            # Generate fix from suggestion
            fix = _generate_param_fix(diag)
            actions.append(CodeAction(
                title=f"Add missing parameter",
                kind=CodeActionKind.QuickFix,
                edit=fix,
                diagnostics=[diag],
            ))

    return actions
```

### Estimated Effort

| Component | Effort | Dependencies |
|-----------|--------|--------------|
| LSP Server (basic) | 2-3 days | pygls library |
| VS Code Extension | 1-2 days | LSP server |
| Code Actions | 2-3 days | Suggestion system |
| Testing & Polish | 2-3 days | All above |
| **Total** | **1-2 weeks** | |

### Success Metrics

- Contract errors caught before running Guard: >80%
- Time from error to fix: <5 seconds (vs 30+ with Guard cycle)
- Agent productivity increase: measurable reduction in Guard iterations

---

## P16: API Usage Examples in Docstrings

**Status:** Proposed
**Priority:** P3 (Medium impact, Low effort)
**Phase:** 10
**Affects:** API discoverability

### Problem

Agent guesses wrong about Invar APIs:

```python
# WRONG guesses:
symbols = parse_source(source)  # Returns FileInfo, not list
if symbol.has_contract:         # No such attribute
```

### Solution

Enrich docstrings with explicit usage examples:

```python
def parse_source(source: str, path: str) -> FileInfo | None:
    """
    Parse Python source code into FileInfo.

    Args:
        source: Python source code as string
        path: File path (for error messages)

    Returns:
        FileInfo with symbols list, or None if parse fails

    Usage:
        >>> file_info = parse_source("def foo(): pass", "test.py")
        >>> file_info.symbols[0].name
        'foo'
        >>> file_info.symbols[0].kind
        <SymbolKind.FUNCTION: 'function'>

    Common Mistakes:
        # WRONG: parse_source returns FileInfo, not list
        >>> symbols = parse_source(source, path)  # symbols is FileInfo!
        >>> symbols[0]  # TypeError!

        # CORRECT:
        >>> file_info = parse_source(source, path)
        >>> symbols = file_info.symbols  # Now it's a list
    """
```

### Implementation

1. Audit all public APIs in `core/` modules
2. Add "Usage" and "Common Mistakes" sections to docstrings
3. Add `invar api <module>` command to show API docs

```bash
$ invar api parser
parse_source(source: str, path: str) -> FileInfo | None
  Parse Python source into FileInfo.

  Returns: FileInfo (not list!) with .symbols, .imports, .lines

  Usage:
    file_info = parse_source(content, "path.py")
    for symbol in file_info.symbols:
        print(symbol.name, symbol.kind)
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Docstring enrichment | 2-3 hours |
| `invar api` command | 1-2 hours |
| **Total** | **4-5 hours** |

---

## P17: Forbidden Import Alternatives

**Status:** Proposed
**Priority:** P1 (High impact, Low effort)
**Phase:** 10
**Affects:** Guard output, Developer guidance

### Problem

Guard says WHAT is forbidden but not WHAT TO USE INSTEAD:

```
ERROR: 'pathlib' is forbidden in Core
  → (no guidance on alternative)
```

Agent must figure out pure alternatives, wasting reasoning effort.

### Solution

Add pure alternatives to forbidden import messages:

```python
# core/rule_meta.py

FORBIDDEN_IMPORT_ALTERNATIVES = {
    "pathlib": {
        "why": "Path operations may access filesystem",
        "instead": [
            ("Path.match()", "fnmatch.fnmatch(path, pattern)"),
            ("Path.suffix", "os.path.splitext(path)[1] or path.rsplit('.', 1)[-1]"),
            ("Path.stem", "os.path.splitext(os.path.basename(path))[0]"),
            ("Path.parent", "os.path.dirname(path)"),
            ("Path.name", "os.path.basename(path)"),
        ],
        "note": "For pure path string manipulation, use os.path or string methods"
    },
    "os": {
        "why": "OS operations are side effects",
        "instead": [
            ("os.path.join()", "'/'.join(parts) or use posixpath"),
            ("os.path.basename()", "path.rsplit('/', 1)[-1]"),
            ("os.path.dirname()", "path.rsplit('/', 1)[0] if '/' in path else ''"),
            ("os.getenv()", "Pass as function parameter from Shell"),
        ],
        "note": "os.path is pure but os.* (getenv, getcwd, etc.) is not"
    },
    "datetime": {
        "why": "datetime.now() is non-deterministic",
        "instead": [
            ("datetime.now()", "Pass timestamp as parameter from Shell"),
            ("datetime.today()", "Pass date as parameter from Shell"),
        ],
        "note": "datetime arithmetic and parsing are pure, only now()/today() forbidden"
    },
    "random": {
        "why": "Random is non-deterministic",
        "instead": [
            ("random.choice()", "Pass choice as parameter, or use seeded Random"),
            ("random.randint()", "Pass value as parameter from Shell"),
        ],
        "note": "For reproducible randomness, pass seed from Shell"
    },
    "requests": {
        "why": "Network I/O is a side effect",
        "instead": [
            ("requests.get()", "Shell fetches, passes response content to Core"),
        ],
        "note": "Core processes data, Shell handles network"
    },
    "subprocess": {
        "why": "Process execution is a side effect",
        "instead": [
            ("subprocess.run()", "Shell runs command, passes output to Core"),
        ],
        "note": "Core processes output, Shell handles execution"
    },
    "open": {
        "why": "File I/O is a side effect",
        "instead": [
            ("open(path).read()", "Shell reads file, passes content to Core"),
            ("open(path).write()", "Core returns content, Shell writes file"),
        ],
        "note": "Core receives data as strings, not file paths"
    },
}
```

### Output

```
ERROR src/core/utils.py:15 Forbidden import 'pathlib' in Core
  → Why: Path operations may access filesystem
  → Instead of Path.match(): use fnmatch.fnmatch(path, pattern)
  → Instead of Path.suffix: use path.rsplit('.', 1)[-1]
  → Note: For pure path string manipulation, use os.path or string methods

  Hint: Core receives data, not paths. Shell reads files, passes content.
```

### Agent Mode Output

```json
{
  "rule": "forbidden_import",
  "message": "Forbidden import 'pathlib' in Core",
  "import": "pathlib",
  "alternatives": {
    "why": "Path operations may access filesystem",
    "replacements": [
      {"from": "Path.match()", "to": "fnmatch.fnmatch(path, pattern)"},
      {"from": "Path.suffix", "to": "path.rsplit('.', 1)[-1]"}
    ],
    "note": "For pure path string manipulation, use os.path or string methods"
  }
}
```

### Implementation

```python
# core/rules.py - modify check_forbidden_import()

def check_forbidden_import(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    violations = []
    for imp in file_info.imports:
        if imp.module in FORBIDDEN_MODULES:
            alt = FORBIDDEN_IMPORT_ALTERNATIVES.get(imp.module, {})
            suggestion = _format_alternative_suggestion(imp.module, alt)
            violations.append(Violation(
                rule="forbidden_import",
                message=f"Forbidden import '{imp.module}' in Core",
                suggestion=suggestion,
                metadata={"alternatives": alt},  # For --agent mode
            ))
    return violations
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Define alternatives dict | 1-2 hours |
| Modify check_forbidden_import | 30 min |
| Update formatter for output | 30 min |
| Tests | 30 min |
| **Total** | **3-4 hours** |

---

## P18: Module Cohesion Analysis

**Status:** Proposed
**Priority:** P2 (Medium impact, Medium effort)
**Phase:** 10
**Affects:** Refactoring guidance

### Problem

When a file approaches size limit, agent doesn't know HOW to split:

```
WARNING: core/rules.py at 96% capacity (483/500 lines)
  → Consider splitting before reaching limit
  → (but split HOW?)
```

### Solution

Analyze function relationships and suggest cohesive splits:

```
WARNING: core/rules.py at 96% capacity (483/500 lines)

  ANALYSIS:
  ┌─────────────────────────────────────────────────────────┐
  │ Function Groups (by call relationships):                │
  │                                                         │
  │ Group 1: Size Rules (120 lines)                         │
  │   check_file_size ←→ check_function_size                │
  │   _count_code_lines                                     │
  │                                                         │
  │ Group 2: Contract Rules (180 lines)                     │
  │   check_missing_contract ←→ check_empty_contract        │
  │   check_param_mismatch ←→ check_redundant_type          │
  │   _find_lambda, _extract_isinstance_checks              │
  │                                                         │
  │ Group 3: Purity Rules (140 lines)                       │
  │   check_forbidden_import ←→ check_internal_import       │
  │   check_impure_call                                     │
  │   _is_impure_call, _match_pattern                       │
  │                                                         │
  │ Group 4: Shell Rules (40 lines)                         │
  │   check_shell_result                                    │
  └─────────────────────────────────────────────────────────┘

  SUGGESTED SPLIT:
    core/rules/size.py      ← Group 1
    core/rules/contracts.py ← Group 2
    core/rules/purity.py    ← Group 3
    core/rules/shell.py     ← Group 4
    core/rules/__init__.py  ← Re-export check_all_rules
```

### Algorithm

```python
# core/cohesion.py

@dataclass
class FunctionGroup:
    name: str
    functions: list[str]
    lines: int
    internal_calls: set[tuple[str, str]]  # (caller, callee)

def analyze_cohesion(file_info: FileInfo) -> list[FunctionGroup]:
    """
    Analyze function call relationships to identify cohesive groups.

    Algorithm:
    1. Build call graph (which functions call which)
    2. Find connected components
    3. Name groups by common prefix or purpose
    4. Calculate lines per group
    """
    call_graph = _build_call_graph(file_info)
    components = _find_connected_components(call_graph)
    groups = _name_and_size_groups(components, file_info)
    return groups

def _build_call_graph(file_info: FileInfo) -> dict[str, set[str]]:
    """Build graph of function calls within the file."""
    graph = defaultdict(set)
    local_functions = {s.name for s in file_info.symbols
                       if s.kind == SymbolKind.FUNCTION}

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue
        # Parse function body for calls to local functions
        calls = _extract_calls(symbol.source)
        for call in calls:
            if call in local_functions:
                graph[symbol.name].add(call)

    return graph

def suggest_split(file_info: FileInfo) -> SplitSuggestion:
    """Generate module split suggestion."""
    groups = analyze_cohesion(file_info)

    return SplitSuggestion(
        original=file_info.path,
        groups=groups,
        new_modules=[
            ModuleSuggestion(
                path=f"{base}/rules/{g.name}.py",
                functions=g.functions,
                lines=g.lines,
            )
            for g in groups
        ],
    )
```

### Output Formats

#### Human (Rich)

```
$ invar guard --analyze-cohesion src/core/rules.py

Module Cohesion Analysis: src/core/rules.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: 483 lines (96% of limit)

┌──────────────────┬───────┬────────────────────────────────────┐
│ Group            │ Lines │ Functions                          │
├──────────────────┼───────┼────────────────────────────────────┤
│ size             │ 120   │ check_file_size, check_function_.. │
│ contracts        │ 180   │ check_missing_contract, check_em.. │
│ purity           │ 140   │ check_forbidden_import, check_in.. │
│ shell            │ 40    │ check_shell_result                 │
└──────────────────┴───────┴────────────────────────────────────┘

Suggested: Split into 4 modules under core/rules/
```

#### Agent (JSON)

```json
{
  "file": "src/core/rules.py",
  "current_lines": 483,
  "max_lines": 500,
  "percentage": 96,
  "cohesion_analysis": {
    "groups": [
      {
        "name": "size",
        "lines": 120,
        "functions": ["check_file_size", "check_function_size", "_count_code_lines"],
        "internal_calls": [["check_file_size", "_count_code_lines"]]
      },
      {
        "name": "contracts",
        "lines": 180,
        "functions": ["check_missing_contract", "check_empty_contract", "..."]
      }
    ],
    "suggested_split": {
      "base_path": "src/core/rules",
      "modules": [
        {"name": "size.py", "functions": ["..."], "lines": 120},
        {"name": "contracts.py", "functions": ["..."], "lines": 180}
      ]
    }
  }
}
```

### Integration

Add `--analyze-cohesion` flag or auto-show when file >80%:

```python
# shell/cli.py

@app.command()
def guard(..., analyze_cohesion: bool = False):
    ...
    if analyze_cohesion or (file_info.lines > config.max_file_lines * 0.8):
        cohesion = analyze_cohesion(file_info)
        _show_cohesion_analysis(cohesion)
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Call graph builder | 2-3 hours |
| Connected components | 1 hour |
| Group naming heuristics | 1-2 hours |
| Output formatting | 1 hour |
| Integration | 1 hour |
| **Total** | **6-8 hours** |

---

## P19: Doctest/Code Line Split

**Status:** Proposed
**Priority:** P1 (Medium impact, Low effort)
**Phase:** 10
**Affects:** Guard output, Visibility

### Problem

Function warnings don't distinguish code from doctest:

```
WARNING: Function 'analyze_file_context' has 53 lines (max: 50)
```

But actually: 15 code + 38 doctest. The function logic is fine!

### Solution

Show line breakdown in warnings:

```
WARNING: Function 'analyze_file_context' has 53 lines (max: 50)
  → Breakdown: 15 code + 38 doctest
  → Tip: Set exclude_doctest_lines = true to count only code
```

### Implementation

```python
# core/rules.py

def check_function_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    for symbol in file_info.symbols:
        if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue

        total_lines = symbol.lines
        code_lines = _count_code_lines(symbol.source)
        doctest_lines = total_lines - code_lines

        effective_lines = code_lines if config.exclude_doctest_lines else total_lines

        if effective_lines > config.max_function_lines:
            # Already over, report as usual
            violations.append(...)
        elif total_lines > config.max_function_lines:
            # Over total but under code-only
            violations.append(Violation(
                rule="function_size_doctest",
                severity=Severity.INFO,
                message=f"Function '{symbol.name}' has {total_lines} lines "
                        f"({code_lines} code + {doctest_lines} doctest)",
                suggestion="Set exclude_doctest_lines = true to count only code",
            ))
```

### Default Change

Consider making `exclude_doctest_lines = true` the default:

```toml
# pyproject.toml
[tool.invar.guard]
exclude_doctest_lines = true  # NEW default (was false)
```

Rationale:
- Good doctests are valuable, shouldn't be penalized
- Code complexity is what matters, not documentation length
- Agents benefit from seeing more examples

### Estimated Effort

| Task | Effort |
|------|--------|
| Line breakdown calculation | 30 min |
| Update warning message | 30 min |
| Change default | 15 min |
| Tests | 30 min |
| **Total** | **2 hours** |

---

## P20: Proactive Plan Command

**Status:** Proposed
**Priority:** P2 (High impact, High effort)
**Phase:** 10+
**Affects:** Workflow, Proactive guidance

### Problem

Guard is reactive - checks AFTER code is written.

Agent workflow:
1. Write code
2. Run guard
3. See errors
4. Fix
5. Repeat

No guidance BEFORE writing code.

### Solution

`invar plan` command for pre-implementation analysis:

```bash
$ invar plan "Add user authentication"

PLAN ANALYSIS: Add user authentication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AFFECTED FILES (predicted):
  Core (needs @pre/@post):
    - src/core/auth.py (new)
      Suggested contracts:
        - Password validation: @pre(lambda pwd: len(pwd) >= 8)
        - Token verification: @pre(lambda token: token and len(token) == 32)

    - src/core/user.py (modify)
      Current: 180 lines (36%)
      After: ~220 lines (44%) - OK

  Shell (needs Result):
    - src/shell/api.py (modify)
      Add: login_handler, logout_handler
      Return: Result[User, AuthError]

PATTERNS TO FOLLOW:
  Similar feature: src/core/session.py
    - Uses @pre for validation
    - Has SessionError for failures
    - Pattern: validate → process → return

RISKS:
  ⚠️ Password handling - ensure no logging of passwords
  ⚠️ Token storage - Shell concern, not Core

SUGGESTED APPROACH:
  1. Define AuthError in core/errors.py
  2. Create core/auth.py with validation logic
  3. Add login/logout handlers in shell/api.py
  4. Use existing session pattern as template

Run: invar guard --changed after implementation
```

### Algorithm

```python
# core/planner.py

@dataclass
class Plan:
    task: str
    affected_files: list[AffectedFile]
    suggested_contracts: list[ContractSuggestion]
    patterns_to_follow: list[PatternReference]
    risks: list[Risk]
    approach: list[str]

def generate_plan(task: str, project_path: Path) -> Plan:
    """
    Generate implementation plan for a task.

    Steps:
    1. Parse task description for keywords
    2. Search codebase for related files
    3. Analyze existing patterns
    4. Predict new files/changes
    5. Suggest contracts based on task type
    6. Identify risks based on keywords
    """
    keywords = _extract_keywords(task)
    related_files = _find_related_files(project_path, keywords)
    patterns = _analyze_patterns(related_files)
    predictions = _predict_changes(task, related_files)
    contracts = _suggest_contracts(task, predictions)
    risks = _identify_risks(task, keywords)

    return Plan(
        task=task,
        affected_files=predictions,
        suggested_contracts=contracts,
        patterns_to_follow=patterns,
        risks=risks,
        approach=_generate_approach(predictions, patterns),
    )

def _suggest_contracts(task: str, predictions: list) -> list[ContractSuggestion]:
    """Suggest contracts based on task type."""
    suggestions = []

    # Keyword-based suggestions
    if "password" in task.lower():
        suggestions.append(ContractSuggestion(
            function="validate_password",
            contract="@pre(lambda pwd: isinstance(pwd, str) and len(pwd) >= 8)",
            reason="Password minimum length",
        ))

    if "email" in task.lower():
        suggestions.append(ContractSuggestion(
            function="validate_email",
            contract="@pre(lambda email: '@' in email and '.' in email)",
            reason="Basic email format",
        ))

    # Pattern-based suggestions (from similar files)
    ...

    return suggestions
```

### Use Cases

```bash
# Feature planning
$ invar plan "Add dark mode toggle"

# Bug investigation
$ invar plan "Fix authentication timeout"

# Refactoring
$ invar plan "Split rules.py into modules"

# Migration
$ invar plan "Add contracts to existing user module"
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Keyword extraction | 2 hours |
| Related file search | 2-3 hours |
| Pattern analysis | 3-4 hours |
| Contract suggestion | 2-3 hours |
| Risk identification | 1-2 hours |
| Output formatting | 1-2 hours |
| **Total** | **12-16 hours** |

---

## P21: Contract Inference

**Status:** Proposed
**Priority:** P3 (High impact, Very High effort)
**Phase:** 11+
**Affects:** Contract generation

### Problem

Agent must manually write all contracts. This is time-consuming and error-prone.

### Solution

Infer contracts from multiple sources:

```bash
$ invar suggest src/core/calc.py::compute

CONTRACT SUGGESTIONS for compute(x: int, y: int) -> int
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From Doctests:
  >>> compute(5, 3)
  8
  >>> compute(10, 2)
  12

  Inferred: @pre(lambda x, y: x > 0 and y > 0)
  Confidence: HIGH (all examples positive)

From Type Hints:
  x: int, y: int -> int

  Inferred: @pre(lambda x, y: isinstance(x, int) and isinstance(y, int))
  Confidence: LOW (already covered by types)

From Usage Analysis:
  Called 5 times in codebase:
    - process_batch(items): compute(len(items), config.factor)
    - calculate_total(order): compute(order.quantity, order.price)

  Inferred: @pre(lambda x, y: x >= 0 and y >= 0)
  Confidence: MEDIUM (len() and quantity are non-negative)

From Similar Functions:
  - add(a, b) in math_utils.py: @pre(lambda a, b: True)
  - multiply(x, y) in calc.py: @pre(lambda x, y: y != 0)

  Pattern: Binary operations often check for zero divisor
  Inferred: @post(lambda result: isinstance(result, int))
  Confidence: MEDIUM

RECOMMENDED:
  @pre(lambda x, y: x >= 0 and y >= 0)
  @post(lambda result: result >= 0)

  Reasoning: Based on doctest patterns and usage analysis
```

### Inference Sources

| Source | Method | Confidence |
|--------|--------|------------|
| Doctests | Extract inputs, find patterns | High |
| Type hints | Generate isinstance checks | Low (redundant) |
| Usage sites | Analyze actual arguments | Medium |
| Similar functions | Copy patterns from related code | Medium |
| Property tests | Run hypothesis, find failures | High |

### Algorithm

```python
# core/inference.py

@dataclass
class InferredContract:
    contract: str
    source: str  # "doctest", "usage", "similar", "property"
    confidence: float  # 0.0 - 1.0
    reasoning: str

def infer_contracts(symbol: Symbol, project: Project) -> list[InferredContract]:
    """Infer contracts from multiple sources."""
    inferences = []

    # From doctests
    if symbol.doctests:
        doctest_contracts = _infer_from_doctests(symbol)
        inferences.extend(doctest_contracts)

    # From usage analysis
    usages = _find_usages(symbol, project)
    if usages:
        usage_contracts = _infer_from_usages(symbol, usages)
        inferences.extend(usage_contracts)

    # From similar functions
    similar = _find_similar_functions(symbol, project)
    if similar:
        similar_contracts = _infer_from_similar(symbol, similar)
        inferences.extend(similar_contracts)

    # Deduplicate and rank
    return _rank_inferences(inferences)

def _infer_from_doctests(symbol: Symbol) -> list[InferredContract]:
    """Analyze doctest inputs to find patterns."""
    inputs = _extract_doctest_inputs(symbol.doctests)

    patterns = []
    for param, values in inputs.items():
        if all(v > 0 for v in values if isinstance(v, (int, float))):
            patterns.append(f"{param} > 0")
        elif all(v >= 0 for v in values if isinstance(v, (int, float))):
            patterns.append(f"{param} >= 0")
        elif all(isinstance(v, str) and v for v in values):
            patterns.append(f"isinstance({param}, str) and {param}")

    if patterns:
        condition = " and ".join(patterns)
        return [InferredContract(
            contract=f"@pre(lambda {', '.join(inputs.keys())}: {condition})",
            source="doctest",
            confidence=0.8,
            reasoning=f"All {len(values)} doctest examples satisfy this condition",
        )]

    return []
```

### Integration with Property Testing

```python
# Use hypothesis to find counter-examples

from hypothesis import given, strategies as st

def _infer_from_property_test(symbol: Symbol) -> list[InferredContract]:
    """Run property tests to find contract boundaries."""
    # Generate test function
    @given(x=st.integers(), y=st.integers())
    def test_contract(x, y):
        try:
            result = symbol.callable(x, y)
            return True
        except Exception:
            return False

    # Find boundary conditions
    failures = _collect_failures(test_contract)

    if failures:
        # Analyze failure patterns
        # e.g., all failures have y=0 → need y != 0
        pattern = _analyze_failure_pattern(failures)
        return [InferredContract(
            contract=f"@pre(lambda x, y: {pattern})",
            source="property",
            confidence=0.9,
            reasoning=f"Found {len(failures)} failures, pattern: {pattern}",
        )]

    return []
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Doctest parsing | 3-4 hours |
| Usage analysis | 4-5 hours |
| Similar function matching | 3-4 hours |
| Property test integration | 4-5 hours |
| Ranking and dedup | 2 hours |
| Output formatting | 2 hours |
| **Total** | **18-22 hours** |

---

## P22: Automated Refactoring

**Status:** Proposed
**Priority:** P3 (Medium impact, Very High effort)
**Phase:** 11+
**Affects:** Code transformation

### Problem

When refactoring is needed (e.g., split large file), agent must:
1. Identify what to extract
2. Create new module
3. Move functions
4. Update all imports
5. Verify nothing broke

This is mechanical but error-prone.

### Solution

`invar refactor` command for safe transformations:

```bash
$ invar refactor src/core/rules.py --split

REFACTORING: src/core/rules.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analysis: 483 lines, 4 cohesive groups identified

Plan:
  1. Create src/core/rules/ directory
  2. Create src/core/rules/__init__.py (re-exports)
  3. Create src/core/rules/size.py (120 lines)
     - Move: check_file_size, check_function_size, _count_code_lines
  4. Create src/core/rules/contracts.py (180 lines)
     - Move: check_missing_contract, check_empty_contract, ...
  5. Create src/core/rules/purity.py (140 lines)
     - Move: check_forbidden_import, check_internal_import, ...
  6. Create src/core/rules/shell.py (40 lines)
     - Move: check_shell_result
  7. Update imports in 3 files:
     - src/invar/shell/cli.py
     - src/invar/core/formatter.py
     - tests/test_rules.py

Proceed? [y/N] y

✓ Created src/core/rules/
✓ Created src/core/rules/__init__.py
✓ Created src/core/rules/size.py
✓ Created src/core/rules/contracts.py
✓ Created src/core/rules/purity.py
✓ Created src/core/rules/shell.py
✓ Updated src/invar/shell/cli.py
✓ Updated src/invar/core/formatter.py
✓ Updated tests/test_rules.py
✓ Removed src/core/rules.py

Verification:
  ✓ pytest --doctest-modules passed
  ✓ invar guard passed
  ✓ All imports resolved

Done! Refactored 1 file into 4 modules.
```

### Safe Transformations

| Transformation | Safety Level | Description |
|----------------|--------------|-------------|
| Split module | High | Move functions to new files |
| Rename symbol | High | Update all references |
| Extract function | Medium | Extract code block to function |
| Inline function | Medium | Replace calls with body |
| Move to Core/Shell | Low | Change module location |

### Implementation

```python
# shell/refactor.py

@dataclass
class RefactorPlan:
    original: Path
    transformations: list[Transformation]
    affected_files: list[Path]

class SplitModuleTransformation:
    def __init__(self, source: Path, groups: list[FunctionGroup]):
        self.source = source
        self.groups = groups

    def execute(self, dry_run: bool = False) -> RefactorResult:
        """Execute the split transformation."""
        # 1. Create new directory
        new_dir = self.source.parent / self.source.stem
        if not dry_run:
            new_dir.mkdir(exist_ok=True)

        # 2. Create new modules
        for group in self.groups:
            new_file = new_dir / f"{group.name}.py"
            content = self._generate_module(group)
            if not dry_run:
                new_file.write_text(content)

        # 3. Create __init__.py
        init_content = self._generate_init()
        if not dry_run:
            (new_dir / "__init__.py").write_text(init_content)

        # 4. Update imports
        for file in self._find_importers():
            new_content = self._update_imports(file)
            if not dry_run:
                file.write_text(new_content)

        # 5. Remove original
        if not dry_run:
            self.source.unlink()

        return RefactorResult(success=True, files_changed=[...])

    def _generate_module(self, group: FunctionGroup) -> str:
        """Generate new module content."""
        imports = self._collect_imports(group.functions)
        functions = self._extract_functions(group.functions)

        return f'''"""
{group.name.title()} rules for Invar Guard.
"""

{imports}

{functions}
'''
```

### Verification

After refactoring, automatically verify:

```python
def verify_refactor(result: RefactorResult) -> VerificationResult:
    """Verify refactoring didn't break anything."""
    checks = []

    # 1. Syntax check all new files
    for file in result.new_files:
        try:
            ast.parse(file.read_text())
            checks.append(("syntax", file, True))
        except SyntaxError as e:
            checks.append(("syntax", file, False, str(e)))

    # 2. Import resolution
    for file in result.affected_files:
        try:
            importlib.import_module(_path_to_module(file))
            checks.append(("import", file, True))
        except ImportError as e:
            checks.append(("import", file, False, str(e)))

    # 3. Run tests
    test_result = subprocess.run(["pytest", "--doctest-modules", "-x"])
    checks.append(("tests", None, test_result.returncode == 0))

    # 4. Run guard
    guard_result = subprocess.run(["invar", "guard"])
    checks.append(("guard", None, guard_result.returncode == 0))

    return VerificationResult(checks=checks, passed=all(c[2] for c in checks))
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Refactor plan generation | 3-4 hours |
| Split transformation | 4-5 hours |
| Import updating | 3-4 hours |
| Verification | 2-3 hours |
| Rollback support | 2-3 hours |
| CLI integration | 2 hours |
| **Total** | **16-21 hours** |

---

## P23: Cross-Session Memory

**Status:** Proposed
**Priority:** P3 (Medium impact, High effort)
**Phase:** 11+
**Affects:** Learning, Pattern recognition

### Problem

Each session starts fresh. No learning from past mistakes:

```
Session 1: Agent writes wrong @pre params → error → fix
Session 2: Agent writes wrong @pre params → error → fix  (same mistake!)
Session 3: Agent writes wrong @pre params → error → fix  (again!)
```

### Solution

Persistent memory of patterns and mistakes:

```bash
$ invar memory show

INVAR SESSION MEMORY
━━━━━━━━━━━━━━━━━━━━

Common Errors (last 30 days):
┌─────────────────────────────────┬───────┬────────────┐
│ Pattern                         │ Count │ Last Seen  │
├─────────────────────────────────┼───────┼────────────┤
│ @pre param count mismatch       │ 5     │ 2025-12-20 │
│ pathlib import in Core          │ 3     │ 2025-12-19 │
│ Missing Result in Shell         │ 2     │ 2025-12-18 │
└─────────────────────────────────┴───────┴────────────┘

Learned Patterns:
┌─────────────────────────────────┬────────────────────────────────┐
│ File Pattern                    │ Typical Contract               │
├─────────────────────────────────┼────────────────────────────────┤
│ core/parser.py                  │ @pre(lambda source: ...)       │
│ core/rules.py                   │ @pre(lambda file_info, config) │
│ core/formatter.py               │ @pre(lambda v: isinstance(...))│
└─────────────────────────────────┴────────────────────────────────┘

Session Stats:
  Total sessions: 12
  Average errors per session: 3.2
  Most improved: param_mismatch (5 → 1)
```

### Data Structure

```python
# .invar/memory.json

{
  "version": 1,
  "created": "2025-12-01T00:00:00Z",
  "updated": "2025-12-20T15:30:00Z",

  "errors": [
    {
      "pattern": "param_mismatch",
      "count": 5,
      "last_seen": "2025-12-20",
      "contexts": [
        {"file": "core/inspect.py", "function": "analyze_file_context"},
        {"file": "core/rules.py", "function": "check_all_rules"}
      ]
    }
  ],

  "patterns": {
    "core/*.py": {
      "common_contracts": [
        "@pre(lambda file_info: isinstance(file_info, FileInfo))",
        "@pre(lambda source: isinstance(source, str))"
      ],
      "common_imports": ["from deal import pre, post"],
      "typical_structure": "module docstring → imports → dataclass → functions"
    }
  },

  "sessions": [
    {
      "date": "2025-12-20",
      "duration_minutes": 45,
      "files_changed": 5,
      "errors_initial": 8,
      "errors_final": 0,
      "guard_runs": 12
    }
  ]
}
```

### Features

#### 1. Error Prevention

When agent is about to make a known mistake:

```python
# In Guard output, if pattern matches known error:
WARNING: This pattern has caused errors before

  You're writing: @pre(lambda source, max_lines: ...)
  Function has: def analyze(source, path, max_lines)

  History: You've made this mistake 5 times in similar contexts
  Tip: Always include ALL parameters in @pre lambda
```

#### 2. Pattern Suggestion

When creating new file:

```python
# Suggest based on learned patterns
$ invar new core/validator.py

Based on patterns in core/*.py:

```python
"""
Validator module for Invar Core.
"""

from deal import pre, post

from invar.core.models import FileInfo


@pre(lambda file_info: isinstance(file_info, FileInfo))
def validate(file_info: FileInfo) -> bool:
    """
    Validate file info.

    >>> validate(FileInfo(...))
    True
    """
    ...
```

#### 3. Progress Tracking

```bash
$ invar memory stats

ERROR REDUCTION OVER TIME
━━━━━━━━━━━━━━━━━━━━━━━━━

param_mismatch:
  Week 1: ████████████ 12 errors
  Week 2: ████████ 8 errors
  Week 3: ████ 4 errors
  Week 4: █ 1 error

  Improvement: 92% reduction

forbidden_import:
  Week 1: ████ 4 errors
  Week 2: ██ 2 errors
  Week 3: █ 1 error
  Week 4: 0 errors

  Improvement: 100% reduction
```

### Implementation

```python
# shell/memory.py

class SessionMemory:
    def __init__(self, path: Path = Path(".invar/memory.json")):
        self.path = path
        self.data = self._load()

    def record_error(self, violation: Violation, context: dict):
        """Record an error for pattern learning."""
        pattern = violation.rule

        # Update error count
        error = self._find_or_create_error(pattern)
        error["count"] += 1
        error["last_seen"] = datetime.now().isoformat()
        error["contexts"].append(context)

        self._save()

    def record_fix(self, violation: Violation, fix: str):
        """Record how an error was fixed."""
        pattern = violation.rule
        file_pattern = self._extract_file_pattern(violation.file)

        # Learn the fix pattern
        self.data["patterns"].setdefault(file_pattern, {})
        self.data["patterns"][file_pattern].setdefault("fixes", [])
        self.data["patterns"][file_pattern]["fixes"].append({
            "error": pattern,
            "fix": fix,
            "timestamp": datetime.now().isoformat(),
        })

        self._save()

    def get_prevention_hint(self, context: dict) -> str | None:
        """Get hint based on past errors in similar context."""
        file_pattern = self._extract_file_pattern(context.get("file", ""))

        # Find relevant past errors
        relevant = [e for e in self.data["errors"]
                    if self._matches_context(e, context)]

        if relevant:
            most_common = max(relevant, key=lambda e: e["count"])
            return f"Watch out: {most_common['pattern']} error common here ({most_common['count']} times)"

        return None
```

### Integration with Guard

```python
# shell/cli.py

def guard(...):
    memory = SessionMemory()

    # Before checking, show relevant warnings
    if memory.has_relevant_warnings(path):
        warnings = memory.get_prevention_hints(path)
        for w in warnings:
            console.print(f"[yellow]Memory:[/yellow] {w}")

    # After checking, record errors
    for violation in report.violations:
        memory.record_error(violation, {"file": path, ...})

    # Track session
    memory.end_session(report)
```

### Estimated Effort

| Task | Effort |
|------|--------|
| Data structure design | 2 hours |
| Memory persistence | 2-3 hours |
| Error recording | 2 hours |
| Pattern learning | 3-4 hours |
| Prevention hints | 2-3 hours |
| Stats/reporting | 2 hours |
| Guard integration | 2 hours |
| **Total** | **15-18 hours** |

---

## Priority Summary

### Phase 10 (Immediate)

| ID | Proposal | Effort | Impact |
|----|----------|--------|--------|
| P17 | Forbidden import alternatives | 3-4h | High |
| P19 | Doctest/code line split | 2h | Medium |
| P7 | Semantic tautology detection | 8-10h | High |

### Phase 10+ (Medium-term)

| ID | Proposal | Effort | Impact |
|----|----------|--------|--------|
| P18 | Module cohesion analysis | 6-8h | Medium |
| P16 | API usage examples | 4-5h | Medium |
| P20 | Proactive plan command | 12-16h | High |

### Phase 11+ (Long-term)

| ID | Proposal | Effort | Impact |
|----|----------|--------|--------|
| P15 | IDE/LSP integration | 1-2 weeks | High |
| P21 | Contract inference | 18-22h | High |
| P22 | Automated refactoring | 16-21h | Medium |
| P23 | Cross-session memory | 15-18h | Medium |

---

## Implementation Order Recommendation

```
Phase 10:
  P17 (alternatives) → P19 (line split) → P7 (tautology)

Phase 10.5:
  P18 (cohesion) → P16 (API docs) → P20 (plan)

Phase 11:
  P15 (LSP) [parallel with below]
  P21 (inference) → P22 (refactor) → P23 (memory)
```

Rationale:
- P17, P19: Quick wins with immediate value
- P7: Foundation for contract quality
- P18, P20: Enable proactive guidance
- P15: Game-changer for real-time feedback
- P21-P23: Advanced automation features

---

*These proposals build on Phase 9 learnings to further reduce friction and improve Agent-Native design.*
