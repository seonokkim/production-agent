"""Dialect-aware embedding storage: Vector(512) on Postgres, JSON text on SQLite."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Float


try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[misc, assignment]


class EmbeddingVector(TypeDecorator):
    """Store a 512-d float list. Postgres+pgvector preferred; SQLite uses JSON text."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 512) -> None:
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(self.dim))
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Float))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[float] | None, dialect) -> Any:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect) -> list[float] | None:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if isinstance(value, str):
            return [float(x) for x in json.loads(value)]
        return [float(x) for x in value]
