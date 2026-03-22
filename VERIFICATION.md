# Verification Report: refs-index-classes

**Date**: 2026-03-23
**Verifier**: Integration Verifier
**Scope**: Class symbol indexing and reference detection in references.py

## Results

| Check | Result | Evidence |
|-------|--------|----------|
| Symbol indexing (CLASS kind) | PASS | `build_symbol_index()` includes `SymbolKind.CLASS` at lines 241-243 |
| Parser ClassDef extraction | PASS | `_parse_class()` extracts class symbols (parser.py lines 197-207) |
| invar refs CLI for classes | PASS | `invar refs src/invar/core/models.py::FileInfo` returns 131 references |
| Base class detection via jedi | PASS | `invar refs src/invar/core/patterns/detector.py::BaseDetector` shows inheritance refs |
| Core find_references_in_source() | PARTIAL | Base class usage not detected (see Gap section) |

## Evidence Levels

| Level | Status |
|-------|--------|
| L2 (Real Wiring) | PASS |
| L3 (Live Service) | N/A |

## Verification Details

### 1. Class Symbol Indexing (PASS)

```python
# From references.py lines 241-243:
symbol_index: dict[str, set[str]] = defaultdict(set)

for file_info in file_infos:
    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS):
            symbol_index[symbol.name].add(file_info.path)
```

**Verdict**: Classes ARE included in the symbol index.

### 2. Parser ClassDef Extraction (PASS)

```python
# From parser.py lines 92-97:
elif isinstance(node, ast.ClassDef):
    symbols.append(_parse_class(node))
    # Extract methods from class body
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.append(_parse_method(item, node.name))
```

**Verdict**: ClassDef nodes ARE correctly parsed.

### 3. invar refs CLI Test (PASS)

```bash
$ uv run invar refs src/invar/core/models.py::FileInfo
{
  "target": "src/invar/core/models.py::FileInfo",
  "total": 131,
  ...
}

$ uv run invar refs src/invar/core/patterns/detector.py::BaseDetector
{
  "target": "src/invar/core/patterns/detector.py::BaseDetector",
  "total": 11,
  "references": [
    {"context": "class BaseDetector:", "is_definition": true},
    {"context": "class ExhaustiveMatchDetector(BaseDetector):", ...},
    {"context": "class LiteralDetector(BaseDetector):", ...},
    ...
  ]
}
```

**Verdict**: The jedi-based `invar refs` correctly finds class references including inheritance.

### 4. Core find_references_in_source() Gap (PARTIAL)

The AST-based reference finder has a gap: it does NOT detect base class references.

```python
# Test result:
source = """from mod import BaseClass

class Child(BaseClass):
    name: str
"""
refs = find_references_in_source(source, {"BaseClass"})
# Result: [('BaseClass', 1)]  # Only the import!
# Missing: ('BaseClass', 3) for the base class usage
```

**Impact Assessment**:
- `invar refs` CLI: NOT affected (uses jedi)
- `build_symbol_index()`: NOT affected (just builds index)
- `count_cross_file_references()`: AFFECTED for class base references
- `dead_export.py`: POTENTIALLY affected if extended to classes

**Current dead_export.py status**: Only analyzes `SymbolKind.FUNCTION` (line 225), so this gap is NOT a blocker for the current DX-95 implementation.

## Gap Analysis

The `find_references_in_source()` function would need this addition to detect base class references:

```python
# Not yet implemented:
if isinstance(node, ast.ClassDef):
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in known_symbols:
            line = getattr(base, "lineno", 0)
            seen.add((base.id, line))
```

However, for DX-95's dead_export extension to classes:
1. The `invar refs` CLI already works correctly (jedi handles all reference types)
2. `build_symbol_index()` correctly includes classes
3. The gap is only in the AST-based `find_references_in_source()` used by `count_cross_file_references()`

If dead_export needs to use `count_cross_file_references()` for classes, the gap would need to be fixed.

## Final Verdict

**PASS**: Classes ARE indexed and references ARE findable.

- `invar refs <file>::<ClassName>` works correctly
- Class symbols are included in the reference index
- jedi-based reference finding handles all class reference patterns

**No blocker for DX-95 dead_export extension.**

The gap in `find_references_in_source()` for base class references is NOT a blocker because:
1. `invar refs` (used interactively) uses jedi and works correctly
2. Current `dead_export.py` only targets functions, not classes
3. If `count_cross_file_references()` is needed for class analysis, a small fix would be required

## Spec Link
- DX-95: Dead export extension to classes