"""Supplier distress classifier — XGBoost binary model.

Label is the synthetic ``distress_score >= 0.5`` threshold (see
``synthetic.generate_suppliers``); on real data, the operator would swap
in a ground-truth distress flag from their vendor risk system.

Feature set (drawn from ``supplier_profile``):

* ``annual_spend_billions`` — concentration risk proxy
* ``otd_rate_90d``         — delivery-performance signal
* ``dpo_days``             — working-capital / cash-cycle signal
* ``revenue_concentration_top3`` — customer concentration
* tier (ordinal)
* category (one-hot)
* country (one-hot)

A calibrated ``isotonic`` sigmoid is layered on top of the raw XGBoost
probability so downstream consumers (Playbooks / Alerts severity) can
rely on probabilities that actually correspond to empirical frequencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from asciip_shared import get_logger

from asciip_data_pipeline.features import get_feature_store
from asciip_ml_models.registry import ModelRegistration, get_registry


FEATURE_COLUMNS: tuple[str, ...] = (
    "annual_spend_billions",
    "otd_rate_90d",
    "dpo_days",
    "revenue_concentration_top3",
    "tier",
)

CATEGORICAL_COLUMNS: tuple[str, ...] = ("category", "country")


@dataclass(frozen=True)
class DistressModel:
    estimator: CalibratedClassifierCV
    feature_names: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    categorical_levels: dict[str, tuple[str, ...]]
    version: str

    def _featurise(self, rows: list[dict[str, object]]) -> np.ndarray:
        frame = pd.DataFrame(rows)
        frame = _one_hot(frame, self.categorical_levels)
        ordered = frame.reindex(columns=self.feature_names, fill_value=0.0)
        return ordered.to_numpy(dtype=np.float64, copy=False)

    def predict_proba(self, rows: list[dict[str, object]]) -> np.ndarray:
        X = self._featurise(rows)
        return self.estimator.predict_proba(X)[:, 1]


@dataclass(frozen=True)
class DistressTrainingResult:
    model: DistressModel
    roc_auc: float
    pr_auc: float
    brier: float
    n_samples: int
    n_positive: int
    registry_id: str = ""


# --------------------------------------------------------------------------- data


def _load_supplier_frame() -> pd.DataFrame:
    store = get_feature_store()
    with store.connect() as con:
        df = con.execute(
            "SELECT * FROM src_apple_supplier_pdf"
        ).fetch_df()
    if df.empty:
        raise ValueError("supplier frame is empty — did you run the orchestrator?")
    return df


def _one_hot(frame: pd.DataFrame, levels: dict[str, tuple[str, ...]]) -> pd.DataFrame:
    out = frame.copy()
    for col, col_levels in levels.items():
        for level in col_levels:
            out[f"{col}__{level}"] = (out.get(col) == level).astype(float)
    return out


# --------------------------------------------------------------------------- train


def train_distress_classifier(
    *,
    version: str | None = None,
    register: bool = True,
    promote: bool = True,
    distress_threshold: float = 0.5,
) -> DistressTrainingResult:
    log = get_logger("asciip.ml.distress")
    df = _load_supplier_frame()

    if "distress_score" not in df.columns:
        raise ValueError("supplier frame lacks a `distress_score` column")
    y = (df["distress_score"].astype(float) >= distress_threshold).astype(int).to_numpy()
    if y.sum() < 5 or (len(y) - y.sum()) < 5:
        raise ValueError(
            f"need at least 5 positive and 5 negative samples, got "
            f"{int(y.sum())} positives / {int(len(y) - y.sum())} negatives"
        )

    # Capture categorical levels so inference can rebuild the same design matrix.
    categorical_levels: dict[str, tuple[str, ...]] = {}
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            categorical_levels[col] = tuple(sorted(df[col].dropna().unique().tolist()))
    ohe = _one_hot(df, categorical_levels)

    numeric = list(FEATURE_COLUMNS)
    feature_names = tuple(
        numeric + [
            f"{col}__{level}"
            for col, levels in categorical_levels.items()
            for level in levels
        ]
    )
    X = ohe.reindex(columns=feature_names, fill_value=0.0).to_numpy(dtype=np.float64)

    # Stratified 5-fold CV for both evaluation and isotonic calibration.
    cv = StratifiedKFold(n_splits=min(5, max(2, y.sum(), len(y) - y.sum())), shuffle=True, random_state=20250101)

    base = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        random_state=20250101,
    )
    calibrated = CalibratedClassifierCV(estimator=base, method="isotonic", cv=cv)
    calibrated.fit(X, y)
    proba = calibrated.predict_proba(X)[:, 1]

    roc_auc = float(roc_auc_score(y, proba))
    pr_auc = float(average_precision_score(y, proba))
    brier = float(brier_score_loss(y, proba))

    model = DistressModel(
        estimator=calibrated,
        feature_names=feature_names,
        numeric_columns=tuple(numeric),
        categorical_levels=categorical_levels,
        version=version or datetime.now(UTC).strftime("v%Y%m%d-%H%M%S"),
    )
    log.info(
        "distress.trained",
        n=len(y),
        n_positive=int(y.sum()),
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        brier=brier,
    )

    result = DistressTrainingResult(
        model=model,
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        brier=brier,
        n_samples=int(len(y)),
        n_positive=int(y.sum()),
    )

    if register:
        record = get_registry().register(
            ModelRegistration(
                family="supplier_distress_classifier",
                version=model.version,
                estimator=model,
                metrics={
                    "roc_auc": roc_auc,
                    "pr_auc": pr_auc,
                    "brier": brier,
                    "n_samples": int(len(y)),
                    "n_positive": int(y.sum()),
                },
                hyperparameters={
                    "xgb": {
                        "n_estimators": 300,
                        "max_depth": 4,
                        "learning_rate": 0.05,
                    },
                    "calibration": "isotonic",
                    "feature_names": list(feature_names),
                    "distress_threshold": distress_threshold,
                },
                notes="Isotonic-calibrated XGBoost on Apple supplier features.",
                promote_to_production=promote,
            )
        )
        return DistressTrainingResult(**{**result.__dict__, "registry_id": record.id})
    return result


def load_production() -> DistressModel | None:
    record = get_registry().get_production("supplier_distress_classifier")
    return record.load() if record else None
