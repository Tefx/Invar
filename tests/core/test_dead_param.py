from __future__ import annotations

from invar.core.dead_param import check_dead_params
from invar.core.models import FileInfo, RuleConfig


def _check_source(source: str) -> list:
    file_info = FileInfo(
        path="src/invar/core/sample.py", lines=len(source.splitlines()), source=source
    )
    return check_dead_params([file_info], RuleConfig())


def test_detects_basic_dead_parameter() -> None:
    source = """
def add(x, y):
    return y
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "add" in violations[0].message
    assert "x" in violations[0].message


def test_self_and_cls_are_excluded() -> None:
    source = """
class Repo:
    def save(self, value):
        return value

    @classmethod
    def build(cls, value):
        return value
"""
    violations = _check_source(source)
    assert violations == []


def test_varargs_and_kwargs_are_excluded() -> None:
    source = """
def forward(*args, **kwargs):
    return call(*args, **kwargs)
"""
    violations = _check_source(source)
    assert violations == []


def test_abstractmethod_is_exempt() -> None:
    source = """
from abc import abstractmethod

class Service:
    @abstractmethod
    def execute(self, token):
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_property_is_exempt() -> None:
    source = """
class User:
    @property
    def name(self):
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_decorator_consumed_parameter_is_not_reported() -> None:
    source = """
def configure(timeout):
    @retry(wait=timeout)
    def run():
        return 1
    return run()
"""
    violations = _check_source(source)
    assert violations == []


def test_protocol_method_is_exempt() -> None:
    source = """
from typing import Protocol

class Repository(Protocol):
    def save(self, payload):
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_nested_closure_capture_counts_as_usage() -> None:
    source = """
def create_handler(token):
    def handle() -> str:
        return token
    return handle
"""
    violations = _check_source(source)
    assert violations == []


def test_signal_registered_callback_signature_is_exempt() -> None:
    source = """
import signal

def setup():
    def handle_signal(signum, frame):
        return 0
    signal.signal(signal.SIGINT, handle_signal)
"""
    violations = _check_source(source)
    assert violations == []


def test_entry_point_decorated_function_is_exempt() -> None:
    source = """
import click

@click.command()
def cli(ctx):
    return 1
"""
    violations = _check_source(source)
    assert violations == []


def test_allow_marker_suppresses_dead_param() -> None:
    source = """
# @invar:allow dead_param: framework callback signature
def callback(request):
    return 1
"""
    violations = _check_source(source)
    assert violations == []


def test_non_registrar_callback_still_reports_dead_param() -> None:
    source = """
def setup():
    def callback(request):
        return 1
    run(callback)
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "request" in violations[0].message
