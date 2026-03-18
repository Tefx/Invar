from __future__ import annotations

from invar.core.utils import matches_file_symbol_pattern, parse_guard_config


def test_parse_guard_config_reads_escape_scalar_fields() -> None:
    config = parse_guard_config(
        {
            "escape_suppressible_per_file": 4,
            "escape_expensive_per_file": 3,
            "escape_suppressible_per_project": 11,
            "escape_expensive_per_project": 7,
            "escape_budget_limit": 19,
            "escape_warning_threshold": 0.6,
            "escape_exempt_limit": 24,
            "escape_exempt_warning": 18,
        }
    )

    assert config.escape_suppressible_per_file == 4
    assert config.escape_expensive_per_file == 3
    assert config.escape_suppressible_per_project == 11
    assert config.escape_expensive_per_project == 7
    assert config.escape_budget_limit == 19
    assert config.escape_warning_threshold == 0.6
    assert config.escape_exempt_limit == 24
    assert config.escape_exempt_warning == 18


def test_match_exempt_pattern_file_only_glob() -> None:
    assert matches_file_symbol_pattern("cli/commands/run.py", None, "cli/commands/*.py")


def test_match_exempt_pattern_file_symbol_glob() -> None:
    assert matches_file_symbol_pattern("mcp/server.py", "create_table", "mcp/server.py::create_*")


def test_match_exempt_pattern_dotted_symbol_glob() -> None:
    assert matches_file_symbol_pattern(
        "core/patterns/detector.py",
        "PatternDetector.description",
        "core/patterns/detector.py::*.description",
    )


def test_match_exempt_pattern_dotted_symbol_glob_accepts_slash_symbols() -> None:
    assert matches_file_symbol_pattern(
        "core/patterns/detector.py",
        "PatternDetector/description",
        "core/patterns/detector.py::*.description",
    )
