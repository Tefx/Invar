"""
Verification cache for proof verification.

DX-13: Caches CrossHair verification results to avoid re-verification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path  # noqa: TC003 - runtime usage


@dataclass
class CacheEntry:
    """Cache entry for a verified file."""

    file_path: str
    file_hash: str
    verified_at: str
    result: str
    crosshair_version: str
    invar_version: str
    time_taken_ms: int = 0
    functions_checked: int = 0


@dataclass
class ProveCache:
    """Cache for proof verification results."""

    cache_dir: Path
    entries: dict[str, CacheEntry] = field(default_factory=dict)
    _crosshair_version: str = ""
    _invar_version: str = ""

    def __post_init__(self) -> None:
        """Initialize cache directory and load existing entries."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_manifest()
        self._crosshair_version = self._get_crosshair_version()
        self._invar_version = self._get_invar_version()

    def _load_manifest(self) -> None:
        """Load cache manifest if exists."""
        manifest_path = self.cache_dir / "manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                for key, entry_data in data.get("entries", {}).items():
                    self.entries[key] = CacheEntry(**entry_data)
            except (json.JSONDecodeError, TypeError):
                pass  # Corrupted cache, will rebuild

    def _save_manifest(self) -> None:
        """Save cache manifest."""
        manifest_path = self.cache_dir / "manifest.json"
        data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "crosshair_version": self._crosshair_version,
            "invar_version": self._invar_version,
            "entries": {k: vars(v) for k, v in self.entries.items()},
        }
        manifest_path.write_text(json.dumps(data, indent=2))

    def _get_crosshair_version(self) -> str:
        """Get installed CrossHair version."""
        try:
            import crosshair

            return getattr(crosshair, "__version__", "unknown")
        except ImportError:
            return "not_installed"

    def _get_invar_version(self) -> str:
        """Get Invar version."""
        try:
            from invar import __version__

            return __version__
        except ImportError:
            return "unknown"

    def get(self, file_path: Path) -> CacheEntry | None:
        """Get cache entry for a file."""
        key = str(file_path)
        return self.entries.get(key)

    def is_valid(self, file_path: Path) -> bool:
        """Check if cache entry is valid for file."""
        entry = self.get(file_path)
        if entry is None:
            return False

        # Check file hash
        current_hash = self._hash_file(file_path)
        if entry.file_hash != current_hash:
            return False

        # Check CrossHair version
        return entry.crosshair_version == self._crosshair_version

    def set(
        self,
        file_path: Path,
        result: str,
        time_taken_ms: int = 0,
        functions_checked: int = 0,
    ) -> None:
        """Set cache entry for a file."""
        key = str(file_path)
        self.entries[key] = CacheEntry(
            file_path=key,
            file_hash=self._hash_file(file_path),
            verified_at=datetime.now().isoformat(),
            result=result,
            crosshair_version=self._crosshair_version,
            invar_version=self._invar_version,
            time_taken_ms=time_taken_ms,
            functions_checked=functions_checked,
        )
        self._save_manifest()

    def _hash_file(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except OSError:
            return "error"
