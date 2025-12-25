"""
Loop invariant support for Invar.

Provides runtime-checked loop invariants inspired by Dafny.
Checking controlled by INVAR_CHECK environment variable (default: ON).

MINOR-10: Environment variable is read at import time for performance.
To change behavior, restart the Python process or manually set _INVAR_CHECK.
"""

from __future__ import annotations

import os


class InvariantViolation(Exception):
    """Raised when a loop invariant is violated."""

    pass


# Read once at module load time - effectively a constant
_INVAR_CHECK = os.environ.get("INVAR_CHECK", "1") == "1"


# @invar:allow entry_point_too_thick: False positive - .get() matches router.get pattern
def invariant(condition: bool, message: str = "") -> None:
    """
    Assert loop invariant. Checked at runtime when INVAR_CHECK=1.

    Place at the START of loop body to check condition each iteration.
    Invariants document what must remain true throughout loop execution.

    Args:
        condition: Boolean condition that must hold
        message: Optional message describing the invariant

    Raises:
        InvariantViolation: When condition is False and INVAR_CHECK=1

    Examples:
        >>> invariant(True)  # OK

        >>> invariant(True, "x is positive")  # OK with message

        >>> try:
        ...     invariant(False, "x must be positive")
        ... except InvariantViolation as e:
        ...     print(str(e))
        Loop invariant violated: x must be positive

    Typical usage in a binary search:

        while lo < hi:
            invariant(0 <= lo <= hi <= len(arr))
            invariant(target not in arr[:lo])  # Already searched
            ...
    """
    if _INVAR_CHECK and not condition:
        msg = f"Loop invariant violated: {message}" if message else "Loop invariant violated"
        raise InvariantViolation(msg)
