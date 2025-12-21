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


@pre(lambda data, source: isinstance(data, dict) and isinstance(source, str))
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


@pre(lambda config, key: isinstance(config, dict) and isinstance(key, str))
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


@pre(lambda config, key: isinstance(config, dict) and isinstance(key, str))
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


@pre(lambda config, key: isinstance(config, dict) and isinstance(key, str))
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
        >>> cfg = parse_guard_config({"use_code_lines": "invalid"})  # Invalid type ignored
        >>> cfg.use_code_lines  # Falls back to model default (False)
        False
    """
    kwargs: dict[str, Any] = {}

    val = _get_int(guard_config, "max_file_lines")
    if val is not None:
        kwargs["max_file_lines"] = val

    val = _get_int(guard_config, "max_function_lines")
    if val is not None:
        kwargs["max_function_lines"] = val

    if "forbidden_imports" in guard_config:
        v = guard_config["forbidden_imports"]
        if isinstance(v, (list, tuple)):
            kwargs["forbidden_imports"] = tuple(v)

    bval = _get_bool(guard_config, "require_contracts")
    if bval is not None:
        kwargs["require_contracts"] = bval

    bval = _get_bool(guard_config, "require_doctests")
    if bval is not None:
        kwargs["require_doctests"] = bval

    bval = _get_bool(guard_config, "strict_pure")
    if bval is not None:
        kwargs["strict_pure"] = bval

    bval = _get_bool(guard_config, "use_code_lines")
    if bval is not None:
        kwargs["use_code_lines"] = bval

    bval = _get_bool(guard_config, "exclude_doctest_lines")
    if bval is not None:
        kwargs["exclude_doctest_lines"] = bval

    # Phase 9 P1: Parse rule_exclusions
    if "rule_exclusions" in guard_config:
        raw_exclusions = guard_config["rule_exclusions"]
        if isinstance(raw_exclusions, list):
            exclusions = []
            for excl in raw_exclusions:
                if isinstance(excl, dict) and "pattern" in excl and "rules" in excl:
                    pattern = excl["pattern"]
                    rules = excl["rules"]
                    if isinstance(pattern, str) and isinstance(rules, list):
                        exclusions.append(
                            RuleExclusion(pattern=str(pattern), rules=[str(r) for r in rules])
                        )
            if exclusions:
                kwargs["rule_exclusions"] = exclusions

    # Phase 9 P2: Parse severity_overrides (merge with defaults)
    if "severity_overrides" in guard_config:
        raw_overrides = guard_config["severity_overrides"]
        if isinstance(raw_overrides, dict):
            defaults: dict[str, str] = {"redundant_type_contract": "off"}
            for k, v in raw_overrides.items():
                if isinstance(k, str) and isinstance(v, str):
                    defaults[str(k)] = str(v)  # Convert to real Python strings
            kwargs["severity_overrides"] = defaults

    # Phase 9 P8: Parse size_warning_threshold
    fval = _get_float(guard_config, "size_warning_threshold")
    if fval is not None:
        kwargs["size_warning_threshold"] = fval

    # B4: Parse purity declarations
    if "purity_pure" in guard_config:
        v = guard_config["purity_pure"]
        if isinstance(v, (list, tuple)):
            kwargs["purity_pure"] = [str(x) for x in v if isinstance(x, str)]
    if "purity_impure" in guard_config:
        v = guard_config["purity_impure"]
        if isinstance(v, (list, tuple)):
            kwargs["purity_impure"] = [str(x) for x in v if isinstance(x, str)]

    try:
        return RuleConfig(**kwargs)
    except Exception:
        # Invalid config values - return defaults
        return RuleConfig()


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
