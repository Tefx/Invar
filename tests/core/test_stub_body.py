"""Tests for stub_body placeholder detection."""

from __future__ import annotations

from invar.core.models import FileInfo, RuleConfig
from invar.core.stub_body import check_stub_bodies


def _violation_count(source: str) -> int:
    file_info = FileInfo(path="src/example.py", lines=len(source.splitlines()), source=source)
    return len(check_stub_bodies([file_info], RuleConfig()))


def test_detects_pass_only_body() -> None:
    source = "def f():\n    pass\n"
    assert _violation_count(source) == 1


def test_detects_raise_not_implemented_error_body() -> None:
    source = "def f():\n    raise NotImplementedError('todo')\n"
    assert _violation_count(source) == 1


def test_detects_ellipsis_body() -> None:
    source = "def f():\n    ...\n"
    assert _violation_count(source) == 1


def test_detects_bare_docstring_only_body() -> None:
    source = 'def f():\n    """placeholder"""\n'
    assert _violation_count(source) == 1


def test_exempts_abstract_method() -> None:
    source = """
from abc import abstractmethod

class Base:
    @abstractmethod
    def run(self) -> int:
        pass
"""
    assert _violation_count(source) == 0


def test_exempts_protocol_method() -> None:
    source = """
from typing import Protocol

class Runner(Protocol):
    def run(self) -> int:
        ...
"""
    assert _violation_count(source) == 0


def test_detects_nested_function_placeholder_body() -> None:
    source = """
def outer() -> int:
    def inner() -> int:
        ...
    return 1
"""
    assert _violation_count(source) == 1


def test_detects_class_method_placeholder_body() -> None:
    source = """
class Service:
    def run(self) -> int:
        ...
"""
    assert _violation_count(source) == 1


def test_exempts_inherited_protocol_method() -> None:
    source = """
from typing import Protocol

class Base(Protocol):
    def run(self) -> int:
        ...

class Child(Base):
    def run(self) -> int:
        ...
"""
    assert _violation_count(source) == 0
