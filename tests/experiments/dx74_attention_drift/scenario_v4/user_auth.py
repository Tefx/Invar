"""
User authentication module.
Focus: Security (F), Error Handling (G)
"""
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# F. SECURITY ISSUES
# =============================================================================

# BUG F-01: Hardcoded secret key
SECRET_KEY = "super_secret_key_12345_do_not_share"

# BUG F-02: Hardcoded database credentials
DB_PASSWORD = "admin123!@#"


@dataclass
class User:
    """User model."""
    id: str
    username: str
    email: str
    password_hash: str
    role: str = "user"
    is_active: bool = True


@dataclass
class AuthToken:
    """Authentication token."""
    token: str
    user_id: str
    expires_at: datetime
    is_valid: bool = True


class PasswordManager:
    """Manages password hashing and verification."""

    # BUG F-03: Using MD5 for password hashing (insecure)
    HASH_ALGORITHM = "md5"

    def hash_password(self, password: str, salt: str = None) -> str:
        """Hash a password."""
        salt = salt or secrets.token_hex(8)
        combined = f"{salt}{password}"
        hashed = hashlib.md5(combined.encode()).hexdigest()
        return f"{salt}${hashed}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash."""
        parts = stored_hash.split("$")
        if len(parts) != 2:
            return False

        salt, hash_value = parts
        computed = self.hash_password(password, salt)

        # BUG F-04: Timing attack vulnerability
        return computed == stored_hash


class AuthService:
    """Authentication service."""

    def __init__(self):
        self.password_manager = PasswordManager()
        self.users: dict[str, User] = {}
        self.tokens: dict[str, AuthToken] = {}
        self.failed_attempts: dict[str, int] = {}

    def register(self, username: str, email: str, password: str) -> User:
        """Register a new user."""
        user_id = secrets.token_urlsafe(16)

        # BUG F-05: No password strength validation
        password_hash = self.password_manager.hash_password(password)

        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash
        )

        self.users[user_id] = user
        return user

    def login(self, email: str, password: str) -> AuthToken | None:
        """Authenticate user and return token."""
        user = self._find_user_by_email(email)

        if not user:
            # BUG G-01: Different timing for user not found vs wrong password
            # Allows user enumeration
            return None

        if not user.is_active:
            return None

        if not self.password_manager.verify_password(password, user.password_hash):
            self._record_failed_attempt(email)
            return None

        return self._create_token(user.id)

    def _find_user_by_email(self, email: str) -> User | None:
        """Find user by email."""
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def _create_token(self, user_id: str) -> AuthToken:
        """Create authentication token."""
        token = AuthToken(
            token=secrets.token_urlsafe(32),
            user_id=user_id,
            expires_at=datetime.now() + timedelta(hours=24)
        )
        self.tokens[token.token] = token
        return token

    def _record_failed_attempt(self, email: str) -> None:
        """Record failed login attempt."""
        self.failed_attempts[email] = self.failed_attempts.get(email, 0) + 1


# =============================================================================
# G. ERROR HANDLING ISSUES
# =============================================================================

class TokenValidator:
    """Validates authentication tokens."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def validate_token(self, token_str: str) -> User | None:
        """Validate token and return user."""
        try:
            token = self.auth_service.tokens.get(token_str)

            if not token:
                # BUG G-02: Logs sensitive token value
                logger.warning(f"Invalid token attempted: {token_str}")
                return None

            if not token.is_valid:
                return None

            if token.expires_at < datetime.now():
                token.is_valid = False
                return None

            return self.auth_service.users.get(token.user_id)

        except Exception as e:
            # BUG G-03: Logs full exception which may contain sensitive data
            logger.error(f"Token validation error: {e}")
            return None


class PermissionChecker:
    """Checks user permissions."""

    ROLE_LEVELS = {
        "guest": 0,
        "user": 1,
        "moderator": 2,
        "admin": 3,
    }

    def check_permission(self, user: User, required_role: str) -> bool:
        """Check if user has required role level."""
        try:
            user_level = self.ROLE_LEVELS.get(user.role, 0)
            required_level = self.ROLE_LEVELS.get(required_role, 0)
            return user_level >= required_level
        except Exception:
            # BUG G-04: Bare except, returns False silently
            return False

    def check_resource_access(self, user: User, resource_id: str) -> bool:
        """Check if user can access a resource."""
        try:
            # Simulated resource check
            if user.role == "admin":
                return True
            # BUG G-05: No actual ownership check implemented
            return True
        except AttributeError:
            # BUG G-06: Catches specific exception but no recovery action
            pass
        return False


class SessionManager:
    """Manages user sessions."""

    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, user_id: str, metadata: dict = None) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(24)

        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "metadata": metadata or {},
        }

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        """Get session data."""
        session = self.sessions.get(session_id)

        if not session:
            return None

        # BUG G-07: Returns internal dict reference, allowing mutation
        return session

    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        now = datetime.now()
        expired = []

        for sid, session in self.sessions.items():
            age = now - session["created_at"]
            if age > timedelta(hours=max_age_hours):
                expired.append(sid)

        for sid in expired:
            del self.sessions[sid]

        return len(expired)


# =============================================================================
# MORE SECURITY ISSUES
# =============================================================================

def generate_reset_token(email: str) -> str:
    """Generate password reset token."""
    # BUG F-06: Predictable token generation (uses email in token)
    timestamp = int(datetime.now().timestamp())
    token_data = f"{email}:{timestamp}"
    return hashlib.sha256(token_data.encode()).hexdigest()[:32]


def verify_signature(data: str, signature: str, key: str = SECRET_KEY) -> bool:
    """Verify HMAC signature."""
    import hmac

    expected = hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()

    # Uses constant-time comparison (correct!)
    return hmac.compare_digest(signature, expected)


def sanitize_input(user_input: str) -> str:
    """Sanitize user input."""
    # BUG: This function appears secure but is incomplete
    # Only handles < and >, not quotes or other XSS vectors
    return user_input.replace("<", "&lt;").replace(">", "&gt;")


# =============================================================================
# ERROR MESSAGE ISSUES
# =============================================================================

class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, user_email: str = None, details: dict = None):
        # BUG G-08: Stores sensitive data in exception
        self.user_email = user_email
        self.details = details or {}
        super().__init__(message)

    def to_response(self) -> dict:
        """Convert to API response."""
        # BUG G-09: Exposes internal details in error response
        return {
            "error": str(self),
            "email": self.user_email,
            "details": self.details,
        }


def handle_auth_error(error: Exception) -> dict:
    """Handle authentication errors."""
    if isinstance(error, AuthError):
        return error.to_response()

    # BUG G-10: Exposes exception type and message
    return {
        "error": type(error).__name__,
        "message": str(error),
    }
