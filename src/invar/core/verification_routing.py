"""
Verification routing logic for smart tool selection.

DX-22: Automatically routes code to CrossHair or Hypothesis based on imports.
Core module: Pure logic, no I/O.
"""

from __future__ import annotations

import re
from enum import Enum

from deal import post


class VerificationTool(Enum):
    """Verification tool selection."""

    CROSSHAIR = "crosshair"
    HYPOTHESIS = "hypothesis"
    SKIP = "skip"


# C extensions that CrossHair cannot symbolically execute
# These libraries use native code that breaks symbolic execution
CROSSHAIR_INCOMPATIBLE_LIBS = frozenset(
    [
        # Scientific computing (C/Fortran extensions)
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "scikit-learn",
        # Deep learning (CUDA/C++ backends)
        "torch",
        "tensorflow",
        "keras",
        "jax",
        # Image processing (C extensions)
        "cv2",
        "PIL",
        "pillow",
        "skimage",
        # Network I/O (non-deterministic)
        "requests",
        "aiohttp",
        "httpx",
        "urllib3",
        # System calls (side effects)
        "subprocess",
        "multiprocessing",
        # Database I/O
        "sqlalchemy",
        "psycopg2",
        "pymongo",
    ]
)

# Regex pattern to detect imports
# Matches: import numpy, from numpy import, import numpy as np
_IMPORT_PATTERN = re.compile(
    r"^\s*(?:import\s+(\w+)|from\s+(\w+)(?:\.\w+)*\s+import)",
    re.MULTILINE,
)


# @invar:allow missing_contract: Boolean predicate, empty string returns False
def has_incompatible_imports(source: str) -> bool:
    """
    Check if source contains imports incompatible with CrossHair.

    DX-22: Detects C extension libraries that cannot be symbolically executed.
    Used to route code directly to Hypothesis instead of wasting time on CrossHair.

    Examples:
        >>> has_incompatible_imports("import numpy as np")
        True
        >>> has_incompatible_imports("from pandas import DataFrame")
        True
        >>> has_incompatible_imports("from pathlib import Path")
        False
        >>> has_incompatible_imports("import json")
        False
        >>> has_incompatible_imports("from sklearn.model_selection import train_test_split")
        True
        >>> has_incompatible_imports("import torch.nn as nn")
        True
        >>> has_incompatible_imports("")
        False
    """
    # Early return for empty/whitespace-only strings (avoids regex edge cases)
    if not source or not source.strip():
        return False
    for match in _IMPORT_PATTERN.finditer(source):
        lib = match.group(1) or match.group(2)
        if lib and lib.lower() in CROSSHAIR_INCOMPATIBLE_LIBS:
            return True
    return False


@post(lambda result: all(lib in CROSSHAIR_INCOMPATIBLE_LIBS for lib in result))
def get_incompatible_imports(source: str) -> set[str]:
    """
    Get the set of incompatible libraries imported in source.

    Examples:
        >>> sorted(get_incompatible_imports("import numpy\\nfrom pandas import DataFrame"))
        ['numpy', 'pandas']
        >>> get_incompatible_imports("import json")
        set()
        >>> sorted(get_incompatible_imports("import torch\\nimport tensorflow"))
        ['tensorflow', 'torch']
        >>> get_incompatible_imports("")
        set()
    """
    # Early return for empty/whitespace-only strings (avoids regex edge cases)
    if not source or not source.strip():
        return set()
    incompatible: set[str] = set()
    for match in _IMPORT_PATTERN.finditer(source):
        lib = match.group(1) or match.group(2)
        if lib and lib.lower() in CROSSHAIR_INCOMPATIBLE_LIBS:
            incompatible.add(lib.lower())
    return incompatible


@post(lambda result: result in VerificationTool)  # Returns valid enum member
def select_verification_tool(source: str, has_contracts: bool) -> VerificationTool:
    """
    Select the appropriate verification tool for a source file.

    DX-22 Smart Routing:
    - No contracts -> SKIP (nothing to verify)
    - Has C extensions -> HYPOTHESIS (CrossHair will fail)
    - Pure Python with contracts -> CROSSHAIR (can prove correctness)

    Examples:
        >>> select_verification_tool("def foo(): pass", has_contracts=False)
        <VerificationTool.SKIP: 'skip'>
        >>> select_verification_tool("import numpy\\n@pre(lambda x: x > 0)\\ndef foo(x): pass", has_contracts=True)
        <VerificationTool.HYPOTHESIS: 'hypothesis'>
        >>> select_verification_tool("@pre(lambda x: x > 0)\\ndef foo(x): pass", has_contracts=True)
        <VerificationTool.CROSSHAIR: 'crosshair'>
        >>> select_verification_tool("", has_contracts=False)
        <VerificationTool.SKIP: 'skip'>
        >>> select_verification_tool("", has_contracts=True)
        <VerificationTool.CROSSHAIR: 'crosshair'>
    """
    if not has_contracts:
        return VerificationTool.SKIP

    if has_incompatible_imports(source):
        return VerificationTool.HYPOTHESIS

    return VerificationTool.CROSSHAIR
