"""API client with planted input validation bugs.

DX-74 Test Scenario - File 3/6
Bugs: 8 input validation issues
"""

import re


def build_url(base: str, path: str) -> str:
    """Build a URL from base and path.

    # BUG-18: No validation of base URL format
    """
    return f"{base}/{path}"


def make_request(url: str, method: str = "GET") -> dict:
    """Make an HTTP request.

    # BUG-19: No validation of HTTP method
    """
    # Simulated request
    return {"url": url, "method": method, "status": 200}


def parse_response(response: str) -> dict:
    """Parse API response.

    # BUG-20: No input length validation (potential DoS)
    """
    import json
    return json.loads(response)


def validate_email(email: str) -> bool:
    """Validate an email address.

    # BUG-21: Weak email validation regex
    """
    pattern = r".+@.+"  # Too permissive
    return bool(re.match(pattern, email))


def sanitize_input(user_input: str) -> str:
    """Sanitize user input for display.

    # BUG-22: Incomplete XSS sanitization
    """
    # Only removes script tags, not other XSS vectors
    return user_input.replace("<script>", "").replace("</script>", "")


def build_query_string(params: dict) -> str:
    """Build a query string from parameters.

    # BUG-23: No URL encoding for special characters
    """
    parts = [f"{k}={v}" for k, v in params.items()]
    return "&".join(parts)


def parse_user_id(user_id_str: str) -> int:
    """Parse a user ID from string.

    # BUG-24: No validation of negative values
    """
    return int(user_id_str)


def validate_phone(phone: str) -> bool:
    """Validate a phone number.

    # BUG-25: No format validation, accepts any digits
    """
    return phone.isdigit()


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a currency amount.

    This one is OK - simple formatting
    """
    return f"{currency} {amount:.2f}"


def paginate_results(items: list, page: int, per_page: int) -> list:
    """Paginate a list of items.

    This one is OK - basic pagination
    """
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def validate_username(username: str) -> bool:
    """Validate a username.

    This one is OK - reasonable validation
    """
    if not username or len(username) < 3 or len(username) > 50:
        return False
    return username.isalnum()
