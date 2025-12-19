"""
Pure utility functions.

These functions were moved from Shell to Core because they contain
no I/O operations - they are pure data transformations.
"""

from __future__ import annotations

import fnmatch
from typing import Any

from deal import post, pre

from invar.core.models import GuardReport, RuleConfig, RuleExclusion


@pre(lambda report, strict: isinstance(report, GuardReport))
@post(lambda result: result in (0, 1))
def get_exit_code(report: GuardReport, strict: bool) -> int:
    """
    Determine exit code based on report and strict mode.

    Examples:
        >>> from invar.core.models import GuardReport
        >>> get_exit_code(GuardReport(files_checked=1), strict=False)
        0
        >>> report = GuardReport(files_checked=1)
        >>> report.errors = 1
        >>> get_exit_code(report, strict=False)
        1
    """
    if report.errors > 0:
        return 1
    if strict and report.warnings > 0:
        return 1
    return 0


@pre(lambda data, source: isinstance(data, dict))
@post(lambda result: isinstance(result, dict))
def extract_guard_section(data: dict[str, Any], source: str) -> dict[str, Any]:
    """
    Extract guard config section based on source type.

    Examples:
        >>> extract_guard_section({"tool": {"invar": {"guard": {"x": 1}}}}, "pyproject")
        {'x': 1}
        >>> extract_guard_section({"guard": {"y": 2}}, "invar")
        {'y': 2}
        >>> extract_guard_section({}, "default")
        {}
    """
    if source == "pyproject":
        return data.get("tool", {}).get("invar", {}).get("guard", {})
    # invar.toml and .invar/config.toml use [guard] directly
    return data.get("guard", {})


@pre(lambda guard_config: isinstance(guard_config, dict))
@post(lambda result: isinstance(result, RuleConfig))
def parse_guard_config(guard_config: dict[str, Any]) -> RuleConfig:
    """
    Parse configuration from guard section.

    Examples:
        >>> cfg = parse_guard_config({"max_file_lines": 400})
        >>> cfg.max_file_lines
        400
        >>> cfg = parse_guard_config({})
        >>> cfg.max_file_lines  # Phase 9 P1: Default is now 500
        500
        >>> cfg = parse_guard_config({"rule_exclusions": [{"pattern": "**/gen/**", "rules": ["*"]}]})
        >>> len(cfg.rule_exclusions)
        1
        >>> cfg.rule_exclusions[0].pattern
        '**/gen/**'
    """
    kwargs: dict[str, Any] = {}

    if "max_file_lines" in guard_config:
        kwargs["max_file_lines"] = guard_config["max_file_lines"]

    if "max_function_lines" in guard_config:
        kwargs["max_function_lines"] = guard_config["max_function_lines"]

    if "forbidden_imports" in guard_config:
        kwargs["forbidden_imports"] = tuple(guard_config["forbidden_imports"])

    if "require_contracts" in guard_config:
        kwargs["require_contracts"] = guard_config["require_contracts"]

    if "require_doctests" in guard_config:
        kwargs["require_doctests"] = guard_config["require_doctests"]

    if "strict_pure" in guard_config:
        kwargs["strict_pure"] = guard_config["strict_pure"]

    if "use_code_lines" in guard_config:
        kwargs["use_code_lines"] = guard_config["use_code_lines"]

    if "exclude_doctest_lines" in guard_config:
        kwargs["exclude_doctest_lines"] = guard_config["exclude_doctest_lines"]

    # Phase 9 P1: Parse rule_exclusions
    if "rule_exclusions" in guard_config:
        exclusions = []
        for excl in guard_config["rule_exclusions"]:
            exclusions.append(RuleExclusion(
                pattern=excl["pattern"],
                rules=excl["rules"],
            ))
        kwargs["rule_exclusions"] = exclusions

    # Phase 9 P2: Parse severity_overrides (merge with defaults)
    if "severity_overrides" in guard_config:
        # Get default overrides and update with user config
        defaults = {"redundant_type_contract": "off"}
        defaults.update(guard_config["severity_overrides"])
        kwargs["severity_overrides"] = defaults

    # Phase 9 P8: Parse size_warning_threshold
    if "size_warning_threshold" in guard_config:
        kwargs["size_warning_threshold"] = guard_config["size_warning_threshold"]

    return RuleConfig(**kwargs)


@pre(lambda file_path, patterns: isinstance(file_path, str) and isinstance(patterns, list))
def matches_pattern(file_path: str, patterns: list[str]) -> bool:
    """
    Check if a file path matches any of the glob patterns.

    Examples:
        >>> matches_pattern("src/domain/models.py", ["**/domain/**"])
        True
        >>> matches_pattern("src/api/views.py", ["**/domain/**"])
        False
        >>> matches_pattern("src/core/logic.py", ["src/core/**", "**/models/**"])
        True
    """
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
        # Also check with leading path component for ** patterns
        if pattern.startswith("**/"):
            # Match anywhere in path
            if fnmatch.fnmatch(file_path, pattern[3:]):
                return True
            # Try matching each subpath
            parts = file_path.split("/")
            for i in range(len(parts)):
                subpath = "/".join(parts[i:])
                if fnmatch.fnmatch(subpath, pattern[3:]):
                    return True
    return False


@pre(lambda file_path, prefixes: isinstance(file_path, str) and isinstance(prefixes, list))
def matches_path_prefix(file_path: str, prefixes: list[str]) -> bool:
    """
    Check if file_path starts with any of the given prefixes.

    Examples:
        >>> matches_path_prefix("src/core/logic.py", ["src/core", "src/domain"])
        True
        >>> matches_path_prefix("src/shell/cli.py", ["src/core", "src/domain"])
        False
    """
    return any(file_path.startswith(p) for p in prefixes)
