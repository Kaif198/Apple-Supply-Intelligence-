"""Shared fixtures for API tests.

Each test gets a fresh tmp data dir with a fully-seeded feature store so
the HTTP layer can actually return meaningful payloads (not just empty
lists). We cache the seeded dir at module scope to keep the suite fast.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from asciip_shared.config import reset_settings_cache
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def seeded_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("asciip_api_data")
    for sub in ("raw", "features", "models", "exports", "snapshots"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    os.environ["ASCIIP_DATA_DIR"] = str(root)
    os.environ["ASCIIP_DUCKDB_PATH"] = str(root / "features" / "asciip.duckdb")
    os.environ["ASCIIP_SNAPSHOTS_DIR"] = str(root / "snapshots")
    os.environ["ASCIIP_MODELS_DIR"] = str(root / "models")
    os.environ["ASCIIP_EXPORTS_DIR"] = str(root / "exports")
    os.environ["ASCIIP_RAW_DIR"] = str(root / "raw")
    os.environ["ASCIIP_ENABLE_SCHEDULER"] = "false"
    reset_settings_cache()

    from asciip_data_pipeline import synthetic
    from asciip_data_pipeline.features import store as _store_mod
    from asciip_data_pipeline.features.build import build as build_features
    from asciip_ml_models import registry as _reg_mod

    _store_mod._default_store = None  # type: ignore[attr-defined]
    _reg_mod._default_registry = None  # type: ignore[attr-defined]

    synthetic.write_snapshots(root / "snapshots")
    build_features()
    return root


@pytest.fixture
def client(seeded_dir: Path) -> Iterator[TestClient]:
    # Fresh cache between tests.
    from asciip_api.cache import get_cache

    get_cache().clear()

    from asciip_api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
