"""Smoke test for the bootstrap entrypoint (req_1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from asciip_data_pipeline.bootstrap import main

pytestmark = [pytest.mark.unit, pytest.mark.req_1]


def test_bootstrap_runs_without_seed(tmp_data_dir: Path) -> None:
    """Calling bootstrap without --seed-from-snapshots must succeed."""
    rc = main([])
    assert rc == 0


def test_bootstrap_seeds_snapshots_when_empty(tmp_data_dir: Path) -> None:
    """--seed-from-snapshots must populate an empty snapshots directory."""
    rc = main(["--seed-from-snapshots"])
    assert rc == 0
    snapshots = list((tmp_data_dir / "snapshots").glob("*.parquet"))
    assert snapshots, "bootstrap should have written at least one parquet snapshot"
