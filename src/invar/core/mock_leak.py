"""
Mock leak detection for production code.

Identifies test utilities (unittest.mock, faker) imported in non-test files.
Test utilities should only be used in test files.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Severity, Violation


@pre(
    lambda file_infos, config: (
        all(isinstance(fi, FileInfo) for fi in file_infos) and isinstance(config, RuleConfig)
    )
)
@post(lambda result: all(v.rule == "mock_leak" for v in result))
def check_mock_leaks(file_infos: list[FileInfo], config: RuleConfig) -> list[Violation]:
    """
    Check for mock imports in non-test files.

    Detects test utilities imported in production code:
    - unittest.mock (any import)
    - MagicMock
    - patch
    - faker

    Non-test files are those NOT matching:
    - test_*.py (filename starts with test_)
    - *_test.py (filename ends with _test.py)
    - conftest.py (Pytest configuration)
    - Under tests/ directory

    Examples:
        >>> from invar.core.models import FileInfo
        >>> # Case 1: mock import in prod file -> violation
        >>> source1 = "from unittest.mock import Mock\\ndef use_mock(): pass"
        >>> info1 = FileInfo(path="src/api.py", lines=2, imports=["unittest.mock"], source=source1)
        >>> violations1 = check_mock_leaks([info1], RuleConfig())
        >>> len(violations1)
        1
        >>> violations1[0].rule
        'mock_leak'
        >>> violations1[0].severity
        <Severity.ERROR: 'error'>
        >>> violations1[0].file
        'src/api.py'

        >>> # Case 2: legitimate mock in test_*.py -> no violation
        >>> source2 = "from unittest.mock import Mock\\ndef test_something(): pass"
        >>> info2 = FileInfo(path="tests/test_api.py", lines=2, imports=["unittest.mock"], source=source2)
        >>> len(check_mock_leaks([info2], RuleConfig()))
        0

        >>> # Case 3: conftest.py exclusion
        >>> source3 = "from unittest.mock import Mock"
        >>> info3 = FileInfo(path="tests/conftest.py", lines=1, imports=["unittest.mock"], source=source3)
        >>> len(check_mock_leaks([info3], RuleConfig()))
        0

        >>> # Case 4: tests/ directory exclusion
        >>> source4 = "from unittest.mock import patch"
        >>> info4 = FileInfo(path="tests/utils/helpers.py", lines=1, imports=["unittest.mock"], source=source4)
        >>> len(check_mock_leaks([info4], RuleConfig()))
        0

        >>> # Case 5: MagicMock import detection
        >>> source5 = "from unittest.mock import MagicMock\\ndef use_magic(): pass"
        >>> info5 = FileInfo(path="src/core/logic.py", lines=2, imports=["unittest.mock"], source=source5)
        >>> violations5 = check_mock_leaks([info5], RuleConfig())
        >>> len(violations5)
        1
        >>> violations5[0].line
        1

        >>> # Case 6: unittest.mock.patch import detection
        >>> source6 = "from unittest.mock import patch\\ndef use_patch(): pass"
        >>> info6 = FileInfo(path="src/shell/cli.py", lines=2, imports=["unittest.mock"], source=source6)
        >>> len(check_mock_leaks([info6], RuleConfig()))
        1

        >>> # Case 7: faker import detection
        >>> source7 = "from faker import Faker\\ndef create_fake(): pass"
        >>> info7 = FileInfo(path="src/models.py", lines=2, imports=["faker"], source=source7)
        >>> violations7 = check_mock_leaks([info7], RuleConfig())
        >>> len(violations7)
        1
        >>> violations7[0].message
        "Test utility 'faker' imported in production file"

        >>> # Case 8: Valid production code (no mock imports)
        >>> source8 = "def normal_function():\\n    return 42"
        >>> info8 = FileInfo(path="src/calculator.py", lines=2, imports=[], source=source8)
        >>> len(check_mock_leaks([info8], RuleConfig()))
        0

        >>> # Case 9: _test.py suffix exclusion
        >>> source9 = "from unittest.mock import Mock"
        >>> info9 = FileInfo(path="src/api_test.py", lines=1, imports=["unittest.mock"], source=source9)
        >>> len(check_mock_leaks([info9], RuleConfig()))
        0

        >>> # Case 10: Multiple imports, one file
        >>> source10 = "from unittest.mock import Mock, patch\\nimport faker"
        >>> info10 = FileInfo(path="src/bad.py", lines=2, imports=["unittest.mock", "faker"], source=source10)
        >>> violations10 = check_mock_leaks([info10], RuleConfig())
        >>> len(violations10)
        1
        >>> violations10[0].line
        1
    """
    violations: list[Violation] = []

    for file_info in file_infos:
        # Check if this is a test file (excluded)
        if _is_test_file(file_info.path):
            continue

        # Parse source for import detection
        source = file_info.source or ""
        if not source:
            continue

        try:
            tree = ast.parse(source)
        except (SyntaxError, TypeError, ValueError):
            continue

        # Find mock/test imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_mock_import(alias.name):
                        violations.append(
                            Violation(
                                rule="mock_leak",
                                severity=Severity.ERROR,
                                file=file_info.path,
                                line=node.lineno,
                                message=f"Test utility '{alias.name}' imported in production file",
                                suggestion="Move test utilities to test files (test_*.py, *_test.py, or tests/)",
                            )
                        )
                        break  # One violation per file
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if _is_mock_import(module):
                    violations.append(
                        Violation(
                            rule="mock_leak",
                            severity=Severity.ERROR,
                            file=file_info.path,
                            line=node.lineno,
                            message=f"Test utility '{module}' imported in production file",
                            suggestion="Move test utilities to test files (test_*.py, *_test.py, or tests/)",
                        )
                    )
                    break  # One violation per file

    return violations


@pre(lambda file_path: isinstance(file_path, str) and len(file_path) > 0)
@post(lambda result: isinstance(result, bool))
def _is_test_file(file_path: str) -> bool:
    """
    Check if file is a test file (excluded from mock_leak checks).

    Test files match:
    - test_*.py (filename starts with test_)
    - *_test.py (filename ends with _test.py)
    - conftest.py (Pytest configuration)
    - Under tests/ or test/ directory

    Examples:
        >>> _is_test_file("tests/test_api.py")
        True
        >>> _is_test_file("test/test_foo.py")
        True
        >>> _is_test_file("tests/conftest.py")
        True
        >>> _is_test_file("src/api_test.py")
        True
        >>> _is_test_file("src/test_utils.py")  # test_ at start
        True
        >>> _is_test_file("src/api.py")
        False
        >>> _is_test_file("src/contest.py")  # test/ not in path
        False
        >>> _is_test_file("tests/utils/helpers.py")
        True
        >>> _is_test_file("test/integration/test_db.py")
        True
    """
    path_lower = file_path.replace("\\", "/").lower()
    filename = path_lower.rsplit("/", 1)[-1]

    # Check filename patterns
    if filename.startswith("test_") or filename.endswith("_test.py") or filename == "conftest.py":
        return True

    # Check directory patterns (both /tests/ and starting with tests/)
    if path_lower.startswith("tests/") or path_lower.startswith("test/"):
        return True

    return "/tests/" in path_lower or "/test/" in path_lower


@pre(lambda module: len(module) > 0)
@post(lambda result: isinstance(result, bool))
def _is_mock_import(module: str) -> bool:
    """
    Check if module is a test utility (mock/faker).

    Detects:
    - unittest.mock (module or submodule)
    - unittest.mock.Mock
    - unittest.mock.MagicMock
    - unittest.mock.patch
    - faker

    Examples:
        >>> _is_mock_import("unittest.mock")
        True
        >>> _is_mock_import("unittest.mock.MagicMock")
        True
        >>> _is_mock_import("faker")
        True
        >>> _is_mock_import("faker.providers")
        True
        >>> _is_mock_import("requests")
        False
        >>> _is_mock_import("unittest")
        False
        >>> _is_mock_import("unittest.case")
        False
    """
    # unittest.mock module or subimports
    if module == "unittest.mock" or module.startswith("unittest.mock."):
        return True

    # faker module or subimports
    return module == "faker" or module.startswith("faker.")
