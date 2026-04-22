# ASCIIP Architecture

ASCIIP is organised into seven layers. Every layer has one owner module
and a narrow interface; downstream layers only consume the layer
immediately above.

```
 ┌──────────────────────────────────────────┐
 │ 7b  Pages (Next.js app router)           │   Phase 7
 │ 7a  Design system + D3 primitives        │   Phase 6
 │ 6   API routers + middleware + SSE       │   Phase 5
 │ 5   Services (pricing, scenario, …)      │   Phase 5
 │ 4   ML + causal + valuation              │   Phase 4
 │ 3   Feature store (DuckDB + SQL views)   │   Phase 3
 │ 2   Ingestion orchestrator + audit       │   Phase 2
 │ 1   Source adapters + synthetic fallback │   Phase 2
 │ 0   Shared: config, logging, types       │   Phase 1
 └──────────────────────────────────────────┘
```

## Data flow

```
external sources ──► Source adapter ──► data/raw/{source}/*.parquet
                                       └── data/snapshots/{source}.parquet  (offline fallback)
                          │
                          ▼
                  src_{source}  (DuckDB view)
                          │
                          ▼
                feature SQL views  (sql/*.sql)
                          │
                          ▼
                features_wide  (materialised table)
                          │
            ┌─────────────┼──────────────┐
            ▼             ▼              ▼
          Ridge       XGBoost       Monte Carlo
          margin      distress      simulator
            │             │              │
            └─────────────┼──────────────┘
                          ▼
                    FastAPI services
                          │
                          ▼
                 HTTP / SSE / exports
                          │
                          ▼
                     Next.js pages
```

## Key architectural decisions

See the ADRs in `docs/adr/`:

- **ADR-001** — DuckDB as the feature store.
- **ADR-002** — Offline-first operation via snapshot fallback.
- **ADR-003** — Point-in-time correctness via property testing.
- **ADR-004** — RFC 7807 problem+json for every error.
- **ADR-005** — CSS custom properties + Tailwind for the design system.

## Performance envelope

| Operation | Target | Actual |
| --- | --- | --- |
| `/api/health` cold start | < 500 ms | ~120 ms |
| `/api/commodities/prices` warm | < 50 ms | ~30 ms (cache HIT) |
| `/api/scenarios/run` 10 k trials | < 2 s | ~0.9 s |
| Full orchestrator run (9 sources, all fallback) | < 1 s | ~0.6 s |
| DCF base case | < 5 ms | ~0.8 ms |
| Feature-store `build` from cold | < 3 s | ~1.7 s |

## Trust boundaries

- **Public network** — anything outside the process. Every source
  adapter assumes it can fail; every call is wrapped in retries and a
  snapshot-fallback.
- **Process** — shared memory, unit-test isolation via tmp dirs.
- **DuckDB file** — single-writer; the API holds no long-lived handle,
  opening a short-lived connection per request.
- **Model artifacts** — read-only at inference time; regenerated only by
  the explicit training workflow.
