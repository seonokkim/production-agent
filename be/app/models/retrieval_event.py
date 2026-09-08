from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    selected_asset_embedding_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_embeddings.id"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    result_snapshot_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scene = relationship("Scene", back_populates="retrieval_events")
    selected_embedding = relationship(
        "AssetEmbedding",
        back_populates="retrieval_selections",
        foreign_keys=[selected_asset_embedding_id],
    )
