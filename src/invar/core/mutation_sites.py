"""Pure Core mutation-site engine for DX-97.

Collects mutation candidates for the v1 operator set and provides single-site
source rewrite with guards against invalid AST drift.

Core module: no I/O imports. Changed-line spans are supplied by Shell layer.

DX-97: Mutation-site engine foundations.
"""

from __future__ import annotations

import ast
from typing import NamedTuple

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig

# V1 operator set: arithmetic and bitwise binary operators
V1_OPERATORS: frozenset[str] = frozenset(
    [
        "Add",  # +
        "Sub",  # -
        "Mult",  # *
        "Div",  # /
        "Mod",  # %
        "Pow",  # **
        "FloorDiv",  # //
        "BitAnd",  # &
        "BitOr",  # |
        "BitXor",  # ^
        "LShift",  # <<
        "RShift",  # >>
    ]
)


class MutationCandidate(NamedTuple):
    """A single mutation candidate site.

    Identity is stable: file, line, col_offset, operator, original_source.
    This allows deferred reporting without re-parsing.

    Examples:
        >>> c = MutationCandidate(file="foo.py", line=10, col_offset=4,
        ...                        operator="Add", original_source="x + y",
        ...                        mutated_source="x - y")
        >>> c.operator
        'Add'
        >>> c.file
        'foo.py'
    """

    file: str
    line: int
    col_offset: int
    operator: str
    original_source: str
    mutated_source: str

    @post(lambda result: isinstance(result, bool))
    def is_v1_operator(self) -> bool:
        """Check if this candidate's operator is in v1 set.

        Examples:
            >>> c = MutationCandidate(file="a.py", line=1, col_offset=0,
            ...                        operator="Add", original_source="x + y",
            ...                        mutated_source="x - y")
            >>> c.is_v1_operator()
            True
            >>> c._replace(operator="MatMult").is_v1_operator()
            False
        """
        return self.operator in V1_OPERATORS


class RewriteResult(NamedTuple):
    """Result of a rewrite operation.

    Examples:
        >>> ok = RewriteResult(ok=True, source="def f():\\n    return 1\\n")
        >>> ok.is_ok()
        True
        >>> err = RewriteResult(ok=False, source="source mismatch: expected 'x + y' but found 'x - y'")
        >>> err.is_err()
        True
    """

    ok: bool
    source: str

    @post(lambda result: isinstance(result, bool))
    def is_ok(self) -> bool:
        """Return True if rewrite succeeded.

        Examples:
            >>> RewriteResult(ok=True, source="x=1").is_ok()
            True
            >>> RewriteResult(ok=False, source="error").is_ok()
            False
        """
        return self.ok

    @post(lambda result: isinstance(result, bool))
    def is_err(self) -> bool:
        """Return True if rewrite failed.

        Examples:
            >>> RewriteResult(ok=True, source="x=1").is_err()
            False
            >>> RewriteResult(ok=False, source="error").is_err()
            True
        """
        return not self.ok

    @post(lambda result: isinstance(result, str) and len(result) > 0)
    def unwrap(self) -> str:
        """Unwrap the source if OK, raise if error.

        Examples:
            >>> r = RewriteResult(ok=True, source="mutated code")
            >>> r.unwrap()
            'mutated code'
            >>> r_err = RewriteResult(ok=False, source="source mismatch")
            >>> r_err.unwrap()  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
                ...
            ValueError: source mismatch
        """
        if not self.ok:
            raise ValueError(self.source)
        return self.source


@post(lambda result: isinstance(result, bool))
def _is_v1_binop(node: ast.AST) -> bool:
    """Check if AST node is a v1 binary operator."""
    return isinstance(node, ast.BinOp) and type(node.op).__name__ in V1_OPERATORS


@post(lambda result: isinstance(result, str))
def _node_source(node: ast.AST, source: str) -> str:
    """Extract source text for an AST node."""
    if hasattr(node, "lineno") and hasattr(node, "col_offset"):
        end_line = getattr(node, "end_lineno", node.lineno)
        end_col = getattr(node, "end_col_offset", node.col_offset)
        lines = source.splitlines()
        if node.lineno <= len(lines) and end_line <= len(lines):
            if node.lineno == end_line:
                return lines[node.lineno - 1][node.col_offset : end_col]
            else:
                result = lines[node.lineno - 1][node.col_offset :]
                for line_num in range(node.lineno, end_line):
                    result += "\n" + lines[line_num]
                result += "\n" + lines[end_line - 1][:end_col]
                return result
    return ""


# Mutation mapping for v1 operators: maps operator class name to replacement
# operator class name. Operands are preserved from original source.
_BINOP_MUTATION_MAP: dict[str, str] = {
    "Add": "Sub",
    "Sub": "Add",
    "Mult": "Div",
    "Div": "Mult",
    "Mod": "Pow",
    "Pow": "Mod",
    "FloorDiv": "Div",
    "BitAnd": "BitOr",
    "BitOr": "BitAnd",
    "BitXor": "LShift",
    "LShift": "RShift",
    "RShift": "LShift",
}

# AST operator class → source token mapping
_BINOP_TOKEN_MAP: dict[str, str] = {
    "Add": "+",
    "Sub": "-",
    "Mult": "*",
    "Div": "/",
    "Mod": "%",
    "Pow": "**",
    "FloorDiv": "//",
    "BitAnd": "&",
    "BitOr": "|",
    "BitXor": "^",
    "LShift": "<<",
    "RShift": ">>",
}


@pre(
    lambda node, file, source: (
        isinstance(node, ast.BinOp)
        and hasattr(node, "left")
        and hasattr(node, "op")
        and hasattr(node, "right")
        and isinstance(file, str)
        and isinstance(source, str)
    )
)
@post(lambda result: isinstance(result, list))
def _collect_binop_candidates(
    node: ast.BinOp,
    file: str,
    source: str,
) -> list[MutationCandidate]:
    """Collect mutation candidate from a binary operation node.

    Preserves original operand expressions in mutated_source, replacing
    only the operator token. For example, ``price * tax`` becomes
    ``price / tax`` instead of the placeholder ``a / b``.
    """
    candidates: list[MutationCandidate] = []
    op_name = type(node.op).__name__

    if op_name not in V1_OPERATORS:
        return candidates

    original = _node_source(node, source)
    if not original:
        return candidates

    # Build mutated_source preserving original operand expressions
    target_op_name = _BINOP_MUTATION_MAP.get(op_name)
    if target_op_name is None:
        return candidates

    target_token = _BINOP_TOKEN_MAP.get(target_op_name, "")
    if not target_token:
        return candidates

    left_source = _node_source(node.left, source)
    right_source = _node_source(node.right, source)
    if not left_source or not right_source:
        return candidates

    mutated = f"{left_source} {target_token} {right_source}"
    candidates.append(
        MutationCandidate(
            file=file,
            line=node.lineno,
            col_offset=node.col_offset,
            operator=op_name,
            original_source=original,
            mutated_source=mutated,
        )
    )
    return candidates


@post(lambda result: isinstance(result, list))
def _walk_for_binops(node: ast.AST, file: str, source: str) -> list[MutationCandidate]:
    """Walk AST tree collecting v1 binary operation candidates."""
    candidates: list[MutationCandidate] = []

    for child in ast.walk(node):
        if isinstance(child, ast.BinOp):
            candidates.extend(_collect_binop_candidates(child, file, source))

    return candidates


@pre(
    lambda file_infos, config, changed_lines: (
        all(isinstance(fi, FileInfo) for fi in file_infos)
        and isinstance(config, RuleConfig)
        and (changed_lines is None or isinstance(changed_lines, list))
    )
)
@post(
    lambda result: all(
        isinstance(c, MutationCandidate)
        and c.file
        and c.line > 0
        and c.col_offset >= 0
        and c.operator in V1_OPERATORS
        and c.original_source
        for c in result
    )
)
def collect_mutation_candidates(
    file_infos: list[FileInfo],
    config: RuleConfig,
    changed_lines: list[tuple[int, int]] | None,
) -> list[MutationCandidate]:
    """Collect mutation candidates for v1 operator set.

    Only collects candidates for binary arithmetic and bitwise operators.
    Honors changed-line spans when provided (None means no filtering).

    Args:
        file_infos: List of FileInfo objects with source code
        config: RuleConfig (unused but required for interface consistency)
        changed_lines: Optional list of (start, end) line spans to filter candidates.
                      None means no filtering (all candidates returned).

    Returns:
        List of MutationCandidate objects with stable identity.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> source = "def f(a, b):\\n    return a + b\\n"
        >>> fi = FileInfo(path="test.py", lines=3, source=source)
        >>> candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        >>> len(candidates)
        1
        >>> candidates[0].operator
        'Add'

        >>> # Multiple operators on same line
        >>> source2 = "def f(a, b, c):\\n    return a + b + c\\n"
        >>> fi2 = FileInfo(path="test.py", lines=3, source=source2)
        >>> candidates2 = collect_mutation_candidates([fi2], RuleConfig(), changed_lines=None)
        >>> len(candidates2)
        2

        >>> # Changed lines filtering
        >>> source3 = "def f(a, b):\\n    return a + b\\n    return a - b\\n"
        >>> fi3 = FileInfo(path="test.py", lines=4, source=source3)
        >>> candidates3 = collect_mutation_candidates([fi3], RuleConfig(), changed_lines=[(2, 2)])
        >>> len(candidates3)
        1
        >>> candidates3[0].line
        2
    """
    del config  # V1 operator set is fixed; config reserved for future extension

    all_candidates: list[MutationCandidate] = []

    for file_info in file_infos:
        source = file_info.source or ""
        if not source:
            continue

        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue

        file_candidates = _walk_for_binops(tree, file_info.path, source)
        all_candidates.extend(file_candidates)

    # Filter by changed lines if provided
    if changed_lines:
        filtered: list[MutationCandidate] = []
        for candidate in all_candidates:
            for start, end in changed_lines:
                if start <= candidate.line <= end:
                    filtered.append(candidate)
                    break
        return filtered

    return all_candidates


@pre(lambda source, candidate: source is not None and candidate is not None)
@post(lambda result: result.is_ok() or result.is_err())
def rewrite_mutation_site(
    source: str,
    candidate: MutationCandidate,
) -> RewriteResult:
    """Rewrite source by applying mutation at the candidate site.

    Guards against AST drift by verifying the source at candidate location
    matches the original_source exactly before applying mutation.

    Args:
        source: Original source code
        candidate: Mutation candidate with original_source to match

    Returns:
        RewriteResult with ok=True and mutated source, or ok=False with error message.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> source = "def f(a, b):\\n    return a + b\\n"
        >>> fi = FileInfo(path="test.py", lines=3, source=source)
        >>> candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        >>> result = rewrite_mutation_site(source, candidates[0])
        >>> result.is_ok()
        True
        >>> "a - b" in result.unwrap()
        True

        >>> # Source mismatch should fail gracefully
        >>> bad_candidate = MutationCandidate(file="test.py", line=2, col_offset=11,
        ...                                   operator="Add", original_source="WRONG",
        ...                                   mutated_source="a - b")
        >>> result2 = rewrite_mutation_site(source, bad_candidate)
        >>> result2.is_err()
        True
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return RewriteResult(ok=False, source="parse error: invalid source")

    # Find the target node
    target_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            if node.lineno == candidate.line and node.col_offset == candidate.col_offset:
                target_found = True
                actual_source = _node_source(node, source)
                if actual_source != candidate.original_source:
                    return RewriteResult(
                        ok=False,
                        source=f"source mismatch: expected {candidate.original_source!r} but found {actual_source!r}",
                    )
                # Apply the mutation
                lines = source.splitlines(True)
                if node.lineno <= len(lines):
                    line_start = node.col_offset
                    line_end = getattr(node, "end_col_offset", len(lines[node.lineno - 1]))
                    old_line = lines[node.lineno - 1]
                    new_line = (
                        old_line[:line_start] + candidate.mutated_source + old_line[line_end:]
                    )
                    lines[node.lineno - 1] = new_line
                    return RewriteResult(ok=True, source="".join(lines))
                return RewriteResult(ok=False, source="line out of range")

    if not target_found:
        return RewriteResult(ok=False, source="candidate site not found in source")
    return RewriteResult(ok=False, source="internal error")
