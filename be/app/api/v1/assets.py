from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Asset, BatchRun, GenerationJob, Scene
from app.schemas import AssetRead, BatchRunRead, DocumentUploadResponse, ReviewCreate, ReviewRead
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.generation_service import asset_to_read
from app.services.production_agent import ProductionAgent

router = APIRouter(tags=["assets"])
agent = ProductionAgent()
ingestion = DocumentIngestionService()

_IMAGE_TYPES = {"reference", "keyframe"}
_VIDEO_TYPES = {"video"}
_DOC_TYPES = {"document"}


@router.get("/assets", response_model=list[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    tab: str | None = Query(default=None, pattern="^(all|images|videos|documents)$"),
    asset_type: str | None = None,
    status: str | None = None,
    ingestion_status: str | None = None,
    source: str | None = None,
):
    q = db.query(Asset).options(joinedload(Asset.generation_job))
    if tab == "images":
        q = q.filter(Asset.asset_type.in_(list(_IMAGE_TYPES)))
    elif tab == "videos":
        q = q.filter(Asset.asset_type.in_(list(_VIDEO_TYPES)))
    elif tab == "documents":
        q = q.filter(Asset.asset_type.in_(list(_DOC_TYPES)))
    if asset_type:
        q = q.filter(Asset.asset_type == asset_type)
    if status:
        q = q.filter(Asset.status == status)
    if ingestion_status:
        q = q.filter(Asset.ingestion_status == ingestion_status)
    if source:
        q = q.filter(Asset.source == source)
    assets = q.order_by(Asset.id.desc()).limit(200).all()
    return [asset_to_read(a) for a in assets]


@router.post("/assets/documents", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    source: str = Form(default="upload"),
    db: Session = Depends(get_db),
):
    filename = file.filename or "document.txt"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    asset = ingestion.create_pending_document(
        db, filename=filename, data=data, source=source or "upload"
    )
    return DocumentUploadResponse(asset=asset_to_read(asset))


@router.post("/assets/ingestion/run", response_model=BatchRunRead, status_code=201)
def run_asset_ingestion(
    db: Session = Depends(get_db),
    airflow_dag_run_id: str | None = None,
    ingest_landing: bool = True,
):
    """Run production_asset_ingestion pipeline (Airflow task or manual)."""
    run = ingestion.run_pipeline(
        db, airflow_dag_run_id=airflow_dag_run_id, ingest_landing=ingest_landing
    )
    return BatchRunRead.model_validate(run)


@router.get("/assets/ingestion/runs", response_model=list[BatchRunRead])
def list_ingestion_runs(db: Session = Depends(get_db), limit: int = 20):
    rows = (
        db.query(BatchRun)
        .order_by(BatchRun.id.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [BatchRunRead.model_validate(r) for r in rows]


@router.get("/assets/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset_to_read(asset)


@router.post("/assets/{asset_id}/reviews", response_model=ReviewRead, status_code=201)
def create_review(asset_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    try:
        return agent.submit_review(db, asset_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/assets/{asset_id}/provenance")
def asset_provenance(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.generation_job_id is None:
        return {
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "generation_id": None,
            "source": asset.source,
            "ingestion_status": asset.ingestion_status,
            "original_filename": asset.original_filename,
            "ai_generated": False,
        }
    job = (
        db.query(GenerationJob)
        .options(joinedload(GenerationJob.workflow_version))
        .filter(GenerationJob.id == asset.generation_job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Generation not found")
    scene = db.get(Scene, job.scene_id) if job.scene_id else None
    return {
        "asset_id": asset.id,
        "generation_id": job.id,
        "parent_generation_id": job.parent_generation_id,
        "project_id": scene.project_id if scene else None,
        "shot_spec_id": job.shot_spec_id,
        "prompt": job.prompt,
        "negative_prompt": job.negative_prompt,
        "model_name": job.model_name,
        "model_version": job.model_version,
        "seed": job.seed,
        "workflow_name": job.workflow_version.name if job.workflow_version else None,
        "workflow_version": job.workflow_version.version if job.workflow_version else None,
        "workflow_hash": job.workflow_version.workflow_hash if job.workflow_version else None,
        "reference_asset_id": job.reference_asset_id,
        "retrieval_event_id": job.retrieval_event_id,
        "reference_asset_embedding_id": job.reference_asset_embedding_id,
        "width": job.width,
        "height": job.height,
        "fps": job.fps,
        "frame_count": job.frame_count,
        "duration_seconds": job.duration_seconds,
        "generation_ms": job.generation_ms,
        "status": job.status,
        "provider": job.provider,
        "ai_generated": True,
    }
