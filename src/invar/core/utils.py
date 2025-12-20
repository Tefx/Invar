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


def match_glob_pattern(file_path: str, pattern: str) -> bool:
    """
    Check if file path matches a glob pattern with ** support.

    Uses fnmatch for single-segment wildcards, handles ** for multi-segment.

    Examples:
        >>> match_glob_pattern("src/generated/foo.py", "**/generated/**")
        True
        >>> match_glob_pattern("generated/foo.py", "**/generated/**")
        True
        >>> match_glob_pattern("src/core/calc.py", "**/generated/**")
        False
        >>> match_glob_pattern("src/core/data.py", "src/core/data.py")
        True
        >>> match_glob_pattern("src/core/calc.py", "src/core/*.py")
        True
        >>> match_glob_pattern("src/core/sub/calc.py", "src/core/*.py")
        False
        >>> match_glob_pattern("src/core/sub/calc.py", "src/core/**/*.py")
        True
    """
    file_path = file_path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if "**" not in pattern:
        if file_path.count("/") != pattern.count("/"):
            return False
        return fnmatch.fnmatch(file_path, pattern)
    path_parts = file_path.split("/")
    if pattern.startswith("**/") and pattern.endswith("/**"):
        middle = pattern[3:-3]
        if "/" not in middle and "*" not in middle:
            return middle in path_parts[:-1]
    if pattern.startswith("**/") and not pattern.endswith("/**"):
        suffix = pattern[3:]
        for i in range(len(path_parts)):
            if fnmatch.fnmatch("/".join(path_parts[i:]), suffix):
                return True
        return False
    if pattern.endswith("/**") and not pattern.startswith("**/"):
        prefix = pattern[:-3]
        return file_path.startswith(prefix + "/") or file_path == prefix
    parts = pattern.split("**/")
    if len(parts) == 2:
        prefix, suffix = parts[0].rstrip("/"), parts[1].lstrip("/").rstrip("/**")
        for i in range(len(path_parts) + 1):
            head = "/".join(path_parts[:i]) if i > 0 else ""
            tail = "/".join(path_parts[i:])
            if (not prefix or fnmatch.fnmatch(head, prefix)) and \
               (not suffix or fnmatch.fnmatch(tail, suffix) or fnmatch.fnmatch(tail, "*/" + suffix)):
                return True
    return False


@pre(lambda file_path, config: isinstance(config, RuleConfig))
def get_excluded_rules(file_path: str, config: RuleConfig) -> set[str]:
    """
    Get the set of rules to exclude for a given file path.

    Examples:
        >>> from invar.core.models import RuleConfig, RuleExclusion
        >>> excl = RuleExclusion(pattern="**/generated/**", rules=["*"])
        >>> cfg = RuleConfig(rule_exclusions=[excl])
        >>> get_excluded_rules("src/generated/foo.py", cfg)
        {'*'}
        >>> get_excluded_rules("src/core/calc.py", cfg)
        set()
        >>> excl2 = RuleExclusion(pattern="**/data/**", rules=["file_size"])
        >>> cfg2 = RuleConfig(rule_exclusions=[excl, excl2])
        >>> sorted(get_excluded_rules("src/data/big.py", cfg2))
        ['file_size']
    """
    excluded: set[str] = set()
    for exclusion in config.rule_exclusions:
        if match_glob_pattern(file_path, exclusion.pattern):
            excluded.update(exclusion.rules)
    return excluded
