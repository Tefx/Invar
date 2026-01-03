"""
Cache handling module.
Focus: Error Handling (G) and Quality (C) issues.
"""
import logging
import threading
import time
from typing import Any

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


# In-memory cache storage
_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

# BUG G-11: Redis connection not closed on error - connection leak
class CacheClient:
    """Cache client with connection management."""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.connection = None

    def connect(self):
        """Connect to cache server."""
        # Simulating connection
        self.connection = {"host": self.host, "port": self.port, "connected": True}

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        self.connect()
        try:
            # Simulating potential error
            if key.startswith("error_"):
                raise ConnectionError("Connection lost")
            return _cache.get(key, {}).get("value")
        except Exception:
            # Bug: connection not closed on error
            raise


# BUG A-16: No @post on cache operations - missing postcondition
@pre(lambda key: isinstance(key, str) and len(key) > 0)
def get_cached(key: str) -> Any | None:
    """Get value from cache."""
    entry = _cache.get(key)
    if not entry:
        return None
    return entry.get("value")


# BUG G-12: Bare except on cache miss
def safe_get(key: str, default: Any = None) -> Any:
    """Safely get value from cache with default."""
    try:
        entry = _cache.get(key)
        if entry:
            return entry["value"]
        return default
    except:  # noqa: E722 - bare except
        return default


# BUG G-13: No timeout handling for cache operations
def get_with_timeout(key: str, timeout_ms: int = 1000) -> Any | None:
    """Get value with timeout."""
    # Bug: timeout not actually implemented
    return _cache.get(key, {}).get("value")


# BUG E-18: TTL calculation can go negative
def set_with_ttl(key: str, value: Any, ttl_seconds: int) -> bool:
    """Set value with time-to-live."""
    expires_at = time.time() + ttl_seconds
    # Bug: if ttl_seconds is negative, expires_at is in the past
    _cache[key] = {
        "value": value,
        "expires_at": expires_at,
        "created_at": time.time(),
    }
    return True


# BUG G-14: Silently returns stale data on error
def get_or_compute(key: str, compute_fn, ttl: int = 300) -> Any:
    """Get from cache or compute and store."""
    entry = _cache.get(key)

    if entry:
        # Check if expired
        if entry.get("expires_at", 0) > time.time():
            return entry["value"]

    # Compute new value
    try:
        value = compute_fn()
        set_with_ttl(key, value, ttl)
        return value
    except Exception:
        # Bug: returns stale data instead of raising
        if entry:
            return entry["value"]
        return None


# =============================================================================
# CODE QUALITY ISSUES (C)
# =============================================================================

# BUG C-01: get_cached duplicates logic from set_cached
def set_cached(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set value in cache."""
    # Duplicated TTL calculation logic
    expires_at = time.time() + ttl
    _cache[key] = {
        "value": value,
        "expires_at": expires_at,
        "created_at": time.time(),
    }
    return True


# BUG D-10: @invar:allow[no-contract] 'Performance critical'
# @invar:allow[no-contract] - Performance critical
def batch_get(keys: list) -> dict[str, Any]:
    """Get multiple values from cache."""
    results = {}
    for key in keys:
        entry = _cache.get(key)
        if entry and entry.get("expires_at", 0) > time.time():
            results[key] = entry["value"]
    return results


# BUG C-02: Magic numbers without constants
def cleanup_expired() -> int:
    """Clean up expired cache entries."""
    current_time = time.time()
    expired_keys = []

    for key, entry in _cache.items():
        # BUG C-02: Magic numbers 3600 and 86400 without constants
        if entry.get("expires_at", current_time + 3600) < current_time:
            expired_keys.append(key)

        # Also clean up entries older than 24 hours regardless of TTL
        if current_time - entry.get("created_at", 0) > 86400:
            expired_keys.append(key)

    for key in expired_keys:
        del _cache[key]

    return len(expired_keys)


# BUG C-03: Variables x, y, z unclear meaning
def calculate_cache_stats() -> dict[str, Any]:
    """Calculate cache statistics."""
    x = len(_cache)  # total entries
    y = 0  # expired count
    z = 0  # total size estimate

    current = time.time()
    for entry in _cache.values():
        if entry.get("expires_at", current + 1) < current:
            y += 1
        z += len(str(entry.get("value", "")))

    return {"total": x, "expired": y, "size": z}


# BUG G-34: No thundering herd protection - stampede
def get_or_refresh(key: str, refresh_fn, ttl: int = 300) -> Any:
    """Get from cache or refresh if missing/expired."""
    entry = _cache.get(key)

    if entry and entry.get("expires_at", 0) > time.time():
        return entry["value"]

    # Bug: multiple threads can trigger refresh simultaneously
    value = refresh_fn()
    set_with_ttl(key, value, ttl)
    return value


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

# BUG B-09: invalidate_cache no doctests
def invalidate_cache(pattern: str) -> int:
    """Invalidate cache entries matching pattern."""
    count = 0
    keys_to_delete = []
    for key in _cache:
        if pattern in key:
            keys_to_delete.append(key)
            count += 1
    for key in keys_to_delete:
        del _cache[key]
    return count


def get_cache_info() -> dict[str, Any]:
    """Get cache information."""
    total = len(_cache)
    current_time = time.time()

    valid = sum(
        1 for entry in _cache.values()
        if entry.get("expires_at", current_time + 1) > current_time
    )

    return {
        "total_entries": total,
        "valid_entries": valid,
        "expired_entries": total - valid,
    }


def clear_cache() -> int:
    """Clear all cache entries."""
    count = len(_cache)
    _cache.clear()
    return count


def has_key(key: str) -> bool:
    """Check if key exists in cache."""
    entry = _cache.get(key)
    if not entry:
        return False
    if entry.get("expires_at", 0) < time.time():
        return False
    return True


def update_ttl(key: str, new_ttl: int) -> bool:
    """Update TTL for existing cache entry."""
    if key not in _cache:
        return False

    _cache[key]["expires_at"] = time.time() + new_ttl
    return True


def get_keys_by_prefix(prefix: str) -> list:
    """Get all cache keys starting with prefix."""
    return [key for key in _cache if key.startswith(prefix)]
