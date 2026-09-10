# Airflow — production_asset_ingestion (local/dev)

## Role

Airflow owns **scheduled/retryable batch ETL** for production document assets.

It must **never**:
- submit ComfyUI generations
- sit on the synchronous Scene → Generate API path

Generation remains FastAPI + ComfyUI only.

## DAG

| Field | Value |
|---|---|
| DAG id | `production_asset_ingestion` |
| File | `airflow/dags/production_asset_ingestion.py` |
| Schedule | `@daily` (also trigger manually) |
| Effect | `POST /api/v1/assets/ingestion/run` on Production Agent BE |

Pipeline steps (implemented inside the BE service, summarized in `batch_runs`):

```text
discover landing files
  → create pending document assets
  → validate / extract text (txt·md·csv)
  → checksum + normalize
  → mark processed | failed
  → write batch_runs row
```

## Without installing Airflow

```bash
make seed-documents
make ingest-assets
# or:
curl -X POST 'http://127.0.0.1:8001/api/v1/assets/ingestion/run'
```

## Pointing a local Airflow at this DAG

```bash
export PROD_AGENT_ROOT="$(pwd)"   # repo root
export PROD_AGENT_BE_URL=http://127.0.0.1:8001
# Add this folder to AIRFLOW__CORE__DAGS_FOLDER or symlink:
#   ln -s "$PROD_AGENT_ROOT/airflow/dags/"* "$AIRFLOW_HOME/dags/"
```

Optional Compose profile (requires Docker):

```bash
docker compose --profile ops up -d n8n
# Airflow MWAA / full Airflow stack is intentionally NOT created yet (§39).
```

## Observability

Prefer app Dashboard **Asset Operations** strip + `GET /api/v1/assets/ingestion/runs`.
Do not clone the Airflow monitoring UI into the product.
