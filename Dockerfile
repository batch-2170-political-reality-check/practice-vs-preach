# Requires configuration as env vars (.env).
FROM ghcr.io/astral-sh/uv:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync
RUN uv run python -c "import nltk; nltk.download('punkt_tab')"

COPY practicepreach practicepreach/
COPY data data/
COPY bin/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
