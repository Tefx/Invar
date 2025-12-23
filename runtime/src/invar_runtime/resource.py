"""
Resource management decorators for Invar.

Provides @must_close for marking classes that require explicit cleanup.
Inspired by Move language's resource semantics.
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class ResourceWarning(UserWarning):
    """Warning raised when a resource may not be properly closed."""

    pass


class MustCloseViolation(Exception):
    """Raised when a @must_close resource is not properly managed."""

    pass


def must_close(cls: type[T]) -> type[T]:
    """
    Mark a class as a resource that must be explicitly closed.

    The decorated class should have a `close()` method. The decorator:
    1. Adds __invar_must_close__ marker for Guard detection
    2. Adds context manager protocol if not present

    Examples:
        >>> @must_close
        ... class TempFile:
        ...     def __init__(self, path: str):
        ...         self.path = path
        ...         self.closed = False
        ...     def write(self, data: str) -> None:
        ...         if self.closed:
        ...             raise ValueError("File is closed")
        ...     def close(self) -> None:
        ...         self.closed = True

        >>> # Preferred: use as context manager
        >>> with TempFile("test.txt") as f:
        ...     f.write("hello")
        >>> f.closed
        True

        >>> # Also works: explicit close
        >>> f2 = TempFile("test2.txt")
        >>> f2.write("world")
        >>> f2.close()
        >>> f2.closed
        True
    """
    # Mark for Guard detection
    cls.__invar_must_close__ = True  # type: ignore[attr-defined]

    # Add context manager protocol if not present
    if not hasattr(cls, "__enter__"):

        def __enter__(self: Any) -> Any:
            return self

        cls.__enter__ = __enter__  # type: ignore[attr-defined]

    if not hasattr(cls, "__exit__"):

        def __exit__(self: Any, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            if hasattr(self, "close") and callable(self.close):
                self.close()

        cls.__exit__ = __exit__  # type: ignore[attr-defined]

    return cls


def is_must_close(cls_or_obj: Any) -> bool:
    """
    Check if a class or instance is marked with @must_close.

    >>> @must_close
    ... class Resource:
    ...     def close(self): pass
    >>> is_must_close(Resource)
    True
    >>> is_must_close(Resource())
    True
    >>> class Plain: pass
    >>> is_must_close(Plain)
    False
    """
    if isinstance(cls_or_obj, type):
        return getattr(cls_or_obj, "__invar_must_close__", False)
    return getattr(type(cls_or_obj), "__invar_must_close__", False)
