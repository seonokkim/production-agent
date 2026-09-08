"""Embedding provider Protocol for Approved Reference Retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class EmbeddingResult:
    vector: list[float]
    model_name: str
    model_version: str


class EmbeddingProvider(Protocol):
    def embed_text(self, text: str) -> EmbeddingResult: ...

    def embed_video(
        self,
        file_path: Path,
        *,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> EmbeddingResult: ...
