"""AAPL factor regression with HAC (Newey-West) standard errors.

Factors
-------
* ``market`` — daily log return of the broad market proxy (currently
  approximated by AAPL's own return minus its trailing mean, which gives
  us a single-factor CAPM-lite; this is the place to plug in SPY when the
  Yahoo adapter is extended to pull index data).
* ``commodity_stress`` — cross-sectionally standardised average
  commodity log return (negative sign → positive stress). Captures COGS
  pressure on Apple gross margin.
* ``fx_stress`` — change in USD/CNY minus the trailing 20d mean.
* ``supplier_stress`` — fraction of suppliers with ``distress_score>=0.5``
  at the reporting date (recomputed on the fly from ``supplier_profile``).

All factors are lagged by one trading day so the regression coefficients
can be interpreted as *predictive* elasticities without lookahead bias.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm
from asciip_data_pipeline.features import get_feature_store
from asciip_shared import get_logger

from asciip_ml_models.registry import ModelRegistration, get_registry

FACTOR_NAMES: tuple[str, ...] = (
    "market",
    "commodity_stress",
    "fx_stress",
    "supplier_stress",
)


@dataclass(frozen=True)
class FactorModel:
    params: dict[str, float]
    bse: dict[str, float]
    tvalues: dict[str, float]
    pvalues: dict[str, float]
    r_squared: float
    adj_r_squared: float
    n_obs: int
    factor_names: tuple[str, ...]
    version: str

    def predict(self, factor_values: dict[str, float]) -> float:
        return float(
            self.params.get("const", 0.0)
            + sum(self.params.get(n, 0.0) * factor_values.get(n, 0.0) for n in self.factor_names)
        )


@dataclass(frozen=True)
class FactorTrainingResult:
    model: FactorModel
    registry_id: str = ""


# --------------------------------------------------------------------------- data


def _load_series(feature_name: str, entity_id: str | None = None) -> pd.Series:
    store = get_feature_store()
    with store.connect() as con:
        if entity_id is None:
            rows = con.execute(
                "SELECT as_of_ts, feature_value FROM features_wide "
                "WHERE feature_name = ? AND feature_value IS NOT NULL ORDER BY as_of_ts",
                [feature_name],
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT as_of_ts, feature_value FROM features_wide "
                "WHERE feature_name = ? AND entity_id = ? AND feature_value IS NOT NULL "
                "ORDER BY as_of_ts",
                [feature_name, entity_id],
            ).fetchall()
    if not rows:
        return pd.Series(dtype=np.float64)
    idx = pd.DatetimeIndex([r[0] for r in rows]).normalize()
    return pd.Series([float(r[1]) for r in rows], index=idx).groupby(level=0).last()


def _load_supplier_stress() -> pd.Series:
    """One scalar per day: fraction of distressed suppliers.

    For the v1 feature store we only store a single snapshot of supplier
    profiles, so we broadcast that scalar across the training index.
    """
    store = get_feature_store()
    with store.connect() as con:
        row = con.execute(
            "SELECT AVG(CASE WHEN distress_score >= 0.5 THEN 1.0 ELSE 0.0 END) "
            "FROM src_apple_supplier_pdf"
        ).fetchone()
    scalar = float(row[0]) if row and row[0] is not None else 0.0
    return pd.Series({pd.Timestamp("1970-01-01"): scalar})


def _build_panel() -> pd.DataFrame:
    aapl = _load_series("aapl_log_return", entity_id="AAPL")
    if aapl.empty:
        raise ValueError("no AAPL returns available in features_wide")

    commodity_prices = {
        c: _load_series("commodity_price", entity_id=c)
        for c in ("aluminum", "copper", "lithium", "cobalt", "brent")
    }
    commodity_returns = pd.DataFrame(
        {c: np.log(s / s.shift(1)) for c, s in commodity_prices.items() if not s.empty}
    )
    commodity_stress = commodity_returns.mean(axis=1)  # mean log-return across basket
    commodity_stress_std = (commodity_stress - commodity_stress.rolling(60).mean()) / (
        commodity_stress.rolling(60).std() + 1e-9
    )

    fx = _load_series("fx_rate", entity_id="USD_CNY")
    fx_chg = np.log(fx / fx.shift(1)) if not fx.empty else pd.Series(dtype=np.float64)
    fx_stress = fx_chg - fx_chg.rolling(20).mean()

    supplier_stress = _load_supplier_stress()

    # Assemble into a single DataFrame on AAPL's trading-day index.
    panel = pd.DataFrame(index=aapl.index)
    panel["aapl_ret"] = aapl
    panel["market"] = aapl - aapl.rolling(60).mean()
    panel["commodity_stress"] = -commodity_stress_std  # positive = more stress
    panel["fx_stress"] = fx_stress
    panel["supplier_stress"] = float(supplier_stress.iloc[-1])

    # Lag every factor by one trading day.
    for col in FACTOR_NAMES:
        panel[col] = panel[col].shift(1)
    return panel.dropna()


# --------------------------------------------------------------------------- train


def train_factor_regression(
    *,
    hac_lags: int = 5,
    version: str | None = None,
    register: bool = True,
    promote: bool = True,
) -> FactorTrainingResult:
    log = get_logger("asciip.ml.factor")
    panel = _build_panel()
    if len(panel) < 60:
        raise ValueError(f"factor regression needs ≥60 rows, got {len(panel)}")

    y = panel["aapl_ret"].to_numpy(dtype=np.float64)
    X = panel[list(FACTOR_NAMES)].to_numpy(dtype=np.float64)
    X = sm.add_constant(X, has_constant="add")

    ols = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    names = ("const", *FACTOR_NAMES)

    model = FactorModel(
        params=dict(zip(names, ols.params.tolist(), strict=True)),
        bse=dict(zip(names, ols.bse.tolist(), strict=True)),
        tvalues=dict(zip(names, ols.tvalues.tolist(), strict=True)),
        pvalues=dict(zip(names, ols.pvalues.tolist(), strict=True)),
        r_squared=float(ols.rsquared),
        adj_r_squared=float(ols.rsquared_adj),
        n_obs=int(ols.nobs),
        factor_names=FACTOR_NAMES,
        version=version or datetime.now(UTC).strftime("v%Y%m%d-%H%M%S"),
    )
    log.info(
        "factor.trained",
        n_obs=model.n_obs,
        r2=model.r_squared,
        adj_r2=model.adj_r_squared,
        params=model.params,
    )

    if register:
        record = get_registry().register(
            ModelRegistration(
                family="aapl_factor_regression",
                version=model.version,
                estimator=model,
                metrics={
                    "r_squared": model.r_squared,
                    "adj_r_squared": model.adj_r_squared,
                    "n_obs": model.n_obs,
                    "params": model.params,
                    "pvalues": model.pvalues,
                },
                hyperparameters={
                    "factor_names": list(FACTOR_NAMES),
                    "hac_lags": hac_lags,
                    "lag_days": 1,
                },
                notes="OLS with HAC SE; factors lagged 1d for predictive reading.",
                promote_to_production=promote,
            )
        )
        return FactorTrainingResult(model=model, registry_id=record.id)
    return FactorTrainingResult(model=model)


def load_production() -> FactorModel | None:
    record = get_registry().get_production("aapl_factor_regression")
    return record.load() if record else None
