# Requires configuration as env vars (.env).
FROM ghcr.io/astral-sh/uv:bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY api-test ./api-test

# Set by Cloud Run. I.e. GCP uses "PORT".
ENV PORT 8000

CMD uv run uvicorn api-test.fast:app --host 0.0.0.0 --port ${PORT}
