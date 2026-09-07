from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import GenerationAccepted, GenerationRead
from app.services.production_agent import ProductionAgent

router = APIRouter(tags=["generations"])
agent = ProductionAgent()


@router.get("/generations/{generation_id}", response_model=GenerationRead)
def get_generation(generation_id: int, db: Session = Depends(get_db)):
    try:
        return agent.poll_generation(db, generation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generations/{generation_id}/rerun", response_model=GenerationAccepted, status_code=202)
def rerun_generation(generation_id: int, db: Session = Depends(get_db)):
    try:
        return agent.exact_rerun(db, generation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/generations/{generation_id}/cancel", status_code=501)
def cancel_generation(generation_id: int):
    return {"detail": "Cancel is P1; not implemented in MVP draft.", "generation_id": generation_id}


@router.post("/generations/{generation_id}/duplicate", status_code=501)
def duplicate_generation(generation_id: int):
    return {
        "detail": "Duplicate & Edit is P1; use exact rerun for identical config.",
        "generation_id": generation_id,
    }
