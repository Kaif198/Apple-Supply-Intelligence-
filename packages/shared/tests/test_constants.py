"""Tests for the severity and commodity constants."""

from __future__ import annotations

import pytest
from asciip_shared.constants import (
    COMMODITY_CODES,
    COMMODITY_ORDER,
    FORECAST_HORIZONS_DAYS,
    SEVERITY_CLASSES,
    SeverityClass,
    classify_by_probability,
    classify_by_usd,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("impact_usd", "expected"),
    [
        (0.0, SeverityClass.LOW),
        (9_999_999.99, SeverityClass.LOW),
        (10_000_000.0, SeverityClass.MEDIUM),
        (75_000_000.0, SeverityClass.MEDIUM),
        (100_000_000.0, SeverityClass.HIGH),
        (999_999_999.0, SeverityClass.HIGH),
        (1_000_000_000.0, SeverityClass.CRITICAL),
        (5e12, SeverityClass.CRITICAL),
        (-1_200_000_000.0, SeverityClass.CRITICAL),
    ],
)
def test_classify_by_usd(impact_usd: float, expected: SeverityClass) -> None:
    assert classify_by_usd(impact_usd) is expected


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (0.0, SeverityClass.LOW),
        (0.24, SeverityClass.LOW),
        (0.25, SeverityClass.MEDIUM),
        (0.50, SeverityClass.HIGH),
        (0.74, SeverityClass.HIGH),
        (0.75, SeverityClass.CRITICAL),
        (1.0, SeverityClass.CRITICAL),
    ],
)
def test_classify_by_probability(p: float, expected: SeverityClass) -> None:
    assert classify_by_probability(p) is expected


@pytest.mark.parametrize("p", [-0.01, 1.01, 2.0, -1.0])
def test_classify_by_probability_rejects_out_of_range(p: float) -> None:
    with pytest.raises(ValueError):
        classify_by_probability(p)


def test_commodity_manifest_consistency() -> None:
    # Requirement 4.4: five commodities; design locks the order.
    assert len(COMMODITY_ORDER) == 5
    assert set(COMMODITY_ORDER) == set(COMMODITY_CODES.keys())
    assert FORECAST_HORIZONS_DAYS == (7, 30, 90)
    # All four severity classes present and unique.
    assert len(SEVERITY_CLASSES) == 4
    assert len(set(SEVERITY_CLASSES)) == 4
