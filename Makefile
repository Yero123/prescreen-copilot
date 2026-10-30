.PHONY: install test dev hello models up

install:
	cd backend && uv sync

test:
	cd backend && uv run pytest -q

dev:
	cd backend && uv run --env-file ../.env uvicorn app.main:app --reload

hello:
	cd backend && uv run --env-file ../.env python scripts/hello_claude.py

models:
	cd backend && uv run --env-file ../.env python scripts/list_models.py

up:
	docker compose up --build
