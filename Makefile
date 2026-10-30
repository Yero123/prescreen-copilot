.PHONY: install web-install test dev web hello gate-cases read-cases eval baseline seed-file export-overrides models up

install:
	cd backend && uv sync

web-install:
	cd frontend && npm install

test:
	cd backend && uv run pytest -q

dev:
	cd backend && uv run --env-file ../.env uvicorn app.main:app --reload

web:
	cd frontend && VITE_API_URL=http://localhost:8000 npm run dev

hello:
	cd backend && uv run --env-file ../.env python scripts/hello_claude.py

gate-cases:
	cd backend && uv run --env-file ../.env python scripts/run_gate_on_cases.py

read-cases:
	cd backend && uv run --env-file ../.env python scripts/run_read_on_cases.py

SPLIT ?= dev
LABEL ?=
eval:
	cd backend && uv run --env-file ../.env python evals/run.py --split $(SPLIT) --label "$(LABEL)"

baseline:
	cd backend && uv run --env-file ../.env python evals/baseline.py --split $(SPLIT)

seed-file:
	cd backend && uv run python scripts/make_seed_file.py

export-overrides:
	cd backend && uv run python scripts/export_overrides.py

models:
	cd backend && uv run --env-file ../.env python scripts/list_models.py

up:
	docker compose up --build
