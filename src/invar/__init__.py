"""
Invar Tools: AI-native software engineering framework.

Trade structure for safety. The goal is not to make AI simpler,
but to make AI output more reliable.

This package provides development tools (guard, map, sig).
For runtime contracts only, use invar-runtime instead.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("invar-tools")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0.dev"  # Development mode fallback

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
    RelationViolation,
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
    relates,
    relates_multi,
    skip_property_test,
    strategy,
    to_post_contract,
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
    "RelationViolation",
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
    "relates",
    "relates_multi",
    "skip_property_test",
    "strategy",
    "to_post_contract",
]
