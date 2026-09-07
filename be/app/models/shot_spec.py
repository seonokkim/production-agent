from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ShotSpec(Base):
    __tablename__ = "shot_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    time_of_day: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    subjects_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    shot_size: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    camera_angle: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    camera_motion: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    lighting: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mood: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    motion_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scene = relationship("Scene", back_populates="shot_specs")
    generation_jobs = relationship("GenerationJob", back_populates="shot_spec")
