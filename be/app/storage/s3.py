"""S3 AssetStorage stub — raises until AWS credentials + bucket are configured."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings


class S3AssetStorage:
    """P2 target. Prefer LocalAssetStorage for interview/local development."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = (settings.aws_s3_bucket or "").strip()
        self.region = (settings.aws_region or "ap-northeast-2").strip()
        if not self.bucket:
            raise RuntimeError(
                "ASSET_STORAGE_PROVIDER=s3 requires AWS_S3_BUCKET "
                "(and AWS auth). Use local for development."
            )

    def resolve(self, relative_path: str) -> Path:
        raise NotImplementedError("S3AssetStorage.resolve is not implemented yet")

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        raise NotImplementedError(
            "S3AssetStorage.write_bytes is not implemented yet — "
            "keep ASSET_STORAGE_PROVIDER=local until P2 AWS wiring ships."
        )

    def read_bytes(self, relative_path: str) -> bytes:
        raise NotImplementedError("S3AssetStorage.read_bytes is not implemented yet")

    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError("S3AssetStorage.exists is not implemented yet")

    def public_url(self, relative_path: str) -> str:
        # Placeholder shape; real signed URLs come with P2 implementation.
        return f"s3://{self.bucket}/{relative_path.lstrip('/')}"
