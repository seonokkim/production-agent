"""
Bounded workflow coordinator — not an autonomous multi-agent loop.

Coordinates: suggest → validate → generate → monitor → review gate → exact rerun.
Never approves its own output. Never silently overwrites prior results.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import (
    GenerationAccepted,
    GenerationCreate,
    GenerationRead,
    ReviewCreate,
    ReviewRead,
    ShotSpecRead,
)
from app.services.generation_service import GenerationService
from app.services.review_service import ReviewService
from app.services.shot_spec_service import ShotSpecService


class ProductionAgent:
    def __init__(
        self,
        shot_specs: ShotSpecService | None = None,
        generations: GenerationService | None = None,
        reviews: ReviewService | None = None,
    ) -> None:
        self.shot_specs = shot_specs or ShotSpecService()
        self.generations = generations or GenerationService()
        self.reviews = reviews or ReviewService()

    def suggest_shot_spec(
        self,
        db: Session,
        scene_id: int,
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> ShotSpecRead:
        return self.shot_specs.suggest(
            db, scene_id, llm_provider=llm_provider, llm_model=llm_model
        )

    def submit_generation(
        self, db: Session, scene_id: int, payload: GenerationCreate
    ) -> GenerationAccepted:
        return self.generations.submit(db, scene_id, payload)

    def poll_generation(self, db: Session, generation_id: int) -> GenerationRead:
        return self.generations.get(db, generation_id)

    def exact_rerun(self, db: Session, generation_id: int) -> GenerationAccepted:
        return self.generations.rerun(db, generation_id)

    def submit_review(self, db: Session, asset_id: int, payload: ReviewCreate) -> ReviewRead:
        # Human-only gate — this coordinator never invents an approval decision.
        return self.reviews.create(db, asset_id, payload)
