"""
Configuration loading module.
Focus: Escape Hatch (D) and Error Handling (G) issues.
"""
import json
import logging
import os
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def pre(condition):
    """Precondition decorator."""
    def decorator(func):
        return func
    return decorator


def post(condition):
    """Postcondition decorator."""
    def decorator(func):
        return func
    return decorator


# =============================================================================
# ESCAPE HATCH ISSUES (D)
# =============================================================================

# BUG D-01: @invar:allow[no-contract] 'Legacy code' - vague justification
# @invar:allow[no-contract] - Legacy code
def load_legacy_config(path: str) -> dict[str, Any]:
    """Load configuration from legacy format."""
    with open(path) as f:
        content = f.read()

    # Parse custom format
    config = {}
    for line in content.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()

    return config


# BUG D-02: @invar:allow[no-doctest] 'Too complex' - invalid justification
# @invar:allow[no-doctest] - Too complex to test
def parse_complex_config(data: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Parse complex configuration with schema validation."""
    parsed = json.loads(data)

    # Validate against schema
    for field, rules in schema.items():
        if rules.get("required") and field not in parsed:
            raise ValueError(f"Missing required field: {field}")

        if field in parsed:
            expected_type = rules.get("type")
            if expected_type and not isinstance(parsed[field], expected_type):
                raise TypeError(f"Invalid type for {field}")

    return parsed


# BUG D-03: @invar:allow[bare-except] should be specific - wrong approach
# @invar:allow[bare-except] - Need to catch all errors
def safe_load_config(path: str) -> dict[str, Any]:
    """Safely load configuration file."""
    try:
        with open(path) as f:
            return json.load(f)
    except:  # noqa: E722 - bare except
        # Should catch specific exceptions
        return {}


# BUG D-04: @invar:allow[mutable-default] 'Performance' - lazy justification
# @invar:allow[mutable-default] - Performance optimization
_config_cache: dict[str, dict[str, Any]] = {}


def get_config(name: str, defaults: dict = {}) -> dict[str, Any]:  # Bug: mutable default
    """Get configuration by name with defaults."""
    if name in _config_cache:
        return _config_cache[name]

    config = defaults.copy()
    # Load from file or other source
    _config_cache[name] = config
    return config


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

# BUG G-20: Uses yaml.load without Loader - unsafe
def load_yaml_config(path: str) -> dict[str, Any]:
    """Load YAML configuration file."""
    with open(path) as f:
        # Bug: yaml.load without Loader is unsafe
        return yaml.load(f)  # type: ignore


# BUG G-21: Environment variables used without validation
def load_env_config() -> dict[str, Any]:
    """Load configuration from environment variables."""
    return {
        "database_url": os.environ.get("DATABASE_URL"),  # Could be None
        "api_key": os.environ.get("API_KEY"),  # Could be None
        "debug": os.environ.get("DEBUG"),  # Not converted to bool
        "port": os.environ.get("PORT"),  # Not converted to int
    }


# BUG G-22: Silently uses defaults on parse error
def parse_config_value(value: str, value_type: str) -> Any:
    """Parse configuration value to specified type."""
    try:
        if value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        else:
            return value
    except Exception:
        # Bug: silently returns None instead of raising
        return None


# BUG G-38: Config reload not atomic
class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """Reload configuration from file."""
        # Bug: not atomic - partial config can be read
        with open(self.config_path) as f:
            data = json.load(f)

        # Clear existing config
        self.config.clear()

        # Load new config (if error occurs here, config is empty)
        for key, value in data.items():
            self.config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

# BUG B-15: load_config no doctests
def load_config(path: str) -> dict[str, Any]:
    """Load configuration from JSON file."""
    with open(path) as f:
        return json.load(f)


def save_config(config: dict[str, Any], path: str) -> bool:
    """Save configuration to JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple configurations."""
    result = {}
    for config in configs:
        result.update(config)
    return result


def validate_config_schema(config: dict[str, Any], required_fields: list) -> bool:
    """Validate configuration has required fields."""
    for field in required_fields:
        if field not in config:
            return False
    return True


def get_nested_value(config: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get value from nested configuration path."""
    keys = path.split(".")
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def set_nested_value(config: dict[str, Any], path: str, value: Any) -> None:
    """Set value in nested configuration path."""
    keys = path.split(".")
    current = config

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value


def config_diff(old_config: dict[str, Any], new_config: dict[str, Any]) -> dict[str, Any]:
    """Find differences between two configurations."""
    diff = {
        "added": {},
        "removed": {},
        "changed": {},
    }

    for key in new_config:
        if key not in old_config:
            diff["added"][key] = new_config[key]
        elif old_config[key] != new_config[key]:
            diff["changed"][key] = {"old": old_config[key], "new": new_config[key]}

    for key in old_config:
        if key not in new_config:
            diff["removed"][key] = old_config[key]

    return diff
