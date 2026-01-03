"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_project_dir(tmp_path: Path) -> Path:
    """Create a sample project directory for testing."""
    core_dir = tmp_path / "src" / "core"
    shell_dir = tmp_path / "src" / "shell"
    core_dir.mkdir(parents=True)
    shell_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_core_file(sample_project_dir: Path) -> Path:
    """Create a sample Core Python file."""
    core_file = sample_project_dir / "src" / "core" / "example.py"
    core_file.write_text('''"""Example Core module."""

from deal import pre, post


@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def square(x: int) -> int:
    """
    Return the square of x.

    Examples:
        >>> square(2)
        4
        >>> square(0)
        0
    """
    return x * x
''')
    return core_file


@pytest.fixture
def sample_shell_file(sample_project_dir: Path) -> Path:
    """Create a sample Shell Python file."""
    shell_file = sample_project_dir / "src" / "shell" / "example.py"
    shell_file.write_text('''"""Example Shell module."""

import os
from pathlib import Path


def read_file(path: Path) -> str:
    """Read content from a file."""
    return path.read_text()
''')
    return shell_file
