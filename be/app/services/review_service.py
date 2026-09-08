"""Immutable review events — humans approve; the agent never does."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Asset, Review
from app.schemas import ReviewCreate, ReviewRead
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        self.retrieval = retrieval or RetrievalService()

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
        # Mirror latest human decision onto the asset row (history stays in Review).
        if payload.decision in {"approved", "rejected"}:
            asset.status = payload.decision
        db.add(review)
        db.commit()
        db.refresh(review)

        # P1: index approved video assets for reference retrieval.
        if payload.decision == "approved" and asset.asset_type == "video":
            try:
                self.retrieval.index_asset(db, asset_id, require_approved=True)
            except Exception:
                logger.exception("Failed to index approved asset %s for retrieval", asset_id)

        return ReviewRead.model_validate(review)

    def latest_for_asset(self, db: Session, asset_id: int) -> ReviewRead | None:
        row = (
            db.query(Review)
            .filter(Review.asset_id == asset_id)
            .order_by(Review.created_at.desc(), Review.id.desc())
            .first()
        )
        return ReviewRead.model_validate(row) if row else None
