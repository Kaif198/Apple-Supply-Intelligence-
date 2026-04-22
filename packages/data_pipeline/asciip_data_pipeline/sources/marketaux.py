"""Marketaux news adapter.

Free tier: 100 requests/day. We pull the most recent 48h of news tagged
with AAPL or supplier keywords so the Control Tower "Latest signals" and
Disruptions Feed have event copy without relying on paid sources.
"""

from __future__ import annotations

import httpx
import polars as pl

from asciip_data_pipeline.sources.base import Source, register_source


@register_source
class MarketauxNews(Source):
    name = "marketaux_news"
    source_url = "https://api.marketaux.com/v1/news/all"
    snapshot_filename = "marketaux_news.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)
    history_hours = 72

    _KEYWORDS = (
        "AAPL OR Apple OR Foxconn OR TSMC OR 'Luxshare' OR 'Pegatron' "
        "OR 'Hon Hai' OR 'Samsung semiconductor' OR 'LG Display' OR 'BOE' "
        "OR 'lithium' OR 'rare earth'"
    )

    def is_configured(self) -> bool:
        return bool(self.settings.marketaux_api_key)

    def _fetch(self) -> pl.DataFrame:
        key = (
            self.settings.marketaux_api_key.get_secret_value()
            if self.settings.marketaux_api_key
            else ""
        )
        params = {
            "api_token": key,
            "symbols": "AAPL",
            "filter_entities": "true",
            "language": "en",
            "limit": 100,
            "search": self._KEYWORDS,
        }
        with httpx.Client(timeout=15.0) as client:
            r = client.get(self.source_url, params=params)  # type: ignore[arg-type]
            r.raise_for_status()
            payload = r.json()
        articles = payload.get("data") or []
        if not articles:
            raise ConnectionError("marketaux returned zero articles")
        rows = [
            {
                "uuid": a.get("uuid", ""),
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "url": a.get("url", ""),
                "published_at": a.get("published_at", ""),
                "source": a.get("source", ""),
                "sentiment": _avg_sentiment(a.get("entities") or []),
            }
            for a in articles
        ]
        return pl.DataFrame(rows)


def _avg_sentiment(entities: list[dict[str, object]]) -> float:
    scores = [float(e.get("sentiment_score") or 0.0) for e in entities]  # type: ignore[arg-type]
    return float(sum(scores) / len(scores)) if scores else 0.0
