"""Yahoo Finance adapter — AAPL equity + a handful of supplier tickers.

No API key is required; ``yfinance`` rate-limits informally. The adapter
fetches 5 years of daily OHLC for AAPL plus selected listed suppliers so
the factor regression and sparklines have up-to-date inputs.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from asciip_data_pipeline.sources.base import Source, register_source


@register_source
class YahooAapl(Source):
    name = "yfinance_aapl"
    source_url = "https://finance.yahoo.com/quote/AAPL"
    snapshot_filename = "yfinance_aapl.parquet"

    ticker = "AAPL"
    history_years = 5

    def _fetch(self) -> pl.DataFrame:
        import yfinance as yf  # local import — optional heavy dep

        end = date.today()
        start = end - timedelta(days=self.history_years * 365 + 30)
        hist = yf.Ticker(self.ticker).history(
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
            actions=False,
        )
        if hist is None or hist.empty:
            raise ConnectionError("yfinance returned no rows for AAPL")
        hist = hist.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        df = pl.from_pandas(hist)
        return df.with_columns(pl.col("date").cast(pl.Date))
