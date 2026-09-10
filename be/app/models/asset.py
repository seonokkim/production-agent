from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable for uploaded / landing-folder documents (no GenerationJob).
    generation_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_jobs.id"), nullable=True, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ready", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # P1 document / ingestion fields
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ingestion_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    generation_job = relationship(
        "GenerationJob",
        back_populates="assets",
        foreign_keys=[generation_job_id],
    )
    reviews = relationship("Review", back_populates="asset", cascade="all, delete-orphan")
    embeddings = relationship(
        "AssetEmbedding", back_populates="asset", cascade="all, delete-orphan"
    )
