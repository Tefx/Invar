"""File handling module with planted path traversal bugs.

DX-74 Test Scenario - File 4/6
Bugs: 8 path/file handling issues
"""

import os
import shutil

UPLOAD_DIR = "/var/uploads"
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".jpg", ".png"}


def save_uploaded_file(filename: str, content: bytes) -> str:
    """Save an uploaded file.

    # BUG-26: No path traversal prevention
    """
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath


def read_user_file(user_id: str, filename: str) -> bytes:
    """Read a file from user's directory.

    # BUG-27: Path traversal via filename (../)
    """
    user_dir = f"/data/users/{user_id}"
    filepath = os.path.join(user_dir, filename)
    with open(filepath, "rb") as f:
        return f.read()


def delete_temp_file(filename: str) -> bool:
    """Delete a temporary file.

    # BUG-28: No validation of filename
    """
    filepath = f"/tmp/{filename}"
    try:
        os.remove(filepath)
        return True
    except Exception:
        return False


def copy_file(src: str, dst: str) -> bool:
    """Copy a file from source to destination.

    # BUG-29: No path validation on either argument
    """
    try:
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False


def list_directory(path: str) -> list[str]:
    """List files in a directory.

    # BUG-30: No path validation, can list any directory
    """
    return os.listdir(path)


def get_file_extension(filename: str) -> str:
    """Get the extension of a file.

    This one is OK - safe operation
    """
    return os.path.splitext(filename)[1].lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed.

    This one is OK - proper validation
    """
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def create_user_directory(user_id: str) -> str:
    """Create a directory for a user.

    # BUG-31: No validation of user_id (path injection)
    """
    user_dir = f"/data/users/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def move_file(src: str, dst: str) -> bool:
    """Move a file from source to destination.

    # BUG-32: No path validation
    """
    try:
        shutil.move(src, dst)
        return True
    except Exception:
        return False


def read_config_file(config_name: str) -> dict:
    """Read a configuration file.

    # BUG-33: Path traversal via config_name
    """
    import json
    config_path = f"/etc/app/configs/{config_name}.json"
    with open(config_path) as f:
        return json.load(f)


def get_file_size(filepath: str) -> int:
    """Get the size of a file.

    This one is OK - read-only operation
    """
    return os.path.getsize(filepath)


def normalize_path(path: str) -> str:
    """Normalize a file path.

    This one is OK - uses proper normalization
    """
    return os.path.normpath(path)
