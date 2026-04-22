"""Feature store lifecycle: migrate, refresh_views, materialize features_wide."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from asciip_data_pipeline import synthetic
from asciip_data_pipeline.features import get_feature_store, point_in_time_frame, watermark
from asciip_data_pipeline.features.build import build as build_features
from asciip_shared.config import reset_settings_cache

pytestmark = [pytest.mark.integration, pytest.mark.req_3, pytest.mark.req_17]


@pytest.fixture()
def seeded_store(tmp_data_dir: Path):
    # Seed snapshots so refresh_views has something to point at.
    synthetic.write_snapshots(tmp_data_dir / "snapshots")
    reset_settings_cache()
    # Invalidate module-level cached store instance.
    from asciip_data_pipeline.features import store as store_mod

    store_mod._default_store = None  # type: ignore[attr-defined]
    return get_feature_store()


def test_migrations_create_core_tables(seeded_store) -> None:  # type: ignore[no-untyped-def]
    with seeded_store.connect() as con:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' "
            "ORDER BY table_name"
        ).fetchall()
    names = {r[0] for r in rows}
    assert {
        "schema_version",
        "ingestion_audit",
        "model_registry",
        "feature_lineage",
        "features_wide",
        "disruption_events",
        "alerts",
        "suppliers",
        "scoring_audit",
    } <= names


def test_src_views_unify_snapshot_without_raw(seeded_store) -> None:  # type: ignore[no-untyped-def]
    with seeded_store.connect() as con:
        tables = {
            r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
    # With only snapshots seeded, src_* views must still exist for our five.
    for name in (
        "src_fred_commodity_prices",
        "src_fred_fx",
        "src_yfinance_aapl",
        "src_apple_supplier_pdf",
        "src_disruption_events_seed",
    ):
        assert name in tables, f"missing unified src view: {name}"


def test_build_populates_features_wide(seeded_store) -> None:  # type: ignore[no-untyped-def]
    build_features()
    with seeded_store.connect() as con:
        row = con.execute("SELECT COUNT(*) FROM features_wide").fetchone()
        feature_names = {
            r[0] for r in con.execute("SELECT DISTINCT feature_name FROM features_wide").fetchall()
        }
    assert row
    assert row[0] > 100
    # All five planned features landed.
    assert {
        "commodity_price",
        "commodity_vol_30d_annualized",
        "fx_rate",
        "aapl_adj_close",
        "aapl_log_return",
        "target_gross_margin",
    } <= feature_names


def test_watermark_monotonic(seeded_store) -> None:  # type: ignore[no-untyped-def]
    build_features()
    now = watermark()
    past = watermark(datetime(2000, 1, 1, tzinfo=UTC))
    assert now >= past


def test_point_in_time_filters_future_rows(seeded_store) -> None:  # type: ignore[no-untyped-def]
    build_features()
    cutoff = datetime(2022, 1, 1, tzinfo=UTC)
    rows = point_in_time_frame(feature_names=["commodity_price"], as_of=cutoff)
    assert rows, "expected some historical rows before 2022"
    assert all(r["as_of_ts"] <= cutoff for r in rows)
