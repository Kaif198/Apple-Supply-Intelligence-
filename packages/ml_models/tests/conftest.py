"""Shared fixtures for ML-models tests.

Every test that touches the registry or the margin Ridge needs a real
feature store, so this fixture boots one in a tmp dir identical to the
data-pipeline test harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from asciip_shared.config import reset_settings_cache


@pytest.fixture()
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for sub in ("raw", "features", "models", "exports", "snapshots"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ASCIIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCIIP_DUCKDB_PATH", str(tmp_path / "features" / "asciip.duckdb"))
    monkeypatch.setenv("ASCIIP_SNAPSHOTS_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("ASCIIP_MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("ASCIIP_EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ASCIIP_RAW_DIR", str(tmp_path / "raw"))
    reset_settings_cache()

    # Reset module-level singletons so each test sees the fresh paths.
    from asciip_data_pipeline.features import store as _store_mod

    _store_mod._default_store = None  # type: ignore[attr-defined]

    from asciip_ml_models import registry as _reg_mod

    _reg_mod._default_registry = None  # type: ignore[attr-defined]

    return tmp_path


@pytest.fixture()
def seeded_feature_store(tmp_data_dir: Path):
    """Materialise the full feature set end-to-end."""
    from asciip_data_pipeline import synthetic
    from asciip_data_pipeline.features.build import build as build_features

    synthetic.write_snapshots(tmp_data_dir / "snapshots")
    build_features()
    return tmp_data_dir
