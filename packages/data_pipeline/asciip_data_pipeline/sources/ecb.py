"""ECB reference exchange rates (Daily XML).

Public XML feed at sdw-wsrest.ecb.europa.eu. No auth, no rate limit.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

import httpx
import polars as pl

from asciip_data_pipeline.sources.base import Source, register_source


@register_source
class ECBReferenceRates(Source):
    name = "ecb_reference_rates"
    source_url = (
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
    )
    snapshot_filename = "ecb_reference_rates.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)

    _NS = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }

    def _fetch(self) -> pl.DataFrame:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(self.source_url)
            r.raise_for_status()
            tree = ET.fromstring(r.content)
        rows: list[dict[str, object]] = []
        for day_cube in tree.iter("{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
            day = day_cube.attrib.get("time")
            if not day:
                continue
            for cube in day_cube.findall("{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
                currency = cube.attrib.get("currency")
                rate = cube.attrib.get("rate")
                if not currency or not rate:
                    continue
                rows.append(
                    {
                        "date": date.fromisoformat(day),
                        "currency": currency,
                        "rate_eur_base": float(rate),
                    }
                )
        if not rows:
            raise ConnectionError("ECB returned no rates")
        return pl.DataFrame(rows)
