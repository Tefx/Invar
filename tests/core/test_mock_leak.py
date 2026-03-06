from __future__ import annotations

from invar.core.mock_leak import check_mock_leaks
from invar.core.models import FileInfo, RuleConfig, Severity


def _run(path: str, source: str, imports: list[str]) -> list:
    file_info = FileInfo(path=path, lines=len(source.splitlines()), imports=imports, source=source)
    return check_mock_leaks([file_info], RuleConfig())


def test_reports_mock_import_in_production_file() -> None:
    source = "from unittest.mock import MagicMock\n"
    violations = _run("src/invar/core/service.py", source, ["unittest.mock"])

    assert len(violations) == 1
    violation = violations[0]
    assert violation.rule == "mock_leak"
    assert violation.severity == Severity.ERROR
    assert violation.file == "src/invar/core/service.py"


def test_allows_mock_import_in_test_file() -> None:
    source = "from unittest.mock import patch\n"
    violations = _run("tests/test_service.py", source, ["unittest.mock"])
    assert violations == []


def test_allows_mock_import_in_conftest() -> None:
    source = "from unittest.mock import Mock\n"
    violations = _run("tests/conftest.py", source, ["unittest.mock"])
    assert violations == []


def test_reports_faker_import_in_production_file() -> None:
    source = "from faker import Faker\n"
    violations = _run("src/invar/shell/seed.py", source, ["faker"])

    assert len(violations) == 1
    assert violations[0].message == "Test utility 'faker' imported in production file"
