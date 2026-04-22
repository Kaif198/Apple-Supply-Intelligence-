## ASCIIP — Apple Supply Chain Impact Intelligence Platform
## Canonical task runner. Run `make help` for the target list.

# Use bash with strict flags; works under Git Bash / WSL / Linux / macOS.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PYTHON ?= python
UV     ?= uv
PNPM   ?= pnpm
DOCKER_COMPOSE ?= docker compose

API_HOST ?= 0.0.0.0
API_PORT ?= 8000
WEB_PORT ?= 3000

VENV_DIR := .venv

# Colors (best-effort; ignored on plain terminals).
C_GREEN := \033[32m
C_CYAN  := \033[36m
C_DIM   := \033[2m
C_RESET := \033[0m

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help:  ## Show this help
	@echo ""
	@echo "$(C_CYAN)ASCIIP — Apple Supply Chain Impact Intelligence Platform$(C_RESET)"
	@echo ""
	@echo "  Usage:  make $(C_GREEN)<target>$(C_RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(C_DIM)%s$(C_RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)
	@echo ""

##@ Setup

.PHONY: prereqs
prereqs:  ## Verify required tools are installed
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "python is required"; exit 1; }
	@command -v $(UV)     >/dev/null 2>&1 || { echo "uv is required (pip install uv)"; exit 1; }
	@command -v node      >/dev/null 2>&1 || { echo "node 20+ is required"; exit 1; }
	@command -v $(PNPM)   >/dev/null 2>&1 || { echo "pnpm is required (npm i -g pnpm)"; exit 1; }
	@echo "all prerequisites present"

.PHONY: bootstrap
bootstrap: prereqs  ## First-run setup: install deps, seed DuckDB from shipped snapshots
	$(UV) sync --all-extras
	$(PNPM) install --frozen-lockfile || $(PNPM) install
	$(UV) run python -m asciip_data_pipeline.bootstrap --seed-from-snapshots || true
	@echo "bootstrap complete. run 'make up' to start services."

.PHONY: env
env:  ## Copy .env.example to .env if missing
	@[ -f .env ] || cp .env.example .env
	@echo ".env is ready. edit to enable live data sources."

##@ Local dev

.PHONY: up
up: env  ## Start api + web locally (non-docker)
	@echo "starting api on :$(API_PORT) and web on :$(WEB_PORT)"
	@( $(UV) run uvicorn asciip_api.main:app --host $(API_HOST) --port $(API_PORT) --reload ) & \
	  ( $(PNPM) --filter @asciip/web dev -- --port $(WEB_PORT) ) ; wait

.PHONY: up-docker
up-docker:  ## Start api + web via docker compose
	$(DOCKER_COMPOSE) up --build

.PHONY: down
down:  ## Stop local docker services
	$(DOCKER_COMPOSE) down

.PHONY: api
api:  ## Run only the FastAPI backend (autoreload)
	$(UV) run uvicorn asciip_api.main:app --host $(API_HOST) --port $(API_PORT) --reload

.PHONY: web
web:  ## Run only the Next.js frontend
	$(PNPM) --filter @asciip/web dev -- --port $(WEB_PORT)

##@ Data and models

.PHONY: ingest
ingest:  ## Run the ingestion pipeline once
	$(UV) run python -m asciip_data_pipeline.orchestrator

.PHONY: features
features:  ## Rebuild feature store views and materialized tables
	$(UV) run python -m asciip_data_pipeline.features.build

.PHONY: train
train:  ## Retrain all ML models against the current feature store
	$(UV) run python -m asciip_ml_models.train_all

##@ Quality

.PHONY: lint
lint:  ## Lint Python (ruff) and JS/TS (eslint)
	$(UV) run ruff check .
	$(PNPM) run -r lint

.PHONY: format
format:  ## Auto-format Python (ruff) and JS/TS (prettier)
	$(UV) run ruff format .
	$(PNPM) run format

.PHONY: typecheck
typecheck:  ## mypy --strict + tsc --noEmit
	$(UV) run mypy .
	$(PNPM) run typecheck

.PHONY: test
test:  ## Unit + property + integration tests with coverage
	$(UV) run pytest -m "not e2e" --cov --cov-report=term-missing --cov-report=xml

.PHONY: test-unit
test-unit:
	$(UV) run pytest -m "unit"

.PHONY: test-property
test-property:
	$(UV) run pytest -m "property"

.PHONY: test-integration
test-integration:
	$(UV) run pytest -m "integration"

.PHONY: e2e
e2e:  ## Run Playwright end-to-end tests (requires `make up` in another terminal)
	$(PNPM) --filter @asciip/web exec playwright test

.PHONY: smoke
smoke:  ## Post-deploy smoke check against a running stack
	$(UV) run python -m asciip_api.smoke

##@ Housekeeping

.PHONY: clean
clean:  ## Remove caches and build artifacts (keeps .venv and data/)
	rm -rf .ruff_cache .mypy_cache .pytest_cache coverage.xml htmlcov .turbo
	rm -rf apps/web/.next apps/web/.turbo
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: reset-data
reset-data:  ## Wipe data/raw, data/features, data/exports (keeps snapshots)
	rm -rf data/raw/* data/features/* data/exports/*
	mkdir -p data/raw data/features data/exports
	@echo "data reset. run 'make bootstrap' to reseed from snapshots."
