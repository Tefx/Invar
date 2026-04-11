"""Tests for mutation_sites core module.

DX-97: Mutation-site engine for identifying and rewriting mutation candidates.
"""

from __future__ import annotations

import pytest

from invar.core.models import FileInfo, RuleConfig


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
