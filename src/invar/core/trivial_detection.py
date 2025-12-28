"""Trivial contract detection for DX-63.

Pure logic module - no I/O. Detects contracts that provide no real constraint.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from deal import post, pre


@dataclass
class TrivialContract:
    """A trivial contract that provides no real constraint.

    Examples:
        >>> tc = TrivialContract(
        ...     file="src/core/calc.py",
        ...     line=10,
        ...     function_name="process",
        ...     contract_type="post",
        ...     expression="lambda: True"
        ... )
        >>> tc.contract_type
        'post'
    """

    file: str
    line: int
    function_name: str
    contract_type: str  # "pre" or "post"
    expression: str


# Patterns that match trivial contracts
TRIVIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*lambda\s*:\s*True\s*$"),  # lambda: True
    re.compile(r"^\s*lambda\s+\w+\s*:\s*True\s*$"),  # lambda x: True
    re.compile(r"^\s*lambda\s+[\w,\s]+:\s*True\s*$"),  # lambda x, y: True
    re.compile(r"^\s*lambda\s+\*\w+\s*:\s*True\s*$"),  # lambda *args: True
    re.compile(r"^\s*lambda\s+\*\*\w+\s*:\s*True\s*$"),  # lambda **kwargs: True
    re.compile(r"^\s*lambda\s+result\s*:\s*True\s*$"),  # lambda result: True
    re.compile(r"^\s*lambda\s+_\s*:\s*True\s*$"),  # lambda _: True
]


@pre(lambda expression: len(expression.strip()) > 0)
@post(lambda result: isinstance(result, bool))
def is_trivial_contract(expression: str) -> bool:
    """Check if a contract expression is trivial (provides no constraint).

    Trivial contracts always return True regardless of input, providing
    no actual constraint on the function's behavior.

    Examples:
        >>> is_trivial_contract("lambda: True")
        True
        >>> is_trivial_contract("lambda x: True")
        True
        >>> is_trivial_contract("lambda x, y: True")
        True
        >>> is_trivial_contract("lambda result: True")
        True
        >>> is_trivial_contract("lambda x: x > 0")
        False
        >>> is_trivial_contract("lambda items: len(items) > 0")
        False
        >>> is_trivial_contract("lambda result: result >= 0")
        False
    """
    expr = expression.strip()
    return any(pattern.match(expr) for pattern in TRIVIAL_PATTERNS)


@pre(lambda node: isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
@post(lambda result: all(t[0] in ("pre", "post") for t in result))
def extract_contracts_from_decorators(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, str]]:
    """Extract contract expressions from function decorators.

    Returns list of (contract_type, expression) tuples.

    Examples:
        >>> import ast
        >>> code = '''
        ... @pre(lambda x: x > 0)
        ... @post(lambda result: result >= 0)
        ... def calc(x): return x * 2
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> contracts = extract_contracts_from_decorators(func)
        >>> len(contracts)
        2
        >>> contracts[0][0]
        'pre'
    """
    contracts = []

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            # Get decorator name
            if isinstance(decorator.func, ast.Name):
                name = decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                name = decorator.func.attr
            else:
                continue

            # Check if it's a contract decorator
            if name in ("pre", "post"):
                # Get the first argument (the lambda or condition)
                if decorator.args:
                    arg = decorator.args[0]
                    if isinstance(arg, ast.Lambda):
                        # Convert lambda back to source
                        expr = ast.unparse(arg)
                        contracts.append((name, expr))

    return contracts


@pre(lambda source, file_path: len(source) >= 0 and len(file_path) > 0)
@post(lambda result: result[0] >= 0 and result[1] >= 0 and result[1] <= result[0])
def analyze_contracts_in_source(
    source: str, file_path: str
) -> tuple[int, int, list[TrivialContract]]:
    """Analyze contracts in Python source code.

    Pure function - receives source as string, no file I/O.

    Returns: (total_functions, functions_with_contracts, trivial_contracts)

    Examples:
        >>> source = '''
        ... from deal import pre, post
        ... @pre(lambda x: x > 0)
        ... def good(x): return x
        ... def no_contract(x): return x
        ... @post(lambda: True)
        ... def trivial(x): return x
        ... '''
        >>> total, with_c, trivials = analyze_contracts_in_source(source, "test.py")
        >>> total
        3
        >>> with_c
        2
        >>> len(trivials)
        1
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return (0, 0, [])

    total_functions = 0
    functions_with_contracts = 0
    trivial_contracts: list[TrivialContract] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private/dunder methods
            if node.name.startswith("_"):
                continue

            total_functions += 1
            contracts = extract_contracts_from_decorators(node)

            if contracts:
                functions_with_contracts += 1

                # Check for trivial contracts
                for contract_type, expr in contracts:
                    if is_trivial_contract(expr):
                        trivial_contracts.append(
                            TrivialContract(
                                file=file_path,
                                line=node.lineno,
                                function_name=node.name,
                                contract_type=contract_type,
                                expression=expr,
                            )
                        )

    return (total_functions, functions_with_contracts, trivial_contracts)
