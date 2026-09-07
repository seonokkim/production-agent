from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Asset, GenerationJob
from app.schemas import AssetRead, ReviewCreate, ReviewRead
from app.services.generation_service import asset_to_read
from app.services.production_agent import ProductionAgent

router = APIRouter(tags=["assets"])
agent = ProductionAgent()


@router.get("/assets", response_model=list[AssetRead])
def list_assets(db: Session = Depends(get_db)):
    assets = (
        db.query(Asset)
        .options(joinedload(Asset.generation_job))
        .order_by(Asset.id.desc())
        .limit(200)
        .all()
    )
    return [asset_to_read(a) for a in assets]


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
    job = (
        db.query(GenerationJob)
        .options(joinedload(GenerationJob.workflow_version))
        .filter(GenerationJob.id == asset.generation_job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Generation not found")
    return {
        "asset_id": asset.id,
        "generation_id": job.id,
        "parent_generation_id": job.parent_generation_id,
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
