"""Twelve Labs Marengo embedding adapter (embeddings only — local cosine search)."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import get_settings
from app.providers.embedding_base import EmbeddingResult
from app.providers.embedding_mock import MockEmbeddingProvider

logger = logging.getLogger(__name__)

TWELVE_LABS_BASE = "https://api.twelvelabs.io/v1.3"


class MarengoEmbeddingProvider:
    """Calls Twelve Labs Embed API (`marengo3.5` / `marengo3.0`).

    Managed /search is unsupported for 3.5 — we only fetch vectors and search locally.
    Falls back to mock vectors if the API key is missing or the call fails (dev safety),
    and sets `fell_back_to_mock=True` on the result metadata via model_name prefix.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.twelve_labs_api_key
        self.model_name = settings.embedding_model or "marengo3.5"
        self.model_version = "3.5" if "3.5" in self.model_name else "3.0"
        self.dim = settings.embedding_dim
        self._fallback = MockEmbeddingProvider()
        self.last_used: str = "unset"  # marengo | mock-fallback | mock-nokey

    def embed_text(self, text: str) -> EmbeddingResult:
        if not self.api_key:
            logger.warning("TWELVE_LABS_API_KEY missing; using mock text embedding")
            self.last_used = "mock-nokey"
            return self._fallback.embed_text(text)
        try:
            # Twelve Labs /v1.3/embed requires multipart/form-data (not JSON).
            with httpx.Client(timeout=60.0) as client:
                res = client.post(
                    f"{TWELVE_LABS_BASE}/embed",
                    headers={"x-api-key": self.api_key},
                    files={
                        "model_name": (None, self.model_name),
                        "text": (None, text),
                    },
                )
                res.raise_for_status()
                data = res.json()
                vector = self._extract_vector(data)
                if not vector:
                    raise RuntimeError(f"Marengo response missing embedding vector: {data!r}")
                self.last_used = "marengo"
                return EmbeddingResult(
                    vector=self._pad_or_trim(vector),
                    model_name=self.model_name,
                    model_version=self.model_version,
                )
        except Exception:
            logger.exception("Marengo text embed failed; falling back to mock")
            self.last_used = "mock-fallback"
            return self._fallback.embed_text(text)

    def embed_video(
        self,
        file_path: Path,
        *,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> EmbeddingResult:
        if not self.api_key:
            logger.warning("TWELVE_LABS_API_KEY missing; using mock video embedding")
            self.last_used = "mock-nokey"
            return self._fallback.embed_video(file_path, start_sec=start_sec, end_sec=end_sec)
        # Full async task ingestion is environment-specific; for MVP prefer
        # sidecar description / mock when live upload is not configured.
        logger.info(
            "Marengo video upload not configured in MVP; using text sidecar/fallback for %s",
            file_path,
        )
        self.last_used = "mock-fallback"
        return self._fallback.embed_video(file_path, start_sec=start_sec, end_sec=end_sec)

    def _extract_vector(self, data: dict) -> list[float] | None:
        # Be tolerant of response shape differences across API versions.
        if isinstance(data.get("text_embedding"), dict):
            segments = data["text_embedding"].get("segments") or []
            if segments:
                seg = segments[0]
                for key in ("float", "embeddings_float", "embedding"):
                    if key in seg and isinstance(seg[key], list):
                        return seg[key]
        if isinstance(data.get("embedding"), list):
            return data["embedding"]
        if isinstance(data.get("data"), list) and data["data"]:
            first = data["data"][0]
            if isinstance(first, dict):
                for key in ("embedding", "float"):
                    if key in first and isinstance(first[key], list):
                        return first[key]
        return None

    def _pad_or_trim(self, vector: list[float]) -> list[float]:
        if len(vector) == self.dim:
            return vector
        if len(vector) > self.dim:
            return vector[: self.dim]
        return vector + [0.0] * (self.dim - len(vector))
