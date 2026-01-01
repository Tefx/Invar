"""
Invar Runtime: Lightweight contracts for Python.

This package provides the runtime components needed for projects using Invar:
- Contract class with composable &, |, ~ operators
- @pre/@post decorators for preconditions and postconditions
- @relates for input-output relational contracts (DX-28)
- @must_use for marking return values that must be used
- @must_close for resources that require explicit cleanup
- invariant() for loop invariants

For development tools (guard, map, sig), install invar-tools instead.
"""

__version__ = "1.3.0"

from invar_runtime.contracts import (
    AllNonNegative,
    AllPositive,
    Contract,
    InRange,
    Negative,
    NonBlank,
    NonEmpty,
    NonNegative,
    NoNone,
    Percentage,
    Positive,
    Sorted,
    SortedNonEmpty,
    Unique,
    post,
    pre,
)
from invar_runtime.decorators import must_use, skip_property_test, strategy
from invar_runtime.invariant import InvariantViolation, invariant
from invar_runtime.relations import RelationViolation, relates, relates_multi, to_post_contract
from invar_runtime.resource import MustCloseViolation, ResourceWarning, is_must_close, must_close

__all__ = [
    # Contracts
    "AllNonNegative",
    "AllPositive",
    "Contract",
    "InRange",
    "Negative",
    "NoNone",
    "NonBlank",
    "NonEmpty",
    "NonNegative",
    "Percentage",
    "Positive",
    "Sorted",
    "SortedNonEmpty",
    "Unique",
    "post",
    "pre",
    # Decorators
    "must_use",
    "skip_property_test",
    "strategy",
    # Invariants
    "InvariantViolation",
    "invariant",
    # Relations (DX-28)
    "RelationViolation",
    "relates",
    "relates_multi",
    "to_post_contract",
    # Resources
    "MustCloseViolation",
    "ResourceWarning",
    "is_must_close",
    "must_close",
]
