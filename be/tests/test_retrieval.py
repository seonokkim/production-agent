from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

_TEST_ROOT = Path(__file__).resolve().parent / "_tmp" / f"retrieval-{uuid.uuid4().hex[:8]}"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
_DB = _TEST_ROOT / "test.db"
_STORAGE = _TEST_ROOT / "storage"
_STORAGE.mkdir(exist_ok=True)
(_STORAGE / "retrieval").mkdir(exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["GENERATION_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["ASSET_STORAGE_PATH"] = str(_STORAGE)
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import app.database as database  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

database.engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)
database.SessionLocal = sessionmaker(
    bind=database.engine, autoflush=False, autocommit=False, future=True
)
Base = database.Base

import app.models  # noqa: F401, E402
from app.main import create_app  # noqa: E402
from app.models import Project, Scene  # noqa: E402
from app.services import generation_service as generation_service_mod  # noqa: E402
from app.services.workflow_service import ensure_default_workflows  # noqa: E402

generation_service_mod._provider_singleton = None
app = create_app()


def setup_module() -> None:
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        ensure_default_workflows(db)
        project = Project(name="Project Aurora", description="retrieval test")
        db.add(project)
        db.commit()
        db.refresh(project)
        scene = Scene(
            project_id=project.id,
            title="Abandoned Factory",
            episode_no=2,
            scene_no=18,
            brief="Late at night, a detective enters an abandoned factory.",
        )
        db.add(scene)
        db.commit()
    finally:
        db.close()


def _scene_id(client: TestClient) -> int:
    projects = client.get("/api/v1/projects").json()
    scenes = client.get(f"/api/v1/projects/{projects[0]['id']}/scenes").json()
    return scenes[0]["id"]


def _wait(client: TestClient, generation_id: int, timeout: float = 12.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        data = client.get(f"/api/v1/generations/{generation_id}").json()
        if data["status"] in {"completed", "failed"}:
            return data
        time.sleep(0.4)
    raise AssertionError("timeout waiting for generation")


def test_approved_reference_retrieval_flow():
    with TestClient(app) as client:
        scene_id = _scene_id(client)
        spec = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest").json()

        # Create keyframe → video → approve (indexes embedding).
        key = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={"generation_type": "keyframe", "shot_spec_id": spec["id"]},
        )
        key_job = _wait(client, key.json()["generation_id"])
        ref_id = key_job["assets"][0]["id"]

        vid = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={
                "generation_type": "image_to_video",
                "shot_spec_id": spec["id"],
                "reference_asset_id": ref_id,
                "duration_seconds": 4,
            },
        )
        vid_job = _wait(client, vid.json()["generation_id"], timeout=15)
        assert vid_job["status"] == "completed"
        video_asset_id = vid_job["assets"][0]["id"]

        review = client.post(
            f"/api/v1/assets/{video_asset_id}/reviews",
            json={"decision": "approved", "comment": "Good reference"},
        )
        assert review.status_code == 201

        emb = client.post(f"/api/v1/assets/{video_asset_id}/embeddings")
        assert emb.status_code == 201

        search = client.post(
            f"/api/v1/scenes/{scene_id}/reference-search",
            json={"shot_spec_id": spec["id"], "top_k": 3},
        )
        assert search.status_code == 200
        body = search.json()
        assert body["retrieval_event_id"]
        assert body["results"]
        assert body["results"][0]["score"] >= 0

        selected = body["results"][0]["asset_embedding_id"]
        sel = client.post(
            f"/api/v1/retrieval-events/{body['retrieval_event_id']}/select",
            json={"asset_embedding_id": selected},
        )
        assert sel.status_code == 200
        assert sel.json()["selected_asset_embedding_id"] == selected

        # Attach selected reference into next generation provenance.
        next_key = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={
                "generation_type": "keyframe",
                "shot_spec_id": spec["id"],
                "retrieval_event_id": body["retrieval_event_id"],
                "reference_asset_embedding_id": selected,
            },
        )
        assert next_key.status_code == 202
        next_job = _wait(client, next_key.json()["generation_id"])
        assert next_job["retrieval_event_id"] == body["retrieval_event_id"]
        assert next_job["reference_asset_embedding_id"] == selected
        assert next_job["reference_asset_id"] == video_asset_id
