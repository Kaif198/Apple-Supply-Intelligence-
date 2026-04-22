"""Pydantic request/response schemas for every ASCIIP API route.

Consolidated into one module so the OpenAPI surface is easy to diff.
Every schema inherits from ``BaseModel`` with ``extra='forbid'`` so
typos in client payloads fail fast.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------- base model


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ------------------------------------------------------------------------ meta


class HealthComponent(_Model):
    name: str
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None


class HealthResponse(_Model):
    status: Literal["ok", "degraded", "down"]
    service: str
    version: str
    env: str
    started_at: datetime
    uptime_seconds: float
    correlation_id: str | None
    watermark: datetime | None = None
    components: list[HealthComponent]


class VersionResponse(_Model):
    version: str
    build_sha: str
    schema_version: str = "v1"


# ---------------------------------------------------------------- commodities


class CommodityPricePoint(_Model):
    as_of_ts: datetime
    price: float


class CommoditySeries(_Model):
    entity_id: str
    series: list[CommodityPricePoint]
    vol_30d_annualized: float | None = None


class CommoditiesResponse(_Model):
    as_of: datetime
    commodities: list[CommoditySeries]


class CommodityForecastPoint(_Model):
    ts: datetime
    mean: float
    lower: float
    upper: float


class CommodityForecastResponse(_Model):
    entity_id: str
    horizon_days: int
    members: dict[str, float]
    val_mae: dict[str, float]
    forecast: list[CommodityForecastPoint]
    history_tail: list[CommodityPricePoint]


# --------------------------------------------------------------------- equity


class EquityPoint(_Model):
    as_of_ts: datetime
    adj_close: float
    log_return: float | None = None


class AaplHistoryResponse(_Model):
    entity_id: Literal["AAPL"] = "AAPL"
    series: list[EquityPoint]


class FactorCoefficient(_Model):
    name: str
    coefficient: float
    std_error: float
    t_value: float
    p_value: float


class FactorResponse(_Model):
    r_squared: float
    adj_r_squared: float
    n_obs: int
    factors: list[FactorCoefficient]
    notes: str


# ------------------------------------------------------------------ suppliers


class Supplier(_Model):
    id: str
    name: str
    parent: str | None = None
    country: str | None = None
    category: str | None = None
    tier: int | None = None
    annual_spend_billions: float | None = None
    distress_score: float | None = None
    otd_rate_90d: float | None = None
    dpo_days: float | None = None
    revenue_concentration_top3: float | None = None
    lat: float | None = None
    lon: float | None = None


class SuppliersResponse(_Model):
    as_of: datetime
    count: int
    suppliers: list[Supplier]


class SupplierDistressResponse(_Model):
    id: str
    name: str
    distress_probability: float
    distress_score: float | None
    drivers: list[dict[str, Any]]
    model_version: str | None


# --------------------------------------------------------------------- events


class Event(_Model):
    id: str
    as_of_ts: datetime
    event_type: Literal["commodity", "tariff", "logistics", "supplier", "fx"]
    title: str
    summary: str | None = None
    source_name: str
    source_url: str | None = None
    impact_usd: float
    severity: Literal["low", "medium", "high", "critical"]
    margin_delta_bps: int | None = None
    ev_delta_usd: float | None = None
    affected_supplier_ids: list[str] = Field(default_factory=list)


class EventsResponse(_Model):
    as_of: datetime
    count: int
    events: list[Event]


# ------------------------------------------------------------------- scenarios


class ShockSpecIn(_Model):
    name: str
    mean_return: float = 0.0
    volatility: float = Field(..., ge=0.0, le=2.0)
    elasticity_bps_per_10pct: float


class MonteCarloRequest(_Model):
    n_trials: int = Field(10_000, ge=100, le=50_000)
    horizon_years: float = Field(1.0, gt=0.0, le=5.0)
    shocks: list[ShockSpecIn]
    correlation: list[list[float]] | None = None
    supplier_stress_mean: float = Field(0.15, ge=0.0, le=1.0)
    supplier_stress_sd: float = Field(0.05, ge=0.0, le=1.0)
    outage_revenue_haircut_mean: float = Field(0.03, ge=0.0, le=0.5)
    outage_revenue_haircut_sd: float = Field(0.01, ge=0.0, le=0.5)
    seed: int = 20250101


class MonteCarloResponse(_Model):
    n_trials: int
    mean_price: float
    std_price: float
    percentiles: dict[str, float]
    var_5pct: float
    cvar_5pct: float
    mean_margin_delta_bps: float
    mean_revenue_delta_pct: float
    implied_price_samples: list[float]  # subsampled for chart


class DcfRequest(_Model):
    revenue_ttm_bn: float | None = None
    revenue_cagr_5y: float | None = None
    fcf_margin: float | None = None
    wacc: float | None = None
    terminal_growth: float | None = None
    net_cash_bn: float | None = None
    shares_diluted_bn: float | None = None
    horizon_years: int | None = None


class DcfResponse(_Model):
    assumptions: dict[str, float | int]
    projected_revenue_bn: list[float]
    projected_fcf_bn: list[float]
    enterprise_value_bn: float
    equity_value_bn: float
    implied_price_usd: float
    pv_explicit_bn: float
    pv_terminal_bn: float


class SensitivityRequest(_Model):
    row_field: str
    col_field: str
    row_values: list[float]
    col_values: list[float]


class SensitivityResponse(_Model):
    row_field: str
    col_field: str
    row_values: list[float]
    col_values: list[float]
    implied_prices: list[list[float]]


# --------------------------------------------------------------------- causal


class CausalRequest(_Model):
    treatment: Literal["aluminum", "copper", "lithium", "cobalt", "brent"]
    outcome: Literal["aapl_log_return"] = "aapl_log_return"
    confounders: list[str] = Field(default_factory=lambda: ["market_lag1", "fx_change_lag1"])
    lookback_days: int = Field(500, ge=60, le=3650)


class CausalResponse(_Model):
    method: str
    ate: float
    std_error: float
    ci_low: float
    ci_high: float
    n_obs: int
    refutations: dict[str, float]
    assumptions: list[str]


# --------------------------------------------------------------------- alerts


class Alert(_Model):
    id: str
    created_at: datetime
    event_id: str | None
    severity: Literal["low", "medium", "high", "critical"]
    acknowledged_at: datetime | None = None
    channel: str | None
    payload: dict[str, Any]


class AlertsResponse(_Model):
    count: int
    alerts: list[Alert]


class AckAlertRequest(_Model):
    acknowledge: Literal[True] = True


# -------------------------------------------------------------------- exports


class ExportRequest(_Model):
    format: Literal["json", "csv", "xlsx", "pdf"]
    dataset: Literal["commodities", "suppliers", "events", "alerts", "scenarios", "dcf"]
    params: dict[str, Any] = Field(default_factory=dict)


class ExportResponse(_Model):
    format: str
    dataset: str
    artifact_path: str
    size_bytes: int
    sha256: str
