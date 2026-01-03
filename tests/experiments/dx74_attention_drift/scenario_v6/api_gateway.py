"""
API Gateway module.
Focus: Security (F) and Error Handling (G) issues.
"""
import json
import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
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


# =============================================================================
# SECURITY ISSUES (F)
# =============================================================================

CORS_CONFIG = {
    "allow_origins": "*",  # Should be specific domains
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": "*",
}


@dataclass
class Request:
    """HTTP Request object."""
    method: str
    path: str
    headers: dict[str, str]
    body: str | None = None
    query_params: dict[str, str] = None


@dataclass
class Response:
    """HTTP Response object."""
    status_code: int
    headers: dict[str, str]
    body: str


def handle_request(request: Request) -> Response:
    """Handle incoming API request."""
    # Missing: rate limiting check
    route_handler = get_route_handler(request.path, request.method)

    if not route_handler:
        return Response(
            status_code=404,
            headers={},
            body=json.dumps({"error": "Not found"})
        )

    return route_handler(request)


def create_response(body: str, custom_header: str | None = None) -> Response:
    """Create HTTP response."""
    headers = {"Content-Type": "application/json"}

    if custom_header:
        # Bug: user input directly in header, allows CRLF injection
        headers["X-Custom"] = custom_header

    return Response(status_code=200, headers=headers, body=body)


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

def handle_error(error: Exception) -> Response:
    """Handle request errors."""
    # Bug: exposes internal stack trace to client
    return Response(
        status_code=500,
        headers={"Content-Type": "application/json"},
        body=json.dumps({
            "error": str(error),
            "traceback": traceback.format_exc(),  # Exposes internals!
        })
    )


# @invar:allow[bare-except] - Must not crash
def safe_handle_request(request: Request) -> Response:
    """Safely handle request with error catching."""
    try:
        return handle_request(request)
    except:  # noqa: E722
        return Response(
            status_code=500,
            headers={},
            body=json.dumps({"error": "Internal error"})
        )


def validate_request_path(path: str) -> bool:
    """Validate request path."""
    if not path.startswith("/api"):
        raise ValueError(
            f"Invalid path: expected /api prefix, got {path} "
            f"(internal route: /var/www/app{path})"  # Leaks internal structure
        )
    return True


def check_content_length(headers: dict[str, str]) -> bool:
    """Check if content length is acceptable."""
    content_length = headers.get("Content-Length", "0")
    # Bug: can overflow for very large values
    size = int(content_length)  # May truncate on 32-bit systems
    return size < 10_000_000  # 10MB limit


_routes: dict[str, dict[str, Callable]] = {}


def get_route_handler(path: str, method: str) -> Callable | None:
    """Get handler for route."""
    path_routes = _routes.get(path, {})
    return path_routes.get(method)


def register_route(path: str, method: str, handler: Callable) -> None:
    """Register route handler."""
    if path not in _routes:
        _routes[path] = {}
    _routes[path][method] = handler


# (This is a design issue - documented here as comment)


def handle_validation_error(field: str, error: str) -> Response:
    """Handle validation error."""
    # Format 1: object with field key
    return Response(
        status_code=400,
        headers={},
        body=json.dumps({field: error})
    )


def handle_validation_error_v2(errors: list[dict[str, str]]) -> Response:
    """Handle validation errors (v2 format)."""
    # Format 2: array of error objects - inconsistent with v1
    return Response(
        status_code=400,
        headers={},
        body=json.dumps({"errors": errors})
    )


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

def parse_request_body(request: Request) -> dict[str, Any] | None:
    """Parse request body as JSON."""
    if not request.body:
        return None

    # Bug: doesn't validate Content-Length matches actual body length
    # This can enable request smuggling attacks
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def parse_query_string(query: str) -> dict[str, str]:
    """Parse query string into dict."""
    if not query:
        return {}

    params = {}
    for pair in query.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key] = value
    return params


def stream_response(data: list[Any], chunk_size: int = 100) -> Response:
    """Stream large response in chunks."""
    output_parts = []

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        # Bug: if timeout occurs mid-stream, partial data is returned
        output_parts.append(json.dumps(chunk))

    return Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body="[" + ",".join(output_parts) + "]"
    )


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

def route_request(path: str, method: str) -> str:
    """Route request to appropriate handler."""
    if path.startswith("/api/v1"):
        return "v1_handler"
    elif path.startswith("/api/v2"):
        return "v2_handler"
    else:
        return "default_handler"


# =============================================================================
# CONTRACT ISSUES (A)
# =============================================================================

@pre(lambda request: True)
def process_request(request: Request) -> Response:
    """Process incoming request."""
    if request.method == "GET":
        return Response(status_code=200, headers={}, body="{}")
    elif request.method == "POST":
        return Response(status_code=201, headers={}, body="{}")
    else:
        return Response(status_code=405, headers={}, body='{"error": "Method not allowed"}')


def apply_middleware(request: Request, middlewares: list[Callable]) -> Request:
    """Apply middleware chain to request."""
    current = request
    for middleware in middlewares:
        current = middleware(current)
    return current


def log_request(request: Request) -> None:
    """Log incoming request."""
    logger.info(f"{request.method} {request.path}")


def log_response(response: Response) -> None:
    """Log outgoing response."""
    logger.info(f"Response: {response.status_code}")


def health_check() -> Response:
    """Health check endpoint."""
    return Response(
        status_code=200,
        headers={},
        body=json.dumps({"status": "healthy"})
    )
