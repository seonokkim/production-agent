#!/usr/bin/env python3
"""Run production_asset_ingestion without Airflow (local / Makefile / CI)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "be"))

from app.database import SessionLocal  # noqa: E402
from app.services.document_ingestion_service import DocumentIngestionService  # noqa: E402
from app.services.schema_ensure_assets import ensure_asset_ops_schema  # noqa: E402
import app.models  # noqa: E402, F401


def main() -> int:
    parser = argparse.ArgumentParser(description="Run production_asset_ingestion pipeline")
    parser.add_argument("--airflow-dag-run-id", default=None)
    parser.add_argument("--no-landing", action="store_true")
    args = parser.parse_args()

    ensure_asset_ops_schema()
    db = SessionLocal()
    try:
        run = DocumentIngestionService().run_pipeline(
            db,
            airflow_dag_run_id=args.airflow_dag_run_id,
            ingest_landing=not args.no_landing,
        )
        print(
            json.dumps(
                {
                    "id": run.id,
                    "status": run.status,
                    "discovered": run.records_discovered,
                    "processed": run.records_processed,
                    "failed": run.records_failed,
                    "error_summary": run.error_summary,
                },
                indent=2,
            )
        )
        return 0 if run.status == "success" else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
