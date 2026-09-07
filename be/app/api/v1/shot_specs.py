from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ShotSpecCreate, ShotSpecRead, ShotSpecUpdate
from app.services.shot_spec_service import ShotSpecService

router = APIRouter(tags=["shot-specs"])
service = ShotSpecService()


@router.post("/scenes/{scene_id}/shot-specs", response_model=ShotSpecRead, status_code=201)
def create_shot_spec(scene_id: int, payload: ShotSpecCreate, db: Session = Depends(get_db)):
    try:
        return service.create(db, scene_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scenes/{scene_id}/shot-specs", response_model=list[ShotSpecRead])
def list_shot_specs(scene_id: int, db: Session = Depends(get_db)):
    return service.list_for_scene(db, scene_id)


@router.patch("/shot-specs/{shot_spec_id}", response_model=ShotSpecRead)
def update_shot_spec(
    shot_spec_id: int, payload: ShotSpecUpdate, db: Session = Depends(get_db)
):
    try:
        return service.update(db, shot_spec_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
