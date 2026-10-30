FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY roles ./roles
COPY evals/__init__.py evals/cases.py ./evals/
COPY evals/cases ./evals/cases
COPY data/demo_seed.json ./data/demo_seed.json

ENV PATH="/app/.venv/bin:$PATH"
# Railway sets PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
