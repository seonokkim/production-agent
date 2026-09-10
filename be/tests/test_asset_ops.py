"""P1 Asset Operations — document upload, ingestion ETL, n8n webhook emit."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

# Configure isolated env before importing the app package.
_TEST_ROOT = Path(__file__).resolve().parent / "_tmp" / f"asset-ops-{uuid.uuid4().hex[:8]}"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
_DB = _TEST_ROOT / "test.db"
_STORAGE = _TEST_ROOT / "storage"
_LANDING = _TEST_ROOT / "landing"
_STORAGE.mkdir(exist_ok=True)
_LANDING.mkdir(exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ASSET_STORAGE_PATH"] = str(_STORAGE)
os.environ["ASSET_LANDING_PATH"] = str(_LANDING)
os.environ["ASSET_STORAGE_PROVIDER"] = "local"
os.environ["GENERATION_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["N8N_REVIEW_WEBHOOK_URL"] = ""
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
from app.services.schema_ensure_assets import ensure_asset_ops_schema  # noqa: E402
from app.services.workflow_service import ensure_default_workflows  # noqa: E402
import app.models  # noqa: E402, F401

app = create_app()


def setup_module() -> None:
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    ensure_asset_ops_schema()
    db = database.SessionLocal()
    try:
        ensure_default_workflows(db)
    finally:
        db.close()


def test_document_upload_and_ingestion_pipeline():
    with TestClient(app) as client:
        files = {
            "file": ("aurora_note.md", b"# Demo note\nFictional production doc.\n", "text/markdown")
        }
        r = client.post("/api/v1/assets/documents", files=files, data={"source": "upload"})
        assert r.status_code == 201, r.text
        asset = r.json()["asset"]
        assert asset["asset_type"] == "document"
        assert asset["ingestion_status"] == "pending"
        assert asset["generation_job_id"] is None
        assert asset["original_filename"] == "aurora_note.md"

        run = client.post("/api/v1/assets/ingestion/run?ingest_landing=false")
        assert run.status_code == 201, run.text
        run_body = run.json()
        assert run_body["pipeline_name"] == "production_asset_ingestion"
        assert run_body["status"] == "success"
        assert run_body["records_processed"] >= 1

        listed = client.get("/api/v1/assets?tab=documents")
        assert listed.status_code == 200
        docs = listed.json()
        assert any(d["id"] == asset["id"] and d["ingestion_status"] == "processed" for d in docs)
        processed = next(d for d in docs if d["id"] == asset["id"])
        assert processed["extracted_text"] and "Demo note" in processed["extracted_text"]

        metrics = client.get("/api/v1/dashboard")
        assert metrics.status_code == 200
        m = metrics.json()
        assert m["documents"] >= 1
        assert m["last_airflow_run_status"] == "success"


def test_landing_folder_ingest():
    (_LANDING / "aurora_shot_list.csv").write_text(
        "shot_no,location\n1,factory\n", encoding="utf-8"
    )
    with TestClient(app) as client:
        run = client.post("/api/v1/assets/ingestion/run")
        assert run.status_code == 201, run.text
        docs = client.get("/api/v1/assets?tab=documents&source=landing_folder").json()
        assert any(d["original_filename"] == "aurora_shot_list.csv" for d in docs)
        assert any(d["ingestion_status"] == "processed" for d in docs)


def test_review_webhook_optional():
    with TestClient(app) as client:
        files = {"file": ("review_me.txt", b"hello", "text/plain")}
        asset_id = client.post(
            "/api/v1/assets/documents", files=files, data={"source": "upload"}
        ).json()["asset"]["id"]
        r = client.post(
            f"/api/v1/assets/{asset_id}/reviews",
            json={"decision": "approved", "comment": "ok", "reviewer_name": "creator"},
        )
        assert r.status_code == 201
        assert r.json()["decision"] == "approved"
