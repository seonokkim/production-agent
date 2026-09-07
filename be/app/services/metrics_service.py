"""Dashboard / ops metrics."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Asset, GenerationJob, Review
from app.schemas import DashboardMetrics


class MetricsService:
    def dashboard(self, db: Session, project_id: int | None = None) -> DashboardMetrics:
        jobs_q = db.query(GenerationJob)
        if project_id is not None:
            from app.models import Scene

            jobs_q = jobs_q.join(Scene).filter(Scene.project_id == project_id)

        jobs = jobs_q.count()
        failed = jobs_q.filter(GenerationJob.status == "failed").count()

        completed_ms = (
            jobs_q.filter(GenerationJob.generation_ms.is_not(None))
            .with_entities(func.avg(GenerationJob.generation_ms))
            .scalar()
        )

        reviews_q = db.query(Review).join(Asset).join(GenerationJob)
        if project_id is not None:
            from app.models import Scene

            reviews_q = reviews_q.join(Scene).filter(Scene.project_id == project_id)

        approved = reviews_q.filter(Review.decision == "approved").count()
        rejected = reviews_q.filter(Review.decision == "rejected").count()
        decided = approved + rejected
        approval_rate = (approved / decided) if decided else 0.0
        avg_attempts = (jobs / approved) if approved else float(jobs or 0)

        rejection_reasons: dict[str, int] = {}
        for review in reviews_q.filter(Review.decision == "rejected").all():
            key = (review.comment or "unspecified").strip().split("\n")[0][:80] or "unspecified"
            rejection_reasons[key] = rejection_reasons.get(key, 0) + 1

        return DashboardMetrics(
            generation_jobs=jobs,
            approved_assets=approved,
            approval_rate=round(approval_rate, 3),
            avg_attempts_per_approval=round(avg_attempts, 2),
            avg_generation_ms=float(completed_ms) if completed_ms is not None else None,
            failed_jobs=failed,
            rejection_reasons=rejection_reasons,
        )
