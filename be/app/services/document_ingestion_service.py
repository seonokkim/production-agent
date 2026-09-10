"""Document asset ETL — production asset ingestion (not document RAG)."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Asset, BatchRun
from app.storage import get_asset_storage

logger = logging.getLogger(__name__)

PIPELINE_NAME = "production_asset_ingestion"
SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".pdf"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_text(filename: str, data: bytes) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        # Optional: no hard OCR dependency. Best-effort latin-1 fallback for tiny demos.
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


class DocumentIngestionService:
    """Batch/ETL-oriented document ingestion for Asset Library."""

    def create_pending_document(
        self,
        db: Session,
        *,
        filename: str,
        data: bytes,
        source: str = "upload",
        relative_dir: str = "documents",
    ) -> Asset:
        storage = get_asset_storage()
        safe_name = Path(filename).name
        key = f"{relative_dir}/{uuid.uuid4().hex}_{safe_name}"
        storage.write_bytes(key, data)
        asset = Asset(
            generation_job_id=None,
            asset_type="document",
            file_path=key,
            mime_type=_guess_mime(safe_name),
            checksum=_sha256(data),
            status="ready",
            original_filename=safe_name,
            file_size=len(data),
            source=source,
            ingestion_status="pending",
            metadata_json={"pipeline": PIPELINE_NAME},
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    def discover_landing_files(self) -> list[Path]:
        settings = get_settings()
        landing = Path(settings.asset_landing_path)
        landing.mkdir(parents=True, exist_ok=True)
        files: list[Path] = []
        for path in sorted(landing.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(path)
        return files

    def ingest_landing_folder(self, db: Session) -> list[Asset]:
        created: list[Asset] = []
        for path in self.discover_landing_files():
            existing = (
                db.query(Asset)
                .filter(
                    Asset.asset_type == "document",
                    Asset.original_filename == path.name,
                    Asset.source == "landing_folder",
                )
                .first()
            )
            if existing and existing.checksum == _sha256(path.read_bytes()):
                continue
            data = path.read_bytes()
            asset = self.create_pending_document(
                db,
                filename=path.name,
                data=data,
                source="landing_folder",
                relative_dir="documents/landing",
            )
            created.append(asset)
        return created

    def process_pending(self, db: Session, *, limit: int = 100) -> tuple[int, int]:
        """Validate + extract text + mark processed/failed. Returns (ok, failed)."""
        storage = get_asset_storage()
        pending = (
            db.query(Asset)
            .filter(
                Asset.asset_type == "document",
                Asset.ingestion_status.in_(["pending", "failed"]),
            )
            .order_by(Asset.id.asc())
            .limit(limit)
            .all()
        )
        ok = failed = 0
        for asset in pending:
            asset.ingestion_status = "processing"
            db.commit()
            try:
                if not storage.exists(asset.file_path):
                    raise FileNotFoundError(asset.file_path)
                data = storage.read_bytes(asset.file_path)
                name = asset.original_filename or Path(asset.file_path).name
                if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
                    raise ValueError(f"Unsupported document type: {name}")
                asset.checksum = _sha256(data)
                asset.file_size = len(data)
                text = _extract_text(name, data)
                asset.extracted_text = text
                if text is not None:
                    text_key = f"documents/extracted/{asset.id}.txt"
                    storage.write_bytes(text_key, text.encode("utf-8"))
                    asset.extracted_text_path = text_key
                asset.ingestion_status = "processed"
                asset.processed_at = _utcnow()
                asset.metadata_json = {
                    **(asset.metadata_json or {}),
                    "extracted_chars": len(text or ""),
                    "processed_by": PIPELINE_NAME,
                }
                ok += 1
            except Exception as exc:
                logger.exception("Document ingestion failed for asset %s", asset.id)
                asset.ingestion_status = "failed"
                asset.metadata_json = {
                    **(asset.metadata_json or {}),
                    "error": str(exc)[:500],
                }
                failed += 1
            db.commit()
        return ok, failed

    def run_pipeline(
        self,
        db: Session,
        *,
        airflow_dag_run_id: str | None = None,
        ingest_landing: bool = True,
    ) -> BatchRun:
        run = BatchRun(
            pipeline_name=PIPELINE_NAME,
            airflow_dag_run_id=airflow_dag_run_id,
            status="running",
            started_at=_utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        discovered = 0
        try:
            if ingest_landing:
                created = self.ingest_landing_folder(db)
                discovered += len(created)
            pending_count = (
                db.query(Asset)
                .filter(
                    Asset.asset_type == "document",
                    Asset.ingestion_status.in_(["pending", "failed", "processing"]),
                )
                .count()
            )
            discovered = max(discovered, pending_count)
            ok, failed = self.process_pending(db)
            run.records_discovered = discovered
            run.records_processed = ok
            run.records_failed = failed
            run.status = "failed" if failed and not ok else "success"
            run.completed_at = _utcnow()
            if failed:
                run.error_summary = f"{failed} document(s) failed ingestion"
            db.commit()
            db.refresh(run)
        except Exception as exc:
            logger.exception("Asset ingestion pipeline failed")
            run.status = "failed"
            run.error_summary = str(exc)[:1000]
            run.completed_at = _utcnow()
            db.commit()
            db.refresh(run)
        return run
