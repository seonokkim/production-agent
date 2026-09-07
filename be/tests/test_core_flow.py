from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

# Configure isolated env before importing the app package.
_TEST_ROOT = Path(__file__).resolve().parent / "_tmp" / f"run-{uuid.uuid4().hex[:8]}"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
_DB = _TEST_ROOT / "test.db"
_STORAGE = _TEST_ROOT / "storage"
_STORAGE.mkdir(exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["GENERATION_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ASSET_STORAGE_PATH"] = str(_STORAGE)
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

# Rebuild engine against the isolated DATABASE_URL (module may be cached).
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
engine = database.engine
SessionLocal = database.SessionLocal
Base = database.Base

from app.main import create_app  # noqa: E402
from app.models import Project, Scene  # noqa: E402
from app.services import generation_service as generation_service_mod  # noqa: E402
from app.services.workflow_service import ensure_default_workflows  # noqa: E402

# Reset provider singleton so mock jobs are fresh per test process.
generation_service_mod._provider_singleton = None

app = create_app()


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_workflows(db)
        project = Project(name="Project Aurora", description="test")
        db.add(project)
        db.commit()
        db.refresh(project)
        scene = Scene(
            project_id=project.id,
            title="Abandoned Factory",
            episode_no=2,
            scene_no=18,
            brief=(
                "Late at night, a detective enters an abandoned factory.\n"
                "Rain and neon light enter through broken windows."
            ),
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


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_shot_spec_suggest_and_validation():
    with TestClient(app) as client:
        scene_id = _scene_id(client)
        res = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest")
        assert res.status_code == 200
        body = res.json()
        assert body["location"]
        assert body["subjects"]
        assert body["source"] == "llm"


def test_generation_status_machine_and_rerun():
    with TestClient(app) as client:
        scene_id = _scene_id(client)
        spec = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest").json()
        created = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={"generation_type": "keyframe", "shot_spec_id": spec["id"]},
        )
        assert created.status_code == 202
        job = _wait(client, created.json()["generation_id"])
        assert job["status"] == "completed"
        assert job["assets"]
        assert job["workflow_version"]["workflow_hash"]

        asset_id = job["assets"][0]["id"]
        review = client.post(
            f"/api/v1/assets/{asset_id}/reviews",
            json={"decision": "approved", "comment": "Good lighting"},
        )
        assert review.status_code == 201

        rerun = client.post(f"/api/v1/generations/{job['id']}/rerun")
        assert rerun.status_code == 202
        child = _wait(client, rerun.json()["generation_id"])
        assert child["id"] != job["id"]
        assert child["parent_generation_id"] == job["id"]
        assert child["seed"] == job["seed"]

        original = client.get(f"/api/v1/generations/{job['id']}").json()
        assert original["status"] == "completed"


def test_failed_generation_keeps_prior_approved():
    with TestClient(app) as client:
        scene_id = _scene_id(client)
        spec = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest").json()
        ok = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={"generation_type": "keyframe", "shot_spec_id": spec["id"]},
        )
        ok_job = _wait(client, ok.json()["generation_id"])
        asset_id = ok_job["assets"][0]["id"]
        client.post(f"/api/v1/assets/{asset_id}/reviews", json={"decision": "approved"})

        fail = client.post(
            f"/api/v1/scenes/{scene_id}/generations",
            json={
                "generation_type": "keyframe",
                "shot_spec_id": spec["id"],
                "force_fail": True,
            },
        )
        failed = _wait(client, fail.json()["generation_id"])
        assert failed["status"] == "failed"

        prior = client.get(f"/api/v1/assets/{asset_id}").json()
        assert prior["status"] == "ready"
