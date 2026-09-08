.PHONY: install be-install fe-install db-up db-down migrate seed seed-retrieval eval-retrieval run-be run-fe test verify demo

install: be-install fe-install

be-install:
	cd be && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

fe-install:
	cd fe && npm install

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrate:
	cd be && . .venv/bin/activate && alembic upgrade head

seed:
	cd be && . .venv/bin/activate && python ../scripts/seed_demo.py

seed-retrieval:
	cd be && . .venv/bin/activate && python ../scripts/seed_retrieval_corpus.py

eval-retrieval:
	cd be && . .venv/bin/activate && python ../scripts/eval_retrieval.py

# Port map (do NOT collide with sibling production-agent-dev = FE:5173 BE:8000):
#   this repo prod-agent-dev → FE:5174  BE:8001
run-be:
	@echo "prod-agent-dev BE → http://127.0.0.1:8001  (not :8000)"
	cd be && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

run-fe:
	@echo "prod-agent-dev FE → http://127.0.0.1:5174  (not :5173)  proxy→:8001"
	cd fe && npm run dev -- --host 0.0.0.0 --port 5174 --strictPort

test:
	cd be && . .venv/bin/activate && pytest -q

verify:
	cd be && . .venv/bin/activate && python ../scripts/verify_demo.py

demo: seed
	@echo "Demo data seeded. Start backend: make run-be  | frontend: make run-fe"
