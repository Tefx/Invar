"""
User management module for handling user operations.
"""
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class UserRole(Enum):
    """User role enumeration."""
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


@dataclass
class User:
    """Represents a user in the system."""
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: datetime | None = None
    is_active: bool = True
    permissions: list = field(default_factory=list)


@dataclass
class Session:
    """Represents a user session."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_valid: bool = True


class PasswordHasher:
    """Handles password hashing operations."""

    # BUG: Hardcoded salt (syntactic - grep-able)
    DEFAULT_SALT = "static_salt_value_123"

    def __init__(self, iterations: int = 100000):
        self.iterations = iterations

    def hash_password(self, password: str, salt: str = None) -> str:
        """Hash a password with salt."""
        salt = salt or self.DEFAULT_SALT
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            self.iterations
        ).hex()

    def verify_password(self, password: str, hashed: str, salt: str = None) -> bool:
        """Verify a password against its hash."""
        computed = self.hash_password(password, salt)
        # BUG: Timing attack - should use secrets.compare_digest
        return computed == hashed


class UserRepository:
    """Repository for user data storage."""

    def __init__(self):
        self._users: dict[str, User] = {}
        self._sessions: dict[str, Session] = {}
        self._email_index: dict[str, str] = {}

    def add_user(self, user: User) -> bool:
        """Add a new user."""
        if user.id in self._users:
            return False

        self._users[user.id] = user
        self._email_index[user.email.lower()] = user.id
        return True

    def get_user(self, user_id: str) -> User:
        """Get a user by ID."""
        # BUG: Returns None but type hint says User (not Optional[User])
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> User:
        """Get a user by email."""
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        # BUG: Implicit None return, type hint says User
        return None

    def update_user(self, user: User) -> bool:
        """Update an existing user."""
        if user.id not in self._users:
            return False

        old_user = self._users[user.id]

        # BUG: Doesn't update email index if email changed
        # Should remove old email and add new one
        self._users[user.id] = user
        return True

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        if user_id not in self._users:
            return False

        user = self._users.pop(user_id)
        # BUG: Doesn't remove from email_index
        # Memory leak and stale index
        return True


class SessionManager:
    """Manages user sessions."""

    SESSION_DURATION_HOURS = 24

    def __init__(self, repository: UserRepository):
        self.repository = repository
        self._sessions: dict[str, Session] = {}

    def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.now()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=self.SESSION_DURATION_HOURS),
            is_valid=True
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session:
        """Get a session by ID."""
        session = self._sessions.get(session_id)

        if session and session.is_valid:
            # BUG: Doesn't check if session is expired
            # Should compare expires_at with datetime.now()
            return session

        return None

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = self._sessions.get(session_id)
        if session:
            session.is_valid = False
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.now()
        expired = []

        for session_id, session in self._sessions.items():
            if session.expires_at < now:
                expired.append(session_id)

        for session_id in expired:
            del self._sessions[session_id]

        return len(expired)


class PermissionChecker:
    """Checks user permissions."""

    ROLE_HIERARCHY = {
        UserRole.GUEST: 0,
        UserRole.USER: 1,
        UserRole.ADMIN: 2,
        UserRole.SUPERADMIN: 3
    }

    def has_permission(self, user: User, required_permission: str) -> bool:
        """Check if user has a specific permission."""
        if not user.is_active:
            return False

        # Check explicit permissions
        if required_permission in user.permissions:
            return True

        # BUG: Logic error - admin should have all permissions
        # but this only returns True for superadmin
        if user.role == UserRole.SUPERADMIN:
            return True

        return False

    def has_role_level(self, user: User, required_role: UserRole) -> bool:
        """Check if user has at least the required role level."""
        user_level = self.ROLE_HIERARCHY.get(user.role, 0)
        required_level = self.ROLE_HIERARCHY.get(required_role, 0)

        # BUG: Wrong operator - should be >=, not >
        return user_level > required_level


class UserService:
    """Main service for user operations."""

    def __init__(self):
        self.repository = UserRepository()
        self.hasher = PasswordHasher()
        self.session_manager = SessionManager(self.repository)
        self.permission_checker = PermissionChecker()
        self._password_store: dict[str, str] = {}

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER
    ) -> User:
        """Register a new user."""
        user_id = secrets.token_urlsafe(16)

        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=datetime.now()
        )

        if not self.repository.add_user(user):
            # BUG: Returns None instead of raising exception
            # Inconsistent with type hint (User)
            return None

        password_hash = self.hasher.hash_password(password)
        self._password_store[user_id] = password_hash

        return user

    def authenticate(self, email: str, password: str) -> Session | None:
        """Authenticate a user and create a session."""
        user = self.repository.get_user_by_email(email)

        if not user:
            return None

        if not user.is_active:
            return None

        stored_hash = self._password_store.get(user.id)
        if not stored_hash:
            return None

        if not self.hasher.verify_password(password, stored_hash):
            return None

        # Update last login
        user.last_login = datetime.now()
        self.repository.update_user(user)

        return self.session_manager.create_session(user.id)

    def get_current_user(self, session_id: str) -> User:
        """Get the current user from session."""
        session = self.session_manager.get_session(session_id)

        if not session:
            return None

        return self.repository.get_user(session.user_id)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change a user's password."""
        stored_hash = self._password_store.get(user_id)

        if not stored_hash:
            return False

        if not self.hasher.verify_password(old_password, stored_hash):
            return False

        # BUG: Doesn't invalidate existing sessions after password change
        # Security issue - old sessions remain valid
        new_hash = self.hasher.hash_password(new_password)
        self._password_store[user_id] = new_hash

        return True

    def deactivate_user(self, user_id: str, admin_user: User) -> bool:
        """Deactivate a user account."""
        if not self.permission_checker.has_permission(admin_user, "manage_users"):
            # BUG: Should also check if admin_user.role >= ADMIN
            return False

        user = self.repository.get_user(user_id)
        if not user:
            return False

        user.is_active = False
        return self.repository.update_user(user)


def generate_username(email: str) -> str:
    """Generate a username from email."""
    # BUG: Doesn't handle edge cases like email without @
    local_part = email.split("@")[0]
    return local_part.lower().replace(".", "_")


def validate_email(email: str) -> bool:
    """Validate an email address."""
    if not email:
        return False

    # BUG: Overly simple validation, doesn't handle all valid email formats
    # Also doesn't handle edge case of multiple @ symbols
    return "@" in email and "." in email.split("@")[1]


def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate password strength."""
    errors = []

    # BUG: Checks are independent but should all pass
    # Current logic allows weak passwords if they're long enough
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain digit")

    # This is actually fine, returns (True, []) if no errors
    return len(errors) == 0, errors
