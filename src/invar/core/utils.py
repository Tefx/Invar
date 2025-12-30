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


@pre(lambda report, strict: report.files_checked >= 0 and report.errors >= 0)
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


@pre(lambda report, strict, doctest_passed=True, crosshair_passed=True, property_passed=True: report.files_checked >= 0)
@post(lambda result: result in ("passed", "failed"))
def get_combined_status(
    report: GuardReport,
    strict: bool,
    doctest_passed: bool = True,
    crosshair_passed: bool = True,
    property_passed: bool = True,
) -> str:
    """
    Calculate true guard status including all test phases (DX-26).

    Unlike GuardReport.passed which only checks static errors,
    this function combines static analysis with runtime test results.

    Examples:
        >>> from invar.core.models import GuardReport
        >>> report = GuardReport(files_checked=1)
        >>> get_combined_status(report, strict=False)
        'passed'
        >>> get_combined_status(report, strict=False, doctest_passed=False)
        'failed'
        >>> report.errors = 1
        >>> get_combined_status(report, strict=False)
        'failed'
        >>> report2 = GuardReport(files_checked=1, warnings=1)
        >>> get_combined_status(report2, strict=True)
        'failed'
        >>> get_combined_status(report2, strict=False)
        'passed'
    """
    # Static analysis failures
    if report.errors > 0:
        return "failed"
    if strict and report.warnings > 0:
        return "failed"
    # Runtime test failures
    if not doctest_passed:
        return "failed"
    if not crosshair_passed:
        return "failed"
    if not property_passed:
        return "failed"
    return "passed"


@pre(lambda data, source: source in ("pyproject", "invar", "invar_dir", "default"))
@post(lambda result: isinstance(result, dict))
def extract_guard_section(data: dict[str, Any], source: str) -> dict[str, Any]:
    """
    Extract guard config section based on source type.

    Examples:
        >>> extract_guard_section({"tool": {"invar": {"guard": {"x": 1}}}}, "pyproject")
        {'x': 1}
        >>> extract_guard_section({"guard": {"y": 2}}, "invar")
        {'y': 2}
        >>> extract_guard_section({"guard": {"z": 3}}, "invar_dir")
        {'z': 3}
        >>> extract_guard_section({}, "default")
        {}
        >>> extract_guard_section({"guard": 0}, "invar")  # Non-dict value returns empty
        {}
    """
    if source == "pyproject":
        result = data.get("tool", {})
        if not isinstance(result, dict):
            return {}
        result = result.get("invar", {})
        if not isinstance(result, dict):
            return {}
        result = result.get("guard", {})
        return result if isinstance(result, dict) else {}
    # invar.toml and .invar/config.toml use [guard] directly
    result = data.get("guard", {})
    return result if isinstance(result, dict) else {}


@pre(lambda config, key: len(key) > 0)
@post(lambda result: result is None or isinstance(result, bool))
def _get_bool(config: dict[str, Any], key: str) -> bool | None:
    """
    Safely extract a boolean from config, returning None if invalid.

    >>> _get_bool({"a": True}, "a")
    True
    >>> _get_bool({"a": "not bool"}, "a") is None
    True
    """
    val = config.get(key)
    if isinstance(val, bool):
        return bool(val)  # Convert to ensure real Python bool
    return None


@pre(lambda config, key: len(key) > 0)
@post(lambda result: result is None or isinstance(result, int))
def _get_int(config: dict[str, Any], key: str) -> int | None:
    """
    Safely extract an integer from config, returning None if invalid.

    >>> _get_int({"a": 42}, "a")
    42
    >>> _get_int({"a": "not int"}, "a") is None
    True
    """
    val = config.get(key)
    if isinstance(val, int) and not isinstance(val, bool):
        return int(val)  # Convert to ensure real Python int
    return None


@pre(lambda config, key: len(key) > 0)
@post(lambda result: result is None or isinstance(result, float))
def _get_float(config: dict[str, Any], key: str) -> float | None:
    """
    Safely extract a float from config, returning None if invalid.

    >>> _get_float({"a": 3.14}, "a")
    3.14
    >>> _get_float({"a": 10}, "a")
    10.0
    >>> _get_float({"a": "not float"}, "a") is None
    True
    """
    val = config.get(key)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    return None


@pre(lambda config, key: len(key) > 0)
@post(lambda result: result is None or isinstance(result, list))
def _get_str_list(config: dict[str, Any], key: str) -> list[str] | None:
    """
    Safely extract a list of strings from config.

    >>> _get_str_list({"a": ["x", "y"]}, "a")
    ['x', 'y']
    >>> _get_str_list({"a": "not list"}, "a") is None
    True
    """
    val = config.get(key)
    if isinstance(val, (list, tuple)):
        return [str(x) for x in val if isinstance(x, str)]
    return None


@post(lambda result: result is None or isinstance(result, list))
def _parse_rule_exclusions(config: dict[str, Any]) -> list[RuleExclusion] | None:
    """
    Parse rule_exclusions from config.

    >>> excl = _parse_rule_exclusions({"rule_exclusions": [{"pattern": "**/gen/**", "rules": ["*"]}]})
    >>> excl[0].pattern
    '**/gen/**'
    >>> _parse_rule_exclusions({}) is None
    True
    """
    raw = config.get("rule_exclusions")
    if not isinstance(raw, list):
        return None
    exclusions = []
    for excl in raw:
        if isinstance(excl, dict) and "pattern" in excl and "rules" in excl:
            pattern, rules = excl["pattern"], excl["rules"]
            if isinstance(pattern, str) and isinstance(rules, list):
                exclusions.append(RuleExclusion(pattern=str(pattern), rules=[str(r) for r in rules]))
    return exclusions if exclusions else None


@post(lambda result: result is None or isinstance(result, dict))
def _parse_severity_overrides(config: dict[str, Any]) -> dict[str, str] | None:
    """
    Parse severity_overrides from config (merge with defaults).

    >>> _parse_severity_overrides({"severity_overrides": {"foo": "off"}})
    {'redundant_type_contract': 'warning', 'foo': 'off'}
    >>> _parse_severity_overrides({}) is None
    True
    """
    raw = config.get("severity_overrides")
    if not isinstance(raw, dict):
        return None
    # DX-38 Tier 2: redundant_type_contract enabled by default
    defaults: dict[str, str] = {"redundant_type_contract": "warning"}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, str):
            defaults[str(k)] = str(v)
    return defaults


@post(lambda result: isinstance(result, RuleConfig))
def parse_guard_config(guard_config: dict[str, Any]) -> RuleConfig:
    """
    Parse configuration from guard section.

    DX-22: Removed deprecated options (use_code_lines, exclude_doctest_lines).
    These are now always enabled by default.

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

    # Int fields
    for key in ("max_file_lines", "max_function_lines"):
        if (val := _get_int(guard_config, key)) is not None:
            kwargs[key] = val

    # Bool fields
    # DX-22: Removed use_code_lines, exclude_doctest_lines (deprecated)
    for key in ("require_contracts", "require_doctests", "strict_pure"):
        if (val := _get_bool(guard_config, key)) is not None:
            kwargs[key] = val

    # Float fields
    if (val := _get_float(guard_config, "size_warning_threshold")) is not None:
        kwargs["size_warning_threshold"] = val

    # List fields (convert to tuple for forbidden_imports)
    if (val := _get_str_list(guard_config, "forbidden_imports")) is not None:
        kwargs["forbidden_imports"] = tuple(val)
    for key in ("purity_pure", "purity_impure"):
        if (val := _get_str_list(guard_config, key)) is not None:
            kwargs[key] = val

    # Complex fields
    if (val := _parse_rule_exclusions(guard_config)) is not None:
        kwargs["rule_exclusions"] = val
    if (val := _parse_severity_overrides(guard_config)) is not None:
        kwargs["severity_overrides"] = val

    try:
        return RuleConfig(**kwargs)
    except Exception:
        return RuleConfig()


@pre(lambda file_path, patterns: len(file_path) > 0)
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


@pre(lambda file_path, prefixes: len(file_path) > 0)
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


@post(lambda result: isinstance(result, bool))
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
            if (not prefix or fnmatch.fnmatch(head, prefix)) and (
                not suffix or fnmatch.fnmatch(tail, suffix) or fnmatch.fnmatch(tail, "*/" + suffix)
            ):
                return True
    return False


@pre(lambda file_path, config: len(file_path) > 0)
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
