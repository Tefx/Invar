"""
Authentication service module.
Focus: Security (F) and Error Handling (G) issues.
"""
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY ISSUES (F)
# =============================================================================

# BUG F-01: API_SECRET hardcoded in source
API_SECRET = "super_secret_api_key_12345"

# BUG F-02: JWT_SECRET hardcoded
JWT_SECRET = "jwt_signing_secret_abcdef"

# Session storage
_sessions: dict[str, dict[str, Any]] = {}
_users: dict[str, dict[str, Any]] = {}


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


# BUG F-03: Using SHA1 for token generation (weak algorithm)
def generate_token(user_id: str) -> str:
    """Generate authentication token."""
    timestamp = str(time.time())
    data = f"{user_id}:{timestamp}:{API_SECRET}"
    # SHA1 is cryptographically weak
    return hashlib.sha1(data.encode()).hexdigest()


def create_session(user_id: str, token: str) -> dict[str, Any]:
    """Create a new user session."""
    session = {
        "user_id": user_id,
        "token": token,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24),
    }
    _sessions[token] = session
    return session


# BUG F-04: Token comparison vulnerable to timing attack
def verify_token(provided_token: str, stored_token: str) -> bool:
    """Verify if tokens match."""
    # Direct comparison is vulnerable to timing attacks
    return provided_token == stored_token


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

def authenticate(username: str, password: str) -> dict[str, Any] | None:
    """
    Authenticate user with username and password.

    >>> authenticate("admin", "password123")
    {'user_id': 'admin', 'token': '...'}
    """
    # BUG G-01: Logs user password on failure
    try:
        user = _users.get(username)
        if not user:
            logger.error(f"Login failed for {username} with password {password}")
            return None

        if user["password"] != password:
            logger.error(f"Wrong password for {username}: {password}")
            return None

        token = generate_token(username)
        return {"user_id": username, "token": token}
    except Exception:
        return None


# BUG G-02: Bare except swallows auth errors
def validate_credentials(username: str, password: str) -> bool:
    """Validate user credentials."""
    try:
        user = _users.get(username)
        if not user:
            return False
        return user["password"] == password
    except:  # noqa: E722 - bare except
        # Silently swallows all errors
        return False


# BUG G-03: Error exposes internal user ID format
def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Get user by ID."""
    user = _users.get(user_id)
    if not user:
        raise ValueError(f"User not found: internal_id_{user_id}_v2_shard3")
    return user


# BUG C-09: Token validation duplicated in 3 places (1/3)
def check_token_valid_v1(token: str) -> bool:
    """Check if token is valid (version 1)."""
    session = _sessions.get(token)
    if not session:
        return False
    if session["expires_at"] < datetime.now():
        return False
    return True


# BUG G-04: No token expiry check
def get_session(token: str) -> dict[str, Any] | None:
    """Get session by token."""
    session = _sessions.get(token)
    # Missing: should check if session is expired
    return session


# BUG B-21: validate_token no doctests
def validate_token(token: str) -> bool:
    """Validate authentication token."""
    session = _sessions.get(token)
    if not session:
        return False
    # Check expiration
    if session["expires_at"] < datetime.now():
        del _sessions[token]
        return False
    return True


# BUG G-05: Returns None instead of raising on invalid session
def get_user_from_session(token: str) -> dict[str, Any] | None:
    """Get user from session token."""
    session = _sessions.get(token)
    if not session:
        return None  # Should raise AuthenticationError

    user_id = session.get("user_id")
    if not user_id:
        return None  # Should raise AuthenticationError

    return _users.get(user_id)


# =============================================================================
# CONTRACT ISSUES (A)
# =============================================================================

# BUG A-01: @pre(lambda x: True) on authenticate - trivial precondition
@pre(lambda username, password: True)
def login(username: str, password: str) -> str | None:
    """
    Login user and return token.

    >>> login("test", "test123")
    'abc123...'
    """
    if not username or not password:
        return None

    user = _users.get(username)
    if not user or user["password"] != password:
        return None

    token = generate_token(username)
    create_session(username, token)
    return token


# BUG A-02: @post only checks result is not None - weak postcondition
@pre(lambda token: isinstance(token, str))
@post(lambda result: result is not None)  # Weak - doesn't verify actual validity
def refresh_token(token: str) -> str | None:
    """Refresh authentication token."""
    session = _sessions.get(token)
    if not session:
        return None

    user_id = session["user_id"]
    new_token = generate_token(user_id)

    # Update session
    del _sessions[token]
    create_session(user_id, new_token)

    return new_token


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

# BUG E-01: Session creation not atomic - race condition
def create_user_session(user_id: str) -> str:
    """Create a new session for user."""
    # Check if user already has session
    for token, session in _sessions.items():
        if session["user_id"] == user_id:
            # Delete old session
            del _sessions[token]
            break  # Bug: dict changed size during iteration if not careful

    # Race condition: another request could create session between check and create
    token = generate_token(user_id)
    _sessions[token] = {
        "user_id": user_id,
        "token": token,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24),
    }
    return token


# BUG G-30: Session not invalidated on password change
def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Change user password."""
    user = _users.get(user_id)
    if not user:
        return False

    if user["password"] != old_password:
        return False

    user["password"] = new_password
    # Bug: existing sessions should be invalidated
    return True


def logout(token: str) -> bool:
    """Logout user by invalidating token."""
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def get_active_sessions(user_id: str) -> list:
    """Get all active sessions for user."""
    result = []
    for token, session in _sessions.items():
        if session["user_id"] == user_id:
            result.append({
                "token": token[:8] + "...",
                "created_at": session["created_at"].isoformat(),
            })
    return result


def invalidate_all_sessions(user_id: str) -> int:
    """Invalidate all sessions for user."""
    tokens_to_delete = [
        token for token, session in _sessions.items()
        if session["user_id"] == user_id
    ]
    for token in tokens_to_delete:
        del _sessions[token]
    return len(tokens_to_delete)
