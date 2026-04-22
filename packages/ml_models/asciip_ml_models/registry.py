"""Model registry — CRUD over the ``model_registry`` DuckDB table.

Artifacts (pickled estimators, JSON configs) are stored on disk under
``settings.models_dir / {family} / {version}/`` to keep the database small.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
from asciip_data_pipeline.features import get_feature_store
from asciip_shared import get_logger, get_settings


@dataclass(frozen=True)
class ModelRecord:
    id: str
    family: str
    version: str
    created_at: datetime
    metrics: dict[str, Any]
    hyperparameters: dict[str, Any]
    artifact_path: Path
    is_production: bool
    notes: str | None

    def load(self) -> Any:
        """Deserialise the persisted estimator from disk."""
        path = self.artifact_path / "model.joblib"
        if not path.exists():
            raise FileNotFoundError(f"artifact missing at {path}")
        return joblib.load(path)


@dataclass(frozen=True)
class ModelRegistration:
    """Input payload to :meth:`ModelRegistry.register`."""

    family: str
    version: str
    estimator: Any | None
    metrics: dict[str, Any] = field(default_factory=dict)
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    extra_artifacts: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None
    promote_to_production: bool = False


class ModelRegistry:
    """Thin facade over the DuckDB ``model_registry`` table."""

    def __init__(self, models_dir: Path | None = None) -> None:
        settings = get_settings()
        self.models_dir = Path(models_dir or settings.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.log = get_logger("asciip.model_registry")
        self._store = get_feature_store()

    # ------------------------------------------------------------------ CRUD

    def register(self, reg: ModelRegistration) -> ModelRecord:
        """Persist an estimator + metadata and return the created record."""
        rec_id = uuid.uuid4().hex
        created = datetime.now(UTC)
        artifact_dir = self.models_dir / reg.family / reg.version
        artifact_dir.mkdir(parents=True, exist_ok=True)

        if reg.estimator is not None:
            joblib.dump(reg.estimator, artifact_dir / "model.joblib", compress=3)
        (artifact_dir / "metrics.json").write_text(
            json.dumps(reg.metrics, indent=2, default=str), encoding="utf-8"
        )
        (artifact_dir / "hyperparameters.json").write_text(
            json.dumps(reg.hyperparameters, indent=2, default=str), encoding="utf-8"
        )
        for name, payload in reg.extra_artifacts.items():
            path = artifact_dir / name
            if isinstance(payload, bytes | bytearray):
                path.write_bytes(bytes(payload))
            elif isinstance(payload, str):
                path.write_text(payload, encoding="utf-8")
            else:
                path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

        with self._store.connect() as con:
            if reg.promote_to_production:
                con.execute(
                    "UPDATE model_registry SET is_production = FALSE WHERE family = ?",
                    [reg.family],
                )
            con.execute(
                "INSERT INTO model_registry "
                "(id, family, version, created_at, metrics, hyperparameters, "
                "artifact_path, is_production, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    rec_id,
                    reg.family,
                    reg.version,
                    created,
                    json.dumps(reg.metrics, default=str),
                    json.dumps(reg.hyperparameters, default=str),
                    str(artifact_dir),
                    reg.promote_to_production,
                    reg.notes,
                ],
            )

        self.log.info(
            "model_registry.registered",
            family=reg.family,
            version=reg.version,
            id=rec_id,
            production=reg.promote_to_production,
        )
        return ModelRecord(
            id=rec_id,
            family=reg.family,
            version=reg.version,
            created_at=created,
            metrics=reg.metrics,
            hyperparameters=reg.hyperparameters,
            artifact_path=artifact_dir,
            is_production=reg.promote_to_production,
            notes=reg.notes,
        )

    def get_production(self, family: str) -> ModelRecord | None:
        """Return the current production record for ``family``, if any."""
        with self._store.connect() as con:
            row = con.execute(
                "SELECT id, family, version, created_at, metrics, hyperparameters, "
                "artifact_path, is_production, notes "
                "FROM model_registry "
                "WHERE family = ? AND is_production = TRUE "
                "ORDER BY created_at DESC LIMIT 1",
                [family],
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_latest(self, family: str) -> ModelRecord | None:
        with self._store.connect() as con:
            row = con.execute(
                "SELECT id, family, version, created_at, metrics, hyperparameters, "
                "artifact_path, is_production, notes "
                "FROM model_registry "
                "WHERE family = ? "
                "ORDER BY created_at DESC LIMIT 1",
                [family],
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_family(self, family: str) -> list[ModelRecord]:
        with self._store.connect() as con:
            rows = con.execute(
                "SELECT id, family, version, created_at, metrics, hyperparameters, "
                "artifact_path, is_production, notes "
                "FROM model_registry WHERE family = ? ORDER BY created_at DESC",
                [family],
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def promote(self, model_id: str) -> None:
        with self._store.connect() as con:
            family_row = con.execute(
                "SELECT family FROM model_registry WHERE id = ?", [model_id]
            ).fetchone()
            if not family_row:
                raise KeyError(f"model id {model_id} not found")
            con.execute(
                "UPDATE model_registry SET is_production = FALSE WHERE family = ?",
                [family_row[0]],
            )
            con.execute(
                "UPDATE model_registry SET is_production = TRUE WHERE id = ?",
                [model_id],
            )

    def purge(self, model_id: str) -> None:
        with self._store.connect() as con:
            row = con.execute(
                "SELECT artifact_path FROM model_registry WHERE id = ?", [model_id]
            ).fetchone()
            if not row:
                return
            con.execute("DELETE FROM model_registry WHERE id = ?", [model_id])
        path = Path(row[0])
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def _row_to_record(row: tuple) -> ModelRecord:
    (
        rec_id,
        family,
        version,
        created_at,
        metrics_json,
        hyperparameters_json,
        artifact_path,
        is_production,
        notes,
    ) = row
    return ModelRecord(
        id=rec_id,
        family=family,
        version=version,
        created_at=created_at
        if isinstance(created_at, datetime)
        else datetime.fromisoformat(str(created_at)),
        metrics=json.loads(metrics_json) if metrics_json else {},
        hyperparameters=json.loads(hyperparameters_json) if hyperparameters_json else {},
        artifact_path=Path(artifact_path),
        is_production=bool(is_production),
        notes=notes,
    )


_default_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
    return _default_registry
