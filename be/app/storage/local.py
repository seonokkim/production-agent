"""Local filesystem AssetStorage under ASSET_STORAGE_PATH."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings


class LocalAssetStorage:
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.asset_storage_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        rel = relative_path.lstrip("/").replace("\\", "/")
        path = (self.root / rel).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Path escapes asset storage root")
        return path

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return relative_path.lstrip("/").replace("\\", "/")

    def read_bytes(self, relative_path: str) -> bytes:
        return self.resolve(relative_path).read_bytes()

    def exists(self, relative_path: str) -> bool:
        return self.resolve(relative_path).exists()

    def public_url(self, relative_path: str) -> str:
        return f"/storage/{relative_path.lstrip('/')}"
