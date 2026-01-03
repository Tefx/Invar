"""Authentication service with planted security bugs.

DX-74 Test Scenario - File 1/6
Bugs: 8 security-related issues
"""

import hashlib

# BUG-01: Hardcoded secret key
SECRET_KEY = "super_secret_key_12345"

# BUG-02: Hardcoded database password
DB_PASSWORD = "admin123"


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    # BUG-03: Using weak hashing algorithm (MD5)
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == hashed


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate a user by username and password."""
    # BUG-04: SQL injection vulnerability (string formatting)
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

    # Simulated database call
    try:
        result = execute_query(query)
        return result
    # BUG-05: Bare except swallows all errors
    except Exception:
        return None


def execute_query(query: str) -> dict:
    """Execute a database query (simulated)."""
    return {"id": 1, "username": "test"}


def generate_token(user_id: int) -> str:
    """Generate an authentication token."""
    # BUG-06: Predictable token generation (no randomness)
    token = f"token_{user_id}_{SECRET_KEY}"
    return hashlib.sha256(token.encode()).hexdigest()


def validate_token(token: str) -> bool:
    """Validate an authentication token."""
    try:
        # Token validation logic
        return len(token) == 64
    # BUG-07: Bare except hides validation errors
    except Exception:
        return False


# BUG-08: API key exposed in code
API_KEY = "ak_live_1234567890abcdef"


def call_external_api(endpoint: str) -> dict:
    """Call an external API with authentication."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    # Simulated API call
    return {"status": "ok"}


def logout_user(session_id: str) -> bool:
    """Logout a user by invalidating their session."""
    try:
        invalidate_session(session_id)
        return True
    except Exception as e:
        # This one is OK - specific exception handling
        print(f"Logout failed: {e}")
        return False


def invalidate_session(session_id: str) -> None:
    """Invalidate a session (simulated)."""
    pass
