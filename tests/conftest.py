"""Shared pytest configuration for the monorepo."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Ensure every test observes a fresh Settings singleton."""
    from asciip_shared.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture()
def tmp_data_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Point ASCIIP_* path envs at an isolated temp tree."""
    for sub in ("raw", "features", "models", "exports", "snapshots"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ASCIIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCIIP_RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("ASCIIP_DUCKDB_PATH", str(tmp_path / "features" / "asciip.duckdb"))
    monkeypatch.setenv("ASCIIP_SNAPSHOTS_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("ASCIIP_MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("ASCIIP_EXPORTS_DIR", str(tmp_path / "exports"))
    return tmp_path


@pytest.fixture(autouse=True, scope="session")
def _freeze_env() -> Iterator[None]:
    """Pin test runs to the test environment so fail-fast is strict."""
    os.environ.setdefault("ASCIIP_ENV", "test")
    os.environ.setdefault("ASCIIP_LOG_PRETTY", "false")
    yield
