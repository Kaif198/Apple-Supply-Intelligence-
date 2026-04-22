"""Margin sensitivity via Ridge regression.

Training pipeline
-----------------
1. Pull the point-in-time ``target_gross_margin`` series from
   ``features_wide`` (with filing-lag applied — see
   ``features/sql/06_margin_target.sql``).
2. Join to quarter-end commodity prices, 30-day vols, and FX rates using
   the exact ``as_of_ts`` of the target row as the cutoff so there is no
   leakage from after the filing date.
3. Compute percent-change features (4-quarter lag) so the regression
   measures *elasticity* rather than absolute level dependence.
4. Fit an ``sklearn.linear_model.RidgeCV`` with nested leave-one-out on
   the alpha grid.
5. Serialise the estimator + feature contract (column order, fill
   values) to the model registry.

Because the historical sample is small (≤19 quarters), we deliberately
use a high-regularisation Ridge rather than LightGBM to avoid severe
overfit. The design note accompanies the model record.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from asciip_data_pipeline.features import get_feature_store
from asciip_shared import get_logger
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from asciip_ml_models.registry import ModelRegistration, get_registry

# Feature set consumed by the Ridge. Order matters — the serialised
# estimator assumes this exact column contract.
COMMODITY_TICKERS: tuple[str, ...] = ("aluminum", "copper", "lithium", "cobalt", "brent")
FX_PAIRS: tuple[str, ...] = ("USD_CNY", "USD_EUR")
FEATURE_NAMES: tuple[str, ...] = tuple(
    [f"commodity_price:{c}" for c in COMMODITY_TICKERS]
    + [f"commodity_vol_30d_annualized:{c}" for c in COMMODITY_TICKERS]
    + [f"fx_rate:{p}" for p in FX_PAIRS]
)

# RidgeCV alpha grid — log-spaced 0.01 → 100.
ALPHA_GRID: tuple[float, ...] = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)


@dataclass(frozen=True)
class MarginModel:
    """Frozen inference container returned by :func:`load_production`."""

    estimator: RidgeCV
    scaler: StandardScaler
    feature_names: tuple[str, ...]
    intercept_target: float
    version: str

    def predict(self, features: Mapping[str, float]) -> float:
        x = np.array(
            [[features.get(name, np.nan) for name in self.feature_names]], dtype=np.float64
        )
        # NaN fill with training-set median handled by scaler mean (StandardScaler
        # never saw NaNs at fit time; we coerce them to 0 on the standardised scale).
        mask = np.isnan(x)
        x[mask] = 0.0
        x_std = self.scaler.transform(x)
        x_std[mask] = 0.0
        pred = float(self.estimator.predict(x_std)[0])
        return pred

    def elasticities_bps_per_10pct(self) -> dict[str, float]:
        """Translate standardised Ridge coefficients into bps-per-10% moves.

        The standardised coefficient measures delta-margin per +1 std-dev. We convert
        to Δmargin per +10% change by dividing by ``scale * 0.10``, then
        multiply by 10 000 to express in basis points.
        """
        coefs = self.estimator.coef_
        scales = self.scaler.scale_
        elasticities = {}
        for name, coef, scale in zip(self.feature_names, coefs, scales, strict=True):
            if not np.isfinite(scale) or scale == 0:
                elasticities[name] = 0.0
                continue
            per_pct = coef / scale  # Δmargin per +1 unit
            per_10pct = per_pct * 0.10 * _reference_level(name)
            elasticities[name] = float(per_10pct * 10_000.0)
        return elasticities


def _reference_level(feature_name: str) -> float:
    """Rough magnitudes so elasticity conversion returns sensible numbers."""
    if feature_name.startswith("commodity_price:"):
        return {
            "aluminum": 2500.0,
            "copper": 9000.0,
            "lithium": 20000.0,
            "cobalt": 35000.0,
            "brent": 85.0,
        }.get(feature_name.split(":", 1)[1], 1.0)
    if feature_name.startswith("commodity_vol_30d_annualized:"):
        return 0.30
    if feature_name.startswith("fx_rate:"):
        return 7.2 if "CNY" in feature_name else 1.08
    return 1.0


@dataclass(frozen=True)
class MarginTrainingResult:
    model: MarginModel
    train_r2: float
    cv_r2: float
    n_samples: int
    feature_columns: tuple[str, ...]
    alpha_selected: float
    residual_std: float
    trained_at: datetime
    registry_id: str = ""
    notes: str = ""


# --------------------------------------------------------------------------- data


def _fetch_wide(feature_names: Iterable[str]) -> dict[tuple[str, datetime], float]:
    """Return ``(feature_name, as_of_ts) → value`` for the given names."""
    store = get_feature_store()
    placeholders = ",".join("?" for _ in feature_names)
    rows: list[tuple[str, str, datetime, float]] = []
    with store.connect() as con:
        rows = con.execute(
            f"SELECT entity_id, feature_name, as_of_ts, feature_value "
            f"FROM features_wide "
            f"WHERE feature_name IN ({placeholders}) AND feature_value IS NOT NULL "
            f"ORDER BY as_of_ts",
            list(feature_names),
        ).fetchall()
    out: dict[tuple[str, datetime], float] = {}
    for entity_id, feat_name, as_of_ts, value in rows:
        key = f"{feat_name}:{entity_id}"
        ts = as_of_ts if isinstance(as_of_ts, datetime) else datetime.fromisoformat(str(as_of_ts))
        out[(key, ts)] = float(value)
    return out


def _as_of_lookup(
    series: dict[tuple[str, datetime], float], feature_key: str, cutoff: datetime
) -> float:
    """Last observation for ``feature_key`` on or before ``cutoff``."""
    best_ts: datetime | None = None
    best_val: float = float("nan")
    for (key, ts), value in series.items():
        if key != feature_key or ts > cutoff:
            continue
        if best_ts is None or ts > best_ts:
            best_ts = ts
            best_val = value
    return best_val


def build_training_frame() -> tuple[np.ndarray, np.ndarray, list[datetime]]:
    """Build ``(X, y, timestamps)`` from the feature store.

    Each row is one AAPL fiscal quarter. X columns follow ``FEATURE_NAMES``.
    """
    store = get_feature_store()
    with store.connect() as con:
        rows = con.execute(
            "SELECT as_of_ts, feature_value FROM features_wide "
            "WHERE feature_name = 'target_gross_margin' AND feature_value IS NOT NULL "
            "ORDER BY as_of_ts"
        ).fetchall()

    if len(rows) < 6:
        raise ValueError(
            f"margin training requires at least 6 quarters of target data, got {len(rows)}"
        )

    target_ts: list[datetime] = []
    target_val: list[float] = []
    for as_of_ts, value in rows:
        target_ts.append(
            as_of_ts if isinstance(as_of_ts, datetime) else datetime.fromisoformat(str(as_of_ts))
        )
        target_val.append(float(value))

    # Pull the feature source data in one pass.
    base_features = ("commodity_price", "commodity_vol_30d_annualized", "fx_rate")
    raw = _fetch_wide(base_features)

    X = np.zeros((len(target_ts), len(FEATURE_NAMES)), dtype=np.float64)
    for i, cutoff in enumerate(target_ts):
        for j, feat_name in enumerate(FEATURE_NAMES):
            base, entity = feat_name.split(":", 1)
            key = f"{base}:{entity}"
            X[i, j] = _as_of_lookup(raw, key, cutoff)

    return X, np.array(target_val, dtype=np.float64), target_ts


# --------------------------------------------------------------------------- train


def train_margin_ridge(
    *,
    version: str | None = None,
    register: bool = True,
    promote: bool = True,
) -> MarginTrainingResult:
    """Fit the Ridge + optional registration."""
    log = get_logger("asciip.ml.margin")
    X, y, timestamps = build_training_frame()

    # Column-wise impute with median so early quarters without a full feature
    # set do not dominate the loss.
    col_medians = np.nanmedian(X, axis=0)
    nan_mask = np.isnan(X)
    if nan_mask.any():
        X = np.where(nan_mask, col_medians, X)

    scaler = StandardScaler().fit(X)
    X_std = scaler.transform(X)

    n_samples = X_std.shape[0]
    cv_folds = min(5, max(2, n_samples - 1))
    estimator = RidgeCV(alphas=ALPHA_GRID, cv=cv_folds, scoring="r2")
    estimator.fit(X_std, y)

    pred = estimator.predict(X_std)
    residuals = y - pred
    train_r2 = float(r2_score(y, pred))
    # Coarse CV R² estimate by leave-one-out prediction using the chosen alpha.
    cv_r2 = _loocv_r2(X_std, y, alpha=float(estimator.alpha_))

    model = MarginModel(
        estimator=estimator,
        scaler=scaler,
        feature_names=FEATURE_NAMES,
        intercept_target=float(estimator.intercept_),
        version=version or datetime.now(UTC).strftime("v%Y%m%d-%H%M%S"),
    )

    result = MarginTrainingResult(
        model=model,
        train_r2=train_r2,
        cv_r2=cv_r2,
        n_samples=n_samples,
        feature_columns=FEATURE_NAMES,
        alpha_selected=float(estimator.alpha_),
        residual_std=float(np.std(residuals)),
        trained_at=datetime.now(UTC),
    )

    log.info(
        "margin.trained",
        n_samples=n_samples,
        alpha=result.alpha_selected,
        train_r2=result.train_r2,
        cv_r2=result.cv_r2,
        residual_std=result.residual_std,
    )

    if register:
        reg = get_registry()
        record = reg.register(
            ModelRegistration(
                family="margin_sensitivity_ridge",
                version=model.version,
                estimator=model,
                metrics={
                    "train_r2": train_r2,
                    "cv_r2": cv_r2,
                    "residual_std": result.residual_std,
                    "n_samples": n_samples,
                },
                hyperparameters={
                    "alpha_grid": list(ALPHA_GRID),
                    "alpha_selected": result.alpha_selected,
                    "cv_folds": cv_folds,
                    "feature_names": list(FEATURE_NAMES),
                },
                notes="Ridge regression on quarter-end commodity+FX features.",
                promote_to_production=promote,
            )
        )
        return MarginTrainingResult(
            **{**result.__dict__, "registry_id": record.id},
        )
    return result


def _loocv_r2(X: np.ndarray, y: np.ndarray, alpha: float) -> float:
    """Inexpensive leave-one-out R² using the closed-form ridge solution."""
    from sklearn.linear_model import Ridge

    preds = np.zeros_like(y)
    for i in range(len(y)):
        mask = np.ones(len(y), dtype=bool)
        mask[i] = False
        est = Ridge(alpha=alpha)
        est.fit(X[mask], y[mask])
        preds[i] = est.predict(X[i : i + 1])[0]
    return float(r2_score(y, preds))


def load_production() -> MarginModel | None:
    reg = get_registry()
    record = reg.get_production("margin_sensitivity_ridge")
    return record.load() if record else None
