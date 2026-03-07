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


def test_fmcp_custom_route_request_signature_is_exempt() -> None:
    source = """
from starlette.requests import Request

class AgentServer:
    async def _handle_stream_request(self, request: Request):
        return {"ok": True}
"""
    violations = _check_source(source)
    assert violations == []


def test_returned_context_callback_signature_is_exempt() -> None:
    source = """
from typing import Any
from pydantic_ai import RunContext

def build_callback():
    async def inject_meta_callback(ctx: RunContext[Any], name: str):
        return name
    return inject_meta_callback
"""
    violations = _check_source(source)
    assert violations == []


def test_keyword_instructions_context_signature_is_exempt() -> None:
    source = """
from typing import Any

def run_agent(*, instructions):
    return instructions

def setup():
    async def get_dynamic_instructions(ctx: Any):
        return None
    return run_agent(instructions=get_dynamic_instructions)
"""
    violations = _check_source(source)
    assert violations == []


def test_except_fallback_contextmanager_signature_is_exempt() -> None:
    source = """
from contextlib import contextmanager

try:
    from prompt_toolkit.patch_stdout import patch_stdout
except ImportError:
    @contextmanager
    def patch_stdout(*, raw: bool = False):
        yield None
"""
    violations = _check_source(source)
    assert violations == []


def test_request_without_framework_annotation_is_not_exempt() -> None:
    source = """
class AgentServer:
    async def _handle_stream_request(self, request):
        return {"ok": True}
"""
    violations = _check_source(source)
    assert len(violations) == 1
    assert "request" in violations[0].message


# Regression tests for interface/protocol-shaped parameters (DX-92)
# These tests capture known false-positive patterns that should NOT trigger dead_param


def test_class_implementing_protocol_is_exempt() -> None:
    """A class that implements a Protocol should have its methods exempt."""
    source = """
from typing import Protocol

class Repository(Protocol):
    def save(self, data: str) -> None:
        ...

class ConcreteRepository:
    def save(self, data: str) -> None:
        print(data)
"""
    violations = _check_source(source)
    # The save method in ConcreteRepository uses 'data', so no violation expected
    # But the Protocol definition itself should also be exempt
    assert violations == []


def test_runtime_checkable_protocol_is_exempt() -> None:
    """A runtime_checkable Protocol should have its methods exempt."""
    source = """
from typing import Protocol, runtime_checkable

@runtime_checkable
class Comparable(Protocol):
    def __gt__(self, other: "Comparable") -> bool:
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_generic_protocol_is_exempt() -> None:
    """A generic Protocol should have its methods exempt."""
    source = """
from typing import Protocol, TypeVar

T = TypeVar("T")

class Container(Protocol[T]):
    def get(self) -> T:
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_class_inheriting_from_protocol_subclass_is_exempt() -> None:
    """A class inheriting from a subclass of Protocol should be exempt."""
    source = """
from typing import Protocol

class BaseRepository(Protocol):
    def save(self, data: str) -> None:
        ...

class ConcreteRepository(BaseRepository):
    def save(self, data: str) -> None:
        print(data)
"""
    violations = _check_source(source)
    assert violations == []


def test_class_satisfying_protocol_in_same_file_is_exempt() -> None:
    """A class that satisfies a Protocol defined in same file should be exempt.

    This is a known false-positive pattern: when a class implements a Protocol
    interface in the same file as the Protocol definition, the implementation's
    parameters should not be flagged as dead.
    """
    source = """
from typing import Protocol

class Repository(Protocol):
    def get(self, key: str) -> str: ...

class ConcreteRepository:
    def get(self, key: str) -> str:
        return key
"""
    violations = _check_source(source)
    # key is used, so no violation - but this tests the pattern
    assert violations == []


def test_class_satisfying_protocol_method_not_used_is_exempt() -> None:
    """A class implementing Protocol method that's not used should be exempt.

    This is the actual false positive: a class that implements a Protocol
    interface has a method parameter that's not used in the implementation,
    but it's part of the interface contract so shouldn't be flagged.
    """
    source = """
from typing import Protocol

class Repository(Protocol):
    def get(self, key: str) -> str: ...

class ConcreteRepository:
    def get(self, key: str) -> str:
        return "constant"
"""
    violations = _check_source(source)
    # The 'key' parameter is not used in the implementation but is part of
    # the Protocol interface contract, so it should NOT be flagged as dead
    assert violations == []


def test_subclass_of_protocol_implementation_is_exempt() -> None:
    """A subclass of a class that implements a Protocol should be exempt."""
    source = """
from typing import Protocol

class Repository(Protocol):
    def save(self, data: str) -> None: ...

class BaseRepo:
    def save(self, data: str) -> None:
        print(data)

class MyRepo(BaseRepo):
    def save(self, data: str) -> None:
        print(data.upper())
"""
    violations = _check_source(source)
    assert violations == []


def test_class_implementing_protocol_from_another_module_is_exempt() -> None:
    """A class implementing a Protocol from another module should be exempt.

    This tests when Protocol is imported - the implementation's parameters
    should not be flagged as dead since they satisfy the interface.
    """
    source = """
from typing import Protocol

# Simulating import from another module
class ExternalProtocol(Protocol):
    def fetch(self, url: str, timeout: int) -> bytes: ...

class HTTPClient:
    def fetch(self, url: str, timeout: int) -> bytes:
        return b"response"
"""
    violations = _check_source(source)
    # timeout is not used but it's part of the Protocol interface
    assert violations == []


def test_class_with_protocol_method_variadic_unused_is_exempt() -> None:
    """A class implementing Protocol with variadic params not used should be exempt."""
    source = """
from typing import Protocol

class VariadicHandler(Protocol):
    def handle(self, *args, **kwargs): ...

class Handler:
    def handle(self, *args, **kwargs):
        return "handled"
"""
    violations = _check_source(source)
    assert violations == []


def test_protocol_method_with_only_optional_params_is_exempt() -> None:
    """Protocol method with only optional params should be exempt."""
    source = """
from typing import Protocol

class OptionalHandler(Protocol):
    def process(self, data: str = "default"): ...

class Handler:
    def process(self, data: str = "default"):
        return data
"""
    violations = _check_source(source)
    assert violations == []


def test_multiple_protocol_implementations_in_same_class_is_exempt() -> None:
    """A class implementing multiple Protocols should be exempt for all methods."""
    source = """
from typing import Protocol

class Reader(Protocol):
    def read(self, path: str) -> str: ...

class Writer(Protocol):
    def write(self, path: str, content: str) -> None: ...

class FileHandler:
    def read(self, path: str) -> str:
        return "content"
    
    def write(self, path: str, content: str) -> None:
        pass
"""
    violations = _check_source(source)
    # path and content are unused but part of Protocol interface
    assert violations == []


def test_abc_abstract_method_is_exempt() -> None:
    """An abstract method in an ABC should be exempt."""
    source = """
from abc import ABC, abstractmethod

class BaseService(ABC):
    @abstractmethod
    def execute(self, request):
        pass
"""
    violations = _check_source(source)
    assert violations == []


def test_protocol_with_variadic_parameters_is_exempt() -> None:
    """Protocol methods with *args, **kwargs should be exempt."""
    source = """
from typing import Protocol

class Callable(Protocol):
    def __call__(self, *args, **kwargs):
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_class_method_on_protocol_implementation_is_exempt() -> None:
    """A classmethod on a class implementing Protocol should be exempt."""
    source = """
from typing import Protocol

class Builder(Protocol):
    @classmethod
    def build(cls, config):
        ...

class ConcreteBuilder:
    @classmethod
    def build(cls, config):
        return config
"""
    violations = _check_source(source)
    assert violations == []


def test_nested_protocol_definition_is_exempt() -> None:
    """Nested Protocol class should have its methods exempt."""
    source = """
from typing import Protocol

class Outer:
    class Inner(Protocol):
        def process(self, data):
            ...
"""
    violations = _check_source(source)
    assert violations == []


def test_protocol_method_with_multiple_parameters_is_exempt() -> None:
    """Protocol method with multiple parameters should be exempt."""
    source = """
from typing import Protocol

class Adder(Protocol):
    def add(self, x: int, y: int, *, verbose: bool = False) -> int:
        ...
"""
    violations = _check_source(source)
    assert violations == []


def test_protocol_in_multiple_inheritance_is_exempt() -> None:
    """Class with multiple inheritance including Protocol should be exempt."""
    source = """
from typing import Protocol

class Serializable(Protocol):
    def to_json(self) -> str:
        ...

class Base:
    def base_method(self):
        pass

class MyClass(Base, Serializable):
    def to_json(self) -> str:
        return "{}"
"""
    violations = _check_source(source)
    assert violations == []


def test_method_name_match_is_scoped_to_same_file_only() -> None:
    """Method name matching should only work within the same file.

    If a class in file A has a method with the same name as a Protocol method
    in file B, it should NOT be exempt - the scope is file-local only.
    """
    source = """
from typing import Protocol

class ExternalProtocol(Protocol):
    def execute(self, payload): ...

class Handler:
    def execute(self, payload):
        return "done"
"""
    violations = _check_source(source)
    # payload is not used and should be flagged since Protocol is not in same file scope
    assert len(violations) == 1
    assert "payload" in violations[0].message
