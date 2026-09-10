"""
Airflow DAG: production_asset_ingestion

Batch/ETL only — does NOT submit ComfyUI generations.

Logical pipeline (executed in Production Agent DocumentIngestionService):
  discover_assets → validate_files → extract_document_metadata
  → normalize_assets → compute_checksums → upsert_asset_records
  → update_batch_metrics (batch_runs)

Local/dev without Airflow:
  make seed-documents && make ingest-assets
  POST /api/v1/assets/ingestion/run

Requires AIRFLOW_HOME / DAGS_FOLDER to include this file (see airflow/README.md).
"""

from __future__ import annotations

import os
from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import PythonOperator
except ImportError:  # pragma: no cover — Airflow optional for product CI
    DAG = None  # type: ignore


REPO_ROOT = os.environ.get(
    "PROD_AGENT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
BE_URL = os.environ.get("PROD_AGENT_BE_URL", "http://127.0.0.1:8001")


def _trigger_via_api(**context):
    """Call BE ingestion endpoint — keeps ETL logic in the product service."""
    import urllib.request

    dag_run = context.get("dag_run")
    run_id = context.get("run_id") or (dag_run.run_id if dag_run else "manual")
    url = (
        f"{BE_URL}/api/v1/assets/ingestion/run"
        f"?airflow_dag_run_id={run_id}&ingest_landing=true"
    )
    req = urllib.request.Request(url, method="POST", data=b"")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        print(resp.read().decode("utf-8"))


if DAG is not None:
    with DAG(
        dag_id="production_asset_ingestion",
        description="Batch document/asset ETL for Production Agent (not ComfyUI)",
        schedule="@daily",
        start_date=datetime(2026, 9, 1),
        catchup=False,
        tags=["production-agent", "etl", "assets"],
    ) as dag:
        start = EmptyOperator(task_id="discover_assets")
        run_pipeline = PythonOperator(
            task_id="run_ingestion_pipeline",
            python_callable=_trigger_via_api,
        )
        # Named to mirror §39.5 task intent; metrics written by BE → batch_runs.
        finish = EmptyOperator(task_id="update_batch_metrics")

        fallback_script = BashOperator(
            task_id="fallback_local_script",
            bash_command=(
                f"cd {REPO_ROOT} && "
                "cd be && . .venv/bin/activate && "
                "python ../scripts/run_asset_ingestion.py "
                "--airflow-dag-run-id {{ run_id }}"
            ),
            trigger_rule="all_failed",
        )

        start >> run_pipeline >> finish
        run_pipeline >> fallback_script
