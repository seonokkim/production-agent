.PHONY: install be-install fe-install db-up db-down ops-up ops-down migrate seed seed-retrieval seed-documents ingest-assets eval-retrieval run-be run-fe run-comfy test verify demo

install: be-install fe-install

be-install:
	cd be && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

fe-install:
	cd fe && npm install

db-up:
	docker compose up -d db

db-down:
	docker compose down

# Optional: local n8n (Asset Review Automation). Airflow full stack not bundled — see airflow/README.md
ops-up:
	docker compose --profile ops up -d n8n
	@echo "n8n UI → http://127.0.0.1:5678  (import n8n/asset_review_automation.json)"

ops-down:
	docker compose --profile ops stop n8n

migrate:
	cd be && . .venv/bin/activate && alembic upgrade head

seed:
	cd be && . .venv/bin/activate && python ../scripts/seed_demo.py

seed-retrieval:
	cd be && . .venv/bin/activate && python ../scripts/seed_retrieval_corpus.py

seed-documents:
	python3 scripts/seed_documents.py

ingest-assets:
	cd be && . .venv/bin/activate && python ../scripts/run_asset_ingestion.py

eval-retrieval:
	cd be && . .venv/bin/activate && python ../scripts/eval_retrieval.py

# Port map (do NOT collide with sibling production-agent-dev = FE:5173 BE:8000 Comfy:8188):
#   this repo prod-agent-dev → FE:5174  BE:8001  Comfy:8189
run-be:
	@echo "prod-agent-dev BE → http://127.0.0.1:8001  (not :8000)"
	cd be && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

run-fe:
	@echo "prod-agent-dev FE → http://127.0.0.1:5174  (not :5173)  proxy→:8001"
	cd fe && npm run dev -- --host 0.0.0.0 --port 5174 --strictPort

# Isolated ComfyUI for this repo only (:8189). Leaves shared/sibling :8188 alone.
run-comfy:
	@echo "prod-agent-dev ComfyUI → http://127.0.0.1:8189  (not :8188)"
	bash scripts/start_comfyui_isolated.sh

test:
	cd be && . .venv/bin/activate && pytest -q

verify:
	cd be && . .venv/bin/activate && python ../scripts/verify_demo.py

demo: seed seed-documents
	@echo "Demo data seeded (incl. fictional documents in storage/landing)."
	@echo "Run ingestion: make ingest-assets"
	@echo "Optional n8n: make ops-up  then set N8N_REVIEW_WEBHOOK_URL"
	@echo "Start backend: make run-be  | frontend: make run-fe"
