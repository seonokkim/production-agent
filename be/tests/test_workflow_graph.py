"""Tests for read-only ComfyUI workflow graph derivation."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

_TEST_ROOT = Path(__file__).resolve().parent / "_tmp" / f"graph-{uuid.uuid4().hex[:8]}"
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
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import app.database as database  # noqa: E402

database.engine = create_engine(
    os.environ["DATABASE_URL"],
    future=True,
    connect_args={"check_same_thread": False},
)
database.SessionLocal = sessionmaker(
    bind=database.engine, autoflush=False, autocommit=False, future=True
)
Base = database.Base

from app.main import create_app  # noqa: E402
from app.services.workflow_graph_service import api_workflow_to_graph  # noqa: E402
from app.services.workflow_service import ensure_default_workflows  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
KEYFRAME = json.loads((ROOT / "comfy" / "workflows" / "keyframe_v1.json").read_text())
I2V = json.loads((ROOT / "comfy" / "workflows" / "i2v_v1.json").read_text())

app = create_app()


def setup_module() -> None:
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        ensure_default_workflows(db)
    finally:
        db.close()


def test_keyframe_graph_counts_and_class_types():
    graph = api_workflow_to_graph(KEYFRAME, workflow_name="keyframe_v1")
    assert graph["node_count"] == 7
    assert graph["edge_count"] == 9
    classes = {n["class_type"] for n in graph["nodes"]}
    assert classes == {
        "CheckpointLoaderSimple",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    }
    # Checkpoint → KSampler model link
    assert any(
        e["source"] == "4" and e["target"] == "3" and e["target_input"] == "model"
        for e in graph["edges"]
    )
    assert all(n["id"] for n in graph["nodes"])


def test_i2v_graph_counts_and_wan_class():
    graph = api_workflow_to_graph(I2V, workflow_name="i2v_v1")
    assert graph["node_count"] == 12
    assert graph["edge_count"] == 13
    classes = {n["class_type"] for n in graph["nodes"]}
    assert "Wan22ImageToVideoLatent" in classes
    assert "UNETLoader" in classes
    assert "SaveVideo" in classes
    assert "CreateVideo" in classes
    # Unknown class fallback
    weird = api_workflow_to_graph(
        {"99": {"class_type": "TotallyCustomNodeXYZ", "inputs": {"foo": 1}}}
    )
    assert weird["nodes"][0]["label"]
    assert weird["nodes"][0]["category"] == "other"


def test_secrets_stripped_from_parameters():
    graph = api_workflow_to_graph(
        {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors",
                    "api_key": "should-not-appear",
                    "hf_token": "nope",
                },
            }
        }
    )
    params = graph["nodes"][0]["parameters"]
    assert "ckpt_name" in params
    assert "api_key" not in params
    assert "hf_token" not in params


def test_workflow_graph_endpoints():
    client = TestClient(app)
    listed = client.get("/api/v1/workflows").json()
    assert len(listed) >= 2
    names = {w["name"] for w in listed}
    assert "keyframe_v1" in names and "i2v_v1" in names

    kf = client.get("/api/v1/workflows/by-name/keyframe_v1/graph")
    assert kf.status_code == 200
    body = kf.json()
    assert body["node_count"] == 7
    assert body["edge_count"] == 9
    assert body["read_only"] is True
    assert body["frozen"] is False
    assert body["workflow_hash"]

    i2v = client.get("/api/v1/workflows/by-name/i2v_v1/graph")
    assert i2v.status_code == 200
    assert i2v.json()["node_count"] == 12
    assert i2v.json()["edge_count"] == 13

    wid = next(w["id"] for w in listed if w["name"] == "keyframe_v1")
    by_id = client.get(f"/api/v1/workflows/{wid}/graph")
    assert by_id.status_code == 200
    assert by_id.json()["node_count"] == 7

    info = client.get("/api/v1/comfyui/info")
    assert info.status_code == 200
    assert "comfyui_url" in info.json()
