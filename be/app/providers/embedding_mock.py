"""Deterministic mock embeddings for CI / offline demos (512-d)."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from app.config import get_settings
from app.providers.embedding_base import EmbeddingResult


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _hash_unit_vector(text: str, dim: int) -> list[float]:
    """Bag a stable unit vector from text tokens (bag-of-hash features)."""
    vec = [0.0] * dim
    tokens = _tokenize(text) or ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(0, 32, 4):
            idx = int.from_bytes(digest[i : i + 4], "little") % dim
            sign = 1.0 if digest[i] % 2 == 0 else -1.0
            vec[idx] += sign
    # Boost a few semantic buckets so similar drama queries cluster.
    themes = {
        "industrial": 0,
        "factory": 0,
        "neon": 1,
        "rain": 2,
        "night": 2,
        "tracking": 3,
        "rear": 3,
        "dark": 4,
        "blue": 5,
        "red": 5,
        "interior": 6,
        "slow": 7,
        "detective": 8,
        "corridor": 9,
        "daylight": 10,
        "office": 11,
        "handheld": 12,
        "forest": 13,
        "ocean": 14,
        "rooftop": 15,
    }
    for token in tokens:
        if token in themes:
            vec[themes[token] % dim] += 3.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class MockEmbeddingProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.dim = settings.embedding_dim
        self.model_name = "mock-embedding"
        self.model_version = "1.0"
        self.last_used = "mock"

    def embed_text(self, text: str) -> EmbeddingResult:
        self.last_used = "mock"
        return EmbeddingResult(
            vector=_hash_unit_vector(text, self.dim),
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def embed_video(
        self,
        file_path: Path,
        *,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> EmbeddingResult:
        # Prefer sidecar text description when present (seed corpus).
        desc = file_path.with_suffix(".txt")
        if desc.exists():
            text = desc.read_text(encoding="utf-8")
        else:
            text = f"{file_path.stem} start={start_sec} end={end_sec}"
        return self.embed_text(text)
