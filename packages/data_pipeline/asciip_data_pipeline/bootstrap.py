"""First-run bootstrap entrypoint.

Phase 1 delivers this as a stub that validates configuration and prepares
the on-disk data tree. Phase 2 expands it to seed DuckDB from shipped
snapshots and generate the synthetic calibration when they are missing.

Invoked by ``make bootstrap`` and ``./tasks.ps1 bootstrap``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from asciip_shared import configure_logging, get_logger, get_settings


def _ensure_tree(paths: list[Path]) -> list[Path]:
    created: list[Path] = []
    for p in paths:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(p)
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="asciip-bootstrap")
    parser.add_argument(
        "--seed-from-snapshots",
        action="store_true",
        help="Seed DuckDB from shipped Parquet snapshots (Phase 2).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        pretty=settings.log_pretty,
        service_name="asciip-bootstrap",
        version=settings.version,
    )
    log = get_logger(__name__)

    created = _ensure_tree(
        [
            settings.data_dir,
            settings.raw_dir,
            settings.duckdb_path.parent,
            settings.snapshots_dir,
            settings.models_dir,
            settings.exports_dir,
        ]
    )
    for path in created:
        log.info("bootstrap.path_created", path=str(path))

    missing_keys = [
        name
        for name in ("fred", "marketaux", "finnhub", "comtrade")
        if not settings.source_enabled(name)
    ]
    if missing_keys:
        log.warning(
            "bootstrap.missing_api_keys",
            missing=missing_keys,
            note="system will run in snapshot-fallback mode for these sources",
        )

    if args.seed_from_snapshots:
        from asciip_data_pipeline import synthetic
        from asciip_data_pipeline.audit import ensure_audit_schema

        if any(settings.snapshots_dir.glob("*.parquet")):
            log.info(
                "bootstrap.snapshots_present",
                path=str(settings.snapshots_dir),
                note="existing snapshots preserved; not regenerating",
            )
        else:
            paths = synthetic.write_snapshots(settings.snapshots_dir)
            log.info("bootstrap.snapshots_written", count=len(paths))

        ensure_audit_schema()
        log.info("bootstrap.audit_schema_ready", duckdb=str(settings.duckdb_path))

    log.info("bootstrap.done", duckdb=str(settings.duckdb_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
