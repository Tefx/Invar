"""
AST parser for extracting symbols and contracts.

This module receives string content (not file paths) and returns
structured data. No I/O operations.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.models import Contract, FileInfo, Symbol, SymbolKind
from invar.core.purity import (
    count_code_lines,
    count_doctest_lines,
    extract_function_calls,
    extract_impure_calls,
    extract_internal_imports,
)


@pre(lambda source, path="<string>": isinstance(source, str) and len(source.strip()) > 0)
def parse_source(source: str, path: str = "<string>") -> FileInfo | None:
    """
    Parse Python source code and extract symbols.

    Args:
        source: Python source code as string (must contain non-whitespace)
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
        >>> parse_source("   \\n\\t  ")  # Whitespace-only returns None via contract
        Traceback (most recent call last):
            ...
        deal.PreContractError: ...
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return None

    lines = source.count("\n") + 1
    symbols = _extract_symbols(tree)
    imports = _extract_imports(tree)

    return FileInfo(
        path=path,
        lines=lines,
        symbols=symbols,
        imports=imports,
        source=source,
    )


@pre(lambda tree: isinstance(tree, ast.Module) and hasattr(tree, 'body'))
def _extract_symbols(tree: ast.Module) -> list[Symbol]:
    """
    Extract function, class, and method symbols from AST.

    Examples:
        >>> import ast
        >>> tree = ast.parse("class Foo:\\n    def bar(self): pass")
        >>> symbols = _extract_symbols(tree)
        >>> len(symbols)
        2
        >>> symbols[0].kind.value
        'class'
        >>> symbols[1].kind.value
        'method'
    """
    symbols: list[Symbol] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.append(_parse_function(node))
        elif isinstance(node, ast.ClassDef):
            symbols.append(_parse_class(node))
            # Extract methods from class body
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    symbols.append(_parse_method(item, node.name))

    return symbols


@pre(lambda node: (
    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and
    hasattr(node, 'name') and hasattr(node, 'args') and hasattr(node, 'lineno')
))
@post(lambda result: result.kind == SymbolKind.FUNCTION)
def _parse_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Symbol:
    """Parse a function definition into a Symbol."""
    contracts = _extract_contracts(node)
    docstring = ast.get_docstring(node)
    has_doctest = docstring is not None and ">>>" in docstring
    signature = _build_signature(node)
    internal_imports = extract_internal_imports(node)
    impure_calls = extract_impure_calls(node)
    code_lines = count_code_lines(node)
    doctest_lines = count_doctest_lines(node)
    function_calls = extract_function_calls(node)  # P25

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
        doctest_lines=doctest_lines,
        function_calls=function_calls,
    )


@pre(lambda node, class_name: (
    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and
    hasattr(node, 'name') and hasattr(node, 'args') and hasattr(node, 'lineno')
))
@post(lambda result: result.kind == SymbolKind.METHOD)
def _parse_method(node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str) -> Symbol:
    """
    Parse a method definition into a Symbol.

    Examples:
        >>> import ast
        >>> tree = ast.parse("class Foo:\\n    def bar(self): pass")
        >>> method_node = tree.body[0].body[0]
        >>> sym = _parse_method(method_node, "Foo")
        >>> sym.name
        'Foo.bar'
        >>> sym.kind.value
        'method'
    """
    contracts = _extract_contracts(node)
    docstring = ast.get_docstring(node)
    has_doctest = docstring is not None and ">>>" in docstring
    signature = _build_signature(node)
    internal_imports = extract_internal_imports(node)
    impure_calls = extract_impure_calls(node)
    code_lines = count_code_lines(node)
    doctest_lines = count_doctest_lines(node)
    function_calls = extract_function_calls(node)  # P25

    return Symbol(
        name=f"{class_name}.{node.name}",
        kind=SymbolKind.METHOD,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        signature=signature,
        docstring=docstring,
        contracts=contracts,
        has_doctest=has_doctest,
        internal_imports=internal_imports,
        impure_calls=impure_calls,
        code_lines=code_lines,
        doctest_lines=doctest_lines,
        function_calls=function_calls,
    )


@pre(lambda node: isinstance(node, ast.ClassDef) and hasattr(node, 'name') and hasattr(node, 'lineno'))
@post(lambda result: result.kind == SymbolKind.CLASS)
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


@pre(lambda node: (
    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and
    hasattr(node, 'decorator_list')
))
@post(lambda result: all(c.kind in ("pre", "post") for c in result))
def _extract_contracts(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Contract]:
    """Extract @pre and @post contracts from function decorators."""
    contracts: list[Contract] = []

    for decorator in node.decorator_list:
        contract = _parse_decorator_as_contract(decorator)
        if contract:
            contracts.append(contract)

    return contracts


@pre(lambda decorator: not isinstance(decorator, ast.Call) or hasattr(decorator, "func"))
@post(lambda result: result is None or result.kind in ("pre", "post"))
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


@pre(lambda call: isinstance(call, ast.Call) and hasattr(call, 'args'))
def _get_contract_expression(call: ast.Call) -> str:
    """Extract the expression string from a contract decorator call."""
    if call.args:
        return ast.unparse(call.args[0])
    return ""


@pre(lambda node: (
    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and
    hasattr(node, 'args')
))
@post(lambda result: result.startswith("(") and ")" in result)
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


@pre(lambda tree: isinstance(tree, ast.Module) and hasattr(tree, 'body'))
@post(lambda result: all(isinstance(s, str) and s for s in result))
def _extract_imports(tree: ast.Module) -> list[str]:
    """Extract imported module names from AST (top-level only)."""
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])

    return list(set(imports))  # Deduplicate
