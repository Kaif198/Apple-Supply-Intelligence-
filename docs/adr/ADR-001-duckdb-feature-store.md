# ADR-001: DuckDB as the feature store

- **Status**: Accepted · Phase 3 · 2026-04-15
- **Context**: Every ML model needs a point-in-time-correct,
  query-efficient feature matrix. Options considered: Postgres +
  TimescaleDB, ClickHouse, Feast, DuckDB, Polars in-memory.
- **Decision**: DuckDB, with Parquet-backed external views.

## Why

1. **Offline-first**. A single file (`data/features/asciip.duckdb`) is
   all the state the application holds. No Postgres container, no
   network dependency for any read path. The `make up` target boots
   the entire platform without reaching the internet.
2. **SQL surface**. Every feature lives as a `.sql` file under
   `features/sql/`; reviewers read SQL, not ORM queries. DuckDB's
   window functions and `read_parquet` glob support give us the entire
   "wrangling toolbox" without a separate Spark or Polars stage.
3. **Point-in-time queries cost O(log n)**. The `as_of_ts` index on
   `features_wide` means our property test (500 random cutoffs) runs
   in under 3 seconds.
4. **Single-writer is fine**. Ingestion runs every 60+ seconds; the API
   reads concurrently via short-lived connections. No writer queue,
   no replication, no surprises.

## Trade-offs

- **Not multi-process-safe for writes**. If we ever scale to multiple
  ingest workers we will need to move to a client-server store. For
  now, APScheduler runs in-process.
- **No built-in ACL**. Security is handled at the FastAPI boundary,
  not at the DB.
- **No streaming ingestion**. Parquet sidecar pattern requires a
  polling loop. Acceptable because the fastest source (Drewry) updates
  weekly.

## Revisit when

- Ingestion cadence drops below 60 s, or
- Multi-process writers are required, or
- Row count exceeds ~100 M (DuckDB stays fast but disk I/O becomes the
  bottleneck).
