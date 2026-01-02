"""TypeScript Signature Extraction (Core).

Pure logic for extracting function/class signatures from TypeScript source.
Part of LX-06 TypeScript tooling support.

Note: This is a regex-based MVP. Phase 2 can upgrade to tree-sitter for
more robust parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from deal import post, pre


@dataclass(frozen=True)
class TSSymbol:
    """Represents a TypeScript symbol (function, class, interface, type)."""

    name: str
    kind: Literal["function", "class", "interface", "type", "const", "method"]
    signature: str
    line: int
    docstring: str | None = None


# Regex patterns for TypeScript constructs
# Note: These are simplified patterns suitable for common cases.
# Known limitation: Multiline parameter lists are truncated to first line.
# Phase 2 can upgrade to tree-sitter for full multiline support.
_FUNCTION_PATTERN = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s*\n\s*)*"  # Optional decorators
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*"
    r"(<[^>]*>)?"  # Optional generics
    r"\(([^)]*)\)"  # Parameters
    r"(?:\s*:\s*([^\n{]+))?"  # Optional return type
    r"\s*\{",
    re.MULTILINE,
)

_ARROW_FUNCTION_PATTERN = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*"
    r"(?::\s*[^=]+)?\s*=\s*"
    r"(?:async\s+)?\([^)]*\)\s*"
    r"(?::\s*[^\n=>]+)?\s*=>",
    re.MULTILINE,
)

_CLASS_PATTERN = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s*\n\s*)*"  # Optional decorators
    r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)"
    r"(?:<[^{]*>)?"  # Optional generics (allow nested <> by stopping at {)
    r"(?:\s+extends\s+[^\s{]+)?"  # Optional extends
    r"(?:\s+implements\s+[^\s{]+)?"  # Optional implements
    r"\s*\{",
    re.MULTILINE,
)

_INTERFACE_PATTERN = re.compile(
    r"^\s*(?:export\s+)?interface\s+(\w+)"
    r"(?:<[^{]*>)?"  # Optional generics (allow nested <> by stopping at {)
    r"(?:\s+extends\s+[^\s{]+)?"  # Optional extends
    r"\s*\{",
    re.MULTILINE,
)

_TYPE_ALIAS_PATTERN = re.compile(
    r"^\s*(?:export\s+)?type\s+(\w+)"
    r"(?:<[^=]*>)?"  # Optional generics (allow nested <> by stopping at =)
    r"\s*=",
    re.MULTILINE,
)

_JSDOC_PATTERN = re.compile(
    r"/\*\*\s*(.*?)\s*\*/",
    re.DOTALL,
)


# @invar:allow function_size: Regex extraction inherently repetitive per TS construct type
# @invar:allow redundant_type_contract: Defense-in-depth for dynamic callers
@pre(lambda source: isinstance(source, str) and len(source) < 10_000_000)  # ~10MB DoS limit
@post(lambda result: all(s.line > 0 and s.name for s in result))  # Valid line numbers and names
def extract_ts_signatures(source: str) -> list[TSSymbol]:
    """Extract TypeScript symbols from source code.

    Args:
        source: TypeScript source code.

    Returns:
        List of TSSymbol objects representing functions, classes, etc.

    >>> code = '''
    ... function greet(name: string): string {
    ...     return `Hello, ${name}`;
    ... }
    ... '''
    >>> symbols = extract_ts_signatures(code)
    >>> len(symbols)
    1
    >>> symbols[0].name
    'greet'
    >>> symbols[0].kind
    'function'

    >>> code2 = '''
    ... export class User {
    ...     constructor(public name: string) {}
    ... }
    ... '''
    >>> symbols2 = extract_ts_signatures(code2)
    >>> symbols2[0].name
    'User'
    >>> symbols2[0].kind
    'class'
    """
    # Early return for empty source (CrossHair-friendly)
    if not source:
        return []

    symbols: list[TSSymbol] = []
    lines = source.split("\n")

    # Find JSDoc comments for association
    jsdoc_positions: dict[int, str] = {}
    for match in _JSDOC_PATTERN.finditer(source):
        # Find line number of end of JSDoc
        end_pos = match.end()
        line_num = source[:end_pos].count("\n")
        jsdoc_positions[line_num] = match.group(1).strip()

    def get_jsdoc(line: int) -> str | None:
        """Get JSDoc for a symbol at given line."""
        # Check previous lines for JSDoc
        for i in range(max(0, line - 5), line):
            if i in jsdoc_positions:
                return jsdoc_positions[i]
        return None

    def get_line_number(pos: int) -> int:
        """Convert character position to line number (1-indexed)."""
        return source[:pos].count("\n") + 1

    # Extract functions
    for match in _FUNCTION_PATTERN.finditer(source):
        name = match.group(1)
        # Find actual function line (skip decorators)
        match_text = match.group(0)
        func_keyword_pos = match_text.find("function ")
        actual_start = match.start() + func_keyword_pos if func_keyword_pos >= 0 else match.start()
        line = get_line_number(actual_start)
        # Use line content for signature (handles complex types better than regex groups)
        line_content = lines[line - 1].strip() if line <= len(lines) else ""
        signature = line_content.rstrip("{").rstrip()
        symbols.append(
            TSSymbol(
                name=name,
                kind="function",
                signature=signature,
                line=line,
                docstring=get_jsdoc(line - 1),
            )
        )

    # Extract arrow functions (const declarations)
    for match in _ARROW_FUNCTION_PATTERN.finditer(source):
        name = match.group(1)
        line = get_line_number(match.start())
        # For arrow functions, extract the full line as signature approximation
        line_content = lines[line - 1].strip() if line <= len(lines) else ""
        signature = line_content.rstrip("{").rstrip()
        symbols.append(
            TSSymbol(
                name=name,
                kind="const",
                signature=signature,
                line=line,
                docstring=get_jsdoc(line - 1),
            )
        )

    # Extract classes
    for match in _CLASS_PATTERN.finditer(source):
        name = match.group(1)
        # Find actual class line (skip decorators)
        match_text = match.group(0)
        class_keyword_pos = match_text.find("class ")
        actual_start = match.start() + class_keyword_pos if class_keyword_pos >= 0 else match.start()
        line = get_line_number(actual_start)
        line_content = lines[line - 1].strip() if line <= len(lines) else ""
        signature = line_content.rstrip("{").rstrip()
        symbols.append(
            TSSymbol(
                name=name,
                kind="class",
                signature=signature,
                line=line,
                docstring=get_jsdoc(line - 1),
            )
        )

    # Extract interfaces
    for match in _INTERFACE_PATTERN.finditer(source):
        name = match.group(1)
        line = get_line_number(match.start())
        line_content = lines[line - 1].strip() if line <= len(lines) else ""
        signature = line_content.rstrip("{").rstrip()
        symbols.append(
            TSSymbol(
                name=name,
                kind="interface",
                signature=signature,
                line=line,
                docstring=get_jsdoc(line - 1),
            )
        )

    # Extract type aliases
    for match in _TYPE_ALIAS_PATTERN.finditer(source):
        name = match.group(1)
        line = get_line_number(match.start())
        line_content = lines[line - 1].strip() if line <= len(lines) else ""
        # Include the full type definition
        signature = line_content.rstrip(";").strip()
        symbols.append(
            TSSymbol(
                name=name,
                kind="type",
                signature=signature,
                line=line,
                docstring=get_jsdoc(line - 1),
            )
        )

    # Sort by line number
    symbols.sort(key=lambda s: s.line)

    return symbols


@pre(lambda symbols, file_path="": all(s.line > 0 for s in symbols))  # All symbols have valid line numbers
@post(lambda result: "file" in result and "symbols" in result)
def format_ts_signatures_json(
    symbols: list[TSSymbol], file_path: str = ""
) -> dict:
    """Format TypeScript symbols as JSON output.

    Args:
        symbols: List of TSSymbol objects.
        file_path: Source file path.

    Returns:
        JSON-serializable dictionary.

    >>> symbols = [TSSymbol("foo", "function", "function foo(): void", 1)]
    >>> result = format_ts_signatures_json(symbols, "test.ts")
    >>> result["file"]
    'test.ts'
    >>> len(result["symbols"])
    1
    """
    return {
        "file": file_path,
        "symbols": [
            {
                "name": s.name,
                "kind": s.kind,
                "signature": s.signature,
                "line": s.line,
                "docstring": s.docstring,
            }
            for s in symbols
        ],
    }


@pre(lambda symbols, file_path="": all(s.line > 0 for s in symbols))  # All symbols have valid line numbers
@post(lambda result: len(result) > 0)  # Always produces output (at least header)
def format_ts_signatures_text(
    symbols: list[TSSymbol], file_path: str = ""
) -> str:
    """Format TypeScript symbols as human-readable text.

    Args:
        symbols: List of TSSymbol objects.
        file_path: Source file path.

    Returns:
        Formatted text output.

    >>> symbols = [TSSymbol("foo", "function", "function foo(): void", 1)]
    >>> text = format_ts_signatures_text(symbols, "test.ts")
    >>> "foo" in text
    True
    """
    lines = [f"# {file_path}" if file_path else "# TypeScript Signatures", ""]

    for symbol in symbols:
        lines.append(f"[{symbol.kind}] {symbol.name} (line {symbol.line})")
        lines.append(f"  {symbol.signature}")
        if symbol.docstring:
            # Truncate long docstrings
            doc = symbol.docstring[:100] + "..." if len(symbol.docstring) > 100 else symbol.docstring
            lines.append(f"  /** {doc} */")
        lines.append("")

    return "\n".join(lines)
