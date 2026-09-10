"""Storage protocol for production assets."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AssetStorage(Protocol):
    def resolve(self, relative_path: str) -> Path:
        """Absolute path (local) or local cache path for a relative key."""

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        """Persist bytes; return relative path key used in Asset.file_path."""

    def read_bytes(self, relative_path: str) -> bytes:
        ...

    def exists(self, relative_path: str) -> bool:
        ...

    def public_url(self, relative_path: str) -> str:
        """URL path served by the API (or signed URL for S3 later)."""
