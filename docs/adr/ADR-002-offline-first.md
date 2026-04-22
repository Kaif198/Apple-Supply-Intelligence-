# ADR-002: Offline-first operation via snapshot fallback

- **Status**: Accepted · Phase 2 · 2026-04-12

## Context

Every free external data source we consume is best-effort. FRED rotates
API keys, Marketaux trial keys expire, Drewry's HTML scrape breaks on
DOM changes, and Nominatim rate-limits us to 1 req/s. If any single
source blocks a cold start, the demo falls over.

## Decision

Each `Source` adapter must ship a **calibrated synthetic snapshot** in
`data/snapshots/{name}.parquet`. The base class's `_fallback()` method
reads it whenever:

1. `is_configured()` returns `False` (no credentials), or
2. `_fetch()` raises any exception in `retry_exceptions`, or
3. The HTTP request exhausts the retry budget (default 3).

Every fallback is logged to `ingestion_audit` with `fallback=TRUE` and
the snapshot timestamp, so operators can tell at a glance whether a
number on the dashboard came from live data.

The `make bootstrap` / `python -m asciip_data_pipeline.bootstrap
--seed-from-snapshots` targets regenerate the snapshot bundle
deterministically from a seeded numpy RNG (`asciip_data_pipeline.
synthetic`). The SHA-256 sidecar next to each Parquet lets us verify
that shipped snapshots haven't drifted since the last release.

## Consequences

- **Positive**: every demo and CI run works with zero secrets. The
  product is reviewable by anyone without access provisioning. Source
  outages never wake the on-call.
- **Positive**: the synthetic calibration is a known-good regression
  target. Our property tests run against it in seconds.
- **Negative**: a naïve developer could forget to wire the fallback.
  Enforced by a registry-level test (`test_every_source_registered`)
  and by the base class raising if `snapshot_filename` is blank and
  `name.parquet` is also absent.
- **Negative**: dashboard staleness is user-visible. The Topbar shows a
  `data · Nm ago` pill from the feature store watermark to keep this
  honest.

## Alternatives considered

1. **Mock HTTP with recorded fixtures** — tempting, but fixtures rot
   faster than snapshots. A snapshot is a first-class feature-store
   citizen; a fixture is a test-only artefact.
2. **Retry forever on failure** — would cascade to the API as slow
   requests and saturate rate limits. Rejected.
3. **Mandatory keys** — rejected because it makes the open-source
   surface unshippable.
