.PHONY: install be-install fe-install db-up db-down migrate seed run-be run-fe test verify demo

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

run-be:
	cd be && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-fe:
	cd fe && npm run dev

test:
	cd be && . .venv/bin/activate && pytest -q

verify:
	cd be && . .venv/bin/activate && python ../scripts/verify_demo.py

demo: seed
	@echo "Demo data seeded. Start backend: make run-be  | frontend: make run-fe"
