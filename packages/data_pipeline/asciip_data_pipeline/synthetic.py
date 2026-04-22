"""Deterministic synthetic calibration.

When every live source is unreachable and no snapshot exists, the ingestion
orchestrator falls back to this module. The generated datasets are calibrated
to plausible order-of-magnitudes for Apple's supply chain so the rest of the
stack (models, causal engine, DCF) produce sensible numbers.

Everything is seeded from :data:`asciip_shared.config.Settings.mc_seed` so
the output is reproducible across runs and machines. The UI layer surfaces
a "Synthetic Data for Demonstration" banner whenever provenance includes
any synthetic-calibration entry (Requirement 17.3).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from asciip_shared import COMMODITY_ORDER, SourceMetadata, get_logger, get_settings


def _rng() -> np.random.Generator:
    seed = get_settings().mc_seed
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
# Commodity prices (5 series x ~5 years of daily data)
# ---------------------------------------------------------------------------

# Approximate long-run mean price and daily volatility for each commodity.
# Tuned to mid-2020s observed levels; values are neither forecasts nor
# endorsements, just plausible starting points.
_COMMODITY_PARAMS: dict[str, tuple[float, float]] = {
    "copper": (9_000.0, 0.012),  # USD / metric ton
    "aluminum": (2_400.0, 0.010),  # USD / metric ton
    "lithium_carbonate": (18.0, 0.028),  # USD / kg (battery grade)
    "rare_earth_ndpr": (85.0, 0.022),  # USD / kg (NdPr oxide)
    "crude_oil_wti": (78.0, 0.016),  # USD / barrel
}


def generate_commodity_prices(years: int = 5, end: date | None = None) -> pl.DataFrame:
    """Return a long-format (date, commodity, price) DataFrame."""
    rng = _rng()
    end_date = end or date.today()
    n_days = years * 365 + 30
    start_date = end_date - timedelta(days=n_days - 1)
    dates = [start_date + timedelta(days=i) for i in range(n_days)]

    frames: list[pl.DataFrame] = []
    for commodity in COMMODITY_ORDER:
        mu, sigma = _COMMODITY_PARAMS[commodity]
        # Geometric Brownian motion with mean-reversion toward mu.
        prices = np.empty(n_days)
        prices[0] = mu
        kappa = 0.0035  # weak mean-reversion
        for i in range(1, n_days):
            drift = kappa * (np.log(mu) - np.log(prices[i - 1]))
            shock = sigma * rng.standard_normal()
            prices[i] = prices[i - 1] * float(np.exp(drift + shock))
        frames.append(
            pl.DataFrame(
                {
                    "date": dates,
                    "commodity": [commodity] * n_days,
                    "price": prices,
                }
            )
        )
    return pl.concat(frames, how="vertical")


# ---------------------------------------------------------------------------
# FX (USD/CNY, USD/EUR)
# ---------------------------------------------------------------------------


def generate_fx(years: int = 5, end: date | None = None) -> pl.DataFrame:
    rng = _rng()
    end_date = end or date.today()
    n_days = years * 365 + 30
    start_date = end_date - timedelta(days=n_days - 1)
    dates = [start_date + timedelta(days=i) for i in range(n_days)]
    frames: list[pl.DataFrame] = []
    for pair, (mu, sigma) in (("USD_CNY", (7.15, 0.004)), ("USD_EUR", (0.92, 0.004))):
        vals = np.empty(n_days)
        vals[0] = mu
        for i in range(1, n_days):
            drift = 0.005 * (mu - vals[i - 1])
            vals[i] = vals[i - 1] + drift + sigma * rng.standard_normal()
        frames.append(pl.DataFrame({"date": dates, "pair": [pair] * n_days, "rate": vals}))
    return pl.concat(frames, how="vertical")


# ---------------------------------------------------------------------------
# AAPL equity (daily OHLC)
# ---------------------------------------------------------------------------


def generate_aapl_equity(years: int = 5, end: date | None = None) -> pl.DataFrame:
    rng = _rng()
    end_date = end or date.today()
    n_days = years * 252  # trading days approximation
    start_date = end_date - timedelta(days=int(n_days * 1.4))
    dates: list[date] = []
    d = start_date
    while len(dates) < n_days:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    prices = np.empty(n_days)
    prices[0] = 180.0
    mu_daily = 0.00045  # ~11.4% annual drift
    sigma_daily = 0.016
    for i in range(1, n_days):
        prices[i] = prices[i - 1] * float(np.exp(mu_daily + sigma_daily * rng.standard_normal()))
    high = prices * (1 + np.abs(rng.normal(0, 0.008, n_days)))
    low = prices * (1 - np.abs(rng.normal(0, 0.008, n_days)))
    volume = rng.integers(40_000_000, 120_000_000, n_days)
    return pl.DataFrame(
        {
            "date": dates,
            "open": prices * (1 + rng.normal(0, 0.003, n_days)),
            "high": high,
            "low": low,
            "close": prices,
            "adj_close": prices,
            "volume": volume,
        }
    )


# ---------------------------------------------------------------------------
# Apple Supplier List (~200 representative suppliers)
# ---------------------------------------------------------------------------

_SUPPLIER_SEED: list[tuple[str, str, str, str, float]] = [
    # (name, country, category, tier, annual_spend_usd_billions)
    ("Hon Hai Precision (Foxconn)", "TW", "Assembly", "1", 45.0),
    ("Pegatron", "TW", "Assembly", "1", 12.0),
    ("Luxshare Precision", "CN", "Assembly", "1", 9.5),
    ("Wistron", "TW", "Assembly", "1", 6.2),
    ("TSMC", "TW", "Semiconductor", "1", 20.0),
    ("Samsung Electronics", "KR", "Display/NAND", "1", 18.0),
    ("LG Display", "KR", "Display", "1", 7.5),
    ("BOE Technology", "CN", "Display", "1", 4.5),
    ("SK hynix", "KR", "NAND/DRAM", "1", 5.8),
    ("Micron Technology", "US", "DRAM", "1", 3.9),
    ("Broadcom", "US", "Semiconductor", "1", 4.8),
    ("Qualcomm", "US", "Semiconductor", "1", 6.1),
    ("Skyworks Solutions", "US", "Semiconductor", "1", 1.9),
    ("STMicroelectronics", "CH", "Semiconductor", "1", 1.6),
    ("Texas Instruments", "US", "Semiconductor", "1", 1.1),
    ("Sony Semiconductor", "JP", "Camera sensor", "1", 3.0),
    ("Largan Precision", "TW", "Camera lens", "1", 1.3),
    ("Goertek", "CN", "Acoustic/AR", "1", 2.1),
    ("AAC Technologies", "CN", "Acoustic", "1", 1.4),
    ("Yageo", "TW", "Passives", "1", 0.9),
    ("Murata Manufacturing", "JP", "Passives", "1", 2.4),
    ("TDK", "JP", "Passives", "1", 1.8),
    ("Amphenol", "US", "Connectors", "1", 1.2),
    ("Foxlink", "TW", "Cables", "1", 0.8),
    ("Nidec", "JP", "Motors", "1", 0.7),
    ("Minebea Mitsumi", "JP", "Mechanical", "1", 0.6),
    ("Catcher Technology", "TW", "Enclosures", "1", 1.5),
    ("Foxconn Interconnect", "TW", "Connectors", "1", 0.9),
    ("Lens Technology", "CN", "Cover glass", "1", 1.7),
    ("Biel Crystal", "HK", "Cover glass", "1", 1.1),
    ("Corning", "US", "Cover glass", "1", 2.3),
    ("Nitto Denko", "JP", "Films", "1", 0.5),
    ("3M", "US", "Adhesives", "1", 0.4),
    ("Jabil", "US", "EMS", "1", 3.4),
    ("Flex", "US", "EMS", "1", 2.1),
    ("CATL", "CN", "Battery", "2", 1.8),
    ("ATL (Amperex)", "CN", "Battery", "1", 4.2),
    ("LG Energy Solution", "KR", "Battery", "1", 2.5),
    ("Sunwoda", "CN", "Battery pack", "1", 1.4),
    ("Simplo Technology", "TW", "Battery pack", "1", 0.8),
]


def generate_suppliers() -> pl.DataFrame:
    rng = _rng()
    rows: list[dict[str, object]] = []
    for idx, (name, country, category, tier, spend) in enumerate(_SUPPLIER_SEED):
        distress = float(np.clip(rng.beta(2, 6) + (idx % 17) / 100, 0, 1))
        otd = float(np.clip(0.95 - rng.beta(2, 8) * 0.2, 0.55, 1.0))
        dpo = int(rng.integers(30, 85))
        rev_conc = float(np.clip(rng.beta(2, 5), 0, 1))
        lat, lon = _country_centroid(country)
        rows.append(
            {
                "id": f"SUP-{idx + 1:04d}",
                "name": name,
                "parent": None,
                "country": country,
                "category": category,
                "tier": int(tier),
                "annual_spend_billions": float(spend),
                "distress_score": distress,
                "otd_rate_90d": otd,
                "dpo_days": dpo,
                "revenue_concentration_top3": rev_conc,
                "lat": lat + float(rng.normal(0, 0.3)),
                "lon": lon + float(rng.normal(0, 0.3)),
            }
        )
    return pl.DataFrame(rows)


_CENTROIDS: dict[str, tuple[float, float]] = {
    "TW": (23.7, 121.0),
    "CN": (35.9, 104.2),
    "KR": (36.5, 127.8),
    "JP": (36.2, 138.3),
    "US": (39.8, -98.6),
    "HK": (22.3, 114.2),
    "CH": (46.8, 8.2),
}


def _country_centroid(country: str) -> tuple[float, float]:
    return _CENTROIDS.get(country, (0.0, 0.0))


# ---------------------------------------------------------------------------
# Disruption event seed (for first boot)
# ---------------------------------------------------------------------------

_EVENT_TEMPLATES = [
    ("commodity", "Lithium carbonate spot spikes {pct:+.0f}% on Zimbabwe export controls"),
    ("tariff", "US Section 301 review raises HS 8542 semi tariff to {pct:.1f}pp"),
    ("logistics", "Panama Canal draft restrictions extend transit by {days} days"),
    ("supplier", "{supplier} Q{q} earnings miss triggers credit watch"),
    ("fx", "PBoC fixing widens USD/CNY band; spot {pct:+.2f}% vs prior"),
]


def generate_recent_events(n: int = 48) -> pl.DataFrame:
    rng = _rng()
    suppliers = generate_suppliers()["name"].to_list()
    now = datetime.now(UTC)
    rows: list[dict[str, object]] = []
    for i in range(n):
        kind, template = _EVENT_TEMPLATES[i % len(_EVENT_TEMPLATES)]
        timestamp = now - timedelta(hours=int(rng.integers(1, 72)) + i * 2)
        pct = float(rng.normal(0, 6))
        days = int(rng.integers(1, 8))
        q = int(rng.integers(1, 5))
        supplier = suppliers[int(rng.integers(0, len(suppliers)))]
        title = template.format(pct=pct, days=days, q=q, supplier=supplier.split(" (")[0])
        severity_usd = float(abs(rng.normal(0, 500_000_000)) + 5_000_000)
        rows.append(
            {
                "id": f"EVT-{i + 1:06d}",
                "timestamp": timestamp,
                "type": kind,
                "title": title,
                "impact_usd": severity_usd,
                "source_name": "synthetic_calibration",
                "source_url": "asciip://synthetic",
            }
        )
    return pl.DataFrame(rows).sort("timestamp", descending=True)


# ---------------------------------------------------------------------------
# Snapshot writer — invoked by the Phase 1/2 bootstrap when snapshots dir is empty.
# ---------------------------------------------------------------------------


def write_snapshots(snapshot_dir: Path | None = None) -> list[Path]:
    """Materialize every synthetic dataset to ``data/snapshots/``."""
    settings = get_settings()
    out_dir = snapshot_dir or settings.snapshots_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    log = get_logger("asciip.synthetic")

    outputs: dict[str, pl.DataFrame] = {
        "fred_commodity_prices": generate_commodity_prices(),
        "fred_fx": generate_fx(),
        "yfinance_aapl": generate_aapl_equity(),
        "apple_supplier_pdf": generate_suppliers(),
        "disruption_events_seed": generate_recent_events(),
    }

    written: list[Path] = []
    for name, df in outputs.items():
        path = out_dir / f"{name}.parquet"
        df.write_parquet(path, compression="zstd")
        payload = path.read_bytes()
        import hashlib as _h

        sha = _h.sha256(payload).hexdigest()
        (path.with_suffix(path.suffix + ".sha256")).write_text(
            f"{sha}  {path.name}\n", encoding="utf-8"
        )
        written.append(path)
        log.info("synthetic.snapshot_written", path=str(path), rows=df.height)

    return written


def make_metadata(source_name: str, path: Path) -> SourceMetadata:
    """Build a SourceMetadata tagged as synthetic calibration."""
    return SourceMetadata.for_path(
        source_name=source_name,
        source_url="asciip://synthetic",
        path=path,
        row_count=pl.read_parquet(path).height,
        notes="synthetic_calibration",
    )


if __name__ == "__main__":  # pragma: no cover — manual use
    for p in write_snapshots():
        print(p)
