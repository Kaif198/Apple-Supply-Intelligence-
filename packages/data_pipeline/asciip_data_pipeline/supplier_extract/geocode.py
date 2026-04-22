"""OpenStreetMap Nominatim geocoder with on-disk Parquet cache.

Nominatim's public endpoint requires a descriptive User-Agent and caps
traffic at one request per second. We honour both: the User-Agent comes
from ``ASCIIP_NOMINATIM_USER_AGENT`` and every call is rate-limited by
``self.min_interval_s``. Successful lookups are cached in
``data/snapshots/geocode_cache.parquet`` so subsequent runs are instant
and the public service is not hammered.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
import polars as pl

from asciip_shared import get_logger, get_settings


@dataclass(frozen=True)
class GeocodeResult:
    address: str
    lat: float | None
    lon: float | None
    display_name: str


class NominatimGeocoder:
    endpoint = "https://nominatim.openstreetmap.org/search"
    min_interval_s: float = 1.1  # polite pacing

    def __init__(self, cache_path: Path | None = None) -> None:
        settings = get_settings()
        self.user_agent = settings.nominatim_user_agent
        self.cache_path = cache_path or (settings.snapshots_dir / "geocode_cache.parquet")
        self.log = get_logger("asciip.geocode")
        self._cache: dict[str, GeocodeResult] = {}
        self._load_cache()

    # -------------------------------------------------------------- cache I/O

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                df = pl.read_parquet(self.cache_path)
            except Exception as exc:  # pragma: no cover — corrupt cache
                self.log.warning("geocode.cache_unreadable", error=str(exc))
                return
            for row in df.iter_rows(named=True):
                self._cache[str(row["address"])] = GeocodeResult(
                    address=str(row["address"]),
                    lat=row["lat"],
                    lon=row["lon"],
                    display_name=str(row["display_name"] or ""),
                )

    def _save_cache(self) -> None:
        if not self._cache:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        df = pl.DataFrame(
            [
                {
                    "address": r.address,
                    "lat": r.lat,
                    "lon": r.lon,
                    "display_name": r.display_name,
                }
                for r in self._cache.values()
            ]
        )
        df.write_parquet(self.cache_path, compression="zstd")

    # ------------------------------------------------------------------- API

    def lookup(self, address: str) -> GeocodeResult:
        if address in self._cache:
            return self._cache[address]

        time.sleep(self.min_interval_s)
        try:
            with httpx.Client(
                timeout=15.0,
                headers={"User-Agent": self.user_agent, "Accept-Language": "en"},
            ) as client:
                r = client.get(
                    self.endpoint,
                    params={"q": address, "format": "json", "limit": 1},
                )
                r.raise_for_status()
                payload = r.json() or []
        except httpx.HTTPError as exc:
            self.log.warning("geocode.http_error", address=address, error=str(exc))
            result = GeocodeResult(address=address, lat=None, lon=None, display_name="")
            self._cache[address] = result
            return result

        if not payload:
            result = GeocodeResult(address=address, lat=None, lon=None, display_name="")
        else:
            top = payload[0]
            result = GeocodeResult(
                address=address,
                lat=float(top.get("lat") or 0.0) or None,
                lon=float(top.get("lon") or 0.0) or None,
                display_name=str(top.get("display_name") or ""),
            )
        self._cache[address] = result
        self._save_cache()
        return result

    def lookup_many(self, addresses: Iterable[str]) -> list[GeocodeResult]:
        return [self.lookup(a) for a in addresses]


def geocode_suppliers(frame: pl.DataFrame) -> pl.DataFrame:
    """Return ``frame`` with ``lat`` and ``lon`` columns populated."""
    if "address" not in frame.columns:
        raise ValueError("supplier frame must contain an `address` column")
    geocoder = NominatimGeocoder()
    lat: list[float | None] = []
    lon: list[float | None] = []
    for address in frame["address"].to_list():
        result = geocoder.lookup(address or "")
        lat.append(result.lat)
        lon.append(result.lon)
    return frame.with_columns(
        pl.Series("lat", lat, dtype=pl.Float64),
        pl.Series("lon", lon, dtype=pl.Float64),
    )
