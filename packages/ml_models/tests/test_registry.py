"""Model registry CRUD tests."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from asciip_ml_models.registry import ModelRegistration, ModelRegistry


pytestmark = [pytest.mark.integration, pytest.mark.req_28]


def _reg(**kwargs) -> ModelRegistration:
    defaults = dict(
        family="unit_test_family",
        version="v0",
        estimator={"coef": [1.0, 2.0]},
        metrics={"r2": 0.92},
        hyperparameters={"alpha": 1.0},
        notes="unit-test",
        promote_to_production=False,
    )
    defaults.update(kwargs)
    return ModelRegistration(**defaults)


def test_register_then_list(tmp_data_dir) -> None:  # noqa: ARG001
    registry = ModelRegistry()
    record = registry.register(_reg(version="v1"))
    assert record.artifact_path.exists()
    assert (record.artifact_path / "model.joblib").exists()
    assert (record.artifact_path / "metrics.json").exists()

    listed = registry.list_family("unit_test_family")
    assert len(listed) == 1
    assert listed[0].id == record.id
    assert json.loads((record.artifact_path / "metrics.json").read_text())["r2"] == 0.92


def test_promote_exclusivity(tmp_data_dir) -> None:  # noqa: ARG001
    registry = ModelRegistry()
    r1 = registry.register(_reg(version="v1", promote_to_production=True))
    r2 = registry.register(_reg(version="v2", promote_to_production=True))

    prod = registry.get_production("unit_test_family")
    assert prod is not None and prod.id == r2.id

    # Promote r1 explicitly — r2 must be demoted.
    registry.promote(r1.id)
    prod = registry.get_production("unit_test_family")
    assert prod is not None and prod.id == r1.id


def test_latest_orders_by_created_at(tmp_data_dir) -> None:  # noqa: ARG001
    registry = ModelRegistry()
    registry.register(_reg(version="v1"))
    r2 = registry.register(_reg(version="v2"))
    latest = registry.get_latest("unit_test_family")
    assert latest is not None and latest.id == r2.id


def test_purge_removes_artifacts_and_row(tmp_data_dir) -> None:  # noqa: ARG001
    registry = ModelRegistry()
    record = registry.register(_reg(version="v1"))
    path = record.artifact_path
    registry.purge(record.id)
    assert registry.get_latest("unit_test_family") is None
    assert not path.exists()


def test_load_round_trip(tmp_data_dir) -> None:  # noqa: ARG001
    registry = ModelRegistry()
    record = registry.register(_reg(version="v1"))
    loaded = record.load()
    assert loaded == {"coef": [1.0, 2.0]}
