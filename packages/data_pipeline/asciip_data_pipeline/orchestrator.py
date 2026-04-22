"""Ingestion orchestrator — runs every registered source and writes audits.

Invoked by:
    * ``make ingest`` / ``./tasks.ps1 ingest`` (on-demand)
    * The local APScheduler loop running inside the API process
    * GitHub Actions ``ingest.yml`` on a 6-hourly cron
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import polars as pl

from asciip_shared import (
    SourceMetadata,
    bind_correlation_id,
    configure_logging,
    get_logger,
    get_settings,
)
from asciip_shared.correlation import reset_correlation_id

# Register every adapter for the default registry.
from asciip_data_pipeline import synthetic
from asciip_data_pipeline.audit import record_fetch, snapshot_parquet_sidecar
from asciip_data_pipeline.sources import default_registry
from asciip_data_pipeline.sources import apple_supplier_pdf as _apple_pdf  # noqa: F401
from asciip_data_pipeline.sources import comtrade as _comtrade  # noqa: F401
from asciip_data_pipeline.sources import drewry as _drewry  # noqa: F401
from asciip_data_pipeline.sources import ecb as _ecb  # noqa: F401
from asciip_data_pipeline.sources import finnhub as _finnhub  # noqa: F401
from asciip_data_pipeline.sources import fred as _fred  # noqa: F401  (registration side-effect)
from asciip_data_pipeline.sources import marketaux as _marketaux  # noqa: F401
from asciip_data_pipeline.sources import pboc as _pboc  # noqa: F401
from asciip_data_pipeline.sources import yfinance_source as _yf  # noqa: F401


def _raw_dir_for(source_name: str) -> Path:
    settings = get_settings()
    d = settings.raw_dir / source_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_raw(source_name: str, df: pl.DataFrame) -> tuple[Path, str]:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = _raw_dir_for(source_name) / f"{stamp}.parquet"
    df.write_parquet(path, compression="zstd")
    sha = path.with_suffix(path.suffix + ".sha256")
    # Compute sha256 from the on-disk bytes so it matches the stored metadata.
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sha.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path, digest


async def _run_one(source_cls_instance, run_id: str) -> SourceMetadata:  # type: ignore[no-untyped-def]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_one_sync, source_cls_instance, run_id)


def _run_one_sync(source, run_id: str) -> SourceMetadata:  # type: ignore[no-untyped-def]
    log = get_logger(f"asciip.orchestrator.{source.name}")
    try:
        result = source.fetch()
    except Exception as exc:  # pragma: no cover — logged + bubbled
        log.exception("orchestrator.source_failed", source=source.name, error=str(exc))
        raise
    path, digest = _write_raw(source.name, result.data)
    snapshot_parquet_sidecar(path, digest)
    record_fetch(run_id=run_id, meta=result.metadata, parquet_path=path)
    return result.metadata


async def run_once() -> list[SourceMetadata]:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        pretty=settings.log_pretty,
        service_name="asciip-orchestrator",
        version=settings.version,
    )
    log = get_logger(__name__)
    _ensure_offline_snapshots()

    run_id = uuid4().hex
    token = bind_correlation_id(run_id)
    try:
        sources = default_registry.instantiate_all()
        log.info("orchestrator.start", run_id=run_id, sources=[s.name for s in sources])
        tasks = [_run_one(s, run_id) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        reset_correlation_id(token)

    successes: list[SourceMetadata] = []
    for src, outcome in zip(sources, results, strict=True):
        if isinstance(outcome, Exception):
            log.error("orchestrator.error", source=src.name, error=str(outcome))
            continue
        successes.append(outcome)

    log.info(
        "orchestrator.done",
        run_id=run_id,
        ok=len(successes),
        total=len(sources),
        fallback=sum(1 for m in successes if m.fallback),
    )
    return successes


def _ensure_offline_snapshots() -> None:
    """Seed the snapshots directory from the synthetic calibration if empty."""
    settings = get_settings()
    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    if any(settings.snapshots_dir.glob("*.parquet")):
        return
    get_logger("asciip.orchestrator").info(
        "orchestrator.seeding_synthetic_snapshots",
        path=str(settings.snapshots_dir),
    )
    synthetic.write_snapshots(settings.snapshots_dir)


def main() -> int:
    asyncio.run(run_once())
    return 0


if __name__ == "__main__":
    sys.exit(main())
