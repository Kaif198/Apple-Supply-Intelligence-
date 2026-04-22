"""Cross-cutting constants.

These values appear in requirements, design, and UI spec. Centralizing them
here guarantees the same numbers show up everywhere from backend scoring to
frontend legend copy.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

# ---------------------------------------------------------------------------
# Severity (Requirement 5, 26; ui_spec Design Tokens → Severity)
# ---------------------------------------------------------------------------


class SeverityClass(StrEnum):
    """Four-class severity taxonomy used by both distress classifier and events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_CLASSES: Final[tuple[SeverityClass, ...]] = (
    SeverityClass.LOW,
    SeverityClass.MEDIUM,
    SeverityClass.HIGH,
    SeverityClass.CRITICAL,
)

# Probability thresholds for the distress classifier (Requirement 5.3, design §"Model 2").
DISTRESS_PROBABILITY_THRESHOLDS: Final[dict[SeverityClass, tuple[float, float]]] = {
    SeverityClass.LOW: (0.00, 0.25),
    SeverityClass.MEDIUM: (0.25, 0.50),
    SeverityClass.HIGH: (0.50, 0.75),
    SeverityClass.CRITICAL: (0.75, 1.0 + 1e-9),
}

# USD financial-impact thresholds for Disruption events (Requirement 26.2).
SEVERITY_THRESHOLDS_USD: Final[dict[SeverityClass, tuple[float, float]]] = {
    SeverityClass.LOW: (0.0, 10_000_000.0),
    SeverityClass.MEDIUM: (10_000_000.0, 100_000_000.0),
    SeverityClass.HIGH: (100_000_000.0, 1_000_000_000.0),
    SeverityClass.CRITICAL: (1_000_000_000.0, float("inf")),
}


def classify_by_usd(impact_usd: float) -> SeverityClass:
    """Return the severity bucket for a given absolute USD impact."""
    impact = abs(impact_usd)
    for severity, (lo, hi) in SEVERITY_THRESHOLDS_USD.items():
        if lo <= impact < hi:
            return severity
    return SeverityClass.CRITICAL


def classify_by_probability(p: float) -> SeverityClass:
    """Return the severity bucket for a distress probability in [0, 1]."""
    if not 0.0 <= p <= 1.0 + 1e-9:
        raise ValueError(f"probability must be in [0, 1], got {p}")
    for severity, (lo, hi) in DISTRESS_PROBABILITY_THRESHOLDS.items():
        if lo <= p < hi:
            return severity
    return SeverityClass.CRITICAL


# ---------------------------------------------------------------------------
# Commodities (Requirement 4.4)
# ---------------------------------------------------------------------------

# FRED series / proxy codes used by the forecasting engine.
COMMODITY_CODES: Final[dict[str, str]] = {
    "copper": "PCOPPUSDM",  # Global price of copper, USD per metric ton
    "aluminum": "PALUMUSDM",  # Global price of aluminum
    "lithium_carbonate": "PLITHUSDM",  # Proxy; see data_sources.md for full sourcing
    "rare_earth_ndpr": "PRAREUSDM",  # Neodymium-praseodymium proxy
    "crude_oil_wti": "DCOILWTICO",  # WTI crude oil
}

COMMODITY_ORDER: Final[tuple[str, ...]] = (
    "copper",
    "aluminum",
    "lithium_carbonate",
    "rare_earth_ndpr",
    "crude_oil_wti",
)

FORECAST_HORIZONS_DAYS: Final[tuple[int, ...]] = (7, 30, 90)

# ---------------------------------------------------------------------------
# Disruption event types (Requirement 11.3)
# ---------------------------------------------------------------------------


class DisruptionEventType(StrEnum):
    COMMODITY = "commodity"
    TARIFF = "tariff"
    LOGISTICS = "logistics"
    SUPPLIER = "supplier"
    FX = "fx"


# ---------------------------------------------------------------------------
# DCF / Valuation base-case keys (Requirement 8)
# ---------------------------------------------------------------------------

# Apple Inc. base-case line items sourced from the most recent public 10-K.
# Concrete numeric values live in packages/ml_models/valuation/base_case.py
# with citation comments (filing URL, accession, page). The keys below are the
# canonical column names used throughout the codebase.
DCF_LINE_ITEMS: Final[tuple[str, ...]] = (
    "revenue",
    "gross_margin",
    "opex",
    "capex",
    "d_and_a",
    "delta_wc",
    "tax_rate",
    "shares_outstanding",
    "net_cash",
)

MARKET_CAP_TOLERANCE: Final[float] = 0.15  # ±15 % (Requirement 8.6)

# ---------------------------------------------------------------------------
# Performance targets (Requirement 18)
# ---------------------------------------------------------------------------

TARGET_P95_API_MS: Final[int] = 500
TARGET_SCENARIO_LATENCY_MS: Final[int] = 3_000
TARGET_MONTE_CARLO_LATENCY_MS: Final[int] = 5_000
TARGET_NETWORK_RENDER_MS: Final[int] = 3_000

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

APPLE_TICKER: Final[str] = "AAPL"
APPLE_CIK: Final[str] = "0000320193"
TENANT_ID: Final[str] = "AAPL-01"
BRAND_NAME: Final[str] = "ASCIIP"
BRAND_SUBTITLE: Final[str] = "Supply Chain Intelligence"

DEFAULT_RETENTION_YEARS: Final[int] = 5
DEFAULT_PURGE_AFTER_YEARS: Final[int] = 7
