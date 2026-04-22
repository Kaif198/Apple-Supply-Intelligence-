"""Drewry World Container Index scrape.

The WCI is published weekly as a public HTML page. We parse the ``<script>``
block that embeds the tabular series (selectolax is tolerant of fragment
HTML). No authentication; a polite 1-per-minute cadence is enforced by the
scheduler.
"""

from __future__ import annotations

import re

import httpx
import polars as pl
from selectolax.parser import HTMLParser

from asciip_data_pipeline.sources.base import Source, register_source


_NUMBER_RE = re.compile(r"\$?(\d[\d,]*)")


@register_source
class DrewryWCI(Source):
    name = "drewry_wci"
    source_url = (
        "https://www.drewry.co.uk/supply-chain-advisors/supply-chain-expertise/"
        "world-container-index-assessed-by-drewry"
    )
    snapshot_filename = "drewry_wci.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)

    def _fetch(self) -> pl.DataFrame:
        with httpx.Client(
            timeout=20.0,
            headers={"User-Agent": self.settings.nominatim_user_agent},
            follow_redirects=True,
        ) as client:
            r = client.get(self.source_url)
            r.raise_for_status()
        tree = HTMLParser(r.text)
        # Drewry surfaces the index + lane rates inside a table with class `wci-table`.
        rows: list[dict[str, object]] = []
        for row in tree.css("table.wci-table tbody tr"):
            cells = [c.text(strip=True) for c in row.css("td")]
            if len(cells) < 2:
                continue
            lane = cells[0]
            value_match = _NUMBER_RE.search(cells[1])
            if not value_match:
                continue
            rows.append(
                {
                    "lane": lane,
                    "usd_per_40ft": float(value_match.group(1).replace(",", "")),
                }
            )
        if not rows:
            raise ConnectionError("drewry page returned no parseable rows")
        return pl.DataFrame(rows)
