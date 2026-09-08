from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AssetEmbeddingRead,
    ReferenceSearchRequest,
    ReferenceSearchResponse,
    RetrievalEventRead,
    RetrievalSelectRequest,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["retrieval"])
retrieval = RetrievalService()


@router.post(
    "/assets/{asset_id}/embeddings",
    response_model=AssetEmbeddingRead,
    status_code=201,
)
def create_asset_embedding(asset_id: int, db: Session = Depends(get_db)):
    try:
        return retrieval.index_asset(db, asset_id, require_approved=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/scenes/{scene_id}/reference-search",
    response_model=ReferenceSearchResponse,
)
def reference_search(
    scene_id: int, payload: ReferenceSearchRequest, db: Session = Depends(get_db)
):
    try:
        return retrieval.search(db, scene_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/retrieval-events/{retrieval_event_id}/select",
    response_model=RetrievalEventRead,
)
def select_reference(
    retrieval_event_id: int, payload: RetrievalSelectRequest, db: Session = Depends(get_db)
):
    try:
        return retrieval.select_reference(db, retrieval_event_id, payload.asset_embedding_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
