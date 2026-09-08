from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), nullable=False, index=True)
    shot_spec_id: Mapped[int] = mapped_column(ForeignKey("shot_specs.id"), nullable=False)
    workflow_version_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_versions.id"), nullable=False
    )
    parent_generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_jobs.id"), nullable=True, index=True
    )
    provider_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    generation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=1280, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=720, nullable=False)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Soft references — avoid circular FKs with assets / retrieval tables
    reference_asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    reference_asset_embedding_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workflow_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    configuration_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scene = relationship("Scene", back_populates="generation_jobs")
    shot_spec = relationship("ShotSpec", back_populates="generation_jobs")
    workflow_version = relationship("WorkflowVersion", back_populates="generation_jobs")
    parent = relationship("GenerationJob", remote_side=[id], foreign_keys=[parent_generation_id])
    assets = relationship(
        "Asset",
        back_populates="generation_job",
        foreign_keys="Asset.generation_job_id",
        cascade="all, delete-orphan",
    )
