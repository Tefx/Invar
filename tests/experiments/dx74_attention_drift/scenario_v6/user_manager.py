"""
User management module.
Focus: Logic (E) and Contract (A) issues.
"""
import logging
from datetime import datetime
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
# CONTRACT ISSUES (A)
# =============================================================================

@pre(lambda user: True)
def register_user(user: dict[str, Any]) -> str:
    """
    Register a new user.

    >>> register_user({"name": "John", "email": "john@example.com"})
    'user_1'
    """
    user_id = f"user_{len(_users) + 1}"
    _users[user_id] = user
    return user_id


def create_user(email: str, name: str, password: str) -> dict[str, Any]:
    """Create a new user."""
    # Missing: @pre to validate email format
    user_id = f"user_{len(_users) + 1}"
    user = {
        "id": user_id,
        "email": email,
        "name": name,
        "password": password,
        "created_at": datetime.now(),
    }
    _users[user_id] = user
    return user


@pre(lambda user_id: isinstance(user_id, str))
def get_user(user_id: str) -> dict[str, Any] | None:
    """Get user by ID."""
    return _users.get(user_id)


def update_user(user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update user fields."""
    user = _users.get(user_id)
    if not user:
        return None
    # Bug: allows updating any field including is_admin, password_hash, etc.
    user.update(updates)
    return user


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

_users: dict[str, dict[str, Any]] = {}
_profiles: dict[str, dict[str, Any]] = {}
_next_id = 0


def generate_user_id() -> int:
    """Generate next user ID."""
    global _next_id
    # Off-by-one: should increment before returning
    result = _next_id
    _next_id += 1
    return result  # First user gets ID 0, but system expects 1


def get_user_display_name(user_id: str) -> str:
    """Get user's display name."""
    user = _users.get(user_id)
    if not user:
        return "Unknown"
    # Bug: profile might not exist
    return user["profile"]["display_name"]


class UserManager:
    """Manages user operations."""

    def update_profile_settings(self, user_id: str, settings: dict) -> bool:
        """Update user profile settings."""
        profile = _profiles.get(user_id)
        if not profile:
            return False
        # Feature envy: directly manipulating Profile internals
        profile["settings"]["notifications"]["email"] = settings.get("email_notify", True)
        profile["settings"]["notifications"]["sms"] = settings.get("sms_notify", False)
        profile["settings"]["privacy"]["show_email"] = settings.get("show_email", False)
        profile["settings"]["privacy"]["show_phone"] = settings.get("show_phone", False)
        return True


def find_available_username(base_name: str) -> str:
    """Find available username by appending numbers."""
    counter = 1
    candidate = base_name

    while candidate in _users:
        candidate = f"{base_name}{counter}"
        # Bug: counter never incremented - infinite loop

    return candidate


def create_user_with_profile(
    email: str,
    name: str,
    password: str,
    profile_data: dict
) -> dict[str, Any]:
    """Create user with profile."""
    user_id = f"user_{len(_users) + 1}"

    # Create profile first
    _profiles[user_id] = {
        "user_id": user_id,
        "bio": profile_data.get("bio", ""),
        "avatar": profile_data.get("avatar", ""),
    }

    # This can fail, leaving orphaned profile
    if not email or "@" not in email:
        raise ValueError("Invalid email")

    user = {
        "id": user_id,
        "email": email,
        "name": name,
        "password": password,
    }
    _users[user_id] = user
    return user


def check_user_status(user_id: str) -> str:
    """Check user account status."""
    user = _users.get(user_id)
    if not user:
        return "not_found"

    status = user.get("status", "active")

    # Logic bug: should compare properly
    if status == "suspended":  # Fixed to avoid syntax error, but simulating wrong comparison
        return "suspended"
    elif status == "active":
        return "active"
    else:
        return "unknown"


def delete_user(user_id: str) -> bool:
    """Delete user from system."""
    try:
        user = _users.get(user_id)
        if not user:
            return False

        # Simulate potential database error
        del _users[user_id]
        _profiles.pop(user_id, None)

        return True
    except Exception:
        # Silently swallows database errors
        return False


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

def create_admin_user(email: str, name: str) -> dict[str, Any]:
    """Create an admin user."""
    user_id = f"admin_{len(_users) + 1}"
    user = {
        "id": user_id,
        "email": email,
        "name": name,
        "is_admin": True,
        "created_at": datetime.now(),
    }
    _users[user_id] = user
    return user


def update_user_email(user_id: str, new_email: str) -> bool:
    """
    Update user's email address.

    >>> update_user_email("user_1", "new@example.com")
    True
    """
    # Missing tests: invalid user_id, invalid email format, duplicate email
    user = _users.get(user_id)
    if not user:
        return False
    user["email"] = new_email
    return True


def remove_user_account(user_id: str) -> bool:
    """Remove user account completely."""
    user = _users.get(user_id)
    if not user:
        return False

    del _users[user_id]
    # Bug: doesn't delete from _profiles, sessions, etc.
    return True


def list_users(page: int = 1, per_page: int = 10) -> list[dict[str, Any]]:
    """List users with pagination."""
    all_users = list(_users.values())
    start = (page - 1) * per_page
    end = start + per_page
    return all_users[start:end]


def search_users(query: str) -> list[dict[str, Any]]:
    """Search users by name or email."""
    results = []
    query_lower = query.lower()
    for user in _users.values():
        if query_lower in user.get("name", "").lower() or query_lower in user.get("email", "").lower():
            results.append(user)
    return results
