# ASCIIP Documentation

Landing page for everyone reviewing, operating, or extending the
platform. Start at the top; every section links deeper.

## For reviewers

| Document | What's inside |
|---|---|
| [`architecture.md`](architecture.md) | Seven-layer stack diagram, data flow, performance envelope |
| [`adr/ADR-001-duckdb-feature-store.md`](adr/ADR-001-duckdb-feature-store.md) | Why DuckDB over Postgres / Feast |
| [`adr/ADR-002-offline-first.md`](adr/ADR-002-offline-first.md) | Why every adapter must ship a calibrated snapshot |
| [`../README.md`](../README.md) | Quickstart, monorepo layout, repo topology |
| [`../progress.txt`](../progress.txt) | Full per-phase delivery log |

## For operators

| Document | What's inside |
|---|---|
| [`runbook.md`](runbook.md) | First-boot checklist, diagnostics, incident playbooks, env vars |
| [`../.env.example`](../.env.example) | Authoritative list of configuration keys |
| [`../render.yaml`](../render.yaml) | Render.com blueprint (API + ingestion cron) |
| [`../vercel.json`](../vercel.json) | Vercel config + security headers for the Next.js app |

## For contributors

| Document | What's inside |
|---|---|
| [`../.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) | Checklist mirrored in CI |
| [`../.github/workflows/`](../.github/workflows/) | `ci.yml`, `e2e.yml`, `security.yml`, `release.yml`, `ingest.yml`, `retrain.yml`, `smoke.yml` |
| [`../tests/meta/test_requirement_coverage.py`](../tests/meta/test_requirement_coverage.py) | Traceability matrix — every requirement must have a marker |

## Test markers (pytest)

| Marker | Used by | Enforced where |
|---|---|---|
| `unit` | fast, pure-python tests | every CI run |
| `integration` | tests that touch DuckDB / filesystem | CI matrix |
| `property` | Hypothesis property tests (PIT correctness) | CI matrix |
| `e2e` | Playwright + API smoke | `e2e.yml` only |
| `req_1 … req_30` | requirement-traceability markers | `test_requirement_coverage.py` |

## Quick links

- **API docs** — `GET /api/docs` (Swagger) and `/api/redoc` once the API is running.
- **Health** — `GET /api/health` returns a component breakdown; the Topbar polls this every 30 s.
- **Feature-store browser** — any DuckDB CLI can open `data/features/asciip.duckdb` read-only; every view is declared in `packages/data_pipeline/asciip_data_pipeline/features/sql/`.
