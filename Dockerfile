# Requires configuration as env vars (.env).
FROM ghcr.io/astral-sh/uv:bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY practicepreach practicepreach/
COPY data data/

# Set by Cloud Run. I.e. GCP uses "PORT".
ENV PORT=8000

CMD ["uv", "run", "uvicorn", "practicepreach.fast:app", "--host", "0.0.0.0", "--port", "8000"]
