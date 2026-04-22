"""UN Comtrade adapter — bilateral trade flows for tariff/tariff-delta features.

Free anonymous tier: 100 req/hr. With a subscription key: 10,000 req/day.
We pull a narrow HS-code slice relevant to iPhone & Mac bill-of-materials.
"""

from __future__ import annotations

import datetime as _dt

import httpx
import polars as pl

from asciip_data_pipeline.sources.base import Source, register_source

# HS codes:
#   8542 — electronic integrated circuits (semiconductors)
#   8517 — telephones including smartphones
#   8504 — electrical transformers/power supplies
#   2805 — alkali/alkaline earth metals (inc. lithium)
_HS_CODES = ("8542", "8517", "8504", "2805")
_REPORTERS = ("156", "410", "158", "392", "699")  # CN, KR, TW, JP, IN ISO-numeric


@register_source
class ComtradeTrade(Source):
    name = "comtrade_trade"
    source_url = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
    snapshot_filename = "comtrade_trade.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)
    history_years = 3

    def _fetch(self) -> pl.DataFrame:
        subscription = (
            self.settings.comtrade_api_key.get_secret_value()
            if self.settings.comtrade_api_key
            else None
        )
        headers = {"Ocp-Apim-Subscription-Key": subscription} if subscription else {}

        end_year = _dt.date.today().year
        years = ",".join(str(y) for y in range(end_year - self.history_years, end_year + 1))

        rows: list[dict[str, object]] = []
        with httpx.Client(timeout=30.0, headers=headers) as client:
            for hs in _HS_CODES:
                params = {
                    "reporterCode": ",".join(_REPORTERS),
                    "period": years,
                    "partnerCode": "842",  # USA partner
                    "flowCode": "X",  # exports
                    "cmdCode": hs,
                    "freqCode": "A",
                    "typeCode": "C",
                }
                r = client.get(self.source_url, params=params)
                r.raise_for_status()
                payload = r.json()
                for record in payload.get("data") or []:
                    rows.append(
                        {
                            "period": record.get("period"),
                            "reporter": record.get("reporterDesc"),
                            "reporter_code": record.get("reporterCode"),
                            "partner": record.get("partnerDesc"),
                            "hs_code": hs,
                            "trade_value_usd": float(record.get("primaryValue") or 0.0),
                            "trade_weight_kg": float(record.get("netWgt") or 0.0),
                        }
                    )
        if not rows:
            raise ConnectionError("comtrade returned no rows")
        return pl.DataFrame(rows)
