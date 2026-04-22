# ASCIIP Operations Runbook

On-call reference for ASCIIP operators. Every section answers a concrete
question: *the thing broke — what do I do?*

## 1. Service topology

- **`asciip-api`** — FastAPI + Uvicorn on port 8000. Stateless; reads
  DuckDB at `data/features/asciip.duckdb`.
- **`asciip-web`** — Next.js 15 on port 3000. Proxies to the API via
  `NEXT_PUBLIC_API_URL`.
- **`asciip-ingest`** — Same Python process as the API with
  `ASCIIP_ENABLE_SCHEDULER=true`, or a standalone one-shot run via
  `python -m asciip_data_pipeline.orchestrator`.
- **`asciip-train`** — On-demand container for model training; invoked
  by the `retrain.yml` workflow or locally via `make train-all`.

## 2. First-boot checklist

```bash
uv sync --all-extras
pnpm install
python -m asciip_data_pipeline.bootstrap --seed-from-snapshots
uvicorn asciip_api.main:app --reload            # terminal A
pnpm --filter @asciip/web dev                   # terminal B
```

Open http://localhost:3000 — every page should render without touching
the public internet because the snapshot fallback seeds the feature
store with synthetic calibration data.

## 3. Diagnostics

### 3.1 API says `status: degraded`

```bash
curl -s http://localhost:8000/api/health | jq
```

Look at the `components` array. Common failures and their fixes:

| component | signal | fix |
| --- | --- | --- |
| `feature_store` | `duckdb file locked` | stop other Python processes that hold `asciip.duckdb`; DuckDB is single-writer |
| `feature_store` | `no such table: features_wide` | `python -m asciip_data_pipeline.features.build` |
| `api` | never `ok` | check the structured logs for `api.startup` — likely a config validation error |

### 3.2 A source adapter keeps falling back

```bash
uv run python -c "from asciip_data_pipeline.orchestrator import list_sources; \
  import json; print(json.dumps(list_sources(), indent=2))"
```

Every source exposes `is_configured()`. If the adapter reports
`fallback=True` repeatedly, either:

1. The API key is missing from `.env` (see `.env.example`) — platform
   falls back to the shipped snapshot automatically.
2. Upstream is down — consult the source's status page. The orchestrator
   records every failure in `ingestion_audit`:

```sql
SELECT source_name, fetched_at, notes
FROM ingestion_audit
WHERE fallback = TRUE
ORDER BY fetched_at DESC
LIMIT 20;
```

### 3.3 Monte Carlo endpoint is slow

Check the trial count. The API caps at 50 000 trials (see
`MonteCarloRequest` validator). 10 000 completes in < 2 s on commodity
CI hardware; if it's slow check:

- Python is 3.11+ (older versions lose AVX-friendly numpy code paths).
- `numpy` is ≥ 2.1 (older releases use less efficient Mersenne Twister).

## 4. Runbook for common incidents

### 4.1 "The homepage shows 503s"

1. `docker compose ps` — is the API container healthy?
2. `docker compose logs asciip-api --tail=200`
3. If the container restart loops: the DuckDB schema is probably
   corrupted. Delete `data/features/asciip.duckdb` and re-bootstrap; the
   snapshot fallback will reseed within 30 s.

### 4.2 "CI failed on the PIT property test"

The Hypothesis shrinker will have printed the minimal failing cutoff.
Reproduce locally:

```bash
uv run pytest packages/data_pipeline/tests/test_point_in_time.py -k '<hash>' -v
```

Never lower the Hypothesis budget to make this pass — the test is the
last line of defense against data leakage. Investigate the responsible
feature view in `packages/data_pipeline/asciip_data_pipeline/features/sql/`.

### 4.3 "Scheduled ingestion stopped producing new rows"

1. Check the GitHub Actions `ingest.yml` run log.
2. If the run succeeded but rows are stale, the source adapter likely
   fell back. Query `ingestion_audit` (§3.2).
3. If the run failed, confirm the repo secret that holds the API key
   has not expired (FRED keys rotate yearly; Marketaux trial keys
   expire in 30 days).

### 4.4 "Supplier distress predictions look wrong"

The model is isotonic-calibrated but always layer with human review.
The drivers panel on `/suppliers/{id}/distress` surfaces the raw input
features — if `otd_rate_90d` is missing, the XGBoost leaf traversal
degenerates. Re-run the PDF extractor:

```bash
uv run python -m asciip_data_pipeline.sources.apple_supplier_pdf --force
uv run python -m asciip_ml_models.distress.classifier retrain
```

## 5. On-call rotation touchpoints

- **Alert triage** — all high/critical alerts land in the `alerts`
  DuckDB table and surface on `/events`. `POST /api/alerts/{id}/ack`
  to clear.
- **Rollback** — tags are cut from `main`; to roll back, re-tag the
  previous SHA and the `release.yml` workflow will publish Docker
  images with `sha-*` labels that Render/Vercel can pin.
- **Runbook owner** — Platform engineer on rotation. Escalate to ML
  owner for model drift, Data owner for upstream breakage.

## 6. Key environment variables

See `.env.example` for the authoritative list. Highlights:

| Var | Purpose |
| --- | --- |
| `ASCIIP_ENABLE_SCHEDULER` | Flip to `true` only in the dedicated `asciip-ingest` container |
| `ASCIIP_RATE_LIMIT_CAPACITY` | Requests per minute per client IP |
| `ASCIIP_BUILD_SHA` | Populated by CI; surfaces on `/api/version` |
| `NEXT_PUBLIC_API_URL` | Frontend knows where the backend lives (e.g. `https://api.asciip.app/api`) |
| `FRED_API_KEY` / `MARKETAUX_API_KEY` / `FINNHUB_API_KEY` | Optional; snapshot fallback runs without them |
