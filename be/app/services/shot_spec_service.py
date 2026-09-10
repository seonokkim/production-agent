"""Shot specification suggestion and persistence."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Scene, ShotSpec
from app.providers.llm import LLMProvider
from app.schemas import ShotSpecBase, ShotSpecCreate, ShotSpecRead, ShotSpecUpdate
from app.services.style_lock import shot_spec_motion_template, shot_spec_visual_template


def _subjects_to_json(subjects: list[str]) -> str:
    return json.dumps(subjects, ensure_ascii=False)


def _subjects_from_json(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def to_read(spec: ShotSpec) -> ShotSpecRead:
    return ShotSpecRead(
        id=spec.id,
        scene_id=spec.scene_id,
        version=spec.version,
        location=spec.location,
        time_of_day=spec.time_of_day,
        subjects=_subjects_from_json(spec.subjects_json),
        action=spec.action,
        shot_size=spec.shot_size,
        camera_angle=spec.camera_angle,
        camera_motion=spec.camera_motion,
        lighting=spec.lighting,
        mood=spec.mood,
        visual_prompt=spec.visual_prompt,
        motion_prompt=spec.motion_prompt,
        source=spec.source,
        created_at=spec.created_at,
    )


def validate_shot_spec(data: ShotSpecBase) -> ShotSpecBase:
    """Require core fields before generation."""
    required = {
        "location": data.location,
        "time_of_day": data.time_of_day,
        "action": data.action,
        "shot_size": data.shot_size,
        "camera_angle": data.camera_angle,
        "camera_motion": data.camera_motion,
        "lighting": data.lighting,
        "mood": data.mood,
    }
    missing = [k for k, v in required.items() if not (v or "").strip()]
    if missing:
        raise ValueError(f"ShotSpec validation failed; missing: {', '.join(missing)}")
    if not data.subjects:
        raise ValueError("ShotSpec validation failed; subjects required")
    return data


class ShotSpecService:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or LLMProvider()

    def suggest(
        self,
        db: Session,
        scene_id: int,
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> ShotSpecRead:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise LookupError("Scene not found")
        suggestion = validate_shot_spec(
            self.llm.suggest_shot_spec(
                scene.brief, llm_provider=llm_provider, llm_model=llm_model
            )
        )
        return self.create(
            db,
            scene_id,
            ShotSpecCreate(**suggestion.model_dump(), source="llm"),
        )

    def create(self, db: Session, scene_id: int, payload: ShotSpecCreate) -> ShotSpecRead:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise LookupError("Scene not found")
        validated = validate_shot_spec(ShotSpecBase(**payload.model_dump()))
        latest = (
            db.query(ShotSpec)
            .filter(ShotSpec.scene_id == scene_id)
            .order_by(ShotSpec.version.desc())
            .first()
        )
        version = (latest.version + 1) if latest else 1
        row = ShotSpec(
            scene_id=scene_id,
            version=version,
            location=validated.location,
            time_of_day=validated.time_of_day,
            subjects_json=_subjects_to_json(validated.subjects),
            action=validated.action,
            shot_size=validated.shot_size,
            camera_angle=validated.camera_angle,
            camera_motion=validated.camera_motion,
            lighting=validated.lighting,
            mood=validated.mood,
            visual_prompt=validated.visual_prompt or self._build_visual(validated),
            motion_prompt=validated.motion_prompt or self._build_motion(validated),
            source=payload.source,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return to_read(row)

    def list_for_scene(self, db: Session, scene_id: int) -> list[ShotSpecRead]:
        rows = (
            db.query(ShotSpec)
            .filter(ShotSpec.scene_id == scene_id)
            .order_by(ShotSpec.version.desc())
            .all()
        )
        return [to_read(r) for r in rows]

    def update(self, db: Session, shot_spec_id: int, payload: ShotSpecUpdate) -> ShotSpecRead:
        row = db.get(ShotSpec, shot_spec_id)
        if not row:
            raise LookupError("ShotSpec not found")
        data = to_read(row).model_dump()
        updates = payload.model_dump(exclude_unset=True)
        data.update(updates)
        validated = validate_shot_spec(ShotSpecBase(**{k: data[k] for k in ShotSpecBase.model_fields}))
        # Immutable history: edit creates a new version rather than rewriting.
        return self.create(
            db,
            row.scene_id,
            ShotSpecCreate(**validated.model_dump(), source="manual"),
        )

    def _build_visual(self, data: ShotSpecBase) -> str:
        subjects = ", ".join(data.subjects)
        return shot_spec_visual_template(
            location=data.location,
            time_of_day=data.time_of_day,
            subjects=subjects,
            action=data.action,
            shot_size=data.shot_size,
            camera_angle=data.camera_angle,
            lighting=data.lighting,
            mood=data.mood,
        )

    def _build_motion(self, data: ShotSpecBase) -> str:
        return shot_spec_motion_template(
            camera_motion=data.camera_motion,
            action=data.action,
            mood=data.mood,
        )
