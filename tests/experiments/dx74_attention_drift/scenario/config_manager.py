"""Configuration management with planted logic bugs.

DX-74 Test Scenario - File 5/6
Bugs: 8 logic and contract issues
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Config:
    """Application configuration."""

    name: str
    debug: bool = False
    max_connections: int = 100
    timeout: float = 30.0


# BUG-34: Global mutable state
_config_cache: dict[str, Any] = {}


def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value.

    # BUG-35: No validation that key exists in schema
    """
    return _config_cache.get(key, default)


def set_config(key: str, value: Any) -> None:
    """Set a configuration value.

    # BUG-36: No type validation for value
    """
    _config_cache[key] = value


def validate_config(config: dict) -> bool:
    """Validate a configuration dictionary.

    # BUG-37: Incomplete validation (missing required fields check)
    """
    if not isinstance(config, dict):
        return False
    return True  # Should check required fields


def merge_configs(base: dict, override: dict) -> dict:
    """Merge two configuration dictionaries.

    # BUG-38: Shallow merge doesn't handle nested dicts
    """
    result = base.copy()
    result.update(override)
    return result


def load_config_from_env(prefix: str = "APP_") -> dict:
    """Load configuration from environment variables.

    # BUG-39: No sanitization of environment values
    """
    import os
    config = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix):].lower()
            config[config_key] = value  # No type conversion
    return config


def parse_config_value(value: str, value_type: str) -> Any:
    """Parse a configuration value to the correct type.

    # BUG-40: Missing handling for some types
    """
    if value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    # Missing: list, dict, etc.
    return value


def get_nested_config(keys: list[str], default: Any = None) -> Any:
    """Get a nested configuration value.

    # BUG-41: No handling for non-dict intermediate values
    """
    current = _config_cache
    for key in keys:
        if key in current:
            current = current[key]
        else:
            return default
    return current


def reset_config() -> None:
    """Reset configuration to defaults.

    This one is OK - proper state management
    """
    global _config_cache
    _config_cache = {}


def export_config(filepath: str) -> bool:
    """Export configuration to a file.

    This one is OK - proper error handling
    """
    import json
    try:
        with open(filepath, "w") as f:
            json.dump(_config_cache, f, indent=2)
        return True
    except (OSError, TypeError) as e:
        print(f"Export failed: {e}")
        return False


def import_config(filepath: str) -> bool:
    """Import configuration from a file.

    This one is OK - proper error handling
    """
    import json
    try:
        with open(filepath) as f:
            data = json.load(f)
        _config_cache.update(data)
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"Import failed: {e}")
        return False
