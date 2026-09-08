"""Workflow registry — versioned ComfyUI graphs with SHA-256 hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import WorkflowVersion

DEFAULT_WORKFLOWS = [
    {
        "name": "keyframe_v1",
        "workflow_type": "keyframe",
        "version": "v1",
        "model_name": "sd_xl_base_1.0",
        "model_version": "1.0",
        "file": "keyframe_v1.json",
    },
    {
        "name": "i2v_v1",
        "workflow_type": "image_to_video",
        "version": "v1",
        "model_name": "Wan2.2-TI2V-5B",
        "model_version": "fp16",
        "file": "i2v_v1.json",
    },
]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_default_workflows(db: Session) -> None:
    settings = get_settings()
    workflows_dir = Path(settings.comfy_workflows_dir)
    for item in DEFAULT_WORKFLOWS:
        existing = db.query(WorkflowVersion).filter(WorkflowVersion.name == item["name"]).first()
        path = workflows_dir / item["file"]
        if not path.exists():
            continue
        whash = _hash_file(path)
        if existing:
            existing.workflow_path = str(path)
            existing.workflow_hash = whash
            existing.model_name = item["model_name"]
            existing.model_version = item["model_version"]
            existing.active = True
            continue
        db.add(
            WorkflowVersion(
                name=item["name"],
                workflow_type=item["workflow_type"],
                version=item["version"],
                workflow_path=str(path),
                workflow_hash=whash,
                model_name=item["model_name"],
                model_version=item["model_version"],
                active=True,
            )
        )
    db.commit()


def get_active_workflow(db: Session, workflow_type: str) -> WorkflowVersion:
    wf = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_type == workflow_type,
            WorkflowVersion.active.is_(True),
        )
        .order_by(WorkflowVersion.id.desc())
        .first()
    )
    if not wf:
        raise ValueError(f"No active workflow for type={workflow_type}")
    return wf


def load_workflow_snapshot(workflow: WorkflowVersion) -> dict:
    return json.loads(Path(workflow.workflow_path).read_text(encoding="utf-8"))


def load_node_map(workflow_name: str) -> dict:
    settings = get_settings()
    path = Path(settings.comfy_node_map_dir) / f"{workflow_name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
