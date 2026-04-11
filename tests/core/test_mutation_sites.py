"""Tests for mutation_sites core module.

DX-97: Mutation-site engine for identifying and rewriting mutation candidates.
"""

from __future__ import annotations

import pytest

from invar.core.models import FileInfo, RuleConfig


class TestV1OperatorContract:
    """B2 regression: is_v1_operator must have a meaningful (non-vacuous) contract.

    The previous contract `result is True if result else result is False` was
    vacuous — every boolean value satisfies it. The fix uses
    `result == (self.operator in V1_OPERATORS)` which actually constrains
    the method to return the membership test result.
    """

    def test_is_v1_operator_true_for_known_operator(self) -> None:
        """V1 operators return True."""
        from invar.core.mutation_sites import MutationCandidate, V1_OPERATORS

        for op in V1_OPERATORS:
            c = MutationCandidate(
                file="t.py",
                line=1,
                col_offset=0,
                operator=op,
                original_source="x + y",
                mutated_source="x - y",
            )
            assert c.is_v1_operator(), f"Expected {op} to be v1"

    def test_is_v1_operator_false_for_unknown_operator(self) -> None:
        """Non-v1 operators return False."""
        from invar.core.mutation_sites import MutationCandidate

        for non_op in ("MatMult", "Eq", "Lt", "And", "Or"):
            c = MutationCandidate(
                file="t.py",
                line=1,
                col_offset=0,
                operator=non_op,
                original_source="x + y",
                mutated_source="x - y",
            )
            assert not c.is_v1_operator(), f"Expected {non_op} to NOT be v1"


class TestMutationOperatorSet:
    """Test that only v1 operator set is collected."""

    def test_add_operator_is_candidate(self) -> None:
        """Binary Add operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Add"

    def test_sub_operator_is_candidate(self) -> None:
        """Binary Sub operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a - b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Sub"

    def test_mult_operator_is_candidate(self) -> None:
        """Binary Mult operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a * b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Mult"

    def test_div_operator_is_candidate(self) -> None:
        """Binary Div operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a / b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Div"

    def test_mod_operator_is_candidate(self) -> None:
        """Binary Mod operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a % b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Mod"

    def test_pow_operator_is_candidate(self) -> None:
        """Binary Pow operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a ** b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "Pow"

    def test_floordiv_operator_is_candidate(self) -> None:
        """Binary FloorDiv operator should be a candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a // b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == "FloorDiv"

    def test_matmult_operator_not_in_v1(self) -> None:
        """Matrix multiplication operator should NOT be in v1 set."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a @ b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        # @ operator (MatMult) is NOT in v1 operator set
        assert len(candidates) == 0

    def test_compare_operators_not_in_v1(self) -> None:
        """Comparison operators should NOT be in v1 set."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a > b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        # Comparison operators are NOT in v1 operator set
        assert len(candidates) == 0

    def test_boolop_and_or_not_in_v1(self) -> None:
        """Boolean And/Or should NOT be in v1 set."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a and b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        # BoolOp (and/or) is NOT in v1 operator set
        assert len(candidates) == 0


class TestChangedLineIntersection:
    """Test that changed-line spans are honored."""

    def test_candidates_outside_changed_lines_filtered(self) -> None:
        """Candidates outside changed-line spans should be filtered."""
        from invar.core.mutation_sites import collect_mutation_candidates

        # Line 2 has +, line 3 has -
        source = "def f(a, b):\n    return a + b\n    return a - b\n"
        file_info = FileInfo(path="test.py", lines=4, source=source)
        # Only line 2 is changed
        changed_lines = [(2, 2)]
        candidates = collect_mutation_candidates(
            [file_info], RuleConfig(), changed_lines=changed_lines
        )
        assert len(candidates) == 1
        assert candidates[0].line == 2

    def test_candidates_inside_changed_lines_kept(self) -> None:
        """Candidates inside changed-line spans should be kept."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n    return a - b\n"
        file_info = FileInfo(path="test.py", lines=4, source=source)
        # Both lines 2 and 3 are changed
        changed_lines = [(2, 3)]
        candidates = collect_mutation_candidates(
            [file_info], RuleConfig(), changed_lines=changed_lines
        )
        assert len(candidates) == 2

    def test_changed_lines_none_means_no_filtering(self) -> None:
        """None changed_lines means no filtering."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n    return a - b\n"
        file_info = FileInfo(path="test.py", lines=4, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 2

    def test_changed_lines_empty_list_means_no_filtering(self) -> None:
        """Empty list changed_lines means no filtering."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n    return a - b\n"
        file_info = FileInfo(path="test.py", lines=4, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=[])
        assert len(candidates) == 2


class TestStableCandidateIdentity:
    """Test that candidate identity is stable for deferred reporting."""

    def test_candidate_has_stable_identity(self) -> None:
        """Candidate should have stable identity data."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        c = candidates[0]
        # Stable identity fields
        assert c.file == "test.py"
        assert c.line == 2
        assert c.operator == "Add"
        assert c.original_source == "a + b"
        # Should have col_offset for precise location
        assert c.col_offset > 0

    def test_candidate_identity_consistent_across_calls(self) -> None:
        """Same source should produce same candidate identity."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b):\n    return a + b\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates1 = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        candidates2 = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates1) == 1
        assert len(candidates2) == 1
        c1 = candidates1[0]
        c2 = candidates2[0]
        # Identity should be identical
        assert c1.file == c2.file
        assert c1.line == c2.line
        assert c1.operator == c2.operator
        assert c1.original_source == c2.original_source
        assert c1.col_offset == c2.col_offset


class TestSingleSiteRewrite:
    """Test single-site source rewrite capability."""

    def test_rewrite_binary_op(self) -> None:
        """Should be able to rewrite a single binary operation."""
        from invar.core.mutation_sites import MutationCandidate, rewrite_mutation_site

        candidate = MutationCandidate(
            file="test.py",
            line=2,
            col_offset=11,
            operator="Add",
            original_source="a + b",
            mutated_source="a - b",
        )
        result = rewrite_mutation_site("def f(a, b):\n    return a + b\n", candidate)
        assert result.is_ok()
        rewritten = result.unwrap()
        assert "a - b" in rewritten
        assert "a + b" not in rewritten

    def test_rewrite_invalidates_if_source_mismatch(self) -> None:
        """Rewrite should guard against AST drift."""
        from invar.core.mutation_sites import MutationCandidate, rewrite_mutation_site

        candidate = MutationCandidate(
            file="test.py",
            line=2,
            col_offset=11,
            operator="Add",
            original_source="WRONG SOURCE",
            mutated_source="a - b",
        )
        result = rewrite_mutation_site("def f(a, b):\n    return a + b\n", candidate)
        assert result.is_err()

    def test_rewrite_preserves_context(self) -> None:
        """Rewrite should preserve surrounding code."""
        from invar.core.mutation_sites import MutationCandidate, rewrite_mutation_site

        candidate = MutationCandidate(
            file="test.py",
            line=3,
            col_offset=11,
            operator="Add",
            original_source="a + b",
            mutated_source="a - b",
        )
        result = rewrite_mutation_site(
            "def f(a, b):\n    x = 1\n    return a + b\n    y = 2\n", candidate
        )
        assert result.is_ok()
        rewritten = result.unwrap()
        # Context before and after should be preserved
        assert "x = 1" in rewritten
        assert "y = 2" in rewritten
        # Mutated version present
        assert "a - b" in rewritten


class TestV1OperatorSet:
    """Test the complete v1 operator set."""

    @pytest.mark.parametrize(
        "operator,source_tpl",
        [
            ("Add", "def f(a, b):\n    return a + b\n"),
            ("Sub", "def f(a, b):\n    return a - b\n"),
            ("Mult", "def f(a, b):\n    return a * b\n"),
            ("Div", "def f(a, b):\n    return a / b\n"),
            ("Mod", "def f(a, b):\n    return a % b\n"),
            ("Pow", "def f(a, b):\n    return a ** b\n"),
            ("FloorDiv", "def f(a, b):\n    return a // b\n"),
            ("BitAnd", "def f(a, b):\n    return a & b\n"),
            ("BitOr", "def f(a, b):\n    return a | b\n"),
            ("BitXor", "def f(a, b):\n    return a ^ b\n"),
            ("LShift", "def f(a, b):\n    return a << b\n"),
            ("RShift", "def f(a, b):\n    return a >> b\n"),
        ],
    )
    def test_v1_operator_collected(self, operator: str, source_tpl: str) -> None:
        """Each v1 operator should be collected as candidate."""
        from invar.core.mutation_sites import collect_mutation_candidates

        file_info = FileInfo(path="test.py", lines=3, source=source_tpl)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1, f"Expected {operator} to be collected"
        assert candidates[0].operator == operator


class TestOperandPreservation:
    """B1 regression: mutated_source must preserve original operand expressions.

    The mutation must replace only the operator, never substitute placeholder
    operands like 'a' or 'b' that were not in the original source.
    """

    def test_non_placeholder_operands_preserved_add(self) -> None:
        """Add→Sub must preserve real operands, not replace with a/b."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def calc():\n    return price * tax\n"
        fi = FileInfo(path="test.py", lines=2, source=source)
        candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.original_source == "price * tax"
        assert c.mutated_source == "price / tax", (
            f"Expected 'price / tax', got {c.mutated_source!r}"
        )

    @pytest.mark.parametrize(
        "source,op_name,expected_mutated",
        [
            ("def f():\n    return x + y\n", "Add", "x - y"),
            ("def f():\n    return x - y\n", "Sub", "x + y"),
            ("def f():\n    return x * y\n", "Mult", "x / y"),
            ("def f():\n    return x / y\n", "Div", "x * y"),
            ("def f():\n    return x % y\n", "Mod", "x ** y"),
            ("def f():\n    return x ** y\n", "Pow", "x % y"),
            ("def f():\n    return x // y\n", "FloorDiv", "x / y"),
            ("def f():\n    return x & y\n", "BitAnd", "x | y"),
            ("def f():\n    return x | y\n", "BitOr", "x & y"),
            ("def f():\n    return x ^ y\n", "BitXor", "x << y"),
            ("def f():\n    return x << y\n", "LShift", "x >> y"),
            ("def f():\n    return x >> y\n", "RShift", "x << y"),
        ],
    )
    def test_operand_preservation_parametrized(
        self, source: str, op_name: str, expected_mutated: str
    ) -> None:
        """Every v1 mutation preserves operands, only swaps operator."""
        from invar.core.mutation_sites import collect_mutation_candidates

        fi = FileInfo(path="test.py", lines=2, source=source)
        candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        assert candidates[0].operator == op_name
        assert candidates[0].mutated_source == expected_mutated, (
            f"{op_name}: expected {expected_mutated!r}, got {candidates[0].mutated_source!r}"
        )

    def test_complex_operand_expressions_preserved(self) -> None:
        """Operands that are sub-expressions (not just names) are preserved.

        Note: AST _node_source extracts the source span for a node without
        surrounding parentheses, so (a + b) becomes 'a + b' as the left
        operand. The key property being tested is that mutated_source uses
        the actual operand text from the source, not placeholder 'a'/'b'.
        """
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f():\n    return (a + b) * c\n"
        fi = FileInfo(path="test.py", lines=2, source=source)
        candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        # Two candidates: (a + b) and ((a + b) * c) at different nesting levels
        assert len(candidates) == 2
        # Find the Mult candidate (outer expression)
        mult_candidate = [c for c in candidates if c.operator == "Mult"][0]
        # The left operand is (a + b) → extracted as "a + b" (no parens),
        # the right is c. mutated_source should use real operands.
        assert "a + b" in mult_candidate.mutated_source, (
            f"Expected left sub-expr preserved, got {mult_candidate.mutated_source!r}"
        )
        # Must NOT contain bare placeholder 'a' alone — left is the sub-expr
        assert mult_candidate.mutated_source == "a + b / c", (
            f"Expected 'a + b / c', got {mult_candidate.mutated_source!r}"
        )

    def test_rewrite_preserves_non_ab_operands(self) -> None:
        """Rewriting with real operands produces correct source."""
        from invar.core.mutation_sites import (
            collect_mutation_candidates,
            rewrite_mutation_site,
        )

        source = "def calc():\n    return price * tax\n"
        fi = FileInfo(path="test.py", lines=2, source=source)
        candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        result = rewrite_mutation_site(source, candidates[0])
        assert result.is_ok()
        rewritten = result.unwrap()
        assert "price / tax" in rewritten, f"Expected 'price / tax' in {rewritten!r}"
        assert "price * tax" not in rewritten

    def test_no_placeholder_a_or_b_in_mutated_source(self) -> None:
        """mutated_source must never contain bare 'a' or 'b' placeholders
        when operands are longer expressions."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f():\n    return income * rate\n"
        fi = FileInfo(path="test.py", lines=2, source=source)
        candidates = collect_mutation_candidates([fi], RuleConfig(), changed_lines=None)
        assert len(candidates) == 1
        # mutated_source must use the real operands, not 'a' or 'b'
        ms = candidates[0].mutated_source
        assert ms == "income / rate", f"Expected 'income / rate', got {ms!r}"


class TestEdgeCases:
    """Test edge cases for mutation site detection."""

    def test_nested_binary_operations(self) -> None:
        """Multiple binary ops on same line should all be candidates."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b, c):\n    return a + b + c\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        # a + b + c has two Add operators
        assert len(candidates) == 2

    def test_binary_op_in_complex_expression(self) -> None:
        """Binary ops in complex expressions should be detected."""
        from invar.core.mutation_sites import collect_mutation_candidates

        source = "def f(a, b, c):\n    return (a + b) * c\n"
        file_info = FileInfo(path="test.py", lines=3, source=source)
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        # (a + b) * c has Add and Mult
        assert len(candidates) == 2
        operators = {c.operator for c in candidates}
        assert operators == {"Add", "Mult"}

    def test_invalid_source_gracefully_handled(self) -> None:
        """Invalid source should be handled gracefully."""
        from invar.core.mutation_sites import collect_mutation_candidates

        file_info = FileInfo(path="test.py", lines=1, source="invalid python {{{{")
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert candidates == []

    def test_empty_source(self) -> None:
        """Empty source should return no candidates."""
        from invar.core.mutation_sites import collect_mutation_candidates

        file_info = FileInfo(path="test.py", lines=0, source="")
        candidates = collect_mutation_candidates([file_info], RuleConfig(), changed_lines=None)
        assert candidates == []
