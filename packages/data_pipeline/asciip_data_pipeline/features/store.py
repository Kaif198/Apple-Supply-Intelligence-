"""DuckDB connection management + feature-store lifecycle.

The feature store is a single DuckDB file at ``data/features/asciip.duckdb``.
This module encapsulates:

* Lazy singleton access (``get_feature_store()``)
* Schema migrations via numbered SQL files under ``features/migrations/``
* External Parquet views over ``data/raw/{source}/``
* Watermark queries used by the API cache layer and PIT enforcement
"""

from __future__ import annotations

import contextlib
import re
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from asciip_shared import FeatureStoreError, get_logger, get_settings

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_SQL_DIR = Path(__file__).parent / "sql"
_MIGRATION_FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


def _discover_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    if not _MIGRATIONS_DIR.exists():
        return migrations
    for path in sorted(_MIGRATIONS_DIR.iterdir()):
        match = _MIGRATION_FILE_RE.match(path.name)
        if not match:
            continue
        migrations.append(
            Migration(version=int(match.group(1)), name=match.group(2), path=path)
        )
    return migrations


class FeatureStore:
    """Thin wrapper over a DuckDB connection with lifecycle helpers."""

    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.path = Path(db_path) if db_path else settings.duckdb_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        self.log = get_logger("asciip.feature_store")
        self._lock = threading.RLock()
        self._initialised = False

    # ------------------------------------------------------------------ conn

    @contextlib.contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Yield a short-lived connection.

        DuckDB is happy with concurrent readers and serialises writers; we
        keep the contract simple by using independent connections per call.
        """
        with self._lock:
            if not self._initialised:
                self._migrate_locked()
                self._refresh_views_locked()
                self._initialised = True
        con = duckdb.connect(str(self.path))
        try:
            yield con
        finally:
            con.close()

    # ---------------------------------------------------------------- schema

    def migrate(self) -> None:
        with self._lock:
            self._migrate_locked()

    def _migrate_locked(self) -> None:
        con = duckdb.connect(str(self.path))
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS schema_version ("
                " version INTEGER PRIMARY KEY, name VARCHAR, applied_at TIMESTAMP)"
            )
            applied = {
                row[0]
                for row in con.execute("SELECT version FROM schema_version").fetchall()
            }
            for mig in _discover_migrations():
                if mig.version in applied:
                    continue
                self.log.info("feature_store.migrate", version=mig.version, name=mig.name)
                try:
                    con.execute(mig.sql)
                    con.execute(
                        "INSERT INTO schema_version VALUES (?, ?, ?)",
                        [mig.version, mig.name, datetime.now(UTC)],
                    )
                except Exception as exc:
                    raise FeatureStoreError(
                        f"migration {mig.version}_{mig.name} failed: {exc}",
                        detail={"migration": mig.name, "error": str(exc)},
                    ) from exc
        finally:
            con.close()

    # ----------------------------------------------------------------- views

    def refresh_views(self) -> None:
        with self._lock:
            self._refresh_views_locked()

    def _refresh_views_locked(self) -> None:
        """(Re)declare external views and unified ``src_*`` sources.

        Three layers of views are produced:

        * ``raw_{source}``        — Parquet files under ``data/raw/{source}/``
        * ``snapshot_{stem}``     — shipped calibration files in ``data/snapshots``
        * ``src_{name}``          — unified view used by feature SQL; picks
                                    ``raw_{name}`` when present, falls back to
                                    ``snapshot_{name}``. Feature views should
                                    only read from ``src_*``.
        """
        raw_root = self.settings.raw_dir
        raw_root.mkdir(parents=True, exist_ok=True)
        snapshots = self.settings.snapshots_dir
        con = duckdb.connect(str(self.path))
        try:
            raw_names: set[str] = set()
            if raw_root.exists():
                for source_dir in sorted(raw_root.iterdir()):
                    if not source_dir.is_dir():
                        continue
                    if not any(source_dir.glob("*.parquet")):
                        continue
                    view = f"raw_{source_dir.name}"
                    pattern = (source_dir / "*.parquet").as_posix()
                    con.execute(
                        f"CREATE OR REPLACE VIEW {view} AS "
                        f"SELECT * FROM read_parquet('{pattern}')"
                    )
                    raw_names.add(source_dir.name)

            snapshot_names: set[str] = set()
            if snapshots.exists():
                for path in sorted(snapshots.glob("*.parquet")):
                    view = f"snapshot_{path.stem}"
                    con.execute(
                        f"CREATE OR REPLACE VIEW {view} AS "
                        f"SELECT * FROM read_parquet('{path.as_posix()}')"
                    )
                    snapshot_names.add(path.stem)

            # Unified src_* views: raw when it exists, else snapshot.
            for name in raw_names | snapshot_names:
                target = f"raw_{name}" if name in raw_names else f"snapshot_{name}"
                con.execute(
                    f"CREATE OR REPLACE VIEW src_{name} AS SELECT * FROM {target}"
                )
        finally:
            con.close()

    # --------------------------------------------------------- feature views

    def rebuild_feature_views(self) -> None:
        """Execute every ``features/sql/*.sql`` file in lexical order."""
        if not _SQL_DIR.exists():
            return
        con = duckdb.connect(str(self.path))
        try:
            for path in sorted(_SQL_DIR.glob("*.sql")):
                self.log.info("feature_store.view", name=path.stem)
                try:
                    con.execute(path.read_text(encoding="utf-8"))
                except Exception as exc:  # pragma: no cover — SQL error surface
                    raise FeatureStoreError(
                        f"failed to materialise feature {path.stem}: {exc}",
                        detail={"feature": path.stem, "error": str(exc)},
                    ) from exc
        finally:
            con.close()

    # ----------------------------------------------------- watermark queries

    def watermark(self, as_of: datetime | None = None) -> datetime:
        """Return the max ``as_of_ts`` visible at or before ``as_of``.

        Used by the API cache layer (keying) and the PIT CTE pattern.
        """
        cutoff = as_of or datetime.now(UTC)
        with self.connect() as con:
            row = con.execute(
                "SELECT COALESCE(MAX(as_of_ts), TIMESTAMP '1970-01-01') FROM features_wide "
                "WHERE as_of_ts <= ?",
                [cutoff],
            ).fetchone()
        return row[0] if row else datetime(1970, 1, 1, tzinfo=UTC)


_default_store: FeatureStore | None = None
_default_lock = threading.Lock()


def get_feature_store() -> FeatureStore:
    global _default_store
    with _default_lock:
        if _default_store is None:
            _default_store = FeatureStore()
    return _default_store


def watermark(as_of: datetime | None = None) -> datetime:
    return get_feature_store().watermark(as_of)
