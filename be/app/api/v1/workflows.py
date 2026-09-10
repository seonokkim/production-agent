"""Read-only ComfyUI workflow graph inspection APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import GenerationJob, WorkflowVersion
from app.schemas import WorkflowGraphRead, WorkflowVersionRead
from app.services.workflow_graph_service import graph_from_generation, graph_from_workflow_version

router = APIRouter(tags=["workflows"])


@router.get("/workflows", response_model=list[WorkflowVersionRead])
def list_workflows(db: Session = Depends(get_db)):
    rows = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.active.is_(True))
        .order_by(WorkflowVersion.id.asc())
        .all()
    )
    return rows


@router.get("/workflows/{workflow_version_id}/graph", response_model=WorkflowGraphRead)
def get_workflow_graph(workflow_version_id: int, db: Session = Depends(get_db)):
    wf = db.query(WorkflowVersion).filter(WorkflowVersion.id == workflow_version_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail=f"WorkflowVersion {workflow_version_id} not found")
    try:
        return graph_from_workflow_version(wf)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load workflow graph: {exc}") from exc


@router.get("/workflows/by-name/{name}/graph", response_model=WorkflowGraphRead)
def get_workflow_graph_by_name(name: str, db: Session = Depends(get_db)):
    wf = db.query(WorkflowVersion).filter(WorkflowVersion.name == name).first()
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    try:
        return graph_from_workflow_version(wf)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load workflow graph: {exc}") from exc


@router.get("/generations/{generation_id}/workflow-graph", response_model=WorkflowGraphRead)
def get_generation_workflow_graph(generation_id: int, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == generation_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Generation {generation_id} not found")
    try:
        return graph_from_generation(job)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/comfyui/info")
def comfyui_info():
    """Expose ComfyUI URL for the Open ComfyUI action (no secrets)."""
    settings = get_settings()
    public = (settings.comfyui_public_url or "").strip() or settings.comfyui_base_url
    return {
        "comfyui_base_url": settings.comfyui_base_url,
        "comfyui_url": public.rstrip("/"),
        "note": (
            "Browser Open ComfyUI uses comfyui_url. "
            "Set COMFYUI_PUBLIC_URL when 127.0.0.1 is not reachable from the client "
            "(e.g. Backend.AI port forwarding)."
        ),
    }
