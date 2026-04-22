# ASCIIP API — multi-stage build.
# Stage 1 resolves the uv workspace; stage 2 ships a slim runtime.

FROM python:3.11-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl git \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.4.*

WORKDIR /app

# Copy workspace manifests first for layer caching.
COPY pyproject.toml ./
COPY packages/shared/pyproject.toml            packages/shared/
COPY packages/data_pipeline/pyproject.toml     packages/data_pipeline/
COPY packages/ml_models/pyproject.toml         packages/ml_models/
COPY apps/api/pyproject.toml                   apps/api/

# Copy source.
COPY packages/ packages/
COPY apps/api/ apps/api/

# Root pyproject sets `package = false`, so `uv sync` at root only audits.
# Explicitly create a venv and install each workspace member (+ its transitive
# deps) with `uv pip install -e`. This gives us a working /app/.venv that the
# runtime stage copies wholesale.
RUN uv venv /app/.venv \
 && UV_PROJECT_ENVIRONMENT=/app/.venv uv pip install \
      -e packages/shared \
      -e packages/data_pipeline \
      -e packages/ml_models \
      -e apps/api

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ASCIIP_DATA_DIR=/data \
    ASCIIP_DUCKDB_PATH=/data/features/asciip.duckdb \
    ASCIIP_SNAPSHOTS_DIR=/data/snapshots \
    ASCIIP_LOG_PRETTY=false \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --shell /bin/bash asciip

WORKDIR /app
COPY --from=builder --chown=asciip:asciip /app /app

USER asciip

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -m asciip_api.smoke --once --url http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "asciip_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
