from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DashboardMetrics
from app.services.metrics_service import MetricsService

router = APIRouter(tags=["dashboard"])
metrics = MetricsService()


@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(db: Session = Depends(get_db)):
    return metrics.dashboard(db)


@router.get("/projects/{project_id}/metrics", response_model=DashboardMetrics)
def project_metrics(project_id: int, db: Session = Depends(get_db)):
    return metrics.dashboard(db, project_id=project_id)
