from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Scene
from app.schemas import (
    GenerationAccepted,
    GenerationCreate,
    GenerationRead,
    SceneRead,
    SceneUpdate,
    ShotSpecRead,
    ShotSpecSuggestRequest,
)
from app.services.production_agent import ProductionAgent

router = APIRouter(tags=["scenes"])
agent = ProductionAgent()


@router.get("/scenes/{scene_id}", response_model=SceneRead)
def get_scene(scene_id: int, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.patch("/scenes/{scene_id}", response_model=SceneRead)
def update_scene(scene_id: int, payload: SceneUpdate, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(scene, key, value)
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/scenes/{scene_id}/shot-spec/suggest", response_model=ShotSpecRead)
def suggest_shot_spec(
    scene_id: int,
    payload: ShotSpecSuggestRequest | None = None,
    db: Session = Depends(get_db),
):
    body = payload or ShotSpecSuggestRequest()
    try:
        return agent.suggest_shot_spec(
            db,
            scene_id,
            llm_provider=body.llm_provider,
            llm_model=body.llm_model,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/scenes/{scene_id}/generations", response_model=GenerationAccepted, status_code=202)
def submit_generation(
    scene_id: int, payload: GenerationCreate, db: Session = Depends(get_db)
):
    try:
        return agent.submit_generation(db, scene_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scenes/{scene_id}/generations", response_model=list[GenerationRead])
def list_generations(scene_id: int, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return agent.generations.list_for_scene(db, scene_id)
