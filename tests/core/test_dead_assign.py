from __future__ import annotations

from invar.core.dead_assign import check_dead_assigns
from invar.core.models import FileInfo, RuleConfig


def _check_source(source: str) -> list:
    file_info = FileInfo(
        path="src/invar/core/sample.py", lines=len(source.splitlines()), source=source
    )
    return check_dead_assigns([file_info], RuleConfig())


def test_detects_simple_dead_assignment() -> None:
    source = """
def f():
    value = 1
    return 0
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "value" in violations[0].message


def test_augassign_reads_previous_value() -> None:
    source = """
def f():
    total = 1
    total += 2
    return total
"""
    violations = _check_source(source)
    assert violations == []


def test_reports_unpacking_name_that_is_never_read() -> None:
    source = """
def f():
    a, b = (1, 2)
    return a
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "b" in violations[0].message


def test_loop_target_is_tracked() -> None:
    source = """
def f(items):
    for item in items:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "item" in violations[0].message


def test_variable_used_in_nested_scope_is_not_reported() -> None:
    source = """
def f():
    value = 1
    def nested():
        return value
    return nested()
"""
    violations = _check_source(source)
    assert violations == []


def test_with_target_is_tracked() -> None:
    source = """
def f(ctx):
    with ctx as handle:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "handle" in violations[0].message


def test_except_var_is_tracked() -> None:
    source = """
def f():
    try:
        raise ValueError("x")
    except ValueError as err:
        return 1
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "err" in violations[0].message


def test_exclusions_for_underscore_and_inline_allow() -> None:
    source = """
def f():
    _tmp = 1
    x = 2  # @invar:allow dead_assign: intentional scratch
    return 0
"""
    violations = _check_source(source)
    assert violations == []


def test_conditional_overwrite_is_not_reported_false_positive() -> None:
    source = """
def f(flag: bool):
    value = 1
    if flag:
        value = 2
    return value
"""
    violations = _check_source(source)
    assert violations == []


def test_loop_default_overwrite_is_not_reported_false_positive() -> None:
    source = """
def f(items):
    result = 0
    for item in items:
        result = item
    return result
"""
    violations = _check_source(source)
    assert violations == []
