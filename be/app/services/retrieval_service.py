"""Approved Reference Retrieval — index approved videos; cosine search; human select."""

from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.config import ROOT_DIR, get_settings
from app.models import (
    Asset,
    AssetEmbedding,
    GenerationJob,
    RetrievalEvent,
    Review,
    Scene,
    ShotSpec,
)
from app.providers import get_embedding_provider
from app.schemas import (
    AssetEmbeddingRead,
    ReferenceSearchHit,
    ReferenceSearchRequest,
    ReferenceSearchResponse,
    RetrievalEventRead,
)

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _asset_abs_path(asset: Asset) -> Path:
    settings = get_settings()
    return Path(settings.asset_storage_path) / asset.file_path


def _is_approved(db: Session, asset_id: int) -> bool:
    row = (
        db.query(Review)
        .filter(Review.asset_id == asset_id, Review.decision == "approved")
        .order_by(Review.id.desc())
        .first()
    )
    return row is not None


def shot_spec_to_query(shot: ShotSpec) -> str:
    subjects = ""
    try:
        subjects = ", ".join(json.loads(shot.subjects_json or "[]"))
    except json.JSONDecodeError:
        subjects = shot.subjects_json or ""
    parts = [
        shot.camera_motion,
        shot.shot_size,
        shot.camera_angle,
        shot.location,
        shot.lighting,
        shot.mood,
        shot.time_of_day,
        subjects,
        shot.action,
        shot.visual_prompt,
        shot.motion_prompt,
    ]
    return " ".join(p for p in parts if p).strip()


class RetrievalService:
    def index_asset(
        self,
        db: Session,
        asset_id: int,
        *,
        require_approved: bool = True,
    ) -> AssetEmbeddingRead:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise LookupError("Asset not found")
        if asset.asset_type != "video":
            raise ValueError("Only video assets can be indexed for reference retrieval")
        if require_approved and not _is_approved(db, asset_id):
            raise ValueError("Only approved video assets may be indexed")

        existing = (
            db.query(AssetEmbedding)
            .filter(AssetEmbedding.asset_id == asset_id, AssetEmbedding.embedding_scope == "asset")
            .first()
        )
        if existing:
            return AssetEmbeddingRead.model_validate(existing)

        provider = get_embedding_provider()
        path = _asset_abs_path(asset)
        # Seed corpus may live under data/retrieval with relative paths.
        if not path.exists():
            alt = ROOT_DIR / asset.file_path
            path = alt if alt.exists() else path

        result = provider.embed_video(
            path,
            start_sec=0.0,
            end_sec=asset.duration_seconds,
        )
        row = AssetEmbedding(
            asset_id=asset_id,
            segment_start_sec=0.0,
            segment_end_sec=asset.duration_seconds,
            embedding=result.vector,
            model_name=result.model_name,
            model_version=result.model_version,
            embedding_scope="asset",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return AssetEmbeddingRead.model_validate(row)

    def search(
        self, db: Session, scene_id: int, payload: ReferenceSearchRequest
    ) -> ReferenceSearchResponse:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise LookupError("Scene not found")

        query = (payload.query_text or "").strip()
        if not query and payload.shot_spec_id:
            shot = db.get(ShotSpec, payload.shot_spec_id)
            if not shot or shot.scene_id != scene_id:
                raise LookupError("ShotSpec not found for scene")
            query = shot_spec_to_query(shot)
        if not query:
            raise ValueError("query_text or shot_spec_id required")

        top_k = payload.top_k or 3
        started = time.perf_counter()
        provider = get_embedding_provider()
        query_emb = provider.embed_text(query)

        rows = (
            db.query(AssetEmbedding)
            .options(
                joinedload(AssetEmbedding.asset).joinedload(Asset.generation_job).joinedload(
                    GenerationJob.workflow_version
                )
            )
            .all()
        )

        scored: list[tuple[float, AssetEmbedding]] = []
        for row in rows:
            if not _is_approved(db, row.asset_id):
                continue
            if row.asset and row.asset.asset_type != "video":
                continue
            score = cosine_similarity(query_emb.vector, list(row.embedding))
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        latency_ms = int((time.perf_counter() - started) * 1000)

        hits: list[ReferenceSearchHit] = []
        snapshot = []
        for score, row in top:
            asset = row.asset
            job = asset.generation_job if asset else None
            wf = job.workflow_version if job else None
            config = {}
            if job and job.configuration_json:
                try:
                    config = json.loads(job.configuration_json)
                except json.JSONDecodeError:
                    config = {}
            hit = ReferenceSearchHit(
                asset_embedding_id=row.id,
                asset_id=row.asset_id,
                score=round(score, 6),
                segment_start_sec=row.segment_start_sec,
                segment_end_sec=row.segment_end_sec,
                thumbnail_url=f"/storage/{asset.file_path}" if asset else None,
                camera_motion=str(config.get("camera_motion") or ""),
                lighting=str(config.get("lighting") or ""),
                mood=str(config.get("mood") or ""),
                location=str(config.get("location") or ""),
                model_name=job.model_name if job else "",
                model_version=job.model_version if job else "",
                workflow_name=wf.name if wf else None,
                workflow_hash=wf.workflow_hash if wf else None,
                prompt=job.prompt if job else "",
            )
            # Enrich camera/lighting/mood from shot spec when available
            if job:
                shot = db.get(ShotSpec, job.shot_spec_id)
                if shot:
                    hit.camera_motion = shot.camera_motion
                    hit.lighting = shot.lighting
                    hit.mood = shot.mood
                    hit.location = shot.location
            hits.append(hit)
            snapshot.append(
                {
                    "asset_embedding_id": row.id,
                    "asset_id": row.asset_id,
                    "score": hit.score,
                }
            )

        event = RetrievalEvent(
            scene_id=scene_id,
            query_text=query,
            top_k=top_k,
            selected_asset_embedding_id=None,
            model_name=query_emb.model_name,
            model_version=query_emb.model_version,
            result_snapshot_json=json.dumps(snapshot),
            latency_ms=latency_ms,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        return ReferenceSearchResponse(
            retrieval_event_id=event.id,
            query_text=query,
            model_name=query_emb.model_name,
            model_version=query_emb.model_version,
            latency_ms=latency_ms,
            results=hits,
        )

    def select_reference(
        self, db: Session, retrieval_event_id: int, asset_embedding_id: int
    ) -> RetrievalEventRead:
        event = db.get(RetrievalEvent, retrieval_event_id)
        if not event:
            raise LookupError("Retrieval event not found")
        emb = db.get(AssetEmbedding, asset_embedding_id)
        if not emb:
            raise LookupError("Asset embedding not found")
        snapshot = json.loads(event.result_snapshot_json or "[]")
        allowed = {item.get("asset_embedding_id") for item in snapshot}
        if allowed and asset_embedding_id not in allowed:
            raise ValueError("Selected embedding was not in the retrieval top-k results")
        event.selected_asset_embedding_id = asset_embedding_id
        db.commit()
        db.refresh(event)
        return RetrievalEventRead.model_validate(event)
