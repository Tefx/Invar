"""
Invar Tools: AI-native software engineering framework.

Trade structure for safety. The goal is not to make AI simpler,
but to make AI output more reliable.

This package provides development tools (guard, map, sig).
For runtime contracts only, use invar-runtime instead.
"""

__version__ = "1.0.0"
__protocol_version__ = "5.0"  # Protocol/spec version (separate from package version)

# Re-export from invar-runtime for backwards compatibility
from invar_runtime import (
    AllNonNegative,
    AllPositive,
    Contract,
    InRange,
    InvariantViolation,
    MustCloseViolation,
    Negative,
    NonBlank,
    NonEmpty,
    NonNegative,
    NoNone,
    Percentage,
    Positive,
    ResourceWarning,
    Sorted,
    SortedNonEmpty,
    Unique,
    invariant,
    is_must_close,
    must_close,
    must_use,
    post,
    pre,
    skip_property_test,
    strategy,
)

__all__ = [
    "AllNonNegative",
    "AllPositive",
    "Contract",
    "InRange",
    "InvariantViolation",
    "MustCloseViolation",
    "Negative",
    "NoNone",
    "NonBlank",
    "NonEmpty",
    "NonNegative",
    "Percentage",
    "Positive",
    "ResourceWarning",
    "Sorted",
    "SortedNonEmpty",
    "Unique",
    "invariant",
    "is_must_close",
    "must_close",
    "must_use",
    "post",
    "pre",
    "skip_property_test",
    "strategy",
]
