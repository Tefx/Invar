"""
Template transformation helpers.

Core module: pure logic for template content transformations.
"""

from __future__ import annotations

from deal import post


@post(lambda result: "`" not in result or "\\`" in result)
@post(lambda result: "${" not in result or "\\${" in result)
def escape_for_js_template(content: str) -> str:
    """
    Escape content for JavaScript template literal.

    Escapes backticks and ${} sequences that would be interpreted
    by JavaScript template literals.

    >>> escape_for_js_template("Hello `world`")
    'Hello \\\\`world\\\\`'
    >>> escape_for_js_template("Value: ${x}")
    'Value: \\\\${x}'
    >>> escape_for_js_template("Normal text")
    'Normal text'
    """
    # Escape backticks
    content = content.replace("`", "\\`")
    # Escape ${} template expressions
    content = content.replace("${", "\\${")
    return content
