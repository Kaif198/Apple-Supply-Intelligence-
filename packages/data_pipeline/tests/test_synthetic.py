"""Tests for the synthetic calibration and snapshot writer."""

from __future__ import annotations

import hashlib
from pathlib import Path

import polars as pl
import pytest

from asciip_shared import COMMODITY_ORDER

from asciip_data_pipeline import synthetic


pytestmark = [pytest.mark.unit, pytest.mark.req_17]


def test_commodity_prices_cover_all_commodities(tmp_data_dir: Path) -> None:
    df = synthetic.generate_commodity_prices(years=1)
    commodities = set(df["commodity"].unique().to_list())
    assert commodities == set(COMMODITY_ORDER)
    assert (df["price"] > 0).all()


def test_snapshot_determinism(tmp_data_dir: Path) -> None:
    first = synthetic.generate_commodity_prices(years=1)
    second = synthetic.generate_commodity_prices(years=1)
    assert first.equals(second), "synthetic calibration must be deterministic"


def test_write_snapshots_produces_checksums(tmp_data_dir: Path) -> None:
    out = tmp_data_dir / "snapshots"
    paths = synthetic.write_snapshots(out)
    assert len(paths) >= 5
    for path in paths:
        assert path.exists()
        sidecar = path.with_suffix(path.suffix + ".sha256")
        assert sidecar.exists()
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sidecar.read_text(encoding="utf-8").startswith(expected)


def test_suppliers_snapshot_shape() -> None:
    df = synthetic.generate_suppliers()
    assert df.height >= 30
    for col in (
        "id", "name", "country", "category", "tier",
        "annual_spend_billions", "distress_score",
        "otd_rate_90d", "dpo_days", "revenue_concentration_top3",
        "lat", "lon",
    ):
        assert col in df.columns
    assert df["distress_score"].min() >= 0.0
    assert df["distress_score"].max() <= 1.0


def test_events_seed_chronological() -> None:
    df = synthetic.generate_recent_events(n=20)
    ts = df["timestamp"].to_list()
    assert ts == sorted(ts, reverse=True)
    assert (df["impact_usd"] >= 0).all()


def test_aapl_equity_has_trading_days_only() -> None:
    df = synthetic.generate_aapl_equity(years=1)
    weekdays = {d.weekday() for d in df["date"].to_list()}
    assert weekdays.issubset({0, 1, 2, 3, 4})
    for col in ("open", "high", "low", "close", "adj_close", "volume"):
        assert col in df.columns
    assert (df["high"] >= df["low"]).all()
