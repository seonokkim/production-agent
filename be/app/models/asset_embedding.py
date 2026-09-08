from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import EmbeddingVector


class AssetEmbedding(Base):
    __tablename__ = "asset_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    segment_start_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    segment_end_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list] = mapped_column(EmbeddingVector(512), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    embedding_scope: Mapped[str] = mapped_column(String(50), default="asset", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset", back_populates="embeddings")
    retrieval_selections = relationship(
        "RetrievalEvent",
        back_populates="selected_embedding",
        foreign_keys="RetrievalEvent.selected_asset_embedding_id",
    )
