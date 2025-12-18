"""
AST parser for extracting symbols and contracts.

This module receives string content (not file paths) and returns
structured data. No I/O operations.
"""

from __future__ import annotations

import ast

from deal import pre

from invar.core.models import Contract, FileInfo, Symbol, SymbolKind
from invar.core.purity import count_code_lines, extract_impure_calls, extract_internal_imports


@pre(lambda source, path="<string>": isinstance(source, str))
def parse_source(source: str, path: str = "<string>") -> FileInfo | None:
    """
    Parse Python source code and extract symbols.

    Args:
        source: Python source code as string
        path: Path for reporting (not used for I/O)

    Returns:
        FileInfo with extracted symbols, or None if syntax error

    Examples:
        >>> info = parse_source("def foo(): pass")
        >>> info is not None
        True
        >>> len(info.symbols)
        1
        >>> info.symbols[0].name
        'foo'
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    lines = source.count("\n") + 1
    symbols = _extract_symbols(tree)
    imports = _extract_imports(tree)

    return FileInfo(
        path=path,
        lines=lines,
        symbols=symbols,
        imports=imports,
    )


def _extract_symbols(tree: ast.Module) -> list[Symbol]:
    """Extract function and class symbols from AST (top-level only)."""
    symbols: list[Symbol] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol = _parse_function(node)
            symbols.append(symbol)
        elif isinstance(node, ast.ClassDef):
            symbol = _parse_class(node)
            symbols.append(symbol)

    return symbols


def _parse_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Symbol:
    """Parse a function definition into a Symbol."""
    contracts = _extract_contracts(node)
    docstring = ast.get_docstring(node)
    has_doctest = docstring is not None and ">>>" in docstring

    # Build signature
    signature = _build_signature(node)

    # Phase 3: Extract additional info (from purity module)
    internal_imports = extract_internal_imports(node)
    impure_calls = extract_impure_calls(node)
    code_lines = count_code_lines(node)

    return Symbol(
        name=node.name,
        kind=SymbolKind.FUNCTION,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        signature=signature,
        docstring=docstring,
        contracts=contracts,
        has_doctest=has_doctest,
        internal_imports=internal_imports,
        impure_calls=impure_calls,
        code_lines=code_lines,
    )


def _parse_class(node: ast.ClassDef) -> Symbol:
    """Parse a class definition into a Symbol."""
    docstring = ast.get_docstring(node)

    return Symbol(
        name=node.name,
        kind=SymbolKind.CLASS,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        docstring=docstring,
    )


def _extract_contracts(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Contract]:
    """Extract @pre and @post contracts from function decorators."""
    contracts: list[Contract] = []

    for decorator in node.decorator_list:
        contract = _parse_decorator_as_contract(decorator)
        if contract:
            contracts.append(contract)

    return contracts


def _parse_decorator_as_contract(decorator: ast.expr) -> Contract | None:
    """Try to parse a decorator as a contract (@pre or @post)."""
    # Handle @pre(...) or @post(...)
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name) and func.id in ("pre", "post"):
            expr = _get_contract_expression(decorator)
            return Contract(
                kind="pre" if func.id == "pre" else "post",
                expression=expr,
                line=decorator.lineno,
            )
        # Handle deal.pre(...) or deal.post(...)
        if isinstance(func, ast.Attribute) and func.attr in ("pre", "post"):
            expr = _get_contract_expression(decorator)
            return Contract(
                kind="pre" if func.attr == "pre" else "post",
                expression=expr,
                line=decorator.lineno,
            )

    return None


def _get_contract_expression(call: ast.Call) -> str:
    """Extract the expression string from a contract decorator call."""
    if call.args:
        return ast.unparse(call.args[0])
    return ""


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a signature string from function arguments."""
    args = node.args
    parts: list[str] = []

    # Regular args
    for arg in args.args:
        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        parts.append(part)

    sig = f"({', '.join(parts)})"

    # Return type
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"

    return sig


def _extract_imports(tree: ast.Module) -> list[str]:
    """Extract imported module names from AST (top-level only)."""
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    return list(set(imports))  # Deduplicate
