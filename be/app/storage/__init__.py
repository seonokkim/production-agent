"""Asset binary storage abstraction (local now · S3 later)."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.storage.base import AssetStorage
from app.storage.local import LocalAssetStorage
from app.storage.s3 import S3AssetStorage


def get_asset_storage(settings: Settings | None = None) -> AssetStorage:
    cfg = settings or get_settings()
    provider = (cfg.asset_storage_provider or "local").strip().lower()
    if provider == "s3":
        return S3AssetStorage(cfg)
    return LocalAssetStorage(cfg)


__all__ = [
    "AssetStorage",
    "LocalAssetStorage",
    "S3AssetStorage",
    "get_asset_storage",
]
