"""FRED adapter — commodity price and macro series (Requirement 2.1).

Uses the ``fredapi`` wrapper around the Federal Reserve's public REST API.
Requires a free API key (see ``.env.example``); when unconfigured the base
class routes the call through the snapshot fallback path.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from asciip_shared import COMMODITY_CODES

from asciip_data_pipeline.sources.base import Source, register_source


@register_source
class FredCommodityPrices(Source):
    name = "fred_commodity_prices"
    source_url = "https://api.stlouisfed.org/fred/series/observations"
    snapshot_filename = "fred_commodity_prices.parquet"

    #: Lookback window; 5 years covers all forecast-engine training needs.
    history_years = 5

    def is_configured(self) -> bool:
        return bool(self.settings.fred_api_key)

    def _fetch(self) -> pl.DataFrame:
        from fredapi import Fred  # local import — optional heavy dep

        api_key = self.settings.fred_api_key.get_secret_value() if self.settings.fred_api_key else None
        client = Fred(api_key=api_key)
        end = date.today()
        start = end - timedelta(days=self.history_years * 365 + 60)

        frames: list[pl.DataFrame] = []
        for commodity, series_id in COMMODITY_CODES.items():
            try:
                raw = client.get_series(
                    series_id,
                    observation_start=start.isoformat(),
                    observation_end=end.isoformat(),
                )
            except Exception as exc:  # pragma: no cover — per-series transient
                self.log.warning(
                    "fred.series_failed",
                    commodity=commodity,
                    series_id=series_id,
                    error=str(exc),
                )
                continue
            if raw is None or raw.empty:
                continue
            series_df = pl.DataFrame(
                {
                    "date": [ts.date() for ts in raw.index],
                    "commodity": [commodity] * len(raw),
                    "price": raw.values.astype(float),
                    "series_id": [series_id] * len(raw),
                }
            ).drop_nulls("price")
            frames.append(series_df)

        if not frames:
            raise ConnectionError("FRED returned no series — will fall back")
        return pl.concat(frames, how="vertical_relaxed")
