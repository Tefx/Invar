"""
CrossHair contract detection utilities.

Shell module: Extracted for file size compliance.
- DX-13: has_verifiable_contracts for contract detection
- DX-19: @crosshair_accept acknowledgment handling
"""

from __future__ import annotations


# @shell_orchestration: Contract analysis helper for CrossHair prove module
# @shell_complexity: AST traversal for contract detection
def has_verifiable_contracts(source: str) -> bool:
    """
    Check if source has verifiable contracts.

    DX-13: Hybrid detection - fast string check + AST validation.

    Args:
        source: Python source code

    Returns:
        True if file has @pre/@post contracts worth verifying
    """
    # Fast path: no contract keywords at all
    if "@pre" not in source and "@post" not in source:
        return False

    # AST validation to avoid false positives from comments/strings
    try:
        import ast

        tree = ast.parse(source)
    except SyntaxError:
        return True  # Conservative: assume has contracts

    contract_decorators = {"pre", "post"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                    # @pre(...) or @post(...)
                    if isinstance(func, ast.Name) and func.id in contract_decorators:
                        return True
                    # @deal.pre(...) or @deal.post(...)
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in contract_decorators
                    ):
                        return True

    return False


# @shell_orchestration: Acceptance criteria analysis for CrossHair prove
# @shell_complexity: AST traversal for decorator extraction
def get_crosshair_accept_reasons(source: str) -> dict[str, str]:
    """
    Extract @crosshair_accept reasons from source.

    DX-19: Returns a mapping of function_name -> reason for functions
    that have @crosshair_accept decorator.

    Args:
        source: Python source code

    Returns:
        Dict mapping function names to their accept reasons
    """
    # Fast path: no decorator keyword
    if "@crosshair_accept" not in source:
        return {}

    try:
        import ast

        tree = ast.parse(source)
    except SyntaxError:
        return {}

    reasons: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                    # @crosshair_accept("reason")
                    if isinstance(func, ast.Name) and func.id == "crosshair_accept":
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            reasons[node.name] = str(dec.args[0].value)
                    # @invar.crosshair_accept("reason")
                    if isinstance(func, ast.Attribute) and func.attr == "crosshair_accept":
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            reasons[node.name] = str(dec.args[0].value)

    return reasons


# @shell_orchestration: Counterexample parsing helper for CrossHair output
def extract_function_from_counterexample(ce: str) -> str | None:
    """
    Extract function name from CrossHair counterexample.

    DX-19: Counterexamples look like "func_name(args) (error at ...)"
    """
    # Function name is everything before the first '('
    if "(" in ce:
        return ce.split("(")[0].strip()
    return None
