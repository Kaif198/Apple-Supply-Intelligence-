"""Finnhub adapter — supplier company news + basic financial metrics.

Free tier: 60 calls/minute. We rate-ourselves informally (one call per
ticker with a 1.1s sleep) to avoid tripping the quota during a full run.
"""

from __future__ import annotations

import time

import httpx
import polars as pl

from asciip_data_pipeline.sources.base import Source, register_source

# A narrow slice of listed suppliers — the full list is generated from the
# supplier-PDF extractor at runtime.
_SUPPLIER_TICKERS = (
    "AAPL",
    "TSM",      # TSMC
    "005930.KS",  # Samsung
    "035420.KS",  # Naver — placeholder for Korean breadth
    "2354.TW",  # Foxconn / Hon Hai
    "4938.TW",  # Pegatron
    "002475.SZ",  # Luxshare
    "066570.KS",  # LG
    "AVGO",     # Broadcom
    "QCOM",     # Qualcomm
    "SWKS",     # Skyworks
    "MU",       # Micron
)


@register_source
class FinnhubFundamentals(Source):
    name = "finnhub_fundamentals"
    source_url = "https://finnhub.io/api/v1/stock/metric"
    snapshot_filename = "finnhub_fundamentals.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)

    def is_configured(self) -> bool:
        return bool(self.settings.finnhub_api_key)

    def _fetch(self) -> pl.DataFrame:
        key = self.settings.finnhub_api_key.get_secret_value() if self.settings.finnhub_api_key else ""
        rows: list[dict[str, object]] = []
        with httpx.Client(timeout=15.0) as client:
            for ticker in _SUPPLIER_TICKERS:
                try:
                    r = client.get(
                        self.source_url,
                        params={"symbol": ticker, "metric": "all", "token": key},
                    )
                    r.raise_for_status()
                    payload = r.json()
                except httpx.HTTPStatusError as exc:
                    self.log.warning(
                        "finnhub.ticker_http_error",
                        ticker=ticker,
                        status=exc.response.status_code,
                    )
                    continue
                metric = payload.get("metric") or {}
                rows.append(
                    {
                        "ticker": ticker,
                        "market_cap_musd": float(metric.get("marketCapitalization") or 0.0),
                        "debt_to_equity_ttm": float(metric.get("totalDebt/totalEquityAnnual") or 0.0),
                        "current_ratio_ttm": float(metric.get("currentRatioAnnual") or 0.0),
                        "revenue_growth_ttm": float(metric.get("revenueGrowthTTMYoy") or 0.0),
                        "operating_margin_ttm": float(metric.get("operatingMarginTTM") or 0.0),
                        "beta": float(metric.get("beta") or 0.0),
                    }
                )
                time.sleep(1.1)
        if not rows:
            raise ConnectionError("finnhub returned no rows")
        return pl.DataFrame(rows)
