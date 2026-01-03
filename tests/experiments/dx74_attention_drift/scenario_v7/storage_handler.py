"""
Storage Handler module for file and data persistence operations.
Provides utilities for managing files, directories, and cached data.
"""
import hashlib
import json
import os
import pickle
import shutil
import tempfile
from dataclasses import dataclass, field
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
class StorageConfig:
    """Configuration for storage operations."""
    base_path: str
    max_file_size: int = 100 * 1024 * 1024
    allowed_extensions: list[str] = field(default_factory=lambda: [".txt", ".json", ".csv"])
    temp_dir: str = "/tmp/storage"


@dataclass
class FileMetadata:
    """Metadata for stored files."""
    filename: str
    size: int
    created_at: datetime
    modified_at: datetime
    checksum: str
    mime_type: str


class PathResolver:
    """Utility for resolving and normalizing file paths."""

    def __init__(self, base_directory: str):
        self.base_directory = base_directory

    @pre(lambda self, path: isinstance(path, str))
    def resolve(self, path: str) -> str:
        """
        Resolve relative path to absolute path within base directory.

        >>> resolver = PathResolver("/data")
        >>> resolver.resolve("files/doc.txt")
        '/data/files/doc.txt'
        """
        return os.path.join(self.base_directory, path)

    @pre(lambda self, path: isinstance(path, str))
    def is_within_base(self, path: str) -> bool:
        """
        Check if path is within the base directory.

        >>> resolver = PathResolver("/data")
        >>> resolver.is_within_base("/data/files/doc.txt")
        True
        >>> resolver.is_within_base("/etc/passwd")
        False
        """
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.base_directory)

    def normalize(self, path: str) -> str:
        """
        Normalize path by removing redundant separators.

        >>> resolver = PathResolver("/data")
        >>> resolver.normalize("/data//files///doc.txt")
        '/data/files/doc.txt'
        """
        return os.path.normpath(path)

    def get_relative(self, full_path: str) -> str:
        """
        Get path relative to base directory.

        >>> resolver = PathResolver("/data")
        >>> resolver.get_relative("/data/files/doc.txt")
        'files/doc.txt'
        """
        if full_path.startswith(self.base_directory):
            relative = full_path[len(self.base_directory):]
            return relative.lstrip(os.sep)
        return full_path


class FileValidator:
    """Validation utilities for file operations."""

    MAX_FILENAME_LENGTH = 255
    FORBIDDEN_CHARS = set('<>:"|?*\x00')

    @classmethod
    @pre(lambda cls, filename: isinstance(filename, str))
    def is_valid_filename(cls, filename: str) -> bool:
        """
        Validate filename for safety and format.

        >>> FileValidator.is_valid_filename("document.txt")
        True
        >>> FileValidator.is_valid_filename("file<name>.txt")
        False
        >>> FileValidator.is_valid_filename("")
        False
        """
        if not filename or len(filename) > cls.MAX_FILENAME_LENGTH:
            return False

        if any(c in cls.FORBIDDEN_CHARS for c in filename):
            return False

        if filename.startswith(".") or filename.endswith("."):
            return False

        return True

    @classmethod
    def get_extension(cls, filename: str) -> str:
        """
        Extract file extension.

        >>> FileValidator.get_extension("document.txt")
        '.txt'
        >>> FileValidator.get_extension("archive.tar.gz")
        '.gz'
        >>> FileValidator.get_extension("noextension")
        ''
        """
        _, ext = os.path.splitext(filename)
        return ext.lower()

    @classmethod
    def is_allowed_extension(cls, filename: str, allowed: list[str]) -> bool:
        """
        Check if file extension is in allowed list.

        >>> FileValidator.is_allowed_extension("doc.txt", [".txt", ".pdf"])
        True
        >>> FileValidator.is_allowed_extension("script.py", [".txt", ".pdf"])
        False
        """
        ext = cls.get_extension(filename)
        return ext in allowed


class ChecksumCalculator:
    """Utilities for calculating file checksums."""

    @staticmethod
    @pre(lambda data: isinstance(data, (bytes, str)))
    def md5(data: bytes | str) -> str:
        """
        Calculate MD5 checksum of data.

        >>> ChecksumCalculator.md5(b"hello world")
        '5eb63bbbe01eeed093cb22bb8f5acdc3'
        >>> ChecksumCalculator.md5("hello world")
        '5eb63bbbe01eeed093cb22bb8f5acdc3'
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def sha256(data: bytes | str) -> str:
        """
        Calculate SHA256 checksum of data.

        >>> len(ChecksumCalculator.sha256(b"test"))
        64
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def file_checksum(filepath: str, algorithm: str = "md5") -> str:
        """
        Calculate checksum of file contents.

        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(delete=False) as f:
        ...     _ = f.write(b"test content")
        ...     path = f.name
        >>> len(ChecksumCalculator.file_checksum(path)) == 32
        True
        """
        hash_func = hashlib.md5() if algorithm == "md5" else hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()


class DirectoryManager:
    """Utilities for directory operations."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    @pre(lambda self, path: isinstance(path, str))
    def create_directory(self, path: str) -> bool:
        """
        Create directory and parent directories.

        >>> import tempfile
        >>> dm = DirectoryManager(tempfile.gettempdir())
        >>> dm.create_directory("test_subdir")
        True
        """
        full_path = os.path.join(self.base_path, path)
        try:
            os.makedirs(full_path, exist_ok=True)
            return True
        except OSError:
            return False

    def list_directory(self, path: str = "") -> list[str]:
        """
        List contents of directory.

        >>> import tempfile
        >>> dm = DirectoryManager(tempfile.gettempdir())
        >>> isinstance(dm.list_directory(), list)
        True
        """
        full_path = os.path.join(self.base_path, path) if path else self.base_path
        try:
            return os.listdir(full_path)
        except OSError:
            return []

    def get_directory_size(self, path: str = "") -> int:
        """
        Calculate total size of directory contents.

        >>> import tempfile
        >>> dm = DirectoryManager(tempfile.gettempdir())
        >>> dm.get_directory_size() >= 0
        True
        """
        full_path = os.path.join(self.base_path, path) if path else self.base_path
        total_size = 0

        for dirpath, dirnames, filenames in os.walk(full_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass

        return total_size

    @pre(lambda self, path: isinstance(path, str))
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        Delete a directory.

        >>> import tempfile
        >>> dm = DirectoryManager(tempfile.gettempdir())
        >>> dm.create_directory("to_delete")
        True
        >>> dm.delete_directory("to_delete")
        True
        """
        full_path = os.path.join(self.base_path, path)
        try:
            if recursive:
                shutil.rmtree(full_path)
            else:
                os.rmdir(full_path)
            return True
        except OSError:
            return False


class FileStorage:
    """Main file storage handler."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = config.base_path
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Ensure base directory exists."""
        os.makedirs(self.base_path, exist_ok=True)

    @pre(lambda self, filename: isinstance(filename, str))
    def save_file(self, filename: str, content: bytes) -> FileMetadata | None:
        """
        Save file content to storage.

        >>> import tempfile
        >>> config = StorageConfig(base_path=tempfile.gettempdir())
        >>> storage = FileStorage(config)
        >>> meta = storage.save_file("test.txt", b"hello")
        >>> meta is not None
        True
        """
        if len(content) > self.config.max_file_size:
            return None

        filepath = os.path.join(self.base_path, filename)

        with open(filepath, "wb") as f:
            f.write(content)

        now = datetime.now()
        return FileMetadata(
            filename=filename,
            size=len(content),
            created_at=now,
            modified_at=now,
            checksum=ChecksumCalculator.md5(content),
            mime_type="application/octet-stream"
        )

    @pre(lambda self, filename: isinstance(filename, str))
    def read_file(self, filename: str) -> bytes | None:
        """
        Read file content from storage.

        >>> import tempfile
        >>> config = StorageConfig(base_path=tempfile.gettempdir())
        >>> storage = FileStorage(config)
        >>> _ = storage.save_file("read_test.txt", b"content")
        >>> storage.read_file("read_test.txt")
        b'content'
        """
        filepath = os.path.join(self.base_path, filename)
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def delete_file(self, filename: str) -> bool:
        """
        Delete file from storage.

        >>> import tempfile
        >>> config = StorageConfig(base_path=tempfile.gettempdir())
        >>> storage = FileStorage(config)
        >>> _ = storage.save_file("to_delete.txt", b"temp")
        >>> storage.delete_file("to_delete.txt")
        True
        """
        filepath = os.path.join(self.base_path, filename)
        try:
            os.remove(filepath)
            return True
        except OSError:
            return False

    def file_exists(self, filename: str) -> bool:
        """
        Check if file exists in storage.

        >>> import tempfile
        >>> config = StorageConfig(base_path=tempfile.gettempdir())
        >>> storage = FileStorage(config)
        >>> storage.file_exists("nonexistent_file.txt")
        False
        """
        filepath = os.path.join(self.base_path, filename)
        return os.path.isfile(filepath)

    def list_files(self, pattern: str = "*") -> list[str]:
        """
        List files matching pattern.

        >>> import tempfile
        >>> config = StorageConfig(base_path=tempfile.gettempdir())
        >>> storage = FileStorage(config)
        >>> isinstance(storage.list_files(), list)
        True
        """
        from glob import glob
        search_path = os.path.join(self.base_path, pattern)
        return [os.path.basename(f) for f in glob(search_path) if os.path.isfile(f)]


class CacheStorage:
    """Persistent cache storage using pickle serialization."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """Generate cache file path from key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")

    @pre(lambda self, key: isinstance(key, str))
    def get(self, key: str) -> Any | None:
        """
        Retrieve cached value.

        >>> import tempfile
        >>> cache = CacheStorage(tempfile.mkdtemp())
        >>> cache.get("nonexistent") is None
        True
        """
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)

            if "expires_at" in data and datetime.now() > data["expires_at"]:
                os.remove(cache_path)
                return None

            return data.get("value")
        except:
            return None

    @pre(lambda self, key, value: isinstance(key, str))
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store value in cache.

        >>> import tempfile
        >>> cache = CacheStorage(tempfile.mkdtemp())
        >>> cache.set("mykey", {"data": "value"})
        True
        >>> cache.get("mykey")
        {'data': 'value'}
        """
        cache_path = self._get_cache_path(key)
        data = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=ttl)
        }

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
            return True
        except:
            return False

    def delete(self, key: str) -> bool:
        """
        Delete cached value.

        >>> import tempfile
        >>> cache = CacheStorage(tempfile.mkdtemp())
        >>> cache.set("temp", "value")
        True
        >>> cache.delete("temp")
        True
        """
        cache_path = self._get_cache_path(key)
        try:
            os.remove(cache_path)
            return True
        except OSError:
            return False

    def clear_expired(self) -> int:
        """
        Remove all expired cache entries.

        >>> import tempfile
        >>> cache = CacheStorage(tempfile.mkdtemp())
        >>> cache.clear_expired() >= 0
        True
        """
        removed = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".cache"):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, "rb") as f:
                        data = pickle.load(f)
                    if "expires_at" in data and datetime.now() > data["expires_at"]:
                        os.remove(filepath)
                        removed += 1
                except:
                    pass
        return removed


class TempFileManager:
    """Manager for temporary file operations."""

    def __init__(self, prefix: str = "app_"):
        self.prefix = prefix
        self.temp_files: list[str] = []

    @pre(lambda self, suffix: isinstance(suffix, str))
    def create_temp_file(self, suffix: str = ".tmp", content: bytes = b"") -> str:
        """
        Create a temporary file.

        >>> tfm = TempFileManager()
        >>> path = tfm.create_temp_file(".txt", b"test")
        >>> os.path.exists(path)
        True
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=self.prefix)
        try:
            if content:
                os.write(fd, content)
        finally:
            os.close(fd)

        self.temp_files.append(path)
        return path

    def create_temp_directory(self) -> str:
        """
        Create a temporary directory.

        >>> tfm = TempFileManager()
        >>> path = tfm.create_temp_directory()
        >>> os.path.isdir(path)
        True
        """
        path = tempfile.mkdtemp(prefix=self.prefix)
        self.temp_files.append(path)
        return path

    def cleanup(self) -> int:
        """
        Remove all created temporary files and directories.

        >>> tfm = TempFileManager()
        >>> _ = tfm.create_temp_file()
        >>> tfm.cleanup()
        1
        """
        removed = 0
        for path in self.temp_files:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    removed += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    removed += 1
            except OSError:
                pass

        self.temp_files.clear()
        return removed


class JSONStorage:
    """Storage handler for JSON data files."""

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_filepath(self, name: str) -> str:
        """Generate filepath for named JSON storage."""
        return os.path.join(self.storage_dir, f"{name}.json")

    @pre(lambda self, name: isinstance(name, str))
    @pre(lambda self, name, data: isinstance(data, (dict, list)))
    def save(self, name: str, data: dict | list) -> bool:
        """
        Save data as JSON file.

        >>> import tempfile
        >>> js = JSONStorage(tempfile.mkdtemp())
        >>> js.save("config", {"key": "value"})
        True
        """
        filepath = self._get_filepath(name)
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except:
            return False

    @pre(lambda self, name: isinstance(name, str))
    def load(self, name: str) -> dict | list | None:
        """
        Load data from JSON file.

        >>> import tempfile
        >>> js = JSONStorage(tempfile.mkdtemp())
        >>> js.save("test", {"a": 1})
        True
        >>> js.load("test")
        {'a': 1}
        """
        filepath = self._get_filepath(name)
        try:
            with open(filepath) as f:
                return json.load(f)
        except:
            return None

    def exists(self, name: str) -> bool:
        """
        Check if JSON storage exists.

        >>> import tempfile
        >>> js = JSONStorage(tempfile.mkdtemp())
        >>> js.exists("nonexistent")
        False
        """
        return os.path.isfile(self._get_filepath(name))

    def delete(self, name: str) -> bool:
        """
        Delete JSON storage file.

        >>> import tempfile
        >>> js = JSONStorage(tempfile.mkdtemp())
        >>> js.save("temp", {})
        True
        >>> js.delete("temp")
        True
        """
        try:
            os.remove(self._get_filepath(name))
            return True
        except OSError:
            return False

    def list_all(self) -> list[str]:
        """
        List all stored JSON names.

        >>> import tempfile
        >>> js = JSONStorage(tempfile.mkdtemp())
        >>> js.save("item1", {})
        True
        >>> "item1" in js.list_all()
        True
        """
        files = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                files.append(filename[:-5])
        return files


class BackupManager:
    """Manager for file backup operations."""

    def __init__(self, backup_dir: str, max_backups: int = 10):
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        os.makedirs(backup_dir, exist_ok=True)

    @pre(lambda self, source_path: isinstance(source_path, str))
    def create_backup(self, source_path: str) -> str | None:
        """
        Create backup of file.

        >>> import tempfile
        >>> bm = BackupManager(tempfile.mkdtemp())
        >>> with tempfile.NamedTemporaryFile(delete=False) as f:
        ...     _ = f.write(b"content")
        ...     source = f.name
        >>> backup = bm.create_backup(source)
        >>> backup is not None
        True
        """
        if not os.path.exists(source_path):
            return None

        filename = os.path.basename(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filename}.{timestamp}.bak"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            shutil.copy2(source_path, backup_path)
            self._cleanup_old_backups(filename)
            return backup_path
        except OSError:
            return None

    def _cleanup_old_backups(self, filename: str) -> None:
        """Remove old backups exceeding max_backups."""
        pattern = f"{filename}."
        backups = []

        for f in os.listdir(self.backup_dir):
            if f.startswith(pattern) and f.endswith(".bak"):
                path = os.path.join(self.backup_dir, f)
                backups.append((path, os.path.getmtime(path)))

        backups.sort(key=lambda x: x[1], reverse=True)

        for path, _ in backups[self.max_backups:]:
            try:
                os.remove(path)
            except OSError:
                pass

    def list_backups(self, filename: str) -> list[str]:
        """
        List all backups for a file.

        >>> import tempfile
        >>> bm = BackupManager(tempfile.mkdtemp())
        >>> bm.list_backups("nonexistent.txt")
        []
        """
        pattern = f"{filename}."
        return [f for f in os.listdir(self.backup_dir)
                if f.startswith(pattern) and f.endswith(".bak")]

    def restore_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Restore file from backup.

        >>> import tempfile
        >>> bm = BackupManager(tempfile.mkdtemp())
        >>> bm.restore_backup("/nonexistent/backup", "/target")
        False
        """
        if not os.path.exists(backup_path):
            return False

        try:
            shutil.copy2(backup_path, target_path)
            return True
        except OSError:
            return False


class QuotaManager:
    """Manager for storage quota enforcement."""

    def __init__(self, base_path: str, max_bytes: int):
        self.base_path = base_path
        self.max_bytes = max_bytes

    @pre(lambda self: self.max_bytes > 0)
    def get_usage(self) -> int:
        """
        Get current storage usage in bytes.

        >>> import tempfile
        >>> qm = QuotaManager(tempfile.gettempdir(), 1000000)
        >>> qm.get_usage() >= 0
        True
        """
        total = 0
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except OSError:
                    pass
        return total

    def get_remaining(self) -> int:
        """
        Get remaining quota in bytes.

        >>> import tempfile
        >>> qm = QuotaManager(tempfile.gettempdir(), 10000000000)
        >>> qm.get_remaining() >= 0
        True
        """
        usage = self.get_usage()
        return max(0, self.max_bytes - usage)

    @pre(lambda self, size: isinstance(size, int))
    def can_store(self, size: int) -> bool:
        """
        Check if size can be stored within quota.

        >>> import tempfile
        >>> qm = QuotaManager(tempfile.gettempdir(), 10000000000)
        >>> qm.can_store(100)
        True
        """
        return size <= self.get_remaining()

    def get_usage_percent(self) -> float:
        """
        Get quota usage as percentage.

        >>> import tempfile
        >>> qm = QuotaManager(tempfile.gettempdir(), 10000000000)
        >>> 0 <= qm.get_usage_percent() <= 100
        True
        """
        if self.max_bytes == 0:
            return 100.0
        return (self.get_usage() / self.max_bytes) * 100
