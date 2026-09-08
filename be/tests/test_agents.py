from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

_TEST_ROOT = Path(__file__).resolve().parent / "_tmp" / f"agents-{uuid.uuid4().hex[:8]}"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
_DB = _TEST_ROOT / "test.db"
_STORAGE = _TEST_ROOT / "storage"
_STORAGE.mkdir(exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["GENERATION_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["ASSET_STORAGE_PATH"] = str(_STORAGE)
os.environ["APP_ENV"] = "test"
os.environ["AGENTS_SDK_ENABLED"] = "true"

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
        project = Project(name="Project Aurora", description="agents test")
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


def test_agent_catalog():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents")
        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["agent_id"] == "multimodal-rag"
        assert body[0]["display_name_en"] == "Multimodal RAG"
        assert "approved-assets-video" in body[0]["collection_ids"]


def test_mock_run_empty_corpus():
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/agent-runs",
            json={
                "agent_id": "multimodal-rag",
                "query": "handheld night factory clips",
                "media_type": "any",
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "completed"
        assert body["runtime"] == "mock"
        assert body["conversation_id"]
        assert body["citations"] == []
        assert "No approved media" in body["answer_text"]
        stages = {e["stage"] for e in body["events"]}
        assert "searching" in stages
        assert "answering" in stages
        # No video cites → grounding_video skipped
        assert "grounding_video" not in stages

        hist = client.get("/api/v1/agent-conversations")
        assert hist.status_code == 200
        assert any(c["id"] == body["conversation_id"] for c in hist.json())

        detail = client.get(f"/api/v1/agent-conversations/{body['conversation_id']}")
        assert detail.status_code == 200
        msgs = detail.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"


def test_mock_run_with_video_cite_and_attach():
    with TestClient(app) as client:
        scene_id = _scene_id(client)
        spec = client.post(f"/api/v1/scenes/{scene_id}/shot-spec/suggest").json()

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

        run = client.post(
            "/api/v1/agent-runs",
            json={
                "agent_id": "multimodal-rag",
                "query": "abandoned factory night handheld",
                "media_type": "video",
            },
        )
        assert run.status_code == 201
        body = run.json()
        assert body["status"] == "completed"
        assert body["citations"]
        assert body["citations"][0]["media_type"] == "video"
        stages = [e["stage"] for e in body["events"]]
        assert "grounding_video" in stages
        cite_key = body["citations"][0]["cite_key"]

        attach = client.post(
            f"/api/v1/agent-runs/{body['id']}/attach",
            json={"scene_id": scene_id, "cite_keys": [cite_key]},
        )
        assert attach.status_code == 201
        attached = attach.json()
        assert attached["retrieval_event_id"]
        assert attached["reference_asset_ids"] == [video_asset_id]
        assert attached["references"][0]["media_type"] == "video"
        assert attached["references"][0]["cite_key"] == cite_key

        # Poll fallback
        got = client.get(f"/api/v1/agent-runs/{body['id']}")
        assert got.status_code == 200
        assert got.json()["id"] == body["id"]


def test_sse_stream_empty_corpus():
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/agent-runs/stream",
            json={
                "agent_id": "multimodal-rag",
                "query": "night factory handheld",
                "media_type": "any",
            },
        ) as res:
            assert res.status_code == 200
            body = "".join(res.iter_text())
        assert "event: stage" in body
        assert "event: result" in body
        assert "searching" in body
        assert "answering" in body


def test_factory_mock_descriptor():
    from app.agents.multimodal_rag_factory import MultimodalRagAgentFactory

    desc = MultimodalRagAgentFactory.create(runtime="mock")
    assert desc["agent_id"] == "multimodal-rag"
    assert "multimodal_search" in desc["tools"]


def test_optional_marengo_embedding_override():
    """Per-run embedding_provider=marengo should call TwelveLabs (or record fallback)."""
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/agent-runs",
            json={
                "agent_id": "multimodal-rag",
                "query": "night factory handheld with neon",
                "media_type": "any",
                "embedding_provider": "marengo",
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "completed"
        assert body["conversation_id"]
        # Actual live call may be marengo or mock-fallback/mock-nokey depending on key.
        assert body["embedding_provider"] in {
            "marengo",
            "mock-fallback",
            "mock-nokey",
            "mock",
        }


def test_conversation_continue_and_delete():
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/agent-runs",
            json={
                "agent_id": "multimodal-rag",
                "query": "first question about factory",
                "media_type": "any",
            },
        )
        assert first.status_code == 201
        cid = first.json()["conversation_id"]
        assert cid

        second = client.post(
            "/api/v1/agent-runs",
            json={
                "agent_id": "multimodal-rag",
                "query": "follow-up about lighting",
                "media_type": "any",
                "conversation_id": cid,
            },
        )
        assert second.status_code == 201
        assert second.json()["conversation_id"] == cid

        detail = client.get(f"/api/v1/agent-conversations/{cid}").json()
        assert detail["message_count"] == 4
        assert len(detail["messages"]) == 4

        deleted = client.delete(f"/api/v1/agent-conversations/{cid}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/agent-conversations/{cid}").status_code == 404
