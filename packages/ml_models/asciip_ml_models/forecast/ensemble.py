"""Commodity price ensemble forecaster.

Combines:

* **ARIMA(p,1,q)** — captures short-horizon autoregressive structure with
  drift. Order selected by AIC over a small grid.
* **LightGBM** — captures non-linear autocorrelations and cross-commodity
  leading indicators via lag features (own + sibling commodities).
* **Prophet** (optional) — seasonal + trend decomposition when the
  ``prophet`` extra is installed. Skipped gracefully otherwise.

The ensemble forecast is an inverse-variance weighted average of
available members, with weights derived from rolling out-of-sample MAE
on the last 20% of the training window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Sequence

import numpy as np
import pandas as pd

from asciip_shared import get_logger

from asciip_data_pipeline.features import get_feature_store
from asciip_ml_models.registry import ModelRegistration, get_registry

try:  # pragma: no cover — optional dependency
    from prophet import Prophet  # type: ignore

    _HAS_PROPHET = True
except Exception:  # pragma: no cover
    Prophet = None  # type: ignore
    _HAS_PROPHET = False


@dataclass(frozen=True)
class ForecastConfig:
    commodity: str                          # entity_id in features_wide
    horizon_days: int = 30
    sibling_commodities: tuple[str, ...] = ()
    arima_orders: tuple[tuple[int, int, int], ...] = (
        (0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 2),
    )
    lightgbm_lags: tuple[int, ...] = (1, 2, 3, 5, 7, 14, 21)
    val_fraction: float = 0.20
    use_prophet: bool = True
    register: bool = True
    promote: bool = True


@dataclass(frozen=True)
class ForecastResult:
    config: ForecastConfig
    history_index: tuple[pd.Timestamp, ...]
    history_values: tuple[float, ...]
    forecast_index: tuple[pd.Timestamp, ...]
    forecast_mean: tuple[float, ...]
    forecast_lower: tuple[float, ...]
    forecast_upper: tuple[float, ...]
    member_weights: dict[str, float]
    member_val_mae: dict[str, float]
    registry_id: str = ""


# --------------------------------------------------------------------------- data


def _load_history(commodity: str) -> pd.Series:
    store = get_feature_store()
    with store.connect() as con:
        rows = con.execute(
            "SELECT as_of_ts, feature_value FROM features_wide "
            "WHERE feature_name = 'commodity_price' AND entity_id = ? "
            "AND feature_value IS NOT NULL "
            "ORDER BY as_of_ts",
            [commodity],
        ).fetchall()
    if len(rows) < 60:
        raise ValueError(
            f"commodity {commodity!r}: need ≥60 observations, got {len(rows)}"
        )
    idx = pd.DatetimeIndex([r[0] for r in rows]).normalize()
    values = pd.Series([float(r[1]) for r in rows], index=idx, name=commodity)
    # Deduplicate by calendar date (keep last) and forward-fill any gaps.
    values = values.groupby(values.index).last()
    full_range = pd.date_range(values.index.min(), values.index.max(), freq="D")
    return values.reindex(full_range).ffill()


def _load_sibling_frame(commodities: Sequence[str]) -> pd.DataFrame:
    if not commodities:
        return pd.DataFrame()
    frames = [_load_history(c).rename(c) for c in commodities]
    return pd.concat(frames, axis=1).ffill()


# --------------------------------------------------------------------------- members


def _fit_arima(series: pd.Series, orders, horizon: int):
    from statsmodels.tsa.arima.model import ARIMA  # lazy

    best_aic = float("inf")
    best_model = None
    best_order = None
    for order in orders:
        try:
            model = ARIMA(series, order=order).fit()
        except Exception:  # pragma: no cover — convergence failures
            continue
        if model.aic < best_aic:
            best_aic = model.aic
            best_model = model
            best_order = order
    if best_model is None:
        raise RuntimeError("no ARIMA order converged")
    forecast = best_model.get_forecast(steps=horizon)
    mean = forecast.predicted_mean.to_numpy()
    ci = forecast.conf_int(alpha=0.20).to_numpy()  # 80% CI
    return mean, ci[:, 0], ci[:, 1], best_order


def _build_supervised_frame(
    target: pd.Series,
    siblings: pd.DataFrame,
    lags: Sequence[int],
) -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.DataFrame({"target": target})
    for lag in lags:
        frame[f"lag_{lag}"] = target.shift(lag)
    # Simple calendar features.
    frame["dow"] = target.index.dayofweek
    frame["month"] = target.index.month
    # Sibling lag-1 features capture leading indicators.
    for col in siblings.columns:
        frame[f"sib_{col}_lag1"] = siblings[col].shift(1)
    frame = frame.dropna()
    y = frame.pop("target")
    return frame, y


def _fit_lightgbm(series: pd.Series, siblings: pd.DataFrame, lags, horizon: int):
    import lightgbm as lgb

    X, y = _build_supervised_frame(series, siblings, lags)
    if len(X) < 30:
        raise RuntimeError("not enough rows for lightgbm after lagging")

    params = {
        "objective": "regression",
        "metric": "mae",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 3,
        "verbose": -1,
    }
    train_set = lgb.Dataset(X, label=y)
    booster = lgb.train(params, train_set, num_boost_round=200)

    # Recursive h-step forecast.
    last = series.copy()
    sib = siblings.copy()
    preds: list[float] = []
    for _ in range(horizon):
        next_idx = last.index[-1] + pd.Timedelta(days=1)
        row = {"dow": next_idx.dayofweek, "month": next_idx.month}
        for lag in lags:
            row[f"lag_{lag}"] = float(last.iloc[-lag])
        for col in sib.columns:
            row[f"sib_{col}_lag1"] = float(sib[col].iloc[-1])
        x_next = pd.DataFrame([row], index=[next_idx], columns=X.columns)
        pred = float(booster.predict(x_next)[0])
        preds.append(pred)
        last.loc[next_idx] = pred
        # Keep siblings flat — we do not forecast them here.
        if not sib.empty:
            sib.loc[next_idx] = sib.iloc[-1].values
    preds_arr = np.array(preds, dtype=np.float64)
    # Bootstrap-free interval: use residual std on training fit.
    resid_std = float(np.std(y - booster.predict(X)))
    lower = preds_arr - 1.28 * resid_std
    upper = preds_arr + 1.28 * resid_std
    return preds_arr, lower, upper, booster


def _fit_prophet(series: pd.Series, horizon: int):  # pragma: no cover
    if not _HAS_PROPHET:
        raise RuntimeError("prophet is not installed")
    frame = series.reset_index()
    frame.columns = ["ds", "y"]
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        interval_width=0.80,
    )
    model.fit(frame)
    future = model.make_future_dataframe(periods=horizon, freq="D")
    forecast = model.predict(future).tail(horizon)
    return (
        forecast["yhat"].to_numpy(),
        forecast["yhat_lower"].to_numpy(),
        forecast["yhat_upper"].to_numpy(),
    )


# --------------------------------------------------------------------------- train


def _eval_val_mae(
    series: pd.Series,
    siblings: pd.DataFrame,
    config: ForecastConfig,
) -> dict[str, float]:
    split = int(len(series) * (1 - config.val_fraction))
    split = max(split, 60)
    train = series.iloc[:split]
    val = series.iloc[split:]
    siblings_tr = siblings.iloc[:split] if not siblings.empty else siblings
    maes: dict[str, float] = {}
    horizon = len(val)
    if horizon <= 0:
        return maes

    # ARIMA
    try:
        a_mean, _, _, _ = _fit_arima(train, config.arima_orders, horizon)
        maes["arima"] = float(np.mean(np.abs(val.to_numpy() - a_mean)))
    except Exception:
        pass
    # LightGBM
    try:
        l_mean, _, _, _ = _fit_lightgbm(train, siblings_tr, config.lightgbm_lags, horizon)
        maes["lightgbm"] = float(np.mean(np.abs(val.to_numpy() - l_mean)))
    except Exception:
        pass
    # Prophet
    if config.use_prophet and _HAS_PROPHET:
        try:
            p_mean, _, _ = _fit_prophet(train, horizon)
            maes["prophet"] = float(np.mean(np.abs(val.to_numpy() - p_mean)))
        except Exception:  # pragma: no cover
            pass
    return maes


def _weights_from_mae(mae: dict[str, float]) -> dict[str, float]:
    if not mae:
        return {}
    inv = {k: 1.0 / max(v, 1e-6) for k, v in mae.items()}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()}


def train_commodity_ensemble(config: ForecastConfig) -> ForecastResult:
    log = get_logger("asciip.ml.forecast")
    series = _load_history(config.commodity)
    siblings = _load_sibling_frame(config.sibling_commodities)

    val_mae = _eval_val_mae(series, siblings, config)
    weights = _weights_from_mae(val_mae)
    if not weights:
        raise RuntimeError("no forecaster member succeeded on validation split")

    horizon = config.horizon_days
    fut_index = pd.date_range(
        series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )

    mean_stack: list[np.ndarray] = []
    lower_stack: list[np.ndarray] = []
    upper_stack: list[np.ndarray] = []
    w_ordered: list[float] = []

    if "arima" in weights:
        mean, lo, hi, _ = _fit_arima(series, config.arima_orders, horizon)
        mean_stack.append(mean); lower_stack.append(lo); upper_stack.append(hi)
        w_ordered.append(weights["arima"])
    if "lightgbm" in weights:
        mean, lo, hi, _ = _fit_lightgbm(series, siblings, config.lightgbm_lags, horizon)
        mean_stack.append(mean); lower_stack.append(lo); upper_stack.append(hi)
        w_ordered.append(weights["lightgbm"])
    if "prophet" in weights:  # pragma: no cover — optional
        mean, lo, hi = _fit_prophet(series, horizon)
        mean_stack.append(mean); lower_stack.append(lo); upper_stack.append(hi)
        w_ordered.append(weights["prophet"])

    W = np.array(w_ordered, dtype=np.float64)
    W = W / W.sum()
    stacked_mean = np.tensordot(W, np.stack(mean_stack), axes=1)
    stacked_lower = np.tensordot(W, np.stack(lower_stack), axes=1)
    stacked_upper = np.tensordot(W, np.stack(upper_stack), axes=1)

    result = ForecastResult(
        config=config,
        history_index=tuple(series.index),
        history_values=tuple(float(v) for v in series.to_numpy()),
        forecast_index=tuple(fut_index),
        forecast_mean=tuple(float(v) for v in stacked_mean),
        forecast_lower=tuple(float(v) for v in stacked_lower),
        forecast_upper=tuple(float(v) for v in stacked_upper),
        member_weights=weights,
        member_val_mae=val_mae,
    )

    log.info(
        "forecast.trained",
        commodity=config.commodity,
        horizon=horizon,
        members=list(weights.keys()),
        weights=weights,
        val_mae=val_mae,
    )

    if config.register:
        record = get_registry().register(
            ModelRegistration(
                family=f"commodity_forecast_ensemble:{config.commodity}",
                version=datetime.now(UTC).strftime("v%Y%m%d-%H%M%S"),
                estimator=None,  # the fitted booster is re-trained per call
                metrics={
                    "members": list(weights.keys()),
                    "val_mae": val_mae,
                    "weights": weights,
                    "horizon_days": horizon,
                    "history_points": len(series),
                },
                hyperparameters={
                    "arima_orders": [list(o) for o in config.arima_orders],
                    "lightgbm_lags": list(config.lightgbm_lags),
                    "val_fraction": config.val_fraction,
                    "sibling_commodities": list(config.sibling_commodities),
                    "prophet_available": _HAS_PROPHET,
                },
                notes="ARIMA+LightGBM[+Prophet] commodity forecaster.",
                promote_to_production=config.promote,
            )
        )
        return ForecastResult(**{**result.__dict__, "registry_id": record.id})

    return result
