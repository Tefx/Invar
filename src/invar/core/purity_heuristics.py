"""
Purity heuristics for unknown functions.

Core module: analyzes function metadata to guess purity.
Layer 2 of Multi-Layer Purity Detection (B4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from deal import post

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


@post(lambda result: len(result) == 2 and all(x >= 0 for x in result))  # Scores are non-negative
def _analyze_name_patterns(func_name: str, hints: list[str]) -> tuple[int, int]:
    """Analyze function name for purity hints. Returns (impure_score, pure_score).

    >>> h = []
    >>> _analyze_name_patterns("read_file", h)
    (2, 0)
    >>> len(h) > 0
    True
    """
    impure, pure = 0, 0
    for pattern in IMPURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name: {pattern}")
            impure += 2
    for pattern in PURE_NAME_PATTERNS:
        if re.search(pattern, func_name, re.IGNORECASE):
            hints.append(f"Name suggests pure: {pattern}")
            pure += 1
    return impure, pure


@post(lambda result: len(result) == 2 and all(x >= 0 for x in result))  # Scores are non-negative
def _analyze_signature(signature: str | None, hints: list[str]) -> tuple[int, int]:
    """Analyze signature for purity hints. Returns (impure_score, pure_score).

    >>> h = []
    >>> _analyze_signature("(path: str) -> None", h)
    (3, 0)
    """
    if not signature:
        return 0, 0
    impure, pure = 0, 0
    if "-> None" in signature:
        hints.append("Returns None (side effect?)")
        impure += 1
    if re.search(r"path|file", signature, re.IGNORECASE):
        hints.append("Has path/file parameter")
        impure += 2
    if "->" in signature and "None" not in signature:
        hints.append("Returns value")
        pure += 1
    return impure, pure


@post(lambda result: result >= 0)  # Impure score is non-negative
def _analyze_docstring(docstring: str | None, hints: list[str]) -> int:
    """Analyze docstring for purity hints. Returns impure_score.

    >>> h = []
    >>> _analyze_docstring("Reads from file system.", h)
    1
    """
    if not docstring:
        return 0
    doc_lower = docstring.lower()
    for keyword in IMPURE_DOC_KEYWORDS:
        if keyword in doc_lower:
            hints.append(f"Docstring: '{keyword}'")
            return 1
    return 0


@post(lambda result: 0.0 <= result.confidence <= 1.0)  # Confidence in [0, 1]
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

    name_impure, name_pure = _analyze_name_patterns(func_name, hints)
    sig_impure, sig_pure = _analyze_signature(signature, hints)
    doc_impure = _analyze_docstring(docstring, hints)

    impure_score = name_impure + sig_impure + doc_impure
    pure_score = name_pure + sig_pure

    total = impure_score + pure_score
    if total == 0:
        return HeuristicResult(likely_pure=True, confidence=0.5, hints=["No indicators"])

    likely_pure = pure_score >= impure_score
    confidence = min(0.9, 0.5 + abs(pure_score - impure_score) / (total + 1) * 0.4)

    return HeuristicResult(likely_pure, confidence, hints)
