"""End-to-end test for the orchestrator using the snapshot fallback path.

Runs with zero external dependencies: every adapter falls back to a
synthetic snapshot because no API keys are configured in the test env.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from asciip_data_pipeline import orchestrator, synthetic
from asciip_data_pipeline.audit import latest_audit_rows
from asciip_shared.config import reset_settings_cache

pytestmark = [pytest.mark.integration, pytest.mark.req_2, pytest.mark.req_20]


def test_orchestrator_seeds_snapshots_then_runs(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force every optional adapter into snapshot-fallback mode by clearing keys.
    for key in ("FRED_API_KEY", "MARKETAUX_API_KEY", "FINNHUB_API_KEY", "COMTRADE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    reset_settings_cache()

    # Pre-seed the snapshots directory from the synthetic calibration so
    # every source has a fallback file before the orchestrator runs.
    snap_dir = tmp_data_dir / "snapshots"
    synthetic.write_snapshots(snap_dir)

    # Copy synthetic snapshots under the expected adapter filenames when
    # the default name differs from the snapshot name.
    # (FRED commodity prices already match by filename; others share the
    # same synthetic output to keep fallback tolerant.)
    for target in (
        "marketaux_news.parquet",
        "finnhub_fundamentals.parquet",
        "comtrade_trade.parquet",
        "drewry_wci.parquet",
        "ecb_reference_rates.parquet",
        "pboc_fixing.parquet",
        "apple_supplier_pdf.parquet",
    ):
        dest = snap_dir / target
        if not dest.exists():
            src = snap_dir / "fred_commodity_prices.parquet"
            dest.write_bytes(src.read_bytes())

    results = asyncio.run(orchestrator.run_once())

    # Every source falls back successfully.
    assert len(results) >= 9
    assert all(meta.fallback for meta in results)

    # Audit rows were persisted to DuckDB.
    audit = latest_audit_rows(limit=50)
    assert len(audit) >= 9
    names = {row["source_name"] for row in audit}
    assert {"fred_commodity_prices", "yfinance_aapl", "apple_supplier_pdf"} <= names
