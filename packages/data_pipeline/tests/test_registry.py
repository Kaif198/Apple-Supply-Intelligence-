"""Tests that every expected source adapter is registered."""

from __future__ import annotations

# Importing the orchestrator triggers the registration side-effects.
import asciip_data_pipeline.orchestrator  # noqa: F401
import pytest
from asciip_data_pipeline.sources import default_registry

pytestmark = [pytest.mark.unit, pytest.mark.req_2]

EXPECTED: set[str] = {
    "fred_commodity_prices",
    "yfinance_aapl",
    "marketaux_news",
    "finnhub_fundamentals",
    "comtrade_trade",
    "drewry_wci",
    "ecb_reference_rates",
    "pboc_fixing",
    "apple_supplier_pdf",
}


def test_every_source_registered() -> None:
    registered = set(default_registry.names())
    missing = EXPECTED - registered
    assert not missing, f"missing source registrations: {sorted(missing)}"
    assert len(registered) >= 9


def test_every_registered_class_exposes_required_attrs() -> None:
    for name in default_registry.names():
        cls = default_registry.get(name)
        assert cls.name == name
        assert cls.source_url.startswith(("http", "asciip://"))
        assert cls.snapshot_filename.endswith(".parquet")
