"""
Invar: AI-native software engineering framework.

Trade structure for safety. The goal is not to make AI simpler,
but to make AI output more reliable.
"""

__version__ = "0.3.0"

from invar.contracts import (
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
from invar.decorators import must_use
from invar.invariant import InvariantViolation, invariant
from invar.resource import MustCloseViolation, ResourceWarning, is_must_close, must_close

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
]
