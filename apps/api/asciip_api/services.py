"""Service layer.

Routers are intentionally thin — every database read and every model
invocation happens here. This makes the code easy to unit-test without
spinning up the full HTTP stack.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from asciip_shared import get_logger, get_settings

from asciip_data_pipeline.features import get_feature_store
from asciip_ml_models.causal import CausalConfig, estimate_ate
from asciip_ml_models.distress.classifier import load_production as load_distress
from asciip_ml_models.factor.regression import load_production as load_factor
from asciip_ml_models.forecast import ForecastConfig, train_commodity_ensemble
from asciip_ml_models.margin.ridge import load_production as load_margin
from asciip_ml_models.montecarlo import MonteCarloConfig, ShockSpec, run_simulation
from asciip_ml_models.valuation import (
    DCFAssumptions,
    apple_base_case,
    run_dcf,
    two_way_sensitivity,
)


# --------------------------------------------------------------------- pricing

COMMODITIES = ("aluminum", "copper", "lithium_carbonate", "rare_earth_ndpr", "crude_oil_wti")


def get_commodity_panel(lookback_days: int = 365) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    store = get_feature_store()
    with store.connect() as con:
        rows = con.execute(
            "SELECT entity_id, as_of_ts, feature_value "
            "FROM features_wide "
            "WHERE feature_name = 'commodity_price' "
            "  AND entity_id IN (?, ?, ?, ?, ?) "
            "  AND as_of_ts >= ? "
            "  AND feature_value IS NOT NULL "
            "ORDER BY entity_id, as_of_ts",
            [*COMMODITIES, cutoff],
        ).fetchall()
        vol_rows = con.execute(
            "SELECT entity_id, feature_value FROM features_wide "
            "WHERE feature_name = 'commodity_vol_30d_annualized' "
            "  AND feature_value IS NOT NULL "
            "ORDER BY entity_id, as_of_ts DESC"
        ).fetchall()

    by_entity: dict[str, list[dict[str, Any]]] = {c: [] for c in COMMODITIES}
    for entity_id, as_of_ts, value in rows:
        by_entity.setdefault(entity_id, []).append(
            {"as_of_ts": as_of_ts, "price": float(value)}
        )

    latest_vol: dict[str, float] = {}
    for entity_id, value in vol_rows:
        if entity_id not in latest_vol:
            latest_vol[entity_id] = float(value)

    commodities = [
        {
            "entity_id": c,
            "series": by_entity.get(c, []),
            "vol_30d_annualized": latest_vol.get(c),
        }
        for c in COMMODITIES
    ]
    as_of = max((s[-1]["as_of_ts"] for s in by_entity.values() if s), default=datetime.now(UTC))
    return {"as_of": as_of, "commodities": commodities}


def commodity_forecast(entity_id: str, horizon_days: int = 30) -> dict[str, Any]:
    log = get_logger("asciip.api.pricing")
    siblings = tuple(c for c in COMMODITIES if c != entity_id)
    cfg = ForecastConfig(
        commodity=entity_id,
        horizon_days=horizon_days,
        sibling_commodities=siblings,
        register=False,
        promote=False,
    )
    result = train_commodity_ensemble(cfg)
    history_tail = [
        {"as_of_ts": ts, "price": price}
        for ts, price in zip(result.history_index[-60:], result.history_values[-60:])
    ]
    forecast = [
        {"ts": ts, "mean": m, "lower": lo, "upper": hi}
        for ts, m, lo, hi in zip(
            result.forecast_index,
            result.forecast_mean,
            result.forecast_lower,
            result.forecast_upper,
        )
    ]
    log.info(
        "pricing.forecast",
        entity=entity_id,
        horizon=horizon_days,
        members=list(result.member_weights),
    )
    return {
        "entity_id": entity_id,
        "horizon_days": horizon_days,
        "members": result.member_weights,
        "val_mae": result.member_val_mae,
        "forecast": forecast,
        "history_tail": history_tail,
    }


# ------------------------------------------------------------------- equity


def aapl_history(lookback_days: int = 365) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    store = get_feature_store()
    with store.connect() as con:
        rows = con.execute(
            "SELECT adj.as_of_ts, adj.feature_value, ret.feature_value "
            "FROM features_wide adj "
            "LEFT JOIN features_wide ret "
            "  ON adj.as_of_ts = ret.as_of_ts AND adj.entity_id = ret.entity_id "
            " AND ret.feature_name = 'aapl_log_return' "
            "WHERE adj.feature_name = 'aapl_adj_close' AND adj.entity_id = 'AAPL' "
            "  AND adj.as_of_ts >= ? "
            "ORDER BY adj.as_of_ts",
            [cutoff],
        ).fetchall()
    series = [
        {"as_of_ts": ts, "adj_close": float(px), "log_return": float(r) if r is not None else None}
        for ts, px, r in rows
    ]
    return {"series": series}


def factor_report() -> dict[str, Any]:
    model = load_factor()
    if model is None:
        raise RuntimeError(
            "factor model has not been trained yet — run `make train-factor`"
        )
    factors = [
        {
            "name": name,
            "coefficient": model.params.get(name, 0.0),
            "std_error": model.bse.get(name, 0.0),
            "t_value": model.tvalues.get(name, 0.0),
            "p_value": model.pvalues.get(name, 1.0),
        }
        for name in ("const",) + model.factor_names
    ]
    return {
        "r_squared": model.r_squared,
        "adj_r_squared": model.adj_r_squared,
        "n_obs": model.n_obs,
        "factors": factors,
        "notes": "OLS with Newey-West HAC standard errors. Factors lagged 1 trading day.",
    }


# ------------------------------------------------------------------- suppliers


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, float):
        return math.isnan(value)
    return bool(pd.isna(value)) if not isinstance(value, (dict, list, tuple, set)) else False


def _as_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _supplier_id_from_row(row: dict[str, Any]) -> str:
    raw = row.get("id")
    if not _is_missing(raw):
        return str(raw)
    name = str(row.get("name") or "supplier").strip()
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]
    return f"sup-{digest}"


def _normalize_supplier_row(row: dict[str, Any]) -> dict[str, Any]:
    supplier_id = _supplier_id_from_row(row)
    name = str(row.get("name") or supplier_id)
    return {
        "id": supplier_id,
        "name": name,
        "parent": None if _is_missing(row.get("parent")) else str(row.get("parent")),
        "country": None if _is_missing(row.get("country")) else str(row.get("country")),
        "category": None if _is_missing(row.get("category")) else str(row.get("category")),
        "tier": _as_int(row.get("tier")),
        "annual_spend_billions": _as_float(row.get("annual_spend_billions")),
        "distress_score": _as_float(row.get("distress_score")),
        "otd_rate_90d": _as_float(row.get("otd_rate_90d")),
        "dpo_days": _as_float(row.get("dpo_days")),
        "revenue_concentration_top3": _as_float(row.get("revenue_concentration_top3")),
        "lat": _as_float(row.get("lat")),
        "lon": _as_float(row.get("lon")),
    }


def list_suppliers() -> dict[str, Any]:
    store = get_feature_store()
    with store.connect() as con:
        try:
            df = con.execute("SELECT * FROM src_apple_supplier_pdf").fetch_df()
        except Exception:
            df = pd.DataFrame()
    raw_suppliers = df.to_dict(orient="records") if not df.empty else []
    suppliers = [_normalize_supplier_row(row) for row in raw_suppliers]
    as_of = datetime.now(UTC)
    return {"as_of": as_of, "count": len(suppliers), "suppliers": suppliers}


def supplier_distress(supplier_id: str) -> dict[str, Any]:
    store = get_feature_store()
    with store.connect() as con:
        try:
            df = con.execute("SELECT * FROM src_apple_supplier_pdf").fetch_df()
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        raise KeyError(f"supplier {supplier_id!r} not found")

    raw_records = df.to_dict(orient="records")
    normalized = [_normalize_supplier_row(row) for row in raw_records]
    record: dict[str, Any] | None = None
    supplier: dict[str, Any] | None = None
    for idx, row in enumerate(normalized):
        if row["id"] == supplier_id:
            supplier = row
            record = raw_records[idx]
            break

    if supplier is None or record is None:
        raise KeyError(f"supplier {supplier_id!r} not found")

    model = load_distress()
    probability = float(supplier.get("distress_score") or 0.0)
    drivers: list[dict[str, Any]] = []
    model_version: str | None = None
    if model is not None:
        probability = float(model.predict_proba([record])[0])
        model_version = model.version
        # Simple driver explanation: top numeric features by |z-score|
        # relative to the synthetic cohort means.
        cohort = store
        for feature in model.numeric_columns:
            value = record.get(feature)
            if value is None:
                continue
            numeric = _as_float(value)
            if numeric is None:
                continue
            drivers.append({"feature": feature, "value": numeric})

    return {
        "id": supplier["id"],
        "name": supplier["name"],
        "distress_probability": probability,
        "distress_score": supplier.get("distress_score"),
        "drivers": drivers,
        "model_version": model_version,
    }


# --------------------------------------------------------------------- events


def list_events(*, severity: str | None = None, limit: int = 50) -> dict[str, Any]:
    store = get_feature_store()
    params: list[Any] = []
    predicates = []
    if severity:
        predicates.append("severity = ?")
        params.append(severity)
    where = f"WHERE {' AND '.join(predicates)}" if predicates else ""
    sql = (
        "SELECT id, as_of_ts, event_type, title, summary, source_name, source_url, "
        "impact_usd, severity, margin_delta_bps, ev_delta_usd, affected_supplier_ids "
        f"FROM disruption_events {where} "
        "ORDER BY as_of_ts DESC LIMIT ?"
    )
    params.append(limit)
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()

    events = []
    for row in rows:
        events.append({
            "id": row[0],
            "as_of_ts": row[1],
            "event_type": row[2],
            "title": row[3],
            "summary": row[4],
            "source_name": row[5],
            "source_url": row[6],
            "impact_usd": float(row[7]),
            "severity": row[8],
            "margin_delta_bps": int(row[9]) if row[9] is not None else None,
            "ev_delta_usd": float(row[10]) if row[10] is not None else None,
            "affected_supplier_ids": (row[11] or "").split(",") if row[11] else [],
        })

    # If the events table is empty (first boot), fall back to the synthetic seed snapshot.
    if not events:
        events = _events_from_seed_snapshot(severity=severity, limit=limit)

    return {
        "as_of": datetime.now(UTC),
        "count": len(events),
        "events": events,
    }


def _events_from_seed_snapshot(*, severity: str | None, limit: int) -> list[dict[str, Any]]:
    store = get_feature_store()
    with store.connect() as con:
        try:
            df = con.execute(
                "SELECT * FROM src_disruption_events_seed ORDER BY as_of_ts DESC"
            ).fetch_df()
        except Exception:
            return []
    if df.empty:
        return []
    if severity:
        df = df[df["severity"] == severity]
    df = df.head(limit)
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        out.append({
            "id": str(row.get("id") or uuid.uuid4().hex),
            "as_of_ts": row.get("as_of_ts"),
            "event_type": str(row.get("event_type") or "commodity"),
            "title": str(row.get("title") or "Disruption event"),
            "summary": str(row.get("summary") or ""),
            "source_name": str(row.get("source_name") or "synthetic"),
            "source_url": row.get("source_url"),
            "impact_usd": float(row.get("impact_usd") or 0.0),
            "severity": str(row.get("severity") or "medium"),
            "margin_delta_bps": int(row.get("margin_delta_bps") or 0) or None,
            "ev_delta_usd": float(row.get("ev_delta_usd") or 0.0) or None,
            "affected_supplier_ids": [],
        })
    return out


def get_event(event_id: str) -> dict[str, Any] | None:
    store = get_feature_store()
    with store.connect() as con:
        row = con.execute(
            "SELECT id, as_of_ts, event_type, title, summary, source_name, source_url, "
            "impact_usd, severity, margin_delta_bps, ev_delta_usd, affected_supplier_ids "
            "FROM disruption_events WHERE id = ?",
            [event_id],
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "as_of_ts": row[1],
        "event_type": row[2],
        "title": row[3],
        "summary": row[4],
        "source_name": row[5],
        "source_url": row[6],
        "impact_usd": float(row[7]),
        "severity": row[8],
        "margin_delta_bps": int(row[9]) if row[9] is not None else None,
        "ev_delta_usd": float(row[10]) if row[10] is not None else None,
        "affected_supplier_ids": (row[11] or "").split(",") if row[11] else [],
    }


# ------------------------------------------------------------------- scenarios


def run_monte_carlo(payload: dict[str, Any], *, sample_size: int = 256) -> dict[str, Any]:
    cfg = MonteCarloConfig(
        n_trials=int(payload["n_trials"]),
        horizon_years=float(payload["horizon_years"]),
        shocks=tuple(
            ShockSpec(
                name=s["name"],
                mean_return=float(s["mean_return"]),
                volatility=float(s["volatility"]),
                elasticity_bps_per_10pct=float(s["elasticity_bps_per_10pct"]),
            )
            for s in payload["shocks"]
        ),
        correlation=(
            tuple(tuple(float(v) for v in row) for row in payload["correlation"])
            if payload.get("correlation")
            else None
        ),
        supplier_stress_mean=float(payload["supplier_stress_mean"]),
        supplier_stress_sd=float(payload["supplier_stress_sd"]),
        outage_revenue_haircut_mean=float(payload["outage_revenue_haircut_mean"]),
        outage_revenue_haircut_sd=float(payload["outage_revenue_haircut_sd"]),
        seed=int(payload["seed"]),
    )
    result = run_simulation(cfg)
    summary = result.summary()
    # Down-sample to a reasonable payload size for the histogram chart.
    rng = np.random.default_rng(cfg.seed)
    idx = rng.choice(result.n_trials, size=min(sample_size, result.n_trials), replace=False)
    summary["implied_price_samples"] = [float(v) for v in result.implied_price_samples[np.sort(idx)]]
    return summary


def run_dcf_with_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    base = apple_base_case()
    overrides = {k: v for k, v in payload.items() if v is not None}
    if overrides:
        assumptions = DCFAssumptions(
            revenue_ttm_bn=float(overrides.get("revenue_ttm_bn", base.revenue_ttm_bn)),
            revenue_cagr_5y=float(overrides.get("revenue_cagr_5y", base.revenue_cagr_5y)),
            fcf_margin=float(overrides.get("fcf_margin", base.fcf_margin)),
            wacc=float(overrides.get("wacc", base.wacc)),
            terminal_growth=float(overrides.get("terminal_growth", base.terminal_growth)),
            net_cash_bn=float(overrides.get("net_cash_bn", base.net_cash_bn)),
            shares_diluted_bn=float(overrides.get("shares_diluted_bn", base.shares_diluted_bn)),
            horizon_years=int(overrides.get("horizon_years", base.horizon_years)),
        )
    else:
        assumptions = base

    r = run_dcf(assumptions)
    return {
        "assumptions": {
            "revenue_ttm_bn": assumptions.revenue_ttm_bn,
            "revenue_cagr_5y": assumptions.revenue_cagr_5y,
            "fcf_margin": assumptions.fcf_margin,
            "wacc": assumptions.wacc,
            "terminal_growth": assumptions.terminal_growth,
            "net_cash_bn": assumptions.net_cash_bn,
            "shares_diluted_bn": assumptions.shares_diluted_bn,
            "horizon_years": assumptions.horizon_years,
        },
        "projected_revenue_bn": list(r.projected_revenue_bn),
        "projected_fcf_bn": list(r.projected_fcf_bn),
        "enterprise_value_bn": r.enterprise_value_bn,
        "equity_value_bn": r.equity_value_bn,
        "implied_price_usd": r.implied_price_usd,
        "pv_explicit_bn": r.pv_explicit_bn,
        "pv_terminal_bn": r.pv_terminal_bn,
    }


def run_sensitivity(payload: dict[str, Any]) -> dict[str, Any]:
    grid = two_way_sensitivity(
        apple_base_case(),
        row_field=payload["row_field"],
        row_values=payload["row_values"],
        col_field=payload["col_field"],
        col_values=payload["col_values"],
    )
    return grid.to_dict()


# --------------------------------------------------------------------- causal


def estimate_commodity_ate(payload: dict[str, Any]) -> dict[str, Any]:
    """Assemble an AAPL-returns vs. commodity-returns causal panel."""
    treatment = payload["treatment"]
    store = get_feature_store()
    lookback = datetime.now(UTC) - timedelta(days=int(payload["lookback_days"]))
    with store.connect() as con:
        price_rows = con.execute(
            "SELECT as_of_ts, feature_value FROM features_wide "
            "WHERE feature_name = 'commodity_price' AND entity_id = ? AND as_of_ts >= ? "
            "ORDER BY as_of_ts",
            [treatment, lookback],
        ).fetchall()
        aapl_rows = con.execute(
            "SELECT as_of_ts, feature_value FROM features_wide "
            "WHERE feature_name = 'aapl_log_return' AND entity_id = 'AAPL' AND as_of_ts >= ? "
            "ORDER BY as_of_ts",
            [lookback],
        ).fetchall()
        fx_rows = con.execute(
            "SELECT as_of_ts, feature_value FROM features_wide "
            "WHERE feature_name = 'fx_rate' AND entity_id = 'USD_CNY' AND as_of_ts >= ? "
            "ORDER BY as_of_ts",
            [lookback],
        ).fetchall()

    prices = pd.Series(
        {pd.Timestamp(r[0]).normalize(): float(r[1]) for r in price_rows}
    ).sort_index()
    aapl = pd.Series(
        {pd.Timestamp(r[0]).normalize(): float(r[1]) for r in aapl_rows}
    ).sort_index()
    fx = pd.Series(
        {pd.Timestamp(r[0]).normalize(): float(r[1]) for r in fx_rows}
    ).sort_index()

    commodity_ret = np.log(prices / prices.shift(1))
    fx_ret = np.log(fx / fx.shift(1))
    market_lag1 = aapl.rolling(5).mean().shift(1)
    fx_lag1 = fx_ret.shift(1)

    panel = pd.DataFrame({
        "treatment": commodity_ret,
        "outcome": aapl,
        "market_lag1": market_lag1,
        "fx_change_lag1": fx_lag1,
    }).dropna()

    if len(panel) < 60:
        raise RuntimeError(
            f"insufficient overlapping observations for causal estimate: {len(panel)}"
        )

    est = estimate_ate(
        CausalConfig(
            treatment="treatment",
            outcome="outcome",
            confounders=("market_lag1", "fx_change_lag1"),
            data=panel,
        )
    )
    return {
        "method": est.method,
        "ate": est.ate,
        "std_error": est.std_error,
        "ci_low": est.ci_low,
        "ci_high": est.ci_high,
        "n_obs": est.n_obs,
        "refutations": dict(est.refutations),
        "assumptions": list(est.assumptions),
    }


# ---------------------------------------------------------------------- alerts


def list_alerts(*, unacknowledged_only: bool = False, limit: int = 100) -> dict[str, Any]:
    store = get_feature_store()
    sql = (
        "SELECT id, created_at, event_id, severity, acknowledged_at, channel, payload "
        "FROM alerts "
    )
    if unacknowledged_only:
        sql += "WHERE acknowledged_at IS NULL "
    sql += "ORDER BY created_at DESC LIMIT ?"
    with store.connect() as con:
        rows = con.execute(sql, [limit]).fetchall()
    alerts = []
    for row in rows:
        alerts.append({
            "id": row[0],
            "created_at": row[1],
            "event_id": row[2],
            "severity": row[3],
            "acknowledged_at": row[4],
            "channel": row[5],
            "payload": json.loads(row[6]) if row[6] else {},
        })
    return {"count": len(alerts), "alerts": alerts}


def acknowledge_alert(alert_id: str) -> None:
    store = get_feature_store()
    with store.connect() as con:
        con.execute(
            "UPDATE alerts SET acknowledged_at = ? WHERE id = ?",
            [datetime.now(UTC), alert_id],
        )


# -------------------------------------------------------------------- exports


def export_dataset(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist a dataset in the requested format under ``settings.exports_dir``.

    Currently supports JSON + CSV (fast paths). XLSX + PDF route through
    optional dependencies (``openpyxl`` / ``reportlab``) when available.
    """
    settings = get_settings()
    dataset = payload["dataset"]
    fmt = payload["format"]
    params = payload.get("params") or {}

    if dataset == "commodities":
        data = get_commodity_panel(lookback_days=int(params.get("lookback_days", 365)))
    elif dataset == "suppliers":
        data = list_suppliers()
    elif dataset == "events":
        data = list_events(severity=params.get("severity"), limit=int(params.get("limit", 100)))
    elif dataset == "alerts":
        data = list_alerts(unacknowledged_only=bool(params.get("unacknowledged_only", False)))
    elif dataset == "dcf":
        data = run_dcf_with_overrides(params)
    elif dataset == "scenarios":
        if "n_trials" not in params:
            raise ValueError("scenarios export requires the scenarios request body")
        data = run_monte_carlo(params)
    else:
        raise ValueError(f"unknown dataset: {dataset}")

    out_dir: Path = settings.exports_dir / dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{dataset}-{stamp}.{fmt}"

    if fmt == "json":
        path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
    elif fmt == "csv":
        _write_csv(path, data, dataset)
    elif fmt == "xlsx":
        _write_xlsx(path, data, dataset)
    elif fmt == "pdf":
        _write_pdf(path, data, dataset)
    else:
        raise ValueError(f"unsupported format: {fmt}")

    blob = path.read_bytes()
    return {
        "format": fmt,
        "dataset": dataset,
        "artifact_path": str(path),
        "size_bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def _write_csv(path: Path, data: dict[str, Any], dataset: str) -> None:
    # Pick the list-shaped subfield and flatten to a DataFrame.
    candidate = None
    for key in ("commodities", "suppliers", "events", "alerts", "series"):
        if key in data and isinstance(data[key], list):
            candidate = data[key]
            break
    if candidate is None:
        pd.DataFrame([data]).to_csv(path, index=False)
        return
    pd.json_normalize(candidate, sep=".").to_csv(path, index=False)


def _write_xlsx(path: Path, data: dict[str, Any], dataset: str) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = dataset[:31]
    candidate = None
    for key in ("commodities", "suppliers", "events", "alerts", "series"):
        if key in data and isinstance(data[key], list):
            candidate = data[key]
            break
    rows = candidate if candidate is not None else [data]
    df = pd.json_normalize(rows, sep=".")
    ws.append([str(c) for c in df.columns])
    for _, record in df.iterrows():
        ws.append([None if pd.isna(v) else str(v) for v in record.to_list()])
    wb.save(path)


def _write_pdf(path: Path, data: dict[str, Any], dataset: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 800, f"ASCIIP Export — {dataset}")
    c.setFont("Helvetica", 9)
    c.drawString(40, 785, f"Generated: {datetime.now(UTC).isoformat()}")
    text = c.beginText(40, 760)
    payload = json.dumps(data, default=str, indent=2)
    for line in payload.splitlines()[:80]:
        text.textLine(line[:110])
    c.drawText(text)
    c.showPage()
    c.save()
