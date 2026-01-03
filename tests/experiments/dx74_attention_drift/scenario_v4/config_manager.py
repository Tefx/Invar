"""
Configuration management module.
Focus: Escape Hatch Audit (D), Error Handling (G)
"""
import json
import os
from pathlib import Path
from typing import Any, Dict

import yaml

# =============================================================================
# D. ESCAPE HATCH ISSUES - Unjustified @invar:allow markers
# =============================================================================

# @invar:allow[no-contract] - "Legacy code, will add later"
# BUG D-01: Vague justification, no timeline
def load_config(path: str) -> dict:
    """Load configuration from file."""
    with open(path) as f:
        if path.endswith('.json'):
            return json.load(f)
        elif path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported format: {path}")


# @invar:allow[no-doctest] - "Too complex to test"
# BUG D-02: Invalid justification - complex code needs MORE testing, not less
def merge_configs(*configs: dict) -> dict:
    """Merge multiple configuration dictionaries."""
    result = {}
    for config in configs:
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value
    return result


# @invar:allow[bare-except] - "Need to catch all errors"
# BUG D-03: Wrong approach - should catch specific exceptions
def safe_load(path: str) -> dict | None:
    """Safely load config, returning None on any error."""
    try:
        return load_config(path)
    except:  # noqa
        return None


# @invar:allow[mutable-default] - "Intentional for caching"
# BUG D-04: Justification sounds plausible but is still a bug
def get_defaults(overrides: Dict = {}) -> Dict:  # noqa
    """Get default configuration with optional overrides."""
    defaults = {
        "debug": False,
        "log_level": "INFO",
        "timeout": 30,
    }
    defaults.update(overrides)
    return defaults


# =============================================================================
# G. ERROR HANDLING ISSUES - Exceptions, fallback, recovery
# =============================================================================

class ConfigError(Exception):
    """Configuration error."""
    pass


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.cache: dict[str, dict] = {}
        self.watchers: list[callable] = []

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        try:
            config = self._load_main_config()
            keys = key.split(".")
            value = config
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default
        except Exception:
            # BUG G-11: Catches all exceptions, masks real errors
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        config = self._load_main_config()
        keys = key.split(".")

        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        self._save_config(config)

    def _load_main_config(self) -> dict:
        """Load main configuration file."""
        config_path = self.config_dir / "main.json"

        if "main" in self.cache:
            return self.cache["main"]

        if not config_path.exists():
            # BUG G-12: Creates empty config silently instead of raising
            return {}

        with open(config_path) as f:
            config = json.load(f)
            self.cache["main"] = config
            return config

    def _save_config(self, config: dict) -> None:
        """Save configuration to file."""
        config_path = self.config_dir / "main.json"

        # BUG G-13: No error handling for write failures
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        self.cache["main"] = config

    def reload(self) -> None:
        """Reload configuration from disk."""
        self.cache.clear()
        try:
            self._load_main_config()
        except Exception as e:
            # BUG G-14: Logs error but doesn't re-raise or notify
            print(f"Failed to reload config: {e}")


class EnvironmentConfig:
    """Configuration from environment variables."""

    def __init__(self, prefix: str = "APP"):
        self.prefix = prefix

    def get(self, key: str, default: str = None) -> str | None:
        """Get environment variable."""
        env_key = f"{self.prefix}_{key.upper()}"
        return os.environ.get(env_key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            # BUG G-15: Silently returns default on parse error
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean."""
        value = self.get(key)
        if value is None:
            return default
        # BUG G-16: Inconsistent boolean parsing
        return value.lower() in ("true", "1", "yes")

    def require(self, key: str) -> str:
        """Get required environment variable."""
        value = self.get(key)
        if value is None:
            # BUG G-17: Error message exposes internal key format
            raise ConfigError(f"Required environment variable {self.prefix}_{key.upper()} not set")
        return value


class ConfigValidator:
    """Validates configuration."""

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, config: dict) -> list[str]:
        """Validate configuration against schema."""
        errors = []

        for key, rules in self.schema.items():
            if rules.get("required") and key not in config:
                errors.append(f"Missing required key: {key}")
                continue

            if key not in config:
                continue

            value = config[key]

            # Type check
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(f"Invalid type for {key}: expected {expected_type.__name__}")

            # Range check
            if "min" in rules and value < rules["min"]:
                errors.append(f"{key} below minimum: {value} < {rules['min']}")
            if "max" in rules and value > rules["max"]:
                errors.append(f"{key} above maximum: {value} > {rules['max']}")

        # BUG G-18: Doesn't check for extra keys not in schema
        return errors


def load_env_file(path: str) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        # BUG G-19: Silently returns empty dict
        pass
    except Exception:
        # BUG G-20: Bare except, no logging
        pass

    return env_vars
