"""Generation service — freeze config, submit, poll, persist assets, exact rerun."""

from __future__ import annotations

import json
import logging
import random
import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import SessionLocal
from app.models import Asset, GenerationJob, Scene, ShotSpec
from app.providers import get_generation_provider
from app.providers.base import GenerationProvider, GenerationRequest, ProviderStatus
from app.schemas import AssetRead, GenerationAccepted, GenerationCreate, GenerationRead
from app.services.shot_spec_service import _subjects_from_json
from app.services.workflow_service import get_active_workflow, load_node_map, load_workflow_snapshot

logger = logging.getLogger(__name__)

LEGAL_TRANSITIONS = {
    "queued": {"running", "failed"},
    "running": {"completed", "failed"},
    "failed": set(),
    "completed": set(),
}

# Keep provider instances alive so mock in-memory job state survives poll requests.
_provider_singleton: GenerationProvider | None = None
_provider_lock = threading.Lock()


def _provider() -> GenerationProvider:
    global _provider_singleton
    with _provider_lock:
        if _provider_singleton is None:
            _provider_singleton = get_generation_provider()
        return _provider_singleton


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalize DB datetimes (SQLite often returns naive) before arithmetic."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _elapsed_ms(started_at: datetime | None, completed_at: datetime | None) -> int | None:
    start = _as_utc(started_at)
    end = _as_utc(completed_at)
    if start is None or end is None:
        return None
    return int((end - start).total_seconds() * 1000)


def _transition(job: GenerationJob, new_status: str) -> None:
    allowed = LEGAL_TRANSITIONS.get(job.status, set())
    if new_status == job.status:
        return
    if new_status not in allowed:
        raise ValueError(f"Illegal status transition {job.status} → {new_status}")
    job.status = new_status


def asset_to_read(asset: Asset) -> AssetRead:
    return AssetRead(
        id=asset.id,
        generation_job_id=asset.generation_job_id,
        asset_type=asset.asset_type,
        file_path=asset.file_path,
        mime_type=asset.mime_type,
        checksum=asset.checksum,
        width=asset.width,
        height=asset.height,
        duration_seconds=asset.duration_seconds,
        status=asset.status,
        created_at=asset.created_at,
        url=f"/storage/{asset.file_path}",
    )


def job_to_read(job: GenerationJob) -> GenerationRead:
    return GenerationRead(
        id=job.id,
        scene_id=job.scene_id,
        shot_spec_id=job.shot_spec_id,
        workflow_version_id=job.workflow_version_id,
        parent_generation_id=job.parent_generation_id,
        provider_job_id=job.provider_job_id,
        generation_type=job.generation_type,
        provider=job.provider,
        status=job.status,
        prompt=job.prompt,
        negative_prompt=job.negative_prompt,
        model_name=job.model_name,
        model_version=job.model_version,
        seed=job.seed,
        width=job.width,
        height=job.height,
        frame_count=job.frame_count,
        fps=job.fps,
        duration_seconds=job.duration_seconds,
        reference_asset_id=job.reference_asset_id,
        workflow_snapshot_json=job.workflow_snapshot_json,
        configuration_json=job.configuration_json,
        error_code=job.error_code,
        error_message=job.error_message,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        generation_ms=job.generation_ms,
        assets=[asset_to_read(a) for a in job.assets],
        workflow_version=job.workflow_version,
    )


class GenerationService:
    def submit(self, db: Session, scene_id: int, payload: GenerationCreate) -> GenerationAccepted:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise LookupError("Scene not found")
        shot = db.get(ShotSpec, payload.shot_spec_id)
        if not shot or shot.scene_id != scene_id:
            raise LookupError("ShotSpec not found for scene")

        workflow_type = (
            "keyframe" if payload.generation_type == "keyframe" else "image_to_video"
        )
        workflow = get_active_workflow(db, workflow_type)
        snapshot = load_workflow_snapshot(workflow)
        node_map = load_node_map(workflow.name)

        if payload.generation_type == "image_to_video" and not payload.reference_asset_id:
            raise ValueError("image_to_video requires reference_asset_id")

        prompt = shot.visual_prompt if payload.generation_type == "keyframe" else shot.motion_prompt
        negative = "blurry, low quality, watermark, text overlay, deformed"
        seed = payload.seed if payload.seed is not None else random.randint(1, 2_147_483_647)
        duration = payload.duration_seconds if payload.generation_type == "image_to_video" else None
        settings = get_settings()

        configuration = {
            "generation_type": payload.generation_type,
            "shot_spec_id": shot.id,
            "shot_spec_version": shot.version,
            "subjects": _subjects_from_json(shot.subjects_json),
            "location": shot.location,
            "force_fail": payload.force_fail,
            "node_map": node_map,
        }

        job = GenerationJob(
            scene_id=scene_id,
            shot_spec_id=shot.id,
            workflow_version_id=workflow.id,
            generation_type=payload.generation_type,
            provider=settings.generation_provider,
            status="queued",
            prompt=prompt,
            negative_prompt=negative,
            model_name=workflow.model_name,
            model_version=workflow.model_version,
            seed=seed,
            width=1280,
            height=720,
            frame_count=int((duration or 0) * 24) if duration else None,
            fps=24 if duration else None,
            duration_seconds=duration,
            reference_asset_id=payload.reference_asset_id,
            workflow_snapshot_json=json.dumps(snapshot),
            configuration_json=json.dumps(configuration),
            queued_at=_utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        ref_path = None
        if payload.reference_asset_id:
            ref = db.get(Asset, payload.reference_asset_id)
            if ref:
                ref_path = ref.file_path

        try:
            result = _provider().submit(
                GenerationRequest(
                    generation_type=payload.generation_type,
                    prompt=prompt,
                    negative_prompt=negative,
                    seed=seed,
                    width=1280,
                    height=720,
                    duration_seconds=duration,
                    reference_file_path=ref_path,
                    workflow_snapshot=snapshot,
                    node_map=node_map,
                    force_fail=payload.force_fail,
                )
            )
            job.provider_job_id = result.provider_job_id
            db.commit()
        except Exception as exc:
            logger.exception("Provider submit failed for generation %s", job.id)
            _transition(job, "failed")
            job.error_code = "PROVIDER_SUBMIT_FAILED"
            job.error_message = str(exc)
            job.completed_at = _utcnow()
            db.commit()

        return GenerationAccepted(generation_id=job.id, status=job.status)

    def get(self, db: Session, generation_id: int) -> GenerationRead:
        job = (
            db.query(GenerationJob)
            .options(joinedload(GenerationJob.assets), joinedload(GenerationJob.workflow_version))
            .filter(GenerationJob.id == generation_id)
            .first()
        )
        if not job:
            raise LookupError("Generation not found")
        if job.status in {"queued", "running"} and job.provider_job_id:
            self._poll_once(db, job)
            db.refresh(job)
        return job_to_read(job)

    def list_for_scene(self, db: Session, scene_id: int) -> list[GenerationRead]:
        jobs = (
            db.query(GenerationJob)
            .options(joinedload(GenerationJob.assets), joinedload(GenerationJob.workflow_version))
            .filter(GenerationJob.scene_id == scene_id)
            .order_by(GenerationJob.id.desc())
            .all()
        )
        for job in jobs:
            if job.status in {"queued", "running"} and job.provider_job_id:
                self._poll_once(db, job)
        return [job_to_read(j) for j in jobs]

    def rerun(self, db: Session, generation_id: int) -> GenerationAccepted:
        """Exact rerun: copy frozen config into a NEW child job; never overwrite source."""
        source = db.get(GenerationJob, generation_id)
        if not source:
            raise LookupError("Generation not found")
        config = json.loads(source.configuration_json or "{}")
        payload = GenerationCreate(
            generation_type=source.generation_type,
            shot_spec_id=source.shot_spec_id,
            reference_asset_id=source.reference_asset_id,
            seed=source.seed,
            duration_seconds=source.duration_seconds,
            force_fail=bool(config.get("force_fail", False)),
        )
        accepted = self.submit(db, source.scene_id, payload)
        child = db.get(GenerationJob, accepted.generation_id)
        if child:
            child.parent_generation_id = source.id
            # Preserve exact frozen prompts/snapshots from parent when possible.
            child.prompt = source.prompt
            child.negative_prompt = source.negative_prompt
            child.workflow_snapshot_json = source.workflow_snapshot_json
            child.model_name = source.model_name
            child.model_version = source.model_version
            child.width = source.width
            child.height = source.height
            db.commit()
        return accepted

    def _poll_once(self, db: Session, job: GenerationJob) -> None:
        assert job.provider_job_id
        try:
            status = _provider().get_status(job.provider_job_id)
        except Exception as exc:
            logger.exception("Provider poll failed for generation %s", job.id)
            if job.status == "queued":
                _transition(job, "running")
                job.started_at = job.started_at or _utcnow()
            _transition(job, "failed")
            job.error_code = "PROVIDER_POLL_FAILED"
            job.error_message = str(exc)
            job.completed_at = _utcnow()
            db.commit()
            return

        if status.status == ProviderStatus.QUEUED:
            return

        if status.status == ProviderStatus.RUNNING:
            if job.status == "queued":
                _transition(job, "running")
                job.started_at = _utcnow()
                db.commit()
            return

        if status.status == ProviderStatus.FAILED:
            if job.status == "queued":
                _transition(job, "running")
                job.started_at = job.started_at or _utcnow()
            _transition(job, "failed")
            job.error_code = status.error_code or "PROVIDER_FAILED"
            job.error_message = status.error_message
            job.completed_at = _utcnow()
            if job.started_at:
                job.generation_ms = _elapsed_ms(job.started_at, job.completed_at)
            db.commit()
            return

        if status.status == ProviderStatus.COMPLETED:
            if job.status == "queued":
                _transition(job, "running")
                job.started_at = job.started_at or _utcnow()
            if not job.assets:
                for out in status.outputs:
                    db.add(
                        Asset(
                            generation_job_id=job.id,
                            asset_type=out.asset_type,
                            file_path=out.file_path,
                            mime_type=out.mime_type,
                            checksum=out.checksum,
                            width=out.width or job.width,
                            height=out.height or job.height,
                            duration_seconds=out.duration_seconds or job.duration_seconds,
                            status="ready",
                        )
                    )
            _transition(job, "completed")
            job.completed_at = _utcnow()
            if job.started_at:
                job.generation_ms = _elapsed_ms(job.started_at, job.completed_at)
            db.commit()


def background_poll_loop_disabled() -> None:
    """MVP polls on GET; durable workers are out of P0 scope."""
    _ = SessionLocal
