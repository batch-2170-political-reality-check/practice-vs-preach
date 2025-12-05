# Requires configuration as env vars (.env).
FROM ghcr.io/astral-sh/uv:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install gcsfuse dependencies
RUN apt-get update && \
    apt-get install -y curl lsb-release gnupg && \
    rm -rf /var/lib/apt/lists/*

# Add Cloud Storage FUSE apt repo and install
RUN export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s) && \
    echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" \
      > /etc/apt/sources.list.d/gcsfuse.list && \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && \
    apt-get install -y gcsfuse && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync
RUN uv run python -c "import nltk; nltk.download('punkt_tab')"

COPY practicepreach practicepreach/
COPY data data/
COPY bin/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
