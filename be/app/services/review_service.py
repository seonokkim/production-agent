"""Immutable review events — humans approve; the agent never does."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Asset, Review
from app.schemas import ReviewCreate, ReviewRead


class ReviewService:
    def create(self, db: Session, asset_id: int, payload: ReviewCreate) -> ReviewRead:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise LookupError("Asset not found")
        review = Review(
            asset_id=asset_id,
            decision=payload.decision,
            comment=payload.comment,
            reviewer_name=payload.reviewer_name,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return ReviewRead.model_validate(review)

    def latest_for_asset(self, db: Session, asset_id: int) -> ReviewRead | None:
        row = (
            db.query(Review)
            .filter(Review.asset_id == asset_id)
            .order_by(Review.created_at.desc(), Review.id.desc())
            .first()
        )
        return ReviewRead.model_validate(row) if row else None
