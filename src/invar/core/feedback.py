"""
Feedback anonymization logic (Core).

DX-79 Phase D: Pure string transformations for privacy protection.
"""

from __future__ import annotations

import re

from deal import post, pre


@pre(lambda content: len(content) > 0)
@post(lambda result: len(result) > 0)
def anonymize_feedback_content(content: str) -> str:
    """
    Anonymize feedback content by removing identifying information.

    Removes:
    - Project names
    - File paths (absolute and relative)
    - Function/symbol names
    - Error messages
    - Email addresses
    - IP addresses
    - User home directories
    - API tokens and secrets

    Args:
        content: Original feedback content

    Returns:
        Anonymized content with sensitive data redacted

    >>> content = "**Project**: MyApp\\nFile: /Users/alice/src/app.py"
    >>> result = anonymize_feedback_content(content)
    >>> "MyApp" not in result
    True
    >>> "[redacted]" in result
    True
    >>> "/Users/alice" not in result
    True

    >>> content = "Error: Invalid token abc123def456\\nEmail: user@example.com"
    >>> result = anonymize_feedback_content(content)
    >>> "user@example.com" not in result
    True
    >>> "[email redacted]" in result
    True
    """
    # Replace project name
    content = re.sub(r"\*\*Project\*\*: .*", "**Project**: [redacted]", content)

    # Replace email addresses
    content = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b",
        "[email redacted]",
        content,
    )

    # Replace IP addresses
    content = re.sub(
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "[IP redacted]",
        content,
    )

    # Replace user home directories
    content = re.sub(r"/Users/[\w.-]+/?", "[home]/", content)
    content = re.sub(r"/home/[\w.-]+/?", "[home]/", content)
    content = re.sub(r"C:\\Users\\[\w.-]+\\?", r"[home]\\", content)

    # Replace absolute file paths (before specific replacements)
    content = re.sub(r"/[\w/.-]+\.(py|ts|js|md|json|yaml)", "[path redacted]", content)

    # Replace file paths (specific patterns)
    content = re.sub(r"File: [^\s]+", "File: [path redacted]", content, flags=re.IGNORECASE)
    content = re.sub(r"src/[\w/.-]+", "[path redacted]", content)

    # Replace API tokens and secrets (long hex/base64 strings)
    # Match 32+ character hex strings (likely tokens)
    content = re.sub(r"\b[a-fA-F0-9]{32,}\b", "[token redacted]", content)
    # Match base64-like strings (24+ chars with alphanumeric and +/=)
    content = re.sub(r"\b[A-Za-z0-9+/]{24,}={0,2}\b", "[token redacted]", content)

    # Replace function names in prose
    content = re.sub(
        r"function ['\"][\w_]+['\"]",
        "function [name redacted]",
        content,
        flags=re.IGNORECASE,
    )

    # Replace symbol references (more targeted pattern)
    # Only replace if it looks like a function call with parentheses
    content = re.sub(
        r"`([\w.]+)\([^)]*\)`",
        lambda m: "`[symbol redacted]()`" if "." in m.group(1) or "_" in m.group(1) else m.group(0),
        content,
    )

    # Replace error messages (in code blocks or after "Error:")
    content = re.sub(
        r"Error: .+",
        "Error: [message redacted]",
        content,
    )

    return content
