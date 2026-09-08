from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    episode_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scene_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    brief: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", back_populates="scenes")
    shot_specs = relationship("ShotSpec", back_populates="scene", cascade="all, delete-orphan")
    generation_jobs = relationship(
        "GenerationJob", back_populates="scene", cascade="all, delete-orphan"
    )
    retrieval_events = relationship(
        "RetrievalEvent", back_populates="scene", cascade="all, delete-orphan"
    )
