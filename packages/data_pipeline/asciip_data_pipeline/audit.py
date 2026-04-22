"""Ingestion audit + lineage writer.

Every source fetch appends one row to the ``ingestion_audit`` table in DuckDB
so the UI's pipeline-status card and Requirement 17.5 data-lineage view are
a straight SQL query.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from asciip_shared import SourceMetadata, get_logger, get_settings

_CREATE_AUDIT = """
CREATE TABLE IF NOT EXISTS ingestion_audit (
    id                     VARCHAR PRIMARY KEY,
    run_id                 VARCHAR NOT NULL,
    source_name            VARCHAR NOT NULL,
    source_url             VARCHAR NOT NULL,
    fetched_at             TIMESTAMP WITH TIME ZONE NOT NULL,
    row_count              INTEGER NOT NULL,
    checksum_sha256        VARCHAR NOT NULL,
    fallback               BOOLEAN NOT NULL,
    fallback_snapshot_ts   TIMESTAMP WITH TIME ZONE,
    notes                  VARCHAR,
    parquet_path           VARCHAR
);
"""

_INSERT_AUDIT = """
INSERT INTO ingestion_audit
(id, run_id, source_name, source_url, fetched_at, row_count,
 checksum_sha256, fallback, fallback_snapshot_ts, notes, parquet_path)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def _ensure_db() -> Path:
    settings = get_settings()
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.duckdb_path


def ensure_audit_schema() -> None:
    with duckdb.connect(str(_ensure_db())) as con:
        con.execute(_CREATE_AUDIT)


def record_fetch(
    *,
    run_id: str,
    meta: SourceMetadata,
    parquet_path: Path | None,
) -> None:
    """Persist a single ingestion outcome to ``ingestion_audit``."""
    log = get_logger("asciip.audit")
    ensure_audit_schema()
    row_id = f"{meta.source_name}:{meta.fetched_at.isoformat()}"
    with duckdb.connect(str(_ensure_db())) as con:
        con.execute(
            _INSERT_AUDIT,
            [
                row_id,
                run_id,
                meta.source_name,
                meta.source_url,
                meta.fetched_at,
                meta.row_count,
                meta.checksum_sha256,
                meta.fallback,
                meta.fallback_snapshot_ts,
                meta.notes,
                str(parquet_path) if parquet_path else None,
            ],
        )
    log.info(
        "audit.recorded",
        run_id=run_id,
        source=meta.source_name,
        rows=meta.row_count,
        fallback=meta.fallback,
    )


def latest_audit_rows(limit: int = 50) -> list[dict[str, object]]:
    ensure_audit_schema()
    with duckdb.connect(str(_ensure_db())) as con:
        result = con.execute(
            "SELECT * FROM ingestion_audit ORDER BY fetched_at DESC LIMIT ?",
            [limit],
        ).fetchall()
        columns = [d[0] for d in con.description]
    return [dict(zip(columns, row, strict=True)) for row in result]


def snapshot_parquet_sidecar(path: Path, sha256: str) -> Path:
    """Write ``{path}.sha256`` alongside ``path`` to satisfy Requirement 17.6."""
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(f"{sha256}  {path.name}\n", encoding="utf-8")
    return sidecar


def utcnow() -> datetime:
    return datetime.now(UTC)
