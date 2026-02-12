"""JSON output helpers for agent/CLI modes.

Design constraint (issue report): output must be strict JSON (RFC 8259) and must
not be wrapped by Rich console formatting, which can insert real newlines into
string literals and break json.loads().
"""

from __future__ import annotations

import json
import sys
from typing import Any


def write_json(obj: Any, *, indent: int | None = 2) -> None:
    """Write a JSON document to stdout without Rich wrapping.

    Args:
        obj: JSON-serializable object.
        indent: Indentation level for pretty output. Use None for compact.
    """

    sys.stdout.write(json.dumps(obj, indent=indent))
    sys.stdout.write("\n")
