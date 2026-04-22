"""People's Bank of China USD/CNY central-parity fixing scrape.

Public page, no auth, updated once per trading day. The value is embedded
in the table of daily fixings — we scrape only the most recent row.
"""

from __future__ import annotations

import datetime as _dt
import re

import httpx
import polars as pl
from selectolax.parser import HTMLParser

from asciip_data_pipeline.sources.base import Source, register_source


@register_source
class PbocFixing(Source):
    name = "pboc_fixing"
    source_url = "http://www.pbc.gov.cn/en/3688006/3688066/3688067/index.html"
    snapshot_filename = "pboc_fixing.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)

    _RATE_RE = re.compile(r"(\d+\.\d{4})")

    def _fetch(self) -> pl.DataFrame:
        with httpx.Client(
            timeout=20.0,
            headers={"User-Agent": self.settings.nominatim_user_agent},
            follow_redirects=True,
        ) as client:
            r = client.get(self.source_url)
            r.raise_for_status()
        tree = HTMLParser(r.text)

        rows: list[dict[str, object]] = []
        for article in tree.css("a[href*='central-parity']"):
            text = article.text(strip=True)
            m = self._RATE_RE.search(text)
            if not m:
                continue
            # Dates on the PBoC listing are encoded in the anchor's href.
            href = article.attributes.get("href") or ""
            date_match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", href)
            if not date_match:
                continue
            rows.append(
                {
                    "date": _dt.date(
                        int(date_match.group(1)),
                        int(date_match.group(2)),
                        int(date_match.group(3)),
                    ),
                    "usd_cny_mid": float(m.group(1)),
                }
            )
        if not rows:
            raise ConnectionError("PBoC page returned no parsable fixings")
        return pl.DataFrame(rows).unique(subset=["date"]).sort("date")
