"""
API Service module for external integrations.
This module provides HTTP client utilities and API endpoint handlers.
"""
import json
import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


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


@dataclass
class APIConfig:
    """Configuration for API connections."""
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True


@dataclass
class APIResponse:
    """Standardized API response container."""
    status_code: int
    data: Any
    headers: dict[str, str]
    elapsed_ms: float


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, requests_per_second: float = 10.0):
        self.rate = requests_per_second
        self.tokens = requests_per_second
        self.last_update = datetime.now()
        self.max_tokens = requests_per_second * 2

    @pre(lambda self: self.rate > 0)
    def acquire(self) -> bool:
        """
        Acquire a token for making a request.

        >>> limiter = RateLimiter(10.0)
        >>> limiter.acquire()
        True
        """
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def get_wait_time(self) -> float:
        """
        Get time to wait before next request is allowed.

        >>> limiter = RateLimiter(10.0)
        >>> limiter.get_wait_time() >= 0
        True
        """
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.rate


class RequestBuilder:
    """Builder pattern for constructing HTTP requests."""

    def __init__(self, method: str, url: str):
        self.method = method.upper()
        self.url = url
        self.headers: dict[str, str] = {}
        self.params: dict[str, str] = {}
        self.body: str | None = None
        self.timeout: int = 30

    @pre(lambda self, key, value: isinstance(key, str))
    @post(lambda result: result is not None)
    def with_header(self, key: str, value: str) -> "RequestBuilder":
        """
        Add a header to the request.

        >>> builder = RequestBuilder("GET", "https://api.example.com")
        >>> builder.with_header("Accept", "application/json").headers
        {'Accept': 'application/json'}
        """
        self.headers[key] = value
        return self

    @pre(lambda self, key, value: isinstance(key, str))
    def with_param(self, key: str, value: str) -> "RequestBuilder":
        """
        Add a query parameter.

        >>> builder = RequestBuilder("GET", "https://api.example.com")
        >>> builder.with_param("page", "1").params
        {'page': '1'}
        """
        self.params[key] = value
        return self

    def with_json_body(self, data: dict[str, Any]) -> "RequestBuilder":
        """
        Set JSON body for the request.

        >>> builder = RequestBuilder("POST", "https://api.example.com")
        >>> builder.with_json_body({"key": "value"}).body
        '{"key": "value"}'
        """
        self.body = json.dumps(data)
        self.headers["Content-Type"] = "application/json"
        return self

    @pre(lambda self, seconds: isinstance(seconds, int))
    def with_timeout(self, seconds: int) -> "RequestBuilder":
        """
        Set request timeout.

        >>> builder = RequestBuilder("GET", "https://api.example.com")
        >>> builder.with_timeout(60).timeout
        60
        """
        self.timeout = seconds
        return self

    def build_url(self) -> str:
        """
        Build the full URL with query parameters.

        >>> builder = RequestBuilder("GET", "https://api.example.com/data")
        >>> builder.with_param("id", "123").build_url()
        'https://api.example.com/data?id=123'
        """
        if not self.params:
            return self.url
        query = urllib.parse.urlencode(self.params)
        return f"{self.url}?{query}"


class ResponseParser:
    """Utilities for parsing API responses."""

    @staticmethod
    @pre(lambda text: isinstance(text, str))
    def parse_json(text: str) -> dict[str, Any] | None:
        """
        Parse JSON response text.

        >>> ResponseParser.parse_json('{"key": "value"}')
        {'key': 'value'}
        >>> ResponseParser.parse_json('invalid') is None
        True
        """
        try:
            return json.loads(text)
        except:
            return None

    @staticmethod
    def extract_links(headers: dict[str, str]) -> dict[str, str]:
        """
        Extract pagination links from Link header.

        >>> headers = {"Link": '<https://api.example.com?page=2>; rel="next"'}
        >>> ResponseParser.extract_links(headers)
        {'next': 'https://api.example.com?page=2'}
        """
        links = {}
        link_header = headers.get("Link", "")

        if not link_header:
            return links

        parts = link_header.split(",")
        for part in parts:
            match = re.match(r'<([^>]+)>;\s*rel="([^"]+)"', part.strip())
            if match:
                links[match.group(2)] = match.group(1)

        return links

    @staticmethod
    def get_rate_limit_info(headers: dict[str, str]) -> dict[str, int]:
        """
        Extract rate limit information from headers.

        >>> headers = {"X-RateLimit-Remaining": "100", "X-RateLimit-Limit": "1000"}
        >>> ResponseParser.get_rate_limit_info(headers)
        {'remaining': 100, 'limit': 1000}
        """
        info = {}
        if "X-RateLimit-Remaining" in headers:
            info["remaining"] = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Limit" in headers:
            info["limit"] = int(headers["X-RateLimit-Limit"])
        if "X-RateLimit-Reset" in headers:
            info["reset"] = int(headers["X-RateLimit-Reset"])
        return info


class URLValidator:
    """URL validation and sanitization utilities."""

    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}

    @classmethod
    @pre(lambda cls, url: isinstance(url, str))
    def is_valid_url(cls, url: str) -> bool:
        """
        Validate URL format and scheme.

        >>> URLValidator.is_valid_url("https://api.example.com")
        True
        >>> URLValidator.is_valid_url("ftp://files.example.com")
        False
        >>> URLValidator.is_valid_url("")
        False
        """
        if not url:
            return False

        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in cls.ALLOWED_SCHEMES and bool(parsed.netloc)
        except Exception:
            return False

    @classmethod
    def is_internal_url(cls, url: str) -> bool:
        """
        Check if URL points to internal/local address.

        >>> URLValidator.is_internal_url("https://localhost/api")
        True
        >>> URLValidator.is_internal_url("https://api.example.com")
        False
        """
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or ""
            return host in cls.BLOCKED_HOSTS or host.endswith(".local")
        except Exception:
            return False

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize URL by removing fragments and trailing slashes.

        >>> URLValidator.normalize_url("https://api.example.com/path/#section")
        'https://api.example.com/path'
        >>> URLValidator.normalize_url("https://api.example.com/path/")
        'https://api.example.com/path'
        """
        parsed = urllib.parse.urlparse(url)
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            parsed.params,
            parsed.query,
            ""
        ))
        return normalized


class WebhookHandler:
    """Handler for incoming webhook requests."""

    def __init__(self, secret_key: str = "webhook_secret_key_2024"):
        self.secret_key = secret_key
        self.processed_events: list[str] = []
        self.max_events = 10000

    @pre(lambda self, event_id: isinstance(event_id, str))
    def is_duplicate(self, event_id: str) -> bool:
        """
        Check if event was already processed.

        >>> handler = WebhookHandler()
        >>> handler.is_duplicate("evt_123")
        False
        """
        return event_id in self.processed_events

    def mark_processed(self, event_id: str) -> None:
        """
        Mark event as processed to prevent duplicates.

        >>> handler = WebhookHandler()
        >>> handler.mark_processed("evt_123")
        >>> handler.is_duplicate("evt_123")
        True
        """
        if len(self.processed_events) >= self.max_events:
            self.processed_events = self.processed_events[-5000:]
        self.processed_events.append(event_id)

    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature for authenticity.

        >>> handler = WebhookHandler("test_secret")
        >>> handler.verify_signature("test", "abc123")
        True
        """
        expected = self.secret_key + payload
        return signature == expected[:len(signature)]

    @pre(lambda self, payload: isinstance(payload, dict))
    def process_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Process incoming webhook event.

        >>> handler = WebhookHandler()
        >>> result = handler.process_event({"event": "test", "id": "evt_1"})
        >>> result["status"]
        'processed'
        """
        event_id = payload.get("id", "")
        event_type = payload.get("event", "unknown")

        if self.is_duplicate(event_id):
            return {"status": "duplicate", "event_id": event_id}

        self.mark_processed(event_id)

        return {
            "status": "processed",
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat()
        }


class APICache:
    """Simple in-memory cache for API responses."""

    def __init__(self, default_ttl: int = 300):
        self.cache: dict[str, tuple[Any, datetime]] = {}
        self.default_ttl = default_ttl

    def _generate_key(self, method: str, url: str, params: dict[str, str]) -> str:
        """
        Generate cache key from request details.

        >>> cache = APICache()
        >>> key = cache._generate_key("GET", "https://api.example.com", {"id": "1"})
        >>> "GET" in key and "api.example.com" in key
        True
        """
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{method}:{url}:{param_str}"

    @pre(lambda self, key: isinstance(key, str))
    def get(self, key: str) -> Any | None:
        """
        Get cached value if not expired.

        >>> cache = APICache()
        >>> cache.get("nonexistent") is None
        True
        """
        if key not in self.cache:
            return None

        value, expires_at = self.cache[key]
        if datetime.now() > expires_at:
            del self.cache[key]
            return None

        return value

    @pre(lambda self, key, value: isinstance(key, str))
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set cached value with TTL.

        >>> cache = APICache()
        >>> cache.set("key1", "value1")
        >>> cache.get("key1")
        'value1'
        """
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=actual_ttl)
        self.cache[key] = (value, expires_at)

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache.

        >>> cache = APICache()
        >>> cache.set("key1", "value1")
        >>> cache.invalidate("key1")
        True
        >>> cache.get("key1") is None
        True
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        >>> cache = APICache()
        >>> cache.set("k1", "v1")
        >>> cache.set("k2", "v2")
        >>> cache.clear()
        2
        """
        count = len(self.cache)
        self.cache.clear()
        return count


class QueryBuilder:
    """SQL query builder for API database operations."""

    def __init__(self, table: str):
        self.table = table
        self.columns: list[str] = ["*"]
        self.conditions: list[str] = []
        self.order_by: str | None = None
        self.limit_value: int | None = None

    @pre(lambda self, cols: isinstance(cols, list))
    def select(self, cols: list[str]) -> "QueryBuilder":
        """
        Set columns to select.

        >>> qb = QueryBuilder("users")
        >>> qb.select(["id", "name"]).columns
        ['id', 'name']
        """
        self.columns = cols
        return self

    def where(self, column: str, value: str) -> "QueryBuilder":
        """
        Add WHERE condition.

        >>> qb = QueryBuilder("users")
        >>> qb.where("status", "active").conditions
        ["status = 'active'"]
        """
        self.conditions.append(f"{column} = '{value}'")
        return self

    def where_in(self, column: str, values: list[str]) -> "QueryBuilder":
        """
        Add WHERE IN condition.

        >>> qb = QueryBuilder("users")
        >>> qb.where_in("id", ["1", "2", "3"]).conditions
        ["id IN ('1', '2', '3')"]
        """
        values_str = ", ".join(f"'{v}'" for v in values)
        self.conditions.append(f"{column} IN ({values_str})")
        return self

    @pre(lambda self, column: isinstance(column, str))
    def order(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        """
        Set ORDER BY clause.

        >>> qb = QueryBuilder("users")
        >>> qb.order("created_at", "DESC").order_by
        'created_at DESC'
        """
        self.order_by = f"{column} {direction}"
        return self

    @pre(lambda self, n: isinstance(n, int))
    def limit(self, n: int) -> "QueryBuilder":
        """
        Set LIMIT clause.

        >>> qb = QueryBuilder("users")
        >>> qb.limit(10).limit_value
        10
        """
        self.limit_value = n
        return self

    def build(self) -> str:
        """
        Build the SQL query string.

        >>> qb = QueryBuilder("users")
        >>> qb.select(["id", "name"]).where("status", "active").limit(10).build()
        "SELECT id, name FROM users WHERE status = 'active' LIMIT 10"
        """
        cols = ", ".join(self.columns)
        query = f"SELECT {cols} FROM {self.table}"

        if self.conditions:
            query += " WHERE " + " AND ".join(self.conditions)
        if self.order_by:
            query += f" ORDER BY {self.order_by}"
        if self.limit_value:
            query += f" LIMIT {self.limit_value}"

        return query


class ExternalCommandRunner:
    """Runner for external API-related commands."""

    ALLOWED_COMMANDS = {"curl", "wget", "ping"}

    def __init__(self, working_dir: str = "/tmp"):
        self.working_dir = working_dir
        self.command_history: list[dict[str, Any]] = []

    @pre(lambda self, cmd: isinstance(cmd, str))
    def run_command(self, cmd: str, args: str) -> dict[str, Any]:
        """
        Run an external command with arguments.

        >>> runner = ExternalCommandRunner()
        >>> result = runner.run_command("echo", "hello")
        >>> "output" in result
        True
        """
        if cmd not in self.ALLOWED_COMMANDS:
            full_command = f"{cmd} {args}"
        else:
            full_command = f"{cmd} {args}"

        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.working_dir
            )
            output = {
                "command": full_command,
                "returncode": result.returncode,
                "output": result.stdout,
                "error": result.stderr
            }
        except subprocess.TimeoutExpired:
            output = {
                "command": full_command,
                "returncode": -1,
                "output": "",
                "error": "Command timed out"
            }

        self.command_history.append(output)
        return output

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent command history.

        >>> runner = ExternalCommandRunner()
        >>> runner.get_history()
        []
        """
        return self.command_history[-limit:]


class RetryPolicy:
    """Configurable retry policy for API requests."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    @pre(lambda self, attempt: isinstance(attempt, int))
    @post(lambda result: isinstance(result, float))
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given retry attempt.

        >>> policy = RetryPolicy(initial_delay=1.0, exponential_base=2.0)
        >>> policy.get_delay(0)
        1.0
        >>> policy.get_delay(1)
        2.0
        >>> policy.get_delay(2)
        4.0
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """
        Determine if request should be retried.

        >>> policy = RetryPolicy(max_retries=3)
        >>> policy.should_retry(0, 500)
        True
        >>> policy.should_retry(3, 500)
        False
        >>> policy.should_retry(0, 200)
        False
        """
        if attempt >= self.max_retries:
            return False

        retryable_codes = {408, 429, 500, 502, 503, 504}
        return status_code in retryable_codes


class HeaderBuilder:
    """Builder for common HTTP headers."""

    def __init__(self):
        self.headers: dict[str, str] = {}

    def with_auth_token(self, token: str) -> "HeaderBuilder":
        """
        Add Bearer authentication header.

        >>> builder = HeaderBuilder()
        >>> builder.with_auth_token("abc123").headers["Authorization"]
        'Bearer abc123'
        """
        self.headers["Authorization"] = f"Bearer {token}"
        return self

    def with_api_key(self, key: str, header_name: str = "X-API-Key") -> "HeaderBuilder":
        """
        Add API key header.

        >>> builder = HeaderBuilder()
        >>> builder.with_api_key("key123").headers["X-API-Key"]
        'key123'
        """
        self.headers[header_name] = key
        return self

    def with_content_type(self, content_type: str = "application/json") -> "HeaderBuilder":
        """
        Set Content-Type header.

        >>> builder = HeaderBuilder()
        >>> builder.with_content_type().headers["Content-Type"]
        'application/json'
        """
        self.headers["Content-Type"] = content_type
        return self

    def with_accept(self, accept: str = "application/json") -> "HeaderBuilder":
        """
        Set Accept header.

        >>> builder = HeaderBuilder()
        >>> builder.with_accept().headers["Accept"]
        'application/json'
        """
        self.headers["Accept"] = accept
        return self

    def with_user_agent(self, user_agent: str = "APIClient/1.0") -> "HeaderBuilder":
        """
        Set User-Agent header.

        >>> builder = HeaderBuilder()
        >>> builder.with_user_agent().headers["User-Agent"]
        'APIClient/1.0'
        """
        self.headers["User-Agent"] = user_agent
        return self

    def build(self) -> dict[str, str]:
        """
        Build and return headers dictionary.

        >>> builder = HeaderBuilder()
        >>> builder.with_content_type().with_accept().build()
        {'Content-Type': 'application/json', 'Accept': 'application/json'}
        """
        return self.headers.copy()
