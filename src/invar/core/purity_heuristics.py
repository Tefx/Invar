"""
Purity heuristics for unknown functions.

Core module: analyzes function metadata to guess purity.
Layer 2 of Multi-Layer Purity Detection (B4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from deal import post, pre

# Name patterns suggesting impurity
IMPURE_NAME_PATTERNS = [
    r"^read_",
    r"^write_",
    r"^save_",
    r"^load_",
    r"^fetch_",
    r"^send_",
    r"^delete_",
    r"^update_",
    r"^connect_",
    r"^open_",
    r"^close_",
    r"^print_",
    r"^log_",
    r"_to_file$",
    r"_to_disk$",
    r"_to_db$",
]

# Name patterns suggesting purity
PURE_NAME_PATTERNS = [
    r"^calculate_",
    r"^compute_",
    r"^parse_",
    r"^validate_",
    r"^transform_",
    r"^convert_",
    r"^is_",
    r"^has_",
    r"^get_",
    r"^from_",
    r"^to_",
]

# Docstring keywords suggesting impurity
IMPURE_DOC_KEYWORDS = [
    "writes to",
    "reads from",
    "saves",
    "loads",
    "modifies",
    "mutates",
    "side effect",
    "file",
    "disk",
    "database",
    "network",
    "sends",
    "receives",
    "connects",
]


@dataclass
class HeuristicResult:
    """Result of heuristic purity analysis."""

    likely_pure: bool
    confidence: float  # 0.0 - 1.0
    hints: list[str]


@pre(lambda func_name, signature=None, docstring=None: isinstance(func_name, str))
@post(lambda result: isinstance(result, HeuristicResult))
def analyze_purity_heuristic(
    func_name: str,
    signature: str | None = None,
    docstring: str | None = None,
) -> HeuristicResult:
    """
    Guess purity based on heuristics.

    >>> r = analyze_purity_heuristic("read_csv")
    >>> r.likely_pure
    False
    >>> r.confidence > 0.5
    True

    >>> r = analyze_purity_heuristic("calculate_sum")
    >>> r.likely_pure
    True

    >>> r = analyze_purity_heuristic("process_data")
    >>> r.confidence < 0.6
    True
    """
    hints: list[str] = []
    impure_score = 0
    pure_score = 0

    # Check impure name patterns
    for pattern in IMPURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name: {pattern}")
            impure_score += 2

    # Check pure name patterns
    for pattern in PURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name suggests pure: {pattern}")
            pure_score += 1

    # Check signature if provided
    if signature:
        # Returns None with no args → likely side effect
        if "-> None" in signature:
            hints.append("Returns None (side effect?)")
            impure_score += 1
        # Has path/file parameter
        if re.search(r"path|file", signature, re.IGNORECASE):
            hints.append("Has path/file parameter")
            impure_score += 2
        # Returns non-None → more likely pure
        if "->" in signature and "None" not in signature:
            hints.append("Returns value")
            pure_score += 1

    # Check docstring if provided
    if docstring:
        doc_lower = docstring.lower()
        for keyword in IMPURE_DOC_KEYWORDS:
            if keyword in doc_lower:
                hints.append(f"Docstring: '{keyword}'")
                impure_score += 1
                break  # Only count once

    # Calculate result
    total = impure_score + pure_score
    if total == 0:
        return HeuristicResult(likely_pure=True, confidence=0.5, hints=["No indicators"])

    likely_pure = pure_score >= impure_score
    confidence = min(0.9, 0.5 + abs(pure_score - impure_score) / (total + 1) * 0.4)

    return HeuristicResult(likely_pure, confidence, hints)
