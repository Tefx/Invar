"""
Cache service module for caching operations.
"""
import hashlib
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cache entry."""
    key: str
    value: T
    created_at: datetime
    expires_at: datetime | None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class SimpleCache:
    """Simple in-memory cache."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any:
        """Get a value from cache."""
        entry = self._cache.get(key)

        if not entry:
            return None

        # BUG: Should check expiration before returning
        # Expired entries are returned as valid

        entry.access_count += 1
        entry.last_accessed = datetime.now()

        return entry.value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set a value in cache."""
        ttl = ttl or self.default_ttl
        now = datetime.now()

        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl)
        )

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = datetime.now()
        expired_keys = []

        for key, entry in self._cache.items():
            if entry.expires_at and entry.expires_at < now:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


class LRUCache:
    """Least Recently Used cache with size limit."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()

    def get(self, key: str) -> Any:
        """Get a value, moving it to end (most recent)."""
        if key not in self._cache:
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set a value, evicting LRU if needed."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return

        # BUG: Should check >= not > for max_size boundary
        if len(self._cache) > self.max_size:
            # Remove oldest (first) item
            self._cache.popitem(last=False)

        self._cache[key] = value

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False


class ThreadSafeCache:
    """Thread-safe cache implementation."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        """Get a value thread-safely."""
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value thread-safely."""
        with self._lock:
            self._cache[key] = value

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        """Get value or set it using factory if missing."""
        # BUG: Race condition - checks and sets are not atomic
        # Another thread could set between get and set
        value = self.get(key)
        if value is not None:
            return value

        new_value = factory()
        self.set(key, new_value)
        return new_value

    def update(self, key: str, updater: Callable[[Any], Any]) -> Any:
        """Update a value using an updater function."""
        with self._lock:
            current = self._cache.get(key)
            # BUG: Doesn't handle case where key doesn't exist
            # updater(None) might fail
            new_value = updater(current)
            self._cache[key] = new_value
            return new_value


class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(self, cache: SimpleCache = None, key_prefix: str = ""):
        self.cache = cache or SimpleCache()
        self.key_prefix = key_prefix

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create a cache key from function call."""
        # BUG: Doesn't handle unhashable arguments (lists, dicts)
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return f"{self.key_prefix}{hashlib.md5(key_data.encode()).hexdigest()}"

    def __call__(self, func: Callable) -> Callable:
        """Decorate a function with caching."""
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, args, kwargs)

            cached = self.cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            self.cache.set(key, result)

            return result

        return wrapper


class DistributedCache:
    """Simulated distributed cache with multiple nodes."""

    # BUG: Hardcoded connection string with password (syntactic - grep-able)
    DEFAULT_CONNECTION = "redis://admin:cache_secret_123@localhost:6379"

    def __init__(self, nodes: list[str] = None):
        self.nodes = nodes or [self.DEFAULT_CONNECTION]
        self._local_cache: dict[str, Any] = {}
        self._node_index = 0

    def _get_node(self, key: str) -> str:
        """Get the node responsible for a key."""
        # Simple consistent hashing
        hash_val = hash(key)
        return self.nodes[hash_val % len(self.nodes)]

    def get(self, key: str) -> Any:
        """Get a value from distributed cache."""
        # Simulated - just uses local cache
        return self._local_cache.get(key)

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set a value in distributed cache."""
        try:
            # Simulated - just uses local cache
            self._local_cache[key] = value
            return True
        except Exception:
            # BUG: Bare except (syntactic - grep-able)
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from distributed cache."""
        if key in self._local_cache:
            del self._local_cache[key]
            return True
        return False


class CacheManager:
    """Manages multiple cache layers."""

    def __init__(self):
        self.l1_cache = LRUCache(max_size=100)  # Fast, small
        self.l2_cache = SimpleCache(default_ttl=3600)  # Larger, slower

    def get(self, key: str) -> Any:
        """Get from L1, fall back to L2."""
        # Try L1 first
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        # Try L2
        value = self.l2_cache.get(key)
        if value is not None:
            # Promote to L1
            self.l1_cache.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set in both cache layers."""
        self.l1_cache.set(key, value)
        self.l2_cache.set(key, value, ttl)

    def invalidate(self, key: str) -> None:
        """Invalidate a key in all layers."""
        self.l1_cache.delete(key)
        self.l2_cache.delete(key)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        count = 0

        # BUG: Only invalidates L2, forgets about L1
        for key in list(self.l2_cache._cache.keys()):
            if pattern in key:
                self.l2_cache.delete(key)
                count += 1

        return count


def cache_key(*parts) -> str:
    """Create a cache key from parts."""
    # BUG: Doesn't handle None values properly
    # str(None) = "None" which could collide with actual "None" string
    return ":".join(str(p) for p in parts)


def memoize(func: Callable) -> Callable:
    """Simple memoization decorator."""
    cache = {}

    def wrapper(*args):
        # BUG: Doesn't work with keyword arguments
        if args in cache:
            return cache[args]

        result = func(*args)
        cache[args] = result
        return result

    return wrapper


def ttl_cache(ttl_seconds: int) -> Callable:
    """Decorator that caches with TTL."""
    def decorator(func: Callable) -> Callable:
        cache: dict[tuple, tuple[Any, datetime]] = {}

        def wrapper(*args):
            now = datetime.now()

            if args in cache:
                value, cached_at = cache[args]
                # BUG: Wrong expiration check - should check if expired, not if still valid
                if (now - cached_at).seconds < ttl_seconds:
                    return value

            result = func(*args)
            cache[args] = (result, now)
            return result

        return wrapper

    return decorator
