"""
User Service Module

Handles user authentication, registration, profile management,
and session handling for the application.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class UserRole(Enum):
    """User roles in the system."""
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserStatus(Enum):
    """User account status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class UserProfile:
    """User profile information."""
    user_id: str
    username: str
    email: str
    display_name: str
    avatar_url: str | None = None
    bio: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class User:
    """User entity with authentication data."""
    id: str
    username: str
    email: str
    password_hash: str
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING
    profile: UserProfile | None = None
    last_login: datetime | None = None
    failed_attempts: int = 0
    locked_until: datetime | None = None

    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def can_login(self) -> bool:
        """Check if user can attempt login."""
        if self.status != UserStatus.ACTIVE:
            return False
        return not self.is_locked()


@dataclass
class Session:
    """User session data."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_valid: bool = True

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at


class UserRepository(Protocol):
    """Protocol for user data storage."""

    def get_by_id(self, user_id: str) -> User | None: ...
    def get_by_username(self, username: str) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def save(self, user: User) -> bool: ...
    def delete(self, user_id: str) -> bool: ...


class SessionRepository(Protocol):
    """Protocol for session storage."""

    def get(self, session_id: str) -> Session | None: ...
    def save(self, session: Session) -> bool: ...
    def delete(self, session_id: str) -> bool: ...
    def delete_user_sessions(self, user_id: str) -> int: ...


class PasswordHasher:
    """Handles password hashing and verification."""

    ALGORITHM = "sha256"
    ITERATIONS = 100000
    SALT_LENGTH = 32

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password with a random salt."""
        salt = secrets.token_hex(cls.SALT_LENGTH)
        key = hashlib.pbkdf2_hmac(
            cls.ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.ITERATIONS,
        )
        return f"{salt}${key.hex()}"

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_key = password_hash.split("$")
            key = hashlib.pbkdf2_hmac(
                cls.ALGORITHM,
                password.encode("utf-8"),
                salt.encode("utf-8"),
                cls.ITERATIONS,
            )
            return hmac.compare_digest(key.hex(), stored_key)
        except (ValueError, AttributeError):
            return False


class EmailValidator:
    """Email validation utilities."""

    # Standard email regex pattern
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # Disposable email domains to block
    BLOCKED_DOMAINS = {
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "10minutemail.com", "mailinator.com",
    }

    @classmethod
    def is_valid(cls, email: str) -> bool:
        """Check if email format is valid."""
        if not email or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def is_allowed(cls, email: str) -> bool:
        """Check if email domain is allowed."""
        if not cls.is_valid(email):
            return False
        domain = email.split("@")[1].lower()
        return domain not in cls.BLOCKED_DOMAINS


class UsernameValidator:
    """Username validation utilities."""

    MIN_LENGTH = 3
    MAX_LENGTH = 30
    PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

    # Reserved usernames
    RESERVED = {
        "admin", "administrator", "root", "system", "moderator",
        "support", "help", "api", "www", "mail", "ftp",
    }

    @classmethod
    def is_valid(cls, username: str) -> bool:
        """Validate username format and length."""
        if not username:
            return False
        if len(username) < cls.MIN_LENGTH or len(username) > cls.MAX_LENGTH:
            return False
        if not cls.PATTERN.match(username):
            return False
        return username.lower() not in cls.RESERVED


class PasswordValidator:
    """Password strength validation."""

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    @classmethod
    def is_strong(cls, password: str) -> tuple[bool, list[str]]:
        """Check password strength. Returns (is_valid, list of issues)."""
        issues = []

        if len(password) < cls.MIN_LENGTH:
            issues.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        if len(password) > cls.MAX_LENGTH:
            issues.append(f"Password must be at most {cls.MAX_LENGTH} characters")
        if not re.search(r"[A-Z]", password):
            issues.append("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            issues.append("Password must contain at least one lowercase letter")
        if not re.search(r"\d", password):
            issues.append("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            issues.append("Password must contain at least one special character")

        return len(issues) == 0, issues


class RateLimiter:
    """Simple rate limiting for authentication attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if action is allowed for the given key."""
        now = time.time()
        cutoff = now - self.window_seconds

        if key not in self._attempts:
            self._attempts[key] = []

        # Clean old attempts
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

        return len(self._attempts[key]) < self.max_attempts

    def record_attempt(self, key: str) -> None:
        """Record an attempt for the given key."""
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(time.time())

    def reset(self, key: str) -> None:
        """Reset attempts for the given key."""
        self._attempts.pop(key, None)


class UserService:
    """Main user service handling authentication and user management."""

    SESSION_DURATION_HOURS = 24
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        rate_limiter: RateLimiter | None = None,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.rate_limiter = rate_limiter or RateLimiter()

    def register(
        self,
        username: str,
        email: str,
        password: str,
    ) -> tuple[User | None, list[str]]:
        """Register a new user. Returns (user, errors)."""
        errors = []

        # Validate username
        if not UsernameValidator.is_valid(username):
            errors.append("Invalid username format")

        # Validate email
        if not EmailValidator.is_allowed(email):
            errors.append("Invalid or blocked email address")

        # Validate password
        is_strong, password_issues = PasswordValidator.is_strong(password)
        if not is_strong:
            errors.extend(password_issues)

        if errors:
            return None, errors

        # Check for existing user
        if self.user_repo.get_by_username(username):
            errors.append("Username already taken")
            return None, errors

        if self.user_repo.get_by_email(email):
            errors.append("Email already registered")
            return None, errors

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=PasswordHasher.hash_password(password),
            status=UserStatus.PENDING,
        )

        # Create profile
        user.profile = UserProfile(
            user_id=user.id,
            username=username,
            email=email,
            display_name=username,
        )

        if not self.user_repo.save(user):
            errors.append("Failed to create user")
            return None, errors

        logger.info(f"User registered: {username}")
        return user, []

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str,
    ) -> tuple[Session | None, str | None]:
        """Authenticate user and create session. Returns (session, error)."""
        # Check rate limiting
        rate_key = f"auth:{ip_address}"
        if not self.rate_limiter.is_allowed(rate_key):
            return None, "Too many login attempts. Please try again later."

        # Find user
        user = self.user_repo.get_by_username(username)
        if not user:
            self.rate_limiter.record_attempt(rate_key)
            return None, "Invalid username or password"

        # Check if account can login
        if not user.can_login():
            if user.is_locked():
                return None, "Account is locked. Please try again later."
            return None, "Account is not active"

        # Verify password
        if not PasswordHasher.verify_password(password, user.password_hash):
            self.rate_limiter.record_attempt(rate_key)
            user.failed_attempts += 1

            # Lock account if too many failed attempts
            if user.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=self.LOCKOUT_DURATION_MINUTES
                )
                logger.warning(f"Account locked due to failed attempts: {username}")

            self.user_repo.save(user)
            return None, "Invalid username or password"

        # Reset failed attempts on successful login
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.user_repo.save(user)

        # Create session
        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=self.SESSION_DURATION_HOURS),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not self.session_repo.save(session):
            return None, "Failed to create session"

        self.rate_limiter.reset(rate_key)
        logger.info(f"User authenticated: {username}")
        return session, None

    def validate_session(self, session_id: str) -> tuple[User | None, str | None]:
        """Validate session and return user. Returns (user, error)."""
        session = self.session_repo.get(session_id)

        if not session:
            return None, "Session not found"

        if not session.is_valid:
            return None, "Session has been invalidated"

        if session.is_expired():
            self.session_repo.delete(session_id)
            return None, "Session has expired"

        user = self.user_repo.get_by_id(session.user_id)
        if not user:
            return None, "User not found"

        if user.status != UserStatus.ACTIVE:
            return None, "User account is not active"

        return user, None

    def logout(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = self.session_repo.get(session_id)
        if session:
            session.is_valid = False
            return self.session_repo.delete(session_id)
        return False

    def logout_all(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        return self.session_repo.delete_user_sessions(user_id)

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> tuple[bool, str | None]:
        """Change user password. Returns (success, error)."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"

        # Verify current password
        if not PasswordHasher.verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"

        # Validate new password
        is_strong, issues = PasswordValidator.is_strong(new_password)
        if not is_strong:
            return False, "; ".join(issues)

        # Update password
        user.password_hash = PasswordHasher.hash_password(new_password)
        if not self.user_repo.save(user):
            return False, "Failed to update password"

        # Invalidate all sessions
        self.logout_all(user_id)

        logger.info(f"Password changed for user: {user.username}")
        return True, None

    def request_password_reset(self, email: str) -> str | None:
        """Request password reset. Returns reset token or None."""
        user = self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return None

        # Generate reset token (valid for 1 hour)
        token = secrets.token_urlsafe(32)
        # In real implementation, store token with expiry

        logger.info(f"Password reset requested for: {email}")
        return token

    def update_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[UserProfile | None, str | None]:
        """Update user profile. Returns (profile, error)."""
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.profile:
            return None, "User not found"

        if display_name is not None:
            if len(display_name) < 1 or len(display_name) > 50:
                return None, "Display name must be 1-50 characters"
            user.profile.display_name = display_name

        if bio is not None:
            if len(bio) > 500:
                return None, "Bio must be at most 500 characters"
            user.profile.bio = bio

        if avatar_url is not None:
            user.profile.avatar_url = avatar_url

        user.profile.updated_at = datetime.utcnow()

        if not self.user_repo.save(user):
            return None, "Failed to update profile"

        return user.profile, None

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.user_repo.get_by_id(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return self.user_repo.get_by_username(username)

    def activate_user(self, user_id: str) -> bool:
        """Activate a pending user account."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False

        if user.status != UserStatus.PENDING:
            return False

        user.status = UserStatus.ACTIVE
        return self.user_repo.save(user)

    def suspend_user(self, user_id: str, reason: str) -> bool:
        """Suspend a user account."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False

        user.status = UserStatus.SUSPENDED
        self.logout_all(user_id)

        logger.warning(f"User suspended: {user.username}, reason: {reason}")
        return self.user_repo.save(user)

    def delete_user(self, user_id: str) -> bool:
        """Soft delete a user account."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False

        user.status = UserStatus.DELETED
        self.logout_all(user_id)

        logger.info(f"User deleted: {user.username}")
        return self.user_repo.save(user)

    def set_user_role(self, user_id: str, role: UserRole) -> bool:
        """Set user role (admin only operation)."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False

        user.role = role
        logger.info(f"User role changed: {user.username} -> {role.value}")
        return self.user_repo.save(user)


# Utility functions for API layer

def generate_api_key() -> str:
    """Generate a new API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def format_user_response(user: User, include_email: bool = False) -> dict[str, Any]:
    """Format user data for API response."""
    response = {
        "id": user.id,
        "username": user.username,
        "role": user.role.value,
        "status": user.status.value,
    }

    if include_email:
        response["email"] = user.email

    if user.profile:
        response["profile"] = {
            "display_name": user.profile.display_name,
            "avatar_url": user.profile.avatar_url,
            "bio": user.profile.bio,
        }

    return response


def parse_authorization_header(header: str) -> tuple[str, str] | None:
    """Parse Authorization header. Returns (scheme, token) or None."""
    if not header:
        return None

    parts = header.split(" ", 1)
    if len(parts) != 2:
        return None

    return parts[0], parts[1]


def validate_content_type(content_type: str, expected: str = "application/json") -> bool:
    """Validate Content-Type header."""
    if not content_type:
        return False
    return content_type.lower().startswith(expected.lower())


class AuditLogger:
    """Audit logging for security events."""

    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file

    def log_event(
        self,
        event_type: str,
        user_id: str | None,
        ip_address: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a security event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
        }

        # Write to log file
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            logger.error(f"Failed to write audit log: {event_type}")

    def log_login_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool,
    ) -> None:
        """Log a login attempt."""
        self.log_event(
            "login_attempt",
            None,
            ip_address,
            {"username": username, "success": success},
        )

    def log_password_change(self, user_id: str, ip_address: str) -> None:
        """Log a password change."""
        self.log_event("password_change", user_id, ip_address)

    def log_role_change(
        self,
        user_id: str,
        old_role: str,
        new_role: str,
        changed_by: str,
        ip_address: str,
    ) -> None:
        """Log a role change."""
        self.log_event(
            "role_change",
            user_id,
            ip_address,
            {"old_role": old_role, "new_role": new_role, "changed_by": changed_by},
        )
